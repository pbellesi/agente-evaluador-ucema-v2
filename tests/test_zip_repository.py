import hashlib
import io
import stat
import struct
import sys
import types
import unittest
import zipfile

# El adaptador ZIP no usa red; el extractor comparte utilidades con GitHub.
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.get = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("La prueba ZIP no debe usar red")
    )
    sys.modules["requests"] = requests_stub

from src.evaluator_engine import _evaluate_repository_data, run_zip_evaluation
from src.github_fetcher import classify_path
from src.zip_repository import ZipRepositoryError, build_repository_data_from_zip


def zip_bytes(entries):
    """Crea ZIPs determinísticos para probar sólo la fuente de entrada."""
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, content in entries.items():
            info = zipfile.ZipInfo(path, date_time=(2026, 1, 1, 0, 0, 0))
            archive.writestr(info, content)
    return payload.getvalue()


def encrypted_flagged_zip(entries):
    """Marca el ZIP como cifrado sin requerir una herramienta externa."""
    raw = bytearray(zip_bytes(entries))
    for signature, offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        start = 0
        while True:
            index = raw.find(signature, start)
            if index < 0:
                break
            flags = struct.unpack_from("<H", raw, index + offset)[0] | 0x1
            struct.pack_into("<H", raw, index + offset, flags)
            start = index + len(signature)
    return bytes(raw)


def symlink_zip():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "README.md")
    return payload.getvalue()


class ZipRepositoryTests(unittest.TestCase):
    def test_valid_zip_with_direct_root_builds_repository_data(self):
        raw = zip_bytes({"README.md": "# Proyecto", "src/agent.py": "print('ok')"})
        data = build_repository_data_from_zip(raw, "proyecto.zip")
        self.assertEqual(sorted(data["file_contents"]), ["README.md", "src/agent.py"])
        self.assertEqual(data["evaluated_revision"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(data["retrieval_audit"]["source"], "ZIP")

    def test_single_wrapper_directory_is_normalized(self):
        raw = zip_bytes({"trabajo-final/README.md": "# Proyecto", "trabajo-final/src/agent.py": "print('ok')"})
        data = build_repository_data_from_zip(raw, "entrega.zip")
        self.assertIn("README.md", data["file_contents"])
        self.assertNotIn("trabajo-final/README.md", data["file_contents"])

    def test_corrupt_zip_is_rejected(self):
        with self.assertRaisesRegex(ZipRepositoryError, "corrupto"):
            build_repository_data_from_zip(b"no es un zip", "corrupto.zip")

    def test_invalid_zip_keeps_original_sha_as_traceable_revision(self):
        raw = b"no es un zip"
        result = run_zip_evaluation(raw, "corrupto.zip")
        self.assertEqual(result.evaluation_status, "access_error")
        self.assertEqual(result.evaluated_revision, hashlib.sha256(raw).hexdigest())

    def test_empty_zip_is_rejected(self):
        with self.assertRaisesRegex(ZipRepositoryError, "vacío"):
            build_repository_data_from_zip(zip_bytes({}), "vacio.zip")

    def test_zip_slip_is_rejected(self):
        with self.assertRaisesRegex(ZipRepositoryError, "insegura"):
            build_repository_data_from_zip(zip_bytes({"../../fuera.txt": "x"}), "ataque.zip")

    def test_absolute_path_is_rejected(self):
        with self.assertRaisesRegex(ZipRepositoryError, "absoluta"):
            build_repository_data_from_zip(zip_bytes({"/etc/passwd": "x"}), "absoluta.zip")

    def test_symlink_is_rejected(self):
        with self.assertRaisesRegex(ZipRepositoryError, "simbólico"):
            build_repository_data_from_zip(symlink_zip(), "symlink.zip")

    def test_encrypted_zip_is_rejected(self):
        with self.assertRaisesRegex(ZipRepositoryError, "cifrado"):
            build_repository_data_from_zip(encrypted_flagged_zip({"README.md": "x"}), "cifrado.zip")

    def test_nested_zip_is_not_extracted_recursively(self):
        inner = zip_bytes({"src/hidden.py": "print('never inspected')"})
        outer = zip_bytes({"README.md": "# Proyecto", "adjunto.zip": inner})
        data = build_repository_data_from_zip(outer, "externo.zip")
        self.assertNotIn("adjunto.zip", data["file_contents"])
        self.assertNotIn("src/hidden.py", data["file_contents"])

    def test_file_count_limit_is_enforced(self):
        raw = zip_bytes({f"docs/{index}.md": "x" for index in range(3)})
        with self.assertRaisesRegex(ZipRepositoryError, "cantidad máxima"):
            build_repository_data_from_zip(raw, "muchos.zip", max_files=2)

    def test_uncompressed_size_limits_are_enforced(self):
        raw = zip_bytes({"README.md": "x" * 11})
        with self.assertRaisesRegex(ZipRepositoryError, "archivo excede"):
            build_repository_data_from_zip(raw, "grande.zip", max_file_bytes=10)
        with self.assertRaisesRegex(ZipRepositoryError, "tamaño total"):
            build_repository_data_from_zip(raw, "total.zip", max_total_bytes=10)

    def test_same_zip_bytes_produce_same_sha_and_result(self):
        raw = zip_bytes({"README.md": "# Proyecto", "src/agent.py": "print('ok')"})
        first = build_repository_data_from_zip(raw, "proyecto.zip")
        second = build_repository_data_from_zip(raw, "proyecto.zip")
        self.assertEqual(first["evaluated_revision"], second["evaluated_revision"])
        self.assertEqual(_evaluate_repository_data(first).model_dump(), _evaluate_repository_data(second).model_dump())

    def test_zip_and_equivalent_repository_data_have_same_score(self):
        raw = zip_bytes({"README.md": "# Proyecto", "src/agent.py": "print('ok')"})
        zip_data = build_repository_data_from_zip(raw, "proyecto.zip")
        contents = dict(zip_data["file_contents"])
        equivalent = {
            "repository": "equivalente/local",
            "display_name": "equivalente",
            "branch": "local",
            "commit_sha": "local-sha",
            "evaluated_revision": "local-sha",
            "repository_inventory": [classify_path(path, len(content.encode("utf-8"))) for path, content in contents.items()],
            "file_contents": contents,
            "retrieval_audit": {},
        }
        zip_result = _evaluate_repository_data(zip_data)
        equivalent_result = _evaluate_repository_data(equivalent)
        self.assertEqual(zip_result.final_score, equivalent_result.final_score)
        self.assertEqual(
            [item.level_percent for item in zip_result.dimensions],
            [item.level_percent for item in equivalent_result.dimensions],
        )


if __name__ == "__main__":
    unittest.main()
