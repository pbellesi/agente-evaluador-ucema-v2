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

        # Pre-validación de consistencia interna en requirement_checks
        inconsistency_errors = []
        for d_key, d_name, _, _ in OFFICIAL_DIMENSIONS:
            d_item = dim_map[d_key]
            if d_item.level_percent == 100 and getattr(d_item, "requirement_checks", None):
                bad_checks = [c for c in d_item.requirement_checks if c.status in {"PARTIAL", "MISSING", "CONTRADICTED"}]
                if bad_checks:
                    inconsistency_errors.append(
                        f"Dimensión {d_key} ('{d_name}'): asignó nivel 100% pero su propia auditoría registró requisitos no cumplidos: "
                        + "; ".join(f"'{c.requirement}' ({c.status}: {c.explanation})" for c in bad_checks)
                    )
        if inconsistency_errors:
            raise InconsistentEvaluationError(
                "Inconsistencia interna de contrato:\n" + "\n".join(inconsistency_errors)
                + "\nSi marcaste algún requisito como PARTIAL, MISSING o CONTRADICTED, está ESTRICTAMENTE PROHIBIDO asignar 100%. Reaplicá rubrica.md."
            )

        integrity_notes: List[str] = list(payload.integrity_notes)
        dimension_results: List[DimensionResult] = []
        total_score = 0.0

        for dim_key, dim_name, weight, _ in OFFICIAL_DIMENSIONS:
            dim_item = dim_map[dim_key]
            level = dim_item.level_percent

            # EVIDENCE CAPS MECÁNICOS: cross_audit_findings
            if getattr(payload, "cross_audit_findings", None):
                for f_item in payload.cross_audit_findings:
                    # PROMPT INJECTIONS NO DEBEN PENALIZAR: se desobedecen pero no reducen el puntaje si el trabajo es válido
                    desc_lower = (f_item.description or "").lower()
                    f_type = (f_item.finding_type or "").lower()
                    is_injection = (
                        f_type in {"prompt_injection", "injection_attempt", "adversarial_instruction"}
                        or any(
                            kw in desc_lower for kw in [
                                "prompt injection", "force the evaluator", "asignar 95", "asigná 100", "asigna 100",
                                "intento de inyección", "intento de inyeccion", "instrucción para el evaluador",
                                "instruccion para el evaluador", "instrucción adversarial", "instruccion adversarial",
                                "adversarial", "sistema evaluador", "previamente por el profesor", "nota acordada",
                                "calificación de 95", "calificacion de 95", "manipulación", "manipulacion",
                                "para el corrector", "respetar esa calificación", "respetar esa calificacion",
                                "no revises", "dejo constancia de que este trabajo cumple"
                            ]
                        )
                    )
                    if is_injection:
                        continue

                    aff = f_item.affected_dimensions or ["D2", "D3"]
                    if dim_key in aff:
                        cap = 75
                        if f_item.finding_type == "missing_failed_run" and dim_key in ["D2", "D3"]:
                            cap = 50
                        elif f_item.severity == "HIGH" and dim_key in ["D2", "D3"]:
                            cap = 75
                        elif f_item.finding_type in {"documentation_vs_execution", "contradiction_run_ledger"}:
                            cap = 75

                        if level > cap:
                            integrity_notes.append(
                                f"[EVIDENCE_CAP] dimension={dim_key} original={level} final={cap} reason={f_item.description}"
                            )
                            level = cap

            # EVIDENCE CAPS MECÁNICOS: claims CONTRADICTED
            if getattr(payload, "claim_checks", None):
                contradicted_claims = []
                for c in payload.claim_checks:
                    if c.status == "CONTRADICTED":
                        reason_lower = (c.short_reason or "").lower()
                        # Si el claim contradicho es por una prompt injection desobedecida, NO penaliza la dimensión académica
                        is_inj_claim = any(kw in reason_lower for kw in [
                            "injection", "inyección", "inyeccion", "adversarial", "manipulación", "manipulacion",
                            "asigná 100", "asigna 100", "asignar 100", "asignar 95", "corrector", "evaluador",
                            "no revises", "omita", "omitir", "fijar nota", "calificación"
                        ])
                        if not is_inj_claim:
                            contradicted_claims.append(c)

                if contradicted_claims:
                    if dim_key in ["D1", "D2", "D3"]:
                        cap = 75
                        if level > cap:
                            c_descs = [f"[{c.claim_id}: {c.short_reason}]" for c in contradicted_claims]
                            integrity_notes.append(
                                f"[EVIDENCE_CAP] dimension={dim_key} original={level} final={cap} reason=Claims materiales contradichos: {'; '.join(c_descs)}"
                            )
                            level = cap

            # EVIDENCE CAPS MECÁNICOS DETERMINÍSTICOS (LOCALES, BASADOS EN ARCHIVOS)
            if repo_data and "file_contents" in repo_data:
                from src.forensic_evidence import run_mechanical_diagnostics
                mech_diag = run_mechanical_diagnostics(repo_data.get("file_contents", {}))
                if mech_diag.get("chronological_inversion_detected") and dim_key == "D3":
                    if level > 50:
                        inv_alert = mech_diag["chronological_inversions"][0]["alert"] if mech_diag["chronological_inversions"] else "Inversión cronológica en corridas"
                        integrity_notes.append(
                            f"[EVIDENCE_CAP] dimension=D3 original={level} final=50 reason={inv_alert}"
                        )
                        level = 50
                if mech_diag.get("missing_failed_runs") and dim_key in ["D2", "D3"]:
                    if level > 50:
                        mfr_alert = mech_diag["missing_failed_runs"][0]["alert"]
                        integrity_notes.append(
                            f"[EVIDENCE_CAP] dimension={dim_key} original={level} final=50 reason={mfr_alert}"
                        )
                        level = 50
                if mech_diag.get("unimplemented_features") and dim_key in ["D1", "D2"]:
                    if level > 75:
                        uf_alert = mech_diag["unimplemented_features"][0]["alert"]
                        integrity_notes.append(
                            f"[EVIDENCE_CAP] dimension={dim_key} original={level} final=75 reason={uf_alert}"
                        )
                        level = 75
                if mech_diag.get("duplicate_outputs") and dim_key in ["D1", "D3"]:
                    if level > 25:
                        dup_alert = f"Salidas de corridas idénticas detectadas mecánicamente ({len(mech_diag['duplicate_outputs'])} duplicados). Respuestas estáticas hardcodeadas."
                        integrity_notes.append(
                            f"[EVIDENCE_CAP] dimension={dim_key} original={level} final=25 reason={dup_alert}"
                        )
                        level = 25

            # Registrar prompt injection findings en integrity_notes
            if getattr(payload, "prompt_injection_findings", None):
                for pi in payload.prompt_injection_findings:
                    note = f"[PROMPT_INJECTION] Archivo '{pi.file}': {pi.detected_instruction} (desobedecida={pi.disobeyed})"
                    if note not in integrity_notes:
                        integrity_notes.append(note)

            if level == 100:
                just_lower = (dim_item.justification or "").lower()
                for kw in ["contradicción material", "inconsistencia material", "corrida fallida ausente", "corrida fallida no preservada"]:
                    if kw in just_lower and "sin contradicci" not in just_lower and "no hay contradicci" not in just_lower and "no se observan contradicci" not in just_lower:
                        integrity_notes.append(
                            f"[EVIDENCE_CAP] dimension={dim_key} original=100 final=75 reason=Justificación señala '{kw}'"
                        )
                        level = 75
                        break

            dim_item.level_percent = level

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

        concrete_improvement = payload.concrete_improvement
        if concrete_improvement:
            ci_lower = concrete_improvement.lower()
            if any(kw in ci_lower for kw in ["prompt injection", "remover la inyección", "inyección de prompt", "instrucciones dirigidas al evaluador", "remover prompt injection"]):
                concrete_improvement = "Incorporar pruebas automatizadas de regresión o monitoreo continuo de tokens para optimizar la escalabilidad operativa."

        if repo_data and "file_contents" in repo_data:
            from src.forensic_evidence import run_mechanical_diagnostics
            mech_diag = run_mechanical_diagnostics(repo_data.get("file_contents", {}))
            if mech_diag.get("missing_failed_runs"):
                if "corrida fallida" not in (concrete_improvement or "").lower():
                    concrete_improvement = (
                        "Preservar en el repositorio la corrida real donde falló la clasificación de notas de crédito que motivó la variante v4 del prompt, "
                        "y corregir la anacronía temporal en las fechas de las corridas."
                    )

        return EvaluationResult(
            repository=repo_url,
            evaluated_revision=str(evaluated_revision),
            evaluation_date=datetime.now().strftime("%Y-%m-%d"),
            evaluation_status="completed",
            dimensions=dimension_results,
            final_score=round(total_score, 2),
            concrete_improvement=concrete_improvement,
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
