"""Adaptador seguro de ZIP hacia la representación canónica de repositorio.

El módulo no ejecuta ni extrae archivos al sistema: sólo inspecciona miembros del
archivo ZIP en memoria y reutiliza el inventario/retrieval del evaluador.
"""

import hashlib
import io
import os
import re
import stat
import zipfile
from pathlib import PurePosixPath
from typing import Dict, List, Tuple

from src.github_fetcher import (
    CRITICAL_CATEGORIES,
    TRUNCATION_MARKER,
    _coverage,
    _decode_content,
    build_retrieval_plan,
    classify_path,
)


MAX_FILES = 2_000
MAX_TOTAL_BYTES = 50 * 1024 * 1024
MAX_FILE_BYTES = 10 * 1024 * 1024


class ZipRepositoryError(RuntimeError):
    """Error seguro y presentable de carga o estructura de ZIP."""


def _normalise_member_path(name: str) -> str:
    candidate = name.replace("\\", "/")
    if candidate.startswith("/") or candidate.startswith("\\") or re.match(r"^[a-zA-Z]:", candidate):
        raise ZipRepositoryError("El ZIP contiene una ruta absoluta no permitida.")
    path = PurePosixPath(candidate)
    if any(part == ".." for part in path.parts):
        raise ZipRepositoryError("El ZIP contiene una ruta insegura con '..'.")
    normalized = str(path).strip("/")
    if not normalized or normalized == ".":
        raise ZipRepositoryError("El ZIP contiene una ruta de archivo inválida.")
    return normalized


def _is_symlink(member: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK(member.external_attr >> 16)


def _validated_members(archive: zipfile.ZipFile, max_files: int, max_total_bytes: int, max_file_bytes: int) -> List[Tuple[zipfile.ZipInfo, str]]:
    members: List[Tuple[zipfile.ZipInfo, str]] = []
    total_size = 0
    for member in archive.infolist():
        if member.is_dir():
            continue
        if member.flag_bits & 0x1:
            raise ZipRepositoryError("El ZIP está cifrado o protegido con contraseña.")
        if _is_symlink(member):
            raise ZipRepositoryError("El ZIP contiene un enlace simbólico no permitido.")
        normalized = _normalise_member_path(member.filename)
        if member.file_size > max_file_bytes:
            raise ZipRepositoryError("Un archivo excede el tamaño máximo permitido.")
        total_size += member.file_size
        if total_size > max_total_bytes:
            raise ZipRepositoryError("El tamaño total descomprimido excede el límite permitido.")
        members.append((member, normalized))
        if len(members) > max_files:
            raise ZipRepositoryError("El ZIP excede la cantidad máxima de archivos permitida.")
    if not members:
        raise ZipRepositoryError("El ZIP está vacío.")
    return members


def _strip_single_root(members: List[Tuple[zipfile.ZipInfo, str]]) -> List[Tuple[zipfile.ZipInfo, str]]:
    paths = [path for _, path in members]
    root_parts = {path.split("/", 1)[0] for path in paths}
    has_only_nested_paths = all("/" in path for path in paths)
    if len(root_parts) != 1 or not has_only_nested_paths:
        return members
    root = next(iter(root_parts)) + "/"
    return [(member, path[len(root):]) for member, path in members]


def build_repository_data_from_zip(
    zip_bytes: bytes,
    filename: str,
    *,
    max_files: int = MAX_FILES,
    max_total_bytes: int = MAX_TOTAL_BYTES,
    max_file_bytes: int = MAX_FILE_BYTES,
    retrieval_config: dict | None = None,
) -> dict:
    """Convierte un ZIP validado en el mismo ``repo_data`` usado por GitHub.

    No escribe ni ejecuta miembros. Los archivos ZIP anidados se tratan como
    binarios normales y no se descomprimen recursivamente.
    """
    if not isinstance(zip_bytes, (bytes, bytearray)):
        raise ZipRepositoryError("El archivo cargado no es un ZIP válido.")
    safe_filename = os.path.basename(str(filename or "proyecto.zip")) or "proyecto.zip"
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            members = _strip_single_root(_validated_members(archive, max_files, max_total_bytes, max_file_bytes))
            member_by_path: Dict[str, zipfile.ZipInfo] = {}
            for member, path in members:
                if path in member_by_path:
                    raise ZipRepositoryError("El ZIP contiene rutas duplicadas después de normalizar su estructura.")
                member_by_path[path] = member

            inventory = sorted(
                [classify_path(path, member.file_size) for member, path in members],
                key=lambda record: record["path"].lower(),
            )
            plan = build_retrieval_plan(inventory, retrieval_config)
            if not plan["selected"]:
                raise ZipRepositoryError("La estructura del ZIP no contiene archivos de texto evaluables.")

            file_contents: Dict[str, str] = {}
            loaded_files: List[dict] = []
            truncated_files: List[dict] = []
            bytes_loaded = 0
            for selected in plan["selected"]:
                try:
                    raw_bytes = archive.read(member_by_path[selected["path"]])
                    truncated = len(raw_bytes) > selected["byte_limit"]
                    if truncated:
                        raw_bytes = raw_bytes[:max(0, selected["byte_limit"] - len(TRUNCATION_MARKER))] + TRUNCATION_MARKER
                    file_contents[selected["path"]] = _decode_content(raw_bytes)
                    item = {
                        "path": selected["path"], "size": selected["size"], "category": selected["category"],
                        "bytes_loaded": len(raw_bytes), "truncated": truncated, "selection_phase": selected["selection_phase"],
                    }
                    loaded_files.append(item)
                    bytes_loaded += len(raw_bytes)
                    if truncated:
                        truncated_files.append(item)
                except (RuntimeError, OSError, zipfile.BadZipFile) as error:
                    plan["skipped"].append({**selected, "reason": "read_error", "error": str(error)})
    except ZipRepositoryError:
        raise
    except (zipfile.BadZipFile, OSError, ValueError) as error:
        raise ZipRepositoryError("El archivo ZIP está corrupto o no puede leerse.") from error

    loaded_paths = set(file_contents)
    skipped_files = []
    for record in plan["skipped"]:
        clean = {key: value for key, value in record.items() if key not in {"byte_limit", "selection_phase", "error"}}
        if "error" in record:
            clean["error"] = record["error"]
        skipped_files.append(clean)
    skipped_files.sort(key=lambda record: record["path"].lower())

    categories = {}
    for category in (*CRITICAL_CATEGORIES, "other"):
        records = [record for record in inventory if record["category"] == category]
        categories[category] = {
            "discovered": len(records),
            "loaded": sum(record["path"] in loaded_paths for record in records),
            "skipped": sum(record["path"] not in loaded_paths for record in records),
            "bytes_loaded": sum(item["bytes_loaded"] for item in loaded_files if item["category"] == category),
        }

    zip_sha256 = hashlib.sha256(bytes(zip_bytes)).hexdigest()
    total_uncompressed_bytes = sum(member.file_size for member, _ in members)
    retrieval_audit = {
        "retrieval_version": "coverage-v1", "source": "ZIP", "source_filename": safe_filename,
        "zip_sha256": zip_sha256, "evaluated_revision": zip_sha256, "file_count": len(members),
        "total_uncompressed_bytes": total_uncompressed_bytes, "bytes_loaded": bytes_loaded,
        "discovered_count": len(inventory), "loaded_count": len(loaded_files), "skipped_count": len(skipped_files),
        "budget_bytes": plan["config"]["total_budget_bytes"], "categories": categories,
        "loaded_files": sorted(loaded_files, key=lambda item: item["path"].lower()),
        "skipped_files": skipped_files,
        "truncated_files": sorted(truncated_files, key=lambda item: item["path"].lower()),
        "critical_coverage": {
            "implementation": _coverage(inventory, loaded_paths, category="implementation"),
            "economics": _coverage(inventory, loaded_paths, label="economics"),
            "governance": _coverage(inventory, loaded_paths, label="governance"),
            "prompts": _coverage(inventory, loaded_paths, category="prompts"),
            "runs": _coverage(inventory, loaded_paths, category="runs"),
            "tests": _coverage(inventory, loaded_paths, category="tests"),
        },
    }
    tree_inventory = "\n".join(f"{record['path']} ({record['size']} bytes)" for record in inventory)
    formatted_parts = [f"=== TRABAJO EVALUADO: {safe_filename} ===", tree_inventory, "\n=== CONTENIDO DE ARCHIVOS INSPECCIONADOS ==="]
    for path in sorted(file_contents):
        formatted_parts.extend([f"\n--- ARCHIVO: {path} ---", file_contents[path]])
    return {
        "repository": f"ZIP::{safe_filename}", "display_name": safe_filename, "branch": "zip",
        "commit_sha": zip_sha256, "evaluated_revision": zip_sha256, "subpath": "",
        "repository_inventory": inventory, "tree_inventory": tree_inventory, "file_contents": file_contents,
        "skipped_files": skipped_files, "retrieval_audit": retrieval_audit,
        "formatted_context": "\n".join(formatted_parts),
    }
