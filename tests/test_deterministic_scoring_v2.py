import io
import zipfile
import pytest

from src.batch_evaluator import evaluate_project_zip
from src.evaluator_engine import EVALUATOR_VERSION
from src.schema import EvaluationResult
from src.semantic_judge import SemanticJudge
from src.semantic_schema import (
    DimensionEvaluation,
    DimensionEvaluations,
    FindingItem,
    ProjectUnderstanding,
    SemanticJudgePayload,
)
from src.zip_repository import build_repository_data_from_zip


def _build_test_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(
            "src/main.py",
            "import os\nprint('Procesando datos locales')\ndef procesar(x):\n    return x * 2\n",
        )
        zf.writestr("prompts/system_prompt.md", "Sos un agente que clasifica tickets de soporte.")
        zf.writestr("README.md", "# Agente de Soporte\nEjecución: python src/main.py")
        zf.writestr("DECISIONES.md", "Decisión 1: Usar Python 3.11\nDecisión 2: Reglas determinísticas")
        zf.writestr("corridas/corrida_01/salida.json", '{"ticket_id": "T-100", "resultado": "OK"}')
        zf.writestr("analisis_economico.md", "Estimación de costos: 0.05 USD por 1000 tickets.")
        zf.writestr("gobierno_riesgos.md", "Matriz de riesgos y supervisión humana periódica.")
    return buffer.getvalue()


def _make_payload(level: int) -> SemanticJudgePayload:
    return SemanticJudgePayload(
        project_understanding=ProjectUnderstanding(
            system_summary=f"Resumen de prueba con nivel {level}",
            architecture_observed="Pipeline",
            main_technologies=["Python"],
        ),
        findings=[
            FindingItem(
                category="implementation",
                severity="info",
                files=["src/main.py"],
                finding="Implementación correcta.",
                impact_on_evaluation="Positivo",
            )
        ],
        dimension_evaluations=DimensionEvaluations(
            D1=DimensionEvaluation(recommended_level=level, justification=f"Justif D1 {level}"),
            D2=DimensionEvaluation(recommended_level=level, justification=f"Justif D2 {level}"),
            D3=DimensionEvaluation(recommended_level=level, justification=f"Justif D3 {level}"),
            D4=DimensionEvaluation(recommended_level=level, justification=f"Justif D4 {level}"),
            D5=DimensionEvaluation(recommended_level=level, justification=f"Justif D5 {level}"),
        ),
        concrete_improvement="Mejora sugerida por mock",
    )


class MockConstantJudge(SemanticJudge):
    def __init__(self, payload: SemanticJudgePayload):
        self._payload = payload

    def evaluate(self, evidence_packet: dict) -> SemanticJudgePayload:
        return self._payload


class MockErrorJudge(SemanticJudge):
    def __init__(self, error_type: str = "429"):
        self.error_type = error_type

    def evaluate(self, evidence_packet: dict) -> SemanticJudgePayload:
        if self.error_type == "429":
            raise RuntimeError("ResourceExhausted: 429 Resource has been exhausted (e.g. check quota).")
        elif self.error_type == "503":
            raise RuntimeError("ServiceUnavailable: 503 The model is overloaded. Please try again later.")
        else:
            raise TimeoutError("Conexión con el proveedor LLM agotó el tiempo de espera.")


def test_evaluator_version_constant():
    assert EVALUATOR_VERSION == "v2-deterministic-score-1"


def test_cache_key_generation_and_version_invalidation():
    sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    key_current = f"{EVALUATOR_VERSION}:{sha}"
    key_other = f"v2-deterministic-score-0:{sha}"
    assert key_current != key_other
    assert key_current.startswith("v2-deterministic-score-1:")


def test_authoritative_scoring_immutable_across_contradictory_payloads():
    zip_bytes = _build_test_zip()

    judge_0 = MockConstantJudge(_make_payload(0))
    judge_100 = MockConstantJudge(_make_payload(100))
    judge_50 = MockConstantJudge(_make_payload(50))

    outcome_0 = evaluate_project_zip(zip_bytes, "test.zip", judge=judge_0)
    outcome_100 = evaluate_project_zip(zip_bytes, "test.zip", judge=judge_100)
    outcome_50 = evaluate_project_zip(zip_bytes, "test.zip", judge=judge_50)

    assert outcome_0.status == "OK"
    assert outcome_100.status == "OK"
    assert outcome_50.status == "OK"

    # La autoridad absoluta es el motor determinístico:
    # los puntajes finales y por dimensión deben ser EXACTAMENTE IDÉNTICOS
    assert outcome_0.result.final_score == outcome_100.result.final_score
    assert outcome_100.result.final_score == outcome_50.result.final_score

    for i in range(5):
        dim_0 = outcome_0.result.dimensions[i]
        dim_100 = outcome_100.result.dimensions[i]
        dim_50 = outcome_50.result.dimensions[i]

        assert dim_0.level_percent == dim_100.level_percent == dim_50.level_percent
        assert dim_0.score == dim_100.score == dim_50.score
        assert dim_0.weight == dim_100.weight == dim_50.weight


def test_gemini_429_graceful_deterministic_fallback():
    zip_bytes = _build_test_zip()
    judge_429 = MockErrorJudge("429")

    outcome = evaluate_project_zip(zip_bytes, "test.zip", judge=judge_429)

    # Si Gemini devuelve 429, el evaluador NO falla ni devuelve 0
    assert outcome.status == "OK"
    assert outcome.result is not None
    assert outcome.result.final_score is not None
    assert outcome.result.final_score > 0
    assert outcome.payload is None

    # Debe contener nota de advertencia explicativa
    notes = " ".join(outcome.result.integrity_notes or [])
    assert "429" in notes or "semántico no disponible" in notes.lower() or "llm_unavailable" in notes.lower()


def test_gemini_503_graceful_deterministic_fallback():
    zip_bytes = _build_test_zip()
    judge_503 = MockErrorJudge("503")

    outcome = evaluate_project_zip(zip_bytes, "test.zip", judge=judge_503)

    assert outcome.status == "OK"
    assert outcome.result is not None
    assert outcome.result.final_score is not None
    assert outcome.result.final_score > 0
    assert outcome.payload is None


def test_official_weights_and_allowed_levels():
    zip_bytes = _build_test_zip()
    judge = MockConstantJudge(_make_payload(50))
    outcome = evaluate_project_zip(zip_bytes, "test.zip", judge=judge)

    expected_weights = [30.0, 25.0, 15.0, 15.0, 15.0]
    allowed_levels = {0, 25, 50, 75, 100}

    assert len(outcome.result.dimensions) == 5
    for i, dim in enumerate(outcome.result.dimensions):
        assert dim.weight == expected_weights[i]
        assert dim.level_percent in allowed_levels
        expected_dim_score = round(dim.weight * (dim.level_percent / 100.0), 2)
        assert dim.score == expected_dim_score
