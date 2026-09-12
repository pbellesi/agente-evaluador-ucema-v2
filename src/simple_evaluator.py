"""
Módulo Evaluador Principal (src/simple_evaluator.py).

ARQUITECTURA FINAL OFICIAL:
ZIP/GITHUB -> INGESTA LOCAL -> EVIDENCE DOSSIER -> UNA LLAMADA GEMINI -> VALIDACIÓN -> SCORING DETERMINÍSTICO.

Principios:
- Normal path: EXACTAMENTE UNA llamada LLM por evaluación.
- Repair path: Máximo una segunda llamada LLM ante inconsistencia interna (100 con PARTIAL/MISSING/CONTRADICTED).
- Cero loops de tools. Cero fallback automático entre modelos.
- Identidad inequívoca: RUNTIME_FINGERPRINT calculado a partir de los archivos nucleares.
- Cache determinístico por SHA-256 de contenido, fingerprint de runtime, modelo exacto y hashes de prompt/rúbrica.
- Instrumentación detallada de tiempos y métricas.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evidence_dossier import build_evidence_dossier
from src.evaluation_validator import (
    InconsistentEvaluationError,
    validate_and_score_evaluation,
)
from src.schema import EvaluationResult
from src.semantic_judge import (
    SemanticJudgeConfigError,
    SemanticJudgeEvaluationError,
    resolve_gemini_api_key,
    resolve_gemini_model,
)
from src.semantic_schema import SimpleEvaluationPayload
from src.zip_repository import extract_files_from_zip

EVALUATION_CACHE: Dict[str, EvaluationResult] = {}


def get_runtime_fingerprint(project_root: Optional[Path] = None) -> str:
    """
    Calcula automáticamente el RUNTIME_FINGERPRINT a partir del contenido SHA-256 de:
    - app_v2.py
    - src/simple_evaluator.py
    - src/evidence_dossier.py
    - src/evaluation_validator.py
    - agente/system_prompt.md
    - rubrica.md
    Normaliza saltos de línea CRLF/LF para garantizar paridad exacta entre Windows y Linux.
    Retorna los primeros 12 caracteres hexadecimales.
    """
    root = project_root or PROJECT_ROOT
    target_files = [
        root / "app_v2.py",
        root / "src" / "simple_evaluator.py",
        root / "src" / "evidence_dossier.py",
        root / "src" / "evaluation_validator.py",
        root / "agente" / "system_prompt.md",
        root / "rubrica.md",
    ]
    hasher = hashlib.sha256()
    for file_path in target_files:
        if file_path.is_file():
            hasher.update(file_path.name.encode("utf-8"))
            content = file_path.read_bytes().replace(b"\r\n", b"\n")
            hasher.update(content)
        else:
            hasher.update(f"missing:{file_path.name}".encode("utf-8"))
    return hasher.hexdigest()[:12]


def clear_evaluation_cache() -> int:
    """Limpia todos los resultados de evaluación cacheados en memoria."""
    count = len(EVALUATION_CACHE)
    EVALUATION_CACHE.clear()
    return count


def load_system_prompt() -> str:
    """Carga el System Prompt canónico oficial desde agente/system_prompt.md."""
    prompt_path = PROJECT_ROOT / "agente" / "system_prompt.md"
    if prompt_path.is_file():
        try:
            return prompt_path.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""


def load_rubric_text() -> str:
    """Carga el texto normativo de la rúbrica académica oficial desde rubrica.md."""
    rubric_path = PROJECT_ROOT / "rubrica.md"
    if rubric_path.is_file():
        try:
            return rubric_path.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""


def compute_content_sha256(repo_data: Dict[str, Any]) -> str:
    """Calcula el SHA-256 de los contenidos y estructura del repositorio para cachear."""
    if repo_data.get("commit_sha"):
        return str(repo_data["commit_sha"])
    hasher = hashlib.sha256()
    files = repo_data.get("file_contents") or repo_data.get("files") or {}
    for p in sorted(files.keys()):
        hasher.update(p.encode("utf-8"))
        hasher.update(files[p].encode("utf-8"))
    return hasher.hexdigest()


def compute_cache_key(
    content_sha: str,
    runtime_fingerprint: str,
    model_name: str,
    prompt_text: str,
    rubric_text: str,
) -> str:
    """Genera una clave única de caché que invalida si cambia el contenido, el runtime fingerprint, el modelo, el prompt o la rúbrica."""
    prompt_hash = hashlib.sha256(prompt_text.replace("\r\n", "\n").encode("utf-8")).hexdigest()[:12]
    rubric_hash = hashlib.sha256(rubric_text.replace("\r\n", "\n").encode("utf-8")).hexdigest()[:12]
    return f"{content_sha}:{runtime_fingerprint}:{model_name}:{prompt_hash}:{rubric_hash}"


def _extract_payload_from_response(response: Any) -> SimpleEvaluationPayload:
    """Extrae de manera robusta el SimpleEvaluationPayload de la respuesta de Gemini."""
    if hasattr(response, "parsed") and isinstance(response.parsed, SimpleEvaluationPayload):
        return response.parsed
    if hasattr(response, "parsed") and isinstance(response.parsed, dict):
        return SimpleEvaluationPayload.model_validate(response.parsed)

    raw_text = getattr(response, "text", "") or ""
    if not raw_text and hasattr(response, "candidates") and response.candidates:
        for part in reversed(response.candidates[0].content.parts):
            if getattr(part, "text", None):
                raw_text = part.text
                break

    if raw_text:
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return SimpleEvaluationPayload.model_validate_json(cleaned.strip())

    raise ValueError(f"No se pudo extraer JSON estructurado de la respuesta: {response}")


def evaluate_repository_simple(
    repo_data: dict,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    client: Optional[object] = None,
    use_cache: bool = True,
    system_instruction: Optional[str] = None,
    rubric_text: Optional[str] = None,
) -> EvaluationResult:
    """
    Evalúa un repositorio en UNA llamada LLM mediante Evidence Dossier estructurado
    y validación determinística en Python con pesos oficiales.
    """
    t_start = time.time()

    resolved_key = resolve_gemini_api_key(api_key)
    if not resolved_key and client is None:
        raise SemanticJudgeConfigError(
            "Variable de entorno GEMINI_API_KEY no configurada. "
            "Definí GEMINI_API_KEY en tu entorno o en Streamlit secrets."
        )

    # Resolución de modelo único y runtime fingerprint
    resolved_model = resolve_gemini_model(model_name) or "gemini-3.5-flash-lite"
    runtime_fingerprint = get_runtime_fingerprint()

    # Carga canónica de prompt y rúbrica
    system_prompt = load_system_prompt() if system_instruction is None else system_instruction
    rubric_normative = load_rubric_text() if rubric_text is None else rubric_text

    full_system_instruction = (
        f"{system_prompt}\n\n"
        f"--- RÚBRICA ACADÉMICA OFICIAL (rubrica.md) ---\n\n"
        f"{rubric_normative}"
    )

    # 1. Comprobación de Caché estricto
    content_sha = compute_content_sha256(repo_data)
    cache_key = compute_cache_key(
        content_sha=content_sha,
        runtime_fingerprint=runtime_fingerprint,
        model_name=resolved_model,
        prompt_text=system_prompt,
        rubric_text=rubric_normative,
    )

    if use_cache and cache_key in EVALUATION_CACHE:
        cached_result = EVALUATION_CACHE[cache_key]
        return cached_result

    # 2. Ingesta Local y Construcción del Evidence Dossier
    t_dossier_start = time.time()
    dossier_text, dossier_metrics = build_evidence_dossier(repo_data)
    dossier_seconds = round(time.time() - t_dossier_start, 3)

    repo_label = repo_data.get("repo_url") or repo_data.get("zip_name") or repo_data.get("display_name") or "repositorio"

    user_content = (
        f"Se te asigna la evaluación académica del repositorio '{repo_label}'.\n\n"
        f"{dossier_text}\n\n"
        "--- INSTRUCCIONES DE AUDITORÍA Y CALIFICACIÓN ---\n"
        "Aplicá rigurosamente las 4 Fases (Comprender, Auditar, Checklist de Requisitos, Scoring):\n"
        "1. Realizá la auditoría de cada dimensión (D1 a D5).\n"
        "2. Para cada dimensión, antes de fijar el nivel, completá el checklist de requisitos máximos (MET, PARTIAL, MISSING, CONTRADICTED).\n"
        "3. Recordá el guardrail crítico: si algún requisito es PARTIAL, MISSING o CONTRADICTED, el nivel 100% está ESTRICTAMENTE PROHIBIDO.\n"
        "4. Asigná los niveles estrictamente en {0, 25, 50, 75, 100}.\n"
        "5. Emití el payload estructurado con justificaciones fácticas basadas en la evidencia del dossier."
    )

    # 3. Inicializar cliente Gemini
    if client is not None:
        genai_client = client
    else:
        from google import genai
        genai_client = genai.Client(api_key=resolved_key)

    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=full_system_instruction,
        response_mime_type="application/json",
        response_schema=SimpleEvaluationPayload,
        temperature=0.0,
    )

    # 4. LLM Call 1 (Normal Path - EXACTAMENTE UNA LLAMADA AL MODELO FIJO)
    llm_calls = 1
    t_llm_start = time.time()

    try:
        response = genai_client.models.generate_content(
            model=resolved_model,
            contents=user_content,
            config=config,
        )
    except Exception as exc:
        raise SemanticJudgeEvaluationError(f"Fallo al evaluar repositorio con Gemini ({resolved_model}): {exc}") from exc

    llm_seconds = round(time.time() - t_llm_start, 2)
    payload = _extract_payload_from_response(response)

    # 5. Validación Determinística y Guardrail de Consistencia
    t_val_start = time.time()
    evaluation_result = None

    try:
        evaluation_result = validate_and_score_evaluation(
            payload=payload,
            repo_data=repo_data,
            actual_model_used=resolved_model,
            runtime_fingerprint=runtime_fingerprint,
        )
    except InconsistentEvaluationError as inconsistency_error:
        # 6. Repair Path: Máximo UNA llamada de reparación si hay inconsistencia interna
        repair_message = (
            f"Tu evaluación previa presentó la siguiente inconsistencia interna de contrato:\n"
            f"{inconsistency_error}\n\n"
            "RECORDATORIO NORMATIVO OBLIGATORIO:\n"
            "Si en tu checklist de requisitos marcaste algún requisito como PARTIAL, MISSING o CONTRADICTED, "
            "está ESTRICTAMENTE PROHIBIDO asignar 100% a esa dimensión.\n"
            "Reaplicá rubrica.md, corregí el nivel asignado para reflejar fielmente tu propia auditoría "
            "y devolvé el payload estructurado corregido."
        )

        t_repair_start = time.time()
        llm_calls += 1

        repair_response = genai_client.models.generate_content(
            model=resolved_model,
            contents=[user_content, response.text if hasattr(response, "text") else "", repair_message],
            config=config,
        )
        llm_seconds += round(time.time() - t_repair_start, 2)

        repaired_payload = _extract_payload_from_response(repair_response)
        evaluation_result = validate_and_score_evaluation(
            payload=repaired_payload,
            repo_data=repo_data,
            actual_model_used=resolved_model,
            runtime_fingerprint=runtime_fingerprint,
        )
        evaluation_result.integrity_notes.append("[REPAIR_CALL] Se ejecutó 1 llamada de corrección por inconsistencia interna.")

    validation_seconds = round(time.time() - t_val_start, 3)
    total_seconds = round(time.time() - t_start, 2)

    # Adjuntar telemetría y métricas operativas a integrity_notes
    telemetry_note = (
        f"[TELEMETRÍA] runtime={runtime_fingerprint}, model={resolved_model}, llm_calls={llm_calls}, "
        f"dossier_chars={dossier_metrics['dossier_chars']}, dossier_s={dossier_seconds}, "
        f"llm_s={llm_seconds}, val_s={validation_seconds}, total_s={total_seconds}"
    )
    evaluation_result.integrity_notes.append(telemetry_note)

    # Guardar en caché estricto
    if use_cache:
        EVALUATION_CACHE[cache_key] = evaluation_result

    return evaluation_result


def evaluate_project_zip(
    zip_source: Any,
    zip_name: str = "proyecto.zip",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    client: Optional[object] = None,
    use_cache: bool = True,
) -> EvaluationResult:
    """
    Punto de entrada de alto nivel para evaluar un archivo ZIP en memoria.
    """
    t_ingest_start = time.time()
    repo_data = extract_files_from_zip(zip_source, zip_name)
    ingest_seconds = round(time.time() - t_ingest_start, 3)

    result = evaluate_repository_simple(
        repo_data=repo_data,
        api_key=api_key,
        model_name=model_name,
        client=client,
        use_cache=use_cache,
    )

    result.integrity_notes.append(f"[INGESTA_ZIP] ingest_s={ingest_seconds}")
    return result
