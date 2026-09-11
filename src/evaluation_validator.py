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


def validate_and_score_evaluation(
    payload: Union[SemanticJudgePayload, dict],
    repo_data: dict,
) -> EvaluationResult:
    """
    Valida el payload del Juez Semántico y calcula determinísticamente los puntajes.
    Responsabilidades estrictas:
    - Exige niveles estrictamente en {0, 25, 50, 75, 100} (PROHIBIDO el clamping silencioso).
    - Exige las 5 dimensiones oficiales (D1 a D5).
    - Aplica los pesos matemáticos oficiales: 30%, 25%, 15%, 15%, 15%.
    - Verifica citas de archivos contra el inventario del repositorio.
    - Transporta hallazgos de integridad a integrity_notes.
    - NO reinterpreta la evaluación semántica ni modifica justificaciones.
    """
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
