import io
import json
import os
import tempfile
import unittest
import zipfile
from unittest.mock import MagicMock, patch

from agente import evaluate_v2
from src.semantic_schema import SemanticJudgePayload


class TestEvaluateV2CLI(unittest.TestCase):
    def setUp(self):
        self.sample_payload = SemanticJudgePayload(
            project_understanding={
                "system_summary": "Proyecto de prueba CLI",
                "architecture_observed": "Modular",
                "main_technologies": ["Python"],
            },
            findings=[
                {
                    "category": "implementation",
                    "severity": "info",
                    "files": ["main.py"],
                    "finding": "Código estructurado.",
                    "impact_on_evaluation": "Favorable",
                }
            ],
            dimension_evaluations={
                "D1": {"recommended_level": 75, "justification": "Código observable.", "missing_for_next_level": "Conector."},
                "D2": {"recommended_level": 50, "justification": "Doc básica.", "missing_for_next_level": "Más."},
                "D3": {"recommended_level": 100, "justification": "Reproducible.", "missing_for_next_level": None},
                "D4": {"recommended_level": 25, "justification": "Costos iniciales.", "missing_for_next_level": "Detalle."},
                "D5": {"recommended_level": 50, "justification": "Riesgos.", "missing_for_next_level": "Mitigación."},
            },
            concrete_improvement="Mejorar docs.",
        )

        # Crear un ZIP temporal con un proyecto mínimo
        self.temp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        with zipfile.ZipFile(self.temp_zip.name, "w") as zf:
            zf.writestr("README.md", "# Agente CLI\nDocumentación del proyecto.")
            zf.writestr("main.py", "print('hola')")
            zf.writestr("prompts/prompt.txt", "sos un bot")

    def tearDown(self):
        try:
            os.remove(self.temp_zip.name)
        except OSError:
            pass

    def test_missing_api_key_exits_with_error(self):
        with patch.dict(os.environ, {}, clear=True):
            stderr = io.StringIO()
            with patch("sys.stderr", stderr):
                exit_code = evaluate_v2.main(["--zip", self.temp_zip.name])
            self.assertEqual(exit_code, 2)
            self.assertIn("GEMINI_API_KEY", stderr.getvalue())

    def test_successful_evaluation_with_mock_judge(self):
        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = self.sample_payload

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            with patch("agente.evaluate_v2.GeminiSemanticJudge", return_value=mock_judge):
                with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                    exit_code = evaluate_v2.main(["--zip", self.temp_zip.name])

        self.assertEqual(exit_code, 0)
        output_json = json.loads(stdout.getvalue())
        self.assertEqual(output_json["evaluation_status"], "completed")
        self.assertEqual(len(output_json["dimensions"]), 5)
        self.assertAlmostEqual(output_json["final_score"], 61.25, places=2)


if __name__ == "__main__":
    unittest.main()
