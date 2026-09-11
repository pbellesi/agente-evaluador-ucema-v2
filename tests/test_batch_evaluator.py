import io
import zipfile
import pytest

from src.batch_evaluator import (
    ProjectEvaluationOutcome,
    evaluate_batch_zips,
    evaluate_project_zip,
    load_rubric_text,
)
from src.semantic_judge import MockSemanticJudge, SemanticJudge
from src.semantic_schema import (
    DimensionEvaluation,
    DimensionEvaluations,
    FindingItem,
    ProjectUnderstanding,
    SemanticJudgePayload,
)


def _create_sample_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("README.md", "# Test Project\nSistema agéntico de prueba.")
        zf.writestr("prompts/system_prompt.md", "Sos un agente de reposición.")
        zf.writestr("DECISIONES.md", "Bitácora de decisiones v1 a v2.")
        zf.writestr("corridas/corrida_01/salida.json", '{"status": "ok"}')
        zf.writestr("analisis_economico.md", "Tokens: 1000. Costo: 0.01.")
        zf.writestr("gobierno_riesgos.md", "Riesgos L0-L3.")
    return buffer.getvalue()


def _create_sample_payload() -> SemanticJudgePayload:
    return SemanticJudgePayload(
        project_understanding=ProjectUnderstanding(
            system_summary="Sistema de prueba",
            architecture_observed="Monolito Python",
            main_technologies=["Python", "Claude"],
        ),
        findings=[
            FindingItem(
                category="implementation",
                severity="info",
                files=["README.md"],
                finding="Proyecto bien estructurado",
                impact_on_evaluation="Positivo",
            )
        ],
        dimension_evaluations=DimensionEvaluations(
            D1=DimensionEvaluation(recommended_level=100, justification="D1 justif", missing_for_next_level=None),
            D2=DimensionEvaluation(recommended_level=75, justification="D2 justif", missing_for_next_level="Más tests"),
            D3=DimensionEvaluation(recommended_level=100, justification="D3 justif", missing_for_next_level=None),
            D4=DimensionEvaluation(recommended_level=50, justification="D4 justif", missing_for_next_level="Costos"),
            D5=DimensionEvaluation(recommended_level=100, justification="D5 justif", missing_for_next_level=None),
        ),
        concrete_improvement="Agregar más pruebas de integración.",
    )


class FailingMockJudge(SemanticJudge):
    def evaluate(self, evidence_packet: dict) -> SemanticJudgePayload:
        raise RuntimeError("Falla simulada del modelo o red")


def test_evaluate_project_zip_success():
    zip_bytes = _create_sample_zip()
    judge = MockSemanticJudge(_create_sample_payload())
    outcome = evaluate_project_zip(zip_bytes, "proyecto_alpha.zip", judge)

    assert outcome.status == "OK"
    assert outcome.project_name == "proyecto_alpha.zip"
    assert outcome.result is not None
    assert outcome.payload is not None
    assert outcome.error_message is None
    assert outcome.result.final_score is not None
    assert outcome.result.dimensions[0].level_percent == 100


def test_evaluate_project_zip_invalid_bytes():
    judge = MockSemanticJudge(_create_sample_payload())
    outcome = evaluate_project_zip(b"corrupted bytes", "corrupto.zip", judge)

    assert outcome.status == "ERROR"
    assert outcome.project_name == "corrupto.zip"
    assert outcome.result is None
    assert outcome.payload is None
    assert outcome.error_message is not None


def test_evaluate_project_zip_judge_failure():
    zip_bytes = _create_sample_zip()
    judge = FailingMockJudge()
    outcome = evaluate_project_zip(zip_bytes, "fallo_judge.zip", judge)

    assert outcome.status == "ERROR"
    assert outcome.project_name == "fallo_judge.zip"
    assert outcome.result is None
    assert "Falla simulada" in outcome.error_message


def test_evaluate_batch_zips_mixed():
    valid_zip = _create_sample_zip()
    items = [
        ("proyecto_1.zip", valid_zip),
        ("proyecto_invalido.zip", b"not a zip"),
        ("proyecto_3.zip", valid_zip),
    ]
    judge = MockSemanticJudge(_create_sample_payload())
    progress_records = []

    def on_progress(idx: int, total: int, name: str):
        progress_records.append((idx, total, name))

    outcomes = evaluate_batch_zips(items, judge, on_progress=on_progress)

    assert len(outcomes) == 3
    assert outcomes[0].status == "OK"
    assert outcomes[0].project_name == "proyecto_1.zip"
    assert outcomes[1].status == "ERROR"
    assert outcomes[1].project_name == "proyecto_invalido.zip"
    assert outcomes[2].status == "OK"
    assert outcomes[2].project_name == "proyecto_3.zip"

    # Verificar progreso reportado
    assert len(progress_records) == 4  # 3 items + 1 final
    assert progress_records[0] == (0, 3, "proyecto_1.zip")
    assert progress_records[1] == (1, 3, "proyecto_invalido.zip")
    assert progress_records[2] == (2, 3, "proyecto_3.zip")
    assert progress_records[3] == (3, 3, "Finalizado")


def test_load_rubric_text():
    rubric = load_rubric_text()
    assert rubric is not None
    assert "Trabajo final" in rubric or "Rúbrica" in rubric
