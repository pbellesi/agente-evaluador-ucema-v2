"""Agregaciones puras para la vista resumen de evaluaciones por lote."""

from statistics import mean, median
from typing import Any, Iterable

from src.schema import EvaluationResult


DIMENSION_COUNT = 5


def _is_valid_result(result: EvaluationResult) -> bool:
    """Un resultado válido tiene evaluación terminada y nota final numérica."""
    return result.evaluation_status == "completed" and result.final_score is not None


def _numeric_level(result: EvaluationResult, index: int):
    if index >= len(result.dimensions):
        return None
    level = result.dimensions[index].level_percent
    return float(level) if isinstance(level, (int, float)) else None


def summarize_batch_results(
    results: Iterable[EvaluationResult], approval_threshold: float
) -> dict[str, Any]:
    """Resume resultados existentes sin consultar, reevaluar ni modificarlos."""
    collected_results = list(results)
    valid_results = [result for result in collected_results if _is_valid_result(result)]
    access_error_count = sum(
        result.evaluation_status == "access_error" for result in collected_results
    )
    scores = [float(result.final_score) for result in valid_results]

    dimension_averages = []
    dimension_names = []
    for index in range(DIMENSION_COUNT):
        levels = [
            level
            for result in valid_results
            if (level := _numeric_level(result, index)) is not None
        ]
        dimension_averages.append(mean(levels) if levels else None)
        name = next(
            (
                result.dimensions[index].dimension
                for result in valid_results
                if index < len(result.dimensions) and result.dimensions[index].dimension
            ),
            None,
        )
        dimension_names.append(name)

    approved_count = sum(score >= approval_threshold for score in scores)
    return {
        "processed_count": len(collected_results),
        "valid_count": len(valid_results),
        "access_error_count": access_error_count,
        "mean_score": mean(scores) if scores else None,
        "median_score": median(scores) if scores else None,
        "approved_count": approved_count,
        "approval_rate": approved_count / len(scores) if scores else None,
        "dimension_averages": dimension_averages,
        "dimension_names": dimension_names,
    }
