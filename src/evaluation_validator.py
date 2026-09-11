from datetime import datetime
from typing import Dict, List, Union
from pydantic import ValidationError

from src.schema import DimensionResult, EvaluationResult
from src.semantic_schema import SemanticJudgePayload, FindingItem

OFFICIAL_DIMENSIONS = [
    ("D1", "Sistema completo y funcionando", 30.0, "implementation"),
    ("D2", "Proceso documentado", 25.0, "process"),
    ("D3", "Formato y reproducibilidad", 15.0, "reproducibility"),
    ("D4", "Análisis económico", 15.0, "economics"),
    ("D5", "Gobierno y riesgo", 15.0, "governance"),
]

ALLOWED_LEVELS = {0, 25, 50, 75, 100}


def merge_deterministic_and_semantic(
    det_result: EvaluationResult,
    payload: Union[SemanticJudgePayload, dict],
    repo_data: dict,
) -> EvaluationResult:
    """
    Combina el resultado determinístico con el análisis interpretativo del Juez Semántico.
    REGLA DE ORO DE DETERMINISMO:
    - Las dimensiones D1..D5, sus niveles (0/25/50/75/100), sus pesos oficiales y el final_score
      son ESTRICTAMENTE los calculados por el motor determinístico (det_result).
    - El payload semántico enriquece la explicación pedagógica:
      - Audita citas de archivos en los hallazgos contra el inventario real.
      - Agrega hallazgos de integridad a integrity_notes.
      - Incorpora la sugerencia concreta de mejora pedagógica.
    """
    if isinstance(payload, dict):
        try:
            payload = SemanticJudgePayload.model_validate(payload)
        except ValidationError as error:
            raise ValueError(f"Payload de evaluación semántica no cumple el esquema formal: {error}") from error
    elif not isinstance(payload, SemanticJudgePayload):
        raise ValueError(f"Tipo de payload no soportado: {type(payload)}")

    inventory_paths = {
        item.get("path") for item in repo_data.get("repository_inventory", []) if item.get("path")
    }
    if not inventory_paths and "file_contents" in repo_data:
        inventory_paths = set(repo_data["file_contents"].keys())

    integrity_notes = list(det_result.integrity_notes or [])
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
            note = f"[INTEGRIDAD_{item.severity.upper()}] {item.finding}{files_str}"
            if note not in integrity_notes:
                integrity_notes.append(note)
        elif item.category in category_findings:
            category_findings[item.category].append(item.finding)

        for path in item.files:
            if inventory_paths and path not in inventory_paths:
                unverified_note = (
                    f"[CITA_NO_VERIFICADA] El archivo '{path}' citado en hallazgos no figura en el inventario del repositorio."
                )
                if unverified_note not in integrity_notes:
                    integrity_notes.append(unverified_note)

    # Conservar dimensiones determinísticas autorizadas
    merged_dimensions: List[DimensionResult] = []
    cat_map = {
        "Sistema completo y funcionando": "implementation",
        "Proceso documentado": "process",
        "Formato y reproducibilidad": "reproducibility",
        "Análisis económico": "economics",
        "Gobierno y riesgo": "governance",
    }

    for dim in det_result.dimensions:
        merged_evidence = list(dim.evidence)
        cat = cat_map.get(dim.dimension)
        if cat and cat in category_findings:
            for f in category_findings[cat]:
                if f not in merged_evidence:
                    merged_evidence.append(f)

        merged_dimensions.append(
            DimensionResult(
                dimension=dim.dimension,
                weight=dim.weight,
                level_percent=dim.level_percent,
                score=dim.score,
                evidence=merged_evidence,
                justification=dim.justification,
                missing_for_next_level=dim.missing_for_next_level,
            )
        )

    concrete_improvement = (
        payload.concrete_improvement.strip()
        if payload.concrete_improvement and payload.concrete_improvement.strip()
        else det_result.concrete_improvement
    )

    return EvaluationResult(
        repository=det_result.repository,
        evaluated_revision=det_result.evaluated_revision,
        evaluation_date=det_result.evaluation_date,
        evaluation_status=det_result.evaluation_status,
        dimensions=merged_dimensions,
        final_score=det_result.final_score,
        concrete_improvement=concrete_improvement,
        integrity_notes=integrity_notes,
    )


def validate_and_score_evaluation(
    payload: Union[SemanticJudgePayload, dict],
    repo_data: dict,
    authoritative_mode: str = "deterministic",
) -> EvaluationResult:
    """
    Valida el payload del Juez Semántico y calcula los puntajes.
    Si authoritative_mode == 'deterministic' y repo_data contiene 'file_contents',
    delega el scoring al motor determinístico inmutable y enriquece con el análisis semántico.
    Si no, ejecuta la validación y cálculo determinístico sobre el payload.
    """
    if authoritative_mode == "deterministic" and repo_data.get("file_contents"):
        from src.deterministic_evaluator import evaluate_repository_deterministically
        det_result = evaluate_repository_deterministically(repo_data)
        return merge_deterministic_and_semantic(det_result, payload, repo_data)
    if isinstance(payload, dict):
        try:
            payload = SemanticJudgePayload.model_validate(payload)
        except ValidationError as error:
            raise ValueError(f"Payload de evaluación semántica no cumple el esquema formal: {error}") from error
    elif not isinstance(payload, SemanticJudgePayload):
        raise ValueError(f"Tipo de payload no soportado: {type(payload)}")

    # 1. Obtener conjunto de archivos existentes en inventario
    inventory_paths = {
        item.get("path") for item in repo_data.get("repository_inventory", []) if item.get("path")
    }
    if not inventory_paths and "file_contents" in repo_data:
        inventory_paths = set(repo_data["file_contents"].keys())

    # 2. Auditar citas de archivos en hallazgos
    integrity_notes: List[str] = []
    category_findings: Dict[str, List[str]] = {
        "implementation": [],
        "process": [],
        "reproducibility": [],
        "economics": [],
        "governance": [],
    }

    for item in payload.findings:
        # Asegurar tipo FindingItem
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

    for dim_key, dim_name, weight, default_cat in OFFICIAL_DIMENSIONS:
        if dim_key not in payload.dimension_evaluations:
            raise ValueError(f"Dimensión requerida '{dim_key}' ausente en dimension_evaluations.")

        dim_eval = payload.dimension_evaluations[dim_key]
        level = dim_eval.recommended_level

        # Regla estricta: NO clamping
        if level not in ALLOWED_LEVELS:
            raise ValueError(f"Nivel no permitido {level} para dimensión {dim_key}. Debe ser estrictamente 0, 25, 50, 75 o 100.")

        dim_score = round(weight * (level / 100.0), 2)
        total_score += dim_score

        evidence_list = category_findings.get(default_cat, [])

        dimension_results.append(
            DimensionResult(
                dimension=dim_name,
                weight=weight,
                level_percent=level,
                score=dim_score,
                evidence=evidence_list,
                justification=dim_eval.justification,
                missing_for_next_level=dim_eval.missing_for_next_level,
            )
        )

    repo_url = repo_data.get("repo_url") or repo_data.get("repository", "repositorio_evaluado")
    evaluated_revision = repo_data.get("commit_sha") or repo_data.get("branch", "unknown")

    return EvaluationResult(
        repository=repo_url,
        evaluated_revision=str(evaluated_revision),
        evaluation_date=datetime.now().strftime("%Y-%m-%d"),
        evaluation_status="completed",
        dimensions=dimension_results,
        final_score=round(total_score, 2),
        concrete_improvement=payload.concrete_improvement,
        integrity_notes=integrity_notes,
    )
