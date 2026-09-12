from datetime import datetime
from typing import Dict, List, Optional, Union
from pydantic import ValidationError

from src.schema import DimensionResult, EvaluationResult
from src.semantic_schema import (
    SemanticJudgePayload,
    FindingItem,
    SimpleEvaluationPayload,
    DimensionAuditItem,
)

OFFICIAL_DIMENSIONS = [
    ("D1", "Sistema completo y funcionando", 30.0, "implementation"),
    ("D2", "Proceso documentado", 25.0, "process"),
    ("D3", "Formato y reproducibilidad", 15.0, "reproducibility"),
    ("D4", "Análisis económico", 15.0, "economics"),
    ("D5", "Gobierno y riesgo", 15.0, "governance"),
]

ALLOWED_LEVELS = {0, 25, 50, 75, 100}


class InconsistentEvaluationError(ValueError):
    """Lanzada cuando una dimensión recibe 100 pero su propia auditoría contiene PARTIAL, MISSING o CONTRADICTED."""
    pass


def validate_and_score_evaluation(
    payload: Union[SemanticJudgePayload, SimpleEvaluationPayload, dict],
    repo_data: dict,
    actual_model_used: Optional[str] = None,
    runtime_fingerprint: Optional[str] = None,
) -> EvaluationResult:
    """
    Valida el payload del Juez Semántico y calcula determinísticamente los puntajes.
    Responsabilidades estrictas:
    - Exige niveles estrictamente en {0, 25, 50, 75, 100} (PROHIBIDO el clamping silencioso).
    - Exige las 5 dimensiones oficiales (D1 a D5).
    - Aplica los pesos matemáticos oficiales: 30%, 25%, 15%, 15%, 15%.
    - Si el LLM calculó mal el total pero los niveles son válidos: recalcula el total con la fórmula oficial sin alterar los niveles elegidos.
    - Verifica citas de archivos contra el inventario del repositorio.
    - Guardrail estricto: Si una dimensión tiene 100% pero su requirement_checks contiene PARTIAL, MISSING o CONTRADICTED,
      lanza InconsistentEvaluationError (disparador de repair call).
    - Transporta hallazgos de integridad a integrity_notes.
    - NO reinterpreta la evaluación semántica ni modifica justificaciones.
    """
    if isinstance(payload, dict):
        if "dimensions" in payload and isinstance(payload["dimensions"], list):
            try:
                payload = SimpleEvaluationPayload.model_validate(payload)
            except ValidationError as error:
                raise ValueError(f"Payload de evaluación simple no cumple el esquema formal: {error}") from error
        else:
            try:
                payload = SemanticJudgePayload.model_validate(payload)
            except ValidationError as error:
                raise ValueError(f"Payload de evaluación semántica no cumple el esquema formal: {error}") from error
    elif not isinstance(payload, (SemanticJudgePayload, SimpleEvaluationPayload)):
        raise ValueError(f"Tipo de payload no soportado: {type(payload)}")

    # 1. Obtener conjunto de archivos existentes en inventario
    inventory_paths = {
        item.get("path") for item in repo_data.get("repository_inventory", []) if item.get("path")
    }
    if not inventory_paths and "file_contents" in repo_data:
        inventory_paths = set(repo_data["file_contents"].keys())
    if not inventory_paths and "files" in repo_data:
        inventory_paths = set(repo_data["files"].keys())

    repo_url = repo_data.get("repo_url") or repo_data.get("repository", "repositorio_evaluado")
    evaluated_revision = repo_data.get("commit_sha") or repo_data.get("branch", "unknown")

    # Si es SimpleEvaluationPayload (evaluador simple V2)
    if isinstance(payload, SimpleEvaluationPayload):
        dim_map = {item.dimension: item for item in payload.dimensions}
        # Verificar que existan exactamente las 5 dimensiones oficiales
        for dim_key, dim_name, weight, _ in OFFICIAL_DIMENSIONS:
            if dim_key not in dim_map:
                raise ValueError(f"Dimensión requerida '{dim_key}' ausente en payload simple.")
            level = dim_map[dim_key].level_percent
            if level not in ALLOWED_LEVELS:
                raise ValueError(f"Nivel no permitido {level} para dimensión {dim_key}. Debe ser estrictamente 0, 25, 50, 75 o 100.")

        integrity_notes: List[str] = list(payload.integrity_notes)
        dimension_results: List[DimensionResult] = []
        total_score = 0.0

        for dim_key, dim_name, weight, _ in OFFICIAL_DIMENSIONS:
            dim_item = dim_map[dim_key]
            level = dim_item.level_percent

            # GUARDRAIL ESTRICTO: 100% exige ausencia total de PARTIAL, MISSING, CONTRADICTED
            if level == 100 and getattr(dim_item, "requirement_checks", None):
                inconsistent_checks = [
                    c for c in dim_item.requirement_checks
                    if c.status in {"PARTIAL", "MISSING", "CONTRADICTED"}
                ]
                if inconsistent_checks:
                    inconsistencies = [f"'{c.requirement}' ({c.status}: {c.explanation})" for c in inconsistent_checks]
                    raise InconsistentEvaluationError(
                        f"Inconsistencia en dimensión {dim_key} ('{dim_name}'): asignó nivel 100% pero su propia auditoría "
                        f"registró requisitos no cumplidos: {'; '.join(inconsistencies)}. "
                        "Tu score contradice tu propia auditoría. Reaplicá rubrica.md."
                    )

            dim_score = round(weight * (level / 100.0), 2)
            total_score += dim_score

            # Verificar citas contra inventario
            for path in dim_item.evidence:
                if inventory_paths and path not in inventory_paths:
                    integrity_notes.append(
                        f"[CITA_NO_VERIFICADA] El archivo '{path}' citado en evidencia de {dim_key} no figura en el inventario del repositorio."
                    )

            dimension_results.append(
                DimensionResult(
                    dimension=dim_name,
                    weight=weight,
                    level_percent=level,
                    score=dim_score,
                    evidence=dim_item.evidence,
                    justification=dim_item.justification,
                    improvement=dim_item.improvement,
                    missing_for_next_level=dim_item.improvement,
                )
            )

        return EvaluationResult(
            repository=repo_url,
            evaluated_revision=str(evaluated_revision),
            evaluation_date=datetime.now().strftime("%Y-%m-%d"),
            evaluation_status="completed",
            dimensions=dimension_results,
            final_score=round(total_score, 2),
            concrete_improvement=payload.concrete_improvement,
            integrity_notes=integrity_notes,
            status="OK",
            actual_model_used=actual_model_used,
            runtime_fingerprint=runtime_fingerprint,
        )

    # 2. Auditar citas de archivos en hallazgos (SemanticJudgePayload clásico)
    integrity_notes: List[str] = []
    category_findings: Dict[str, List[str]] = {
        "implementation": [],
        "process": [],
        "reproducibility": [],
        "economics": [],
        "governance": [],
    }

    for item in payload.findings:
        if isinstance(item, dict):
            item = FindingItem.model_validate(item)

        if item.category == "integrity":
            files_str = f" (Archivos: {', '.join(item.files)})" if item.files else ""
            integrity_notes.append(f"[INTEGRIDAD_{item.severity.upper()}] {item.finding}{files_str}")
        elif item.category in category_findings:
            category_findings[item.category].append(item.finding)

        for path in item.files:
            if inventory_paths and path not in inventory_paths:
                integrity_notes.append(
                    f"[CITA_NO_VERIFICADA] El archivo '{path}' citado en hallazgos no figura en el inventario del repositorio."
                )

    # 3. Validar y calcular dimensiones con pesos oficiales
    dimension_results: List[DimensionResult] = []
    total_score = 0.0

    if payload.dimensions:
        dim_map = {item.dimension: item for item in payload.dimensions}
        for dim_key, dim_name, weight, _ in OFFICIAL_DIMENSIONS:
            if dim_key not in dim_map:
                raise ValueError(f"Dimensión requerida '{dim_key}' ausente.")
            level = dim_map[dim_key].level_percent
            if level not in ALLOWED_LEVELS:
                raise ValueError(f"Nivel no permitido {level} para dimensión {dim_key}.")
            dim_score = round(weight * (level / 100.0), 2)
            total_score += dim_score
            dimension_results.append(
                DimensionResult(
                    dimension=dim_name,
                    weight=weight,
                    level_percent=level,
                    score=dim_score,
                    evidence=dim_map[dim_key].evidence,
                    justification=dim_map[dim_key].justification,
                    improvement=dim_map[dim_key].improvement,
                    missing_for_next_level=dim_map[dim_key].improvement,
                )
            )
    elif payload.dimension_evaluations:
        evals = payload.dimension_evaluations
        for dim_key, dim_name, weight, cat_key in OFFICIAL_DIMENSIONS:
            dim_eval = getattr(evals, dim_key)
            level = dim_eval.recommended_level
            if level not in ALLOWED_LEVELS:
                raise ValueError(f"Nivel no permitido {level} para dimensión {dim_key}.")
            dim_score = round(weight * (level / 100.0), 2)
            total_score += dim_score
            dimension_results.append(
                DimensionResult(
                    dimension=dim_name,
                    weight=weight,
                    level_percent=level,
                    score=dim_score,
                    evidence=category_findings.get(cat_key, []),
                    justification=dim_eval.justification,
                    improvement=dim_eval.missing_for_next_level,
                    missing_for_next_level=dim_eval.missing_for_next_level,
                )
            )
    else:
        raise ValueError("Payload no contiene evaluaciones por dimensión.")

    return EvaluationResult(
        repository=repo_url,
        evaluated_revision=str(evaluated_revision),
        evaluation_date=datetime.now().strftime("%Y-%m-%d"),
        evaluation_status="completed",
        dimensions=dimension_results,
        final_score=round(total_score, 2),
        concrete_improvement=payload.concrete_improvement,
        integrity_notes=integrity_notes,
        status="OK",
        actual_model_used=actual_model_used,
        runtime_fingerprint=runtime_fingerprint,
    )
