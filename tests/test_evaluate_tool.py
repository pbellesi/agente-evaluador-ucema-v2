import io
import json
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.get = lambda *args, **kwargs: None
    sys.modules["requests"] = requests_stub


from agente import evaluate_tool
from src.schema import DimensionResult, EvaluationResult


def completed_result() -> EvaluationResult:
    return EvaluationResult(
        repository="owner/repository",
        evaluated_revision="a" * 40,
        evaluation_date="2026-09-06",
        evaluation_status="completed",
        dimensions=[
            DimensionResult(
                dimension="Sistema completo y funcionando",
                weight=30,
                level_percent=75,
                score=22.5,
                evidence=["src/agent.py: llamada verificable"],
                justification="Evidencia suficiente para el nivel 75%.",
                missing_for_next_level="Agregar supervisión verificable.",
            )
        ],
        final_score=22.5,
        concrete_improvement="Agregar supervisión verificable.",
        integrity_notes=[],
    )


def access_error_result() -> EvaluationResult:
    return EvaluationResult(
        repository="owner/inaccessible",
        evaluated_revision="unknown",
        evaluation_date="2026-09-06",
        evaluation_status="access_error",
        dimensions=[],
        final_score=None,
        concrete_improvement="Verificar acceso.",
        integrity_notes=["[GITHUB_NOT_FOUND] Recurso no disponible."],
    )


class EvaluateToolTests(unittest.TestCase):
    def run_tool(self, args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = evaluate_tool.main(args)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_github_invokes_engine_once_and_writes_its_json(self):
        result = completed_result()
        url = "https://github.com/owner/repository"
        with patch.object(evaluate_tool, "run_evaluation", return_value=result) as run_evaluation:
            exit_code, stdout, stderr = self.run_tool(["--github", url])

        self.assertEqual(exit_code, 0)
        run_evaluation.assert_called_once_with(url)
        self.assertEqual(json.loads(stdout), result.model_dump(mode="json"))
        self.assertEqual(stderr, "")

    def test_zip_reads_bytes_preserves_filename_and_invokes_engine_once(self):
        result = completed_result()
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "trabajo.zip"
            zip_path.write_bytes(b"synthetic zip bytes")
            with patch.object(evaluate_tool, "run_zip_evaluation", return_value=result) as run_zip_evaluation:
                exit_code, stdout, _ = self.run_tool(["--zip", str(zip_path)])

        self.assertEqual(exit_code, 0)
        run_zip_evaluation.assert_called_once_with(b"synthetic zip bytes", "trabajo.zip")
        self.assertEqual(json.loads(stdout), result.model_dump(mode="json"))

    def test_access_error_is_retransmitted_without_inventing_scores_or_dimensions(self):
        result = access_error_result()
        with patch.object(evaluate_tool, "run_evaluation", return_value=result) as run_evaluation:
            exit_code, stdout, _ = self.run_tool(["--github", "https://github.com/owner/inaccessible"])

        payload = json.loads(stdout)
        self.assertEqual(exit_code, 0)
        run_evaluation.assert_called_once()
        self.assertEqual(payload, result.model_dump(mode="json"))
        self.assertEqual(payload["dimensions"], [])
        self.assertIsNone(payload["final_score"])

    def test_invalid_mutually_exclusive_arguments_return_exit_code_two(self):
        neither_code, neither_stdout, _ = self.run_tool([])
        both_code, both_stdout, _ = self.run_tool(["--github", "https://github.com/owner/repo", "--zip", "archivo.zip"])

        self.assertEqual(neither_code, 2)
        self.assertEqual(both_code, 2)
        self.assertEqual(neither_stdout, "")
        self.assertEqual(both_stdout, "")

    def test_missing_zip_returns_controlled_error_without_evaluation_json(self):
        exit_code, stdout, stderr = self.run_tool(["--zip", "does-not-exist.zip"])

        self.assertEqual(exit_code, 3)
        self.assertEqual(stdout, "")
        self.assertIn("ZIP", stderr)

    def test_unexpected_engine_exception_returns_exit_code_three_without_json(self):
        with patch.object(evaluate_tool, "run_evaluation", side_effect=RuntimeError("unexpected engine failure")):
            exit_code, stdout, stderr = self.run_tool(["--github", "https://github.com/owner/repo"])

        self.assertEqual(exit_code, 3)
        self.assertEqual(stdout, "")
        self.assertIn("inesperado", stderr.lower())

    def test_unexpected_engine_stdout_is_redirected_away_from_json_channel(self):
        result = completed_result()

        def noisy_engine(url):
            print("progreso inesperado")
            return result

        with patch.object(evaluate_tool, "run_evaluation", side_effect=noisy_engine) as run_evaluation:
            exit_code, stdout, stderr = self.run_tool(["--github", "https://github.com/owner/repo"])

        self.assertEqual(exit_code, 0)
        run_evaluation.assert_called_once()
        self.assertEqual(json.loads(stdout), result.model_dump(mode="json"))
        self.assertIn("progreso inesperado", stderr)


if __name__ == "__main__":
    unittest.main()
