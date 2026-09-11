import os
import unittest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from src.semantic_schema import SemanticJudgePayload
from src.semantic_judge import (
    SemanticJudge,
    MockSemanticJudge,
    GeminiSemanticJudge,
    SemanticJudgeConfigError,
    SemanticJudgeEvaluationError,
    resolve_gemini_model,
)


class TestSemanticJudge(unittest.TestCase):
    def setUp(self):
        self.sample_payload = SemanticJudgePayload(
            project_understanding={
                "system_summary": "Sistema de triage médico.",
                "architecture_observed": "Agente modular con herramientas.",
                "main_technologies": ["Python", "FastAPI"],
            },
            findings=[
                {
                    "category": "implementation",
                    "severity": "info",
                    "files": ["src/main.py"],
                    "finding": "Estructura modular completa.",
                    "impact_on_evaluation": "Favorable para D1.",
                }
            ],
            dimension_evaluations={
                "D1": {"recommended_level": 75, "justification": "Código y corridas reales.", "missing_for_next_level": "Conector."},
                "D2": {"recommended_level": 50, "justification": "Proceso documentado.", "missing_for_next_level": "Bitácora."},
                "D3": {"recommended_level": 100, "justification": "Reproducibilidad total.", "missing_for_next_level": None},
                "D4": {"recommended_level": 25, "justification": "Costos iniciales.", "missing_for_next_level": "Análisis."},
                "D5": {"recommended_level": 50, "justification": "Riesgos analizados.", "missing_for_next_level": "Supervisión."},
            },
            concrete_improvement="Incorporar modelo de proyección en docs/analisis_economico.md.",
        )
        self.sample_evidence_packet = {
            "repository_name": "usuario/agente-prueba",
            "full_prompt_context": "Contexto completo con inventario y contenido.",
        }

    def test_mock_judge_evaluates_without_network(self):
        judge = MockSemanticJudge(predefined_payload=self.sample_payload)
        self.assertIsInstance(judge, SemanticJudge)
        result = judge.evaluate(self.sample_evidence_packet)
        self.assertEqual(result.project_understanding.system_summary, "Sistema de triage médico.")
        self.assertEqual(judge.last_evidence_packet, self.sample_evidence_packet)

    def test_gemini_judge_missing_api_key_raises_config_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SemanticJudgeConfigError) as ctx:
                GeminiSemanticJudge(api_key=None)
            self.assertIn("GEMINI_API_KEY", str(ctx.exception))

    def test_resolve_gemini_model_priority(self):
        # 1. Sin GEMINI_MODEL -> usa DEFAULT_MODEL
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_gemini_model(), GeminiSemanticJudge.DEFAULT_MODEL)
            self.assertEqual(resolve_gemini_model(None), "gemini-3.8-flash")

        # 2. Con GEMINI_MODEL=gemini-3.6-flash -> usa gemini-3.6-flash
        with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3.6-flash"}, clear=True):
            self.assertEqual(resolve_gemini_model(), "gemini-3.6-flash")
            self.assertEqual(resolve_gemini_model(None), "gemini-3.6-flash")

        # 3. Parámetro explícito -> tiene prioridad sobre env
        with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3.6-flash"}, clear=True):
            self.assertEqual(resolve_gemini_model("gemini-2.5-pro"), "gemini-2.5-pro")
            self.assertEqual(resolve_gemini_model("explicit-override"), "explicit-override")

    def test_gemini_judge_model_name_configurable(self):
        # Sin GEMINI_MODEL -> usa DEFAULT_MODEL
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_123"}, clear=True):
            with patch("google.genai.Client"):
                judge_default = GeminiSemanticJudge()
                self.assertEqual(judge_default.model_name, "gemini-3.8-flash")

        # Con GEMINI_MODEL=gemini-3.6-flash -> usa gemini-3.6-flash
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_123", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True):
            with patch("google.genai.Client"):
                judge_custom = GeminiSemanticJudge()
                self.assertEqual(judge_custom.model_name, "gemini-3.6-flash")

        # Parámetro explícito -> tiene prioridad sobre env
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_123", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True):
            with patch("google.genai.Client"):
                judge_explicit = GeminiSemanticJudge(model_name="gemini-1.5-pro")
                self.assertEqual(judge_explicit.model_name, "gemini-1.5-pro")

    def test_gemini_judge_success_with_mock_client(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = self.sample_payload
        mock_client.models.generate_content.return_value = mock_response

        judge = GeminiSemanticJudge(api_key="fake_key", client=mock_client)
        result = judge.evaluate(self.sample_evidence_packet)

        self.assertEqual(result, self.sample_payload)
        mock_client.models.generate_content.assert_called_once()
        _, kwargs = mock_client.models.generate_content.call_args
        self.assertEqual(kwargs["model"], judge.model_name)
        config = kwargs["config"]
        self.assertEqual(config.response_schema, SemanticJudgePayload)
        self.assertEqual(config.temperature, 0.2)

    def test_gemini_judge_retries_once_on_invalid_response_then_succeeds(self):
        mock_client = MagicMock()
        mock_bad_response = MagicMock()
        mock_bad_response.parsed = None
        mock_bad_response.text = "{'invalid': 'json'}"

        mock_good_response = MagicMock()
        mock_good_response.parsed = self.sample_payload

        # Falla primero, tiene éxito en el retry
        mock_client.models.generate_content.side_effect = [mock_bad_response, mock_good_response]

        judge = GeminiSemanticJudge(api_key="fake_key", client=mock_client)
        result = judge.evaluate(self.sample_evidence_packet)

        self.assertEqual(result, self.sample_payload)
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    def test_gemini_judge_fails_after_second_invalid_response(self):
        mock_client = MagicMock()
        mock_bad_response = MagicMock()
        mock_bad_response.parsed = None
        mock_bad_response.text = "{'invalid': 'json'}"

        # Falla dos veces consecutivas
        mock_client.models.generate_content.side_effect = [mock_bad_response, mock_bad_response]

        judge = GeminiSemanticJudge(api_key="fake_key", client=mock_client)
        with self.assertRaises(SemanticJudgeEvaluationError):
            judge.evaluate(self.sample_evidence_packet)

        self.assertEqual(mock_client.models.generate_content.call_count, 2)


if __name__ == "__main__":
    unittest.main()
