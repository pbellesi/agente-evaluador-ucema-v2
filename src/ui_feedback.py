from typing import Dict, List, Any
from src.schema import EvaluationResult, DimensionResult


def is_dimension_contradicted(dim: DimensionResult, notes: List[str]) -> bool:
    """
    Determina si una dimensión está afectada por una contradicción objetiva o evidencia invalidada.
    """
    just = (dim.justification or "").lower()
    if any(k in just for k in ["contradicha", "contradichas", "invalidadas", "invalidez de evidencia"]):
        return True

    dim_name = dim.dimension.lower()
    for note in notes:
        n_lower = note.lower()
        if "sistema" in dim_name and ("agente" in n_lower or "conectores" in n_lower or "dummy" in n_lower):
            if "contradicha" in n_lower or "dummy" in n_lower:
                return True
        elif "proceso" in dim_name and "decisiones" in n_lower:
            return True
        elif "formato" in dim_name and ("corridas" in n_lower or "salida" in n_lower):
            return True
        elif "económico" in dim_name and "analisis_economico" in n_lower:
            return True
        elif "gobierno" in dim_name and "gobierno" in n_lower:
            return True

    return False


def format_aspect_description(dim: DimensionResult) -> str:
    """
    Formatea la descripción de un aspecto a mejorar evitando responsabilizar al alumno
    por limitaciones objetivas de la plataforma.
    """
    desc = dim.missing_for_next_level or dim.justification or ""

    if "Análisis económico" in dim.dimension:
        if dim.level_percent == 25 and ("Vincular tokens" in desc or "cualitativo" in (dim.justification or "")):
            return "El análisis económico no alcanza un nivel superior porque no dispone de evidencia cuantitativa verificable de consumo y costo por corrida."

    desc = desc.replace("supervisi/on", "supervisión")
    return desc


def format_priority_recommendation(result: EvaluationResult) -> str:
    """
    Formatea la recomendación prioritaria evitando mandatos irreales cuando existe
    una limitación explícita de la plataforma.
    """
    rec = result.concrete_improvement or ""
    dims = result.dimensions or []

    econ_dim = next((d for d in dims if "Análisis económico" in d.dimension), None)
    if econ_dim and econ_dim.level_percent == 25:
        if "Vincular tokens" in rec or "tokens" in rec.lower():
            return "Documentar explícitamente la limitación de medición de consumo/costo y, si la plataforma lo permite en futuras corridas, incorporar evidencia cuantitativa verificable."

    return clean_text(rec)


def clean_text(text: str) -> str:
    """Corrige erratas conocidas en la salida visual."""
    if not text:
        return ""
    return text.replace("supervisi/on", "supervisión")


def generate_student_feedback(result: EvaluationResult) -> Dict[str, Any]:
    """
    Genera la devolución al alumno evaluado de forma 100% determinística
    a partir exclusivamente del objeto EvaluationResult.
    """
    dims = result.dimensions or []
    notes = [clean_text(n) for n in (result.integrity_notes or [])]

    # 1. Resumen General (máximo 3 frases)
    sentences: List[str] = []

    # Frase A / B: Inconsistencias u Holística según score
    if len(notes) > 0:
        sentences.append(
            "Se identificaron inconsistencias objetivas entre los artefactos documentados y el código ejecutable que requieren revisión."
        )
    else:
        score = result.final_score if result.final_score is not None else 0.0
        if score >= 80.0:
            sentences.append("El trabajo presenta una implementación sólida y bien estructurada.")
        elif score >= 50.0:
            sentences.append("El trabajo demuestra un desarrollo funcional con aspectos pendientes de documentación o reproducibilidad.")
        else:
            sentences.append("El repositorio presenta evidencia insuficiente o un desarrollo parcial según los criterios de la rúbrica oficial.")

    # Frase C: Dimensión con mayor avance
    if dims:
        best_dim = max(dims, key=lambda d: (d.level_percent if d.level_percent is not None else 0, d.weight))
        best_lvl = best_dim.level_percent if best_dim.level_percent is not None else 0
        sentences.append(f"La dimensión con mayor avance es **{best_dim.dimension}** ({best_lvl}% de cumplimiento).")

    # Frase D: Oportunidad de mejora
    if dims:
        worst_dim = min(dims, key=lambda d: (d.level_percent if d.level_percent is not None else 0, -d.weight))
        worst_lvl = worst_dim.level_percent if worst_dim.level_percent is not None else 0
        sentences.append(f"La principal oportunidad de mejora se centra en **{worst_dim.dimension}** ({worst_lvl}% de cumplimiento).")

    resumen_general = " ".join(sentences[:3])

    # 2. Clasificación Disjunta de Dimensiones
    # Fortalezas: level_percent >= 75, evidencia no vacía, Y sin contradicción relevante (máx 3)
    fortalezas_candidates = [
        d for d in dims
        if (d.level_percent is not None and d.level_percent >= 75)
        and d.evidence and len(d.evidence) > 0
        and not is_dimension_contradicted(d, notes)
    ]
    fortalezas_candidates.sort(key=lambda d: (d.level_percent or 0, d.weight), reverse=True)
    fortalezas = fortalezas_candidates[:3]

    fortalezas_ids = {id(d) for d in fortalezas}

    # Avances Parciales: level_percent == 50 (máx 2)
    avances_candidates = [
        d for d in dims
        if (d.level_percent is not None and d.level_percent == 50) and id(d) not in fortalezas_ids
    ]
    avances_candidates.sort(key=lambda d: d.weight, reverse=True)
    avances_parciales = avances_candidates[:2]

    avances_ids = {id(d) for d in avances_parciales}

    # Aspectos a Mejorar: level_percent < 100, no en fortalezas ni avances_parciales (máx 3)
    aspectos_candidates = [
        d for d in dims
        if (d.level_percent is not None and d.level_percent < 100)
        and id(d) not in fortalezas_ids
        and id(d) not in avances_ids
    ]
    aspectos_candidates.sort(key=lambda d: (d.level_percent or 0, -d.weight))
    aspectos_a_mejorar = aspectos_candidates[:3]

    # Formatear descripciones
    formatted_fortalezas = [
        {"dimension": d.dimension, "level_percent": d.level_percent, "text": clean_text(d.justification)}
        for d in fortalezas
    ]

    formatted_avances = [
        {"dimension": d.dimension, "level_percent": d.level_percent, "text": clean_text(d.justification)}
        for d in avances_parciales
    ]

    formatted_aspectos = [
        {"dimension": d.dimension, "level_percent": d.level_percent, "text": format_aspect_description(d)}
        for d in aspectos_a_mejorar
    ]

    # 3. Recomendación Prioritaria
    recomendacion_prioritaria = format_priority_recommendation(result)

    return {
        "resumen_general": resumen_general,
        "fortalezas": formatted_fortalezas,
        "avances_parciales": formatted_avances,
        "aspectos_a_mejorar": formatted_aspectos,
        "recomendacion_prioritaria": recomendacion_prioritaria,
        "tiene_contradicciones": len(notes) > 0,
        "contradicciones": notes
    }
