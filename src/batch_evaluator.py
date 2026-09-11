"""
Módulo de evaluación por lote para el Agente Evaluador UCEMA V2.
Permite procesar múltiples archivos ZIP de forma desacoplada de la interfaz gráfica.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Literal, Optional, Sequence, Tuple

from src.context_builder import build_evidence_packet
from src.deterministic_evaluator import evaluate_repository_deterministically
from src.evaluation_validator import validate_and_score_evaluation
from src.evaluator_engine import EVALUATOR_VERSION
from src.schema import EvaluationResult
from src.semantic_judge import GeminiSemanticJudge, SemanticJudge
from src.semantic_schema import SemanticJudgePayload
from src.zip_repository import ZipRepositoryError, build_repository_data_from_zip


@dataclass
class ProjectEvaluationOutcome:
    project_name: str
    status: Literal["OK", "ERROR"]
    result: Optional[EvaluationResult] = None
    payload: Optional[SemanticJudgePayload] = None
    error_message: Optional[str] = None


def load_rubric_text(rubric_path: Optional[Path] = None) -> Optional[str]:
    """Carga el texto oficial de la rúbrica si existe."""
    target = rubric_path or (Path(__file__).resolve().parents[1] / "rubrica.md")
    if target.is_file():
        try:
            return target.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def evaluate_project_zip(
    zip_bytes: bytes,
    filename: str,
    judge: Optional[SemanticJudge] = None,
    rubric_text: Optional[str] = None,
) -> ProjectEvaluationOutcome:
    """
    Evalúa un único archivo ZIP en memoria de forma aislada.
    REGLA DE ORO DE DETERMINISMO V2:
    - La autoridad de scoring es 100% el motor determinístico en Python (evaluate_repository_deterministically).
    - Si judge está presente, ejecuta análisis interpretativo (findings, sugerencia, integridad).
    - Si judge falla (429 cuota diaria, 503, timeout, etc.), la evaluación NO falla ni da 0:
      retorna el resultado determinístico con status 'OK' y aviso informativo.
    - Si el ZIP está físicamente dañado, retorna status 'ERROR' con el mensaje de error.
    """
    try:
        if rubric_text is None:
            rubric_text = load_rubric_text()

        # 1. Ingesta segura en memoria
        repo_data = build_repository_data_from_zip(zip_bytes, filename)

        # 2. Evaluación determinística autorizada (inmutable)
        det_result = evaluate_repository_deterministically(repo_data)

        # 3. Si no se especificó juez semántico, retornar inmediatamente
        if judge is None:
            return ProjectEvaluationOutcome(
                project_name=filename,
                status="OK",
                result=det_result,
                payload=None,
            )

        # 4. Construcción de Contexto
        evidence_packet = build_evidence_packet(repo_data, rubric_text=rubric_text)

        # 5. Juez Semántico encapsulado (tolerante a fallos de cuota o red)
        try:
            payload = judge.evaluate(evidence_packet)
            result = validate_and_score_evaluation(payload, repo_data)
            return ProjectEvaluationOutcome(
                project_name=filename,
                status="OK",
                result=result,
                payload=payload,
            )
        except Exception as llm_error:
            res_fallback = det_result.model_copy(deep=True)
            res_fallback.integrity_notes.append(
                f"[LLM_UNAVAILABLE] Análisis semántico no disponible: {llm_error}. Calificación calculada 100% determinísticamente."
            )
            return ProjectEvaluationOutcome(
                project_name=filename,
                status="OK",
                result=res_fallback,
                payload=None,
                error_message=f"Aviso semántico: {llm_error}",
            )
    except Exception as exc:
        return ProjectEvaluationOutcome(
            project_name=filename,
            status="ERROR",
            error_message=str(exc),
        )


def evaluate_batch_zips(
    items: Sequence[Tuple[str, bytes]],
    judge: SemanticJudge,
    rubric_text: Optional[str] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> List[ProjectEvaluationOutcome]:
    """
    Evalúa secuencialmente una lista de tuplas (filename, zip_bytes).
    Notifica progreso mediante on_progress(current_index, total_count, current_filename).
    Si un ZIP falla, continúa con los demás sin abortar.
    """
    outcomes: List[ProjectEvaluationOutcome] = []
    total = len(items)

    for idx, (filename, zip_bytes) in enumerate(items):
        if on_progress:
            on_progress(idx, total, filename)
        outcome = evaluate_project_zip(
            zip_bytes=zip_bytes,
            filename=filename,
            judge=judge,
            rubric_text=rubric_text,
        )
        outcomes.append(outcome)

    if on_progress and total > 0:
        on_progress(total, total, "Finalizado")

    return outcomes
