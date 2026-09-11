import os
import hashlib
from datetime import datetime
from typing import Optional, Callable

from src.schema import EvaluationResult
from src.evidence_extractor import extract_objective_evidence
from src.github_fetcher import GitHubRequestError, fetch_repository_data
from src.zip_repository import ZipRepositoryError, build_repository_data_from_zip


PRIMARY_RATE_LIMIT_MARKER = "[GITHUB_PRIMARY_RATE_LIMIT]"


def rate_limit_access_error_result(repo_url: str) -> EvaluationResult:
    """Resultado aislado para URLs no consultadas tras un límite primario en batch."""
    message = "Límite temporal de consultas a GitHub alcanzado durante este lote. Reintentá más tarde."
    return EvaluationResult(
        repository=repo_url,
        evaluated_revision="unknown",
        evaluation_date=datetime.now().strftime("%Y-%m-%d"),
        evaluation_status="access_error",
        dimensions=[],
        final_score=None,
        concrete_improvement=message,
        integrity_notes=[f"{PRIMARY_RATE_LIMIT_MARKER} {message}"],
    )


def is_primary_rate_limit_result(result: EvaluationResult) -> bool:
    return any(note.startswith(PRIMARY_RATE_LIMIT_MARKER) for note in result.integrity_notes or [])


def evaluate_with_rate_limit_guard(repo_url: str, primary_rate_limit_active: bool) -> tuple[EvaluationResult, bool]:
    """Evita consultas adicionales de batch después de un límite primario confirmado."""
    if primary_rate_limit_active:
        return rate_limit_access_error_result(repo_url), True
    result = run_evaluation(repo_url)
    return result, is_primary_rate_limit_result(result)
from src.deterministic_evaluator import evaluate_repository_deterministically


def _access_error_result(
    repository: str,
    improvement: str,
    integrity_note: str,
    evaluated_revision: str = "unknown",
) -> EvaluationResult:
    return EvaluationResult(
        repository=repository,
        evaluated_revision=evaluated_revision,
        evaluation_date=datetime.now().strftime("%Y-%m-%d"),
        evaluation_status="access_error",
        dimensions=[],
        final_score=None,
        concrete_improvement=improvement,
        integrity_notes=[integrity_note],
    )


def _evaluate_repository_data(
    repo_data: dict,
    status_callback: Optional[Callable[[str], None]] = None,
    diagnostics_callback: Optional[Callable[[dict], None]] = None,
) -> EvaluationResult:
    """Ruta única: repo_data → extractor → motor determinístico → resultado."""
    if status_callback:
        status_callback("Aplicando Matriz de Gates de Evidencia Objetiva en Python...")

    result = evaluate_repository_deterministically(repo_data)

    if diagnostics_callback:
        try:
            evidence = extract_objective_evidence(repo_data)
            retrieval_audit = repo_data.get("retrieval_audit", {})
            diagnostics_callback(
                {
                    "evaluated_revision": result.evaluated_revision,
                    "resolved_ref": repo_data.get("branch"),
                    "repository_inventory_count": len(repo_data.get("repository_inventory", [])),
                    "retrieval": {
                        "source": retrieval_audit.get("source", "GitHub"),
                        "source_filename": retrieval_audit.get("source_filename"),
                        "loaded_count": retrieval_audit.get("loaded_count"),
                        "skipped_count": retrieval_audit.get("skipped_count"),
                        "bytes_loaded": retrieval_audit.get("bytes_loaded"),
                    },
                    "found_dummies": evidence["found_dummies"],
                    "has_dummy_connectors": evidence["has_dummy_connectors"],
                    "system_type": evidence["system_type"],
                    "contradictions": evidence["contradictions"],
                    "invalidated_evidence": evidence["invalidated_evidence"],
                }
            )
        except Exception as error:
            try:
                diagnostics_callback({"diagnostic_error": str(error)})
            except Exception:
                pass

    if status_callback:
        status_callback("Evaluación determinística completada exitosamente.")
    return result


def run_evaluation(
    repo_url: str,
    api_key: Optional[str] = None,
    model_name: str = "deterministic",
    status_callback: Optional[Callable[[str], None]] = None,
    diagnostics_callback: Optional[Callable[[dict], None]] = None,
) -> EvaluationResult:
    """
    Ejecuta la evaluación determinística Zero-API de un repositorio público de GitHub.
    - Carga e inspecciona el árbol y contenido del repositorio objetivo.
    - Aplica la Matriz por Gates de Evidencia Objetiva de rubrica.md V2 en Python.
    - Funciona al 100% sin requerir claves de API generativas.
    - Retorna el contrato Pydantic EvaluationResult.
    """
    if status_callback:
        status_callback("Descargando e inspeccionando árbol del repositorio...")

    # 1. Descargar e inspeccionar datos del repositorio objetivo
    try:
        repo_data = fetch_repository_data(repo_url)
    except GitHubRequestError as error:
        return EvaluationResult(
            repository=repo_url,
            evaluated_revision="unknown",
            evaluation_date=datetime.now().strftime("%Y-%m-%d"),
            evaluation_status="access_error",
            dimensions=[],
            final_score=None,
            concrete_improvement=str(error),
            integrity_notes=[f"[GITHUB_{error.category}] {error}"],
        )
    except Exception as e:
        return EvaluationResult(
            repository=repo_url,
            evaluated_revision="unknown",
            evaluation_date=datetime.now().strftime("%Y-%m-%d"),
            evaluation_status="access_error",
            dimensions=[],
            final_score=None,
            concrete_improvement="Verificar que la URL del repositorio de GitHub sea pública y accesible.",
            integrity_notes=[f"Error al acceder o descargar el repositorio objetivo: {str(e)}"]
        )

    return _evaluate_repository_data(repo_data, status_callback, diagnostics_callback)


def run_zip_evaluation(
    zip_bytes: bytes,
    filename: str,
    status_callback: Optional[Callable[[str], None]] = None,
    diagnostics_callback: Optional[Callable[[dict], None]] = None,
) -> EvaluationResult:
    """Evalúa un ZIP como fuente local sin ejecutar su contenido."""
    if status_callback:
        status_callback("Validando e inventariando archivo ZIP sin ejecutar contenido...")
    zip_sha256 = hashlib.sha256(bytes(zip_bytes)).hexdigest() if isinstance(zip_bytes, (bytes, bytearray)) else "unknown"
    try:
        repo_data = build_repository_data_from_zip(zip_bytes, filename)
    except ZipRepositoryError as error:
        return _access_error_result(
            f"ZIP::{filename}",
            str(error),
            f"[ZIP_INVALID] {error}",
            zip_sha256,
        )
    except Exception as error:
        return _access_error_result(
            f"ZIP::{filename}",
            "No se pudo procesar el archivo ZIP cargado.",
            f"[ZIP_ERROR] {error}",
            zip_sha256,
        )
    return _evaluate_repository_data(repo_data, status_callback, diagnostics_callback)
