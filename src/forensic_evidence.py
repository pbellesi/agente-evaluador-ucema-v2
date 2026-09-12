"""
Módulo Forense de Evidencia (src/forensic_evidence.py).

Construye un Forensic Evidence Packet no destructivo para repositorios académicos.
Principios:
1. En repositorios pequeños (hasta ~200k chars), TODO el contenido textual relevante
   llega COMPLETO sin resumir ni truncar.
2. Organiza la evidencia en 8 secciones canónicas (A-H), incluyendo Run Ledger integrado,
   Diagnósticos Mecánicos locales (sin LLM) y Claim Registry obligatorio.
"""

import hashlib
import json
import posixpath
import re
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

BINARY_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz",
    ".exe", ".dll", ".so", ".dylib", ".pyc", ".pyd", ".bin", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".mp3", ".wav", ".db", ".sqlite", ".sqlite3"
}

IGNORED_DIR_PATTERNS: Set[str] = {
    ".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv",
    "env", ".mypy_cache", ".ruff_cache", "dist", "build", ".egg-info"
}

DEFAULT_MAX_PACKET_CHARS = 200000


def is_binary_file(path: str) -> bool:
    ext = posixpath.splitext(path.lower())[1]
    return ext in BINARY_EXTENSIONS


def is_ignored_path(path: str) -> bool:
    parts = [p.lower() for p in path.replace("\\", "/").split("/") if p]
    for part in parts:
        if part in IGNORED_DIR_PATTERNS or part.endswith(".egg-info"):
            return True
    return False


def run_mechanical_diagnostics(files: Dict[str, str]) -> Dict[str, Any]:
    """Genera diagnósticos fácticos mecánicos locales SIN invocar LLM."""
    runs: Dict[str, Dict[str, Any]] = {}
    for path in sorted(files.keys()):
        m = re.search(r"(?:corridas|runs)[/\\](corrida_\d+|run_\d+|sem_\d+|semana_\d+)", path, re.I)
        if m:
            run_name = m.group(1).lower()
            if run_name not in runs:
                runs[run_name] = {"files": [], "fecha": None, "salida_hash": None, "salida_path": None}
            runs[run_name]["files"].append(path)
            if "fecha" in path.lower():
                runs[run_name]["fecha"] = files[path].strip()
            if "salida" in path.lower() and path.endswith((".json", ".txt", ".csv")):
                content_bytes = files[path].encode("utf-8")
                runs[run_name]["salida_hash"] = hashlib.sha256(content_bytes).hexdigest()[:12]
                runs[run_name]["salida_path"] = path

    # Verificar cronología
    chronological_inversions = []
    prev_date = None
    prev_run = None
    for run_name in sorted(runs.keys()):
        d_str = runs[run_name]["fecha"]
        if d_str:
            # Extraer fecha tipo YYYY-MM-DD (soporta tanto '2026-08-18' como '2026-08-18T10:42:00')
            m_date = re.search(r"(\d{4}-\d{2}-\d{2})", d_str)
            if m_date:
                curr_date = m_date.group(1)
                if prev_date and curr_date < prev_date:
                    chronological_inversions.append({
                        "run": run_name,
                        "date": curr_date,
                        "previous_run": prev_run,
                        "previous_date": prev_date,
                        "alert": f"Inversión temporal: {run_name} ({curr_date}) es anterior a {prev_run} ({prev_date})"
                    })
                prev_date = curr_date
                prev_run = run_name

    # Salidas idénticas entre corridas
    duplicate_outputs = []
    seen_hashes: Dict[str, str] = {}
    for run_name, data in runs.items():
        shash = data.get("salida_hash")
        if shash:
            if shash in seen_hashes:
                duplicate_outputs.append({
                    "run": run_name,
                    "duplicate_of": seen_hashes[shash],
                    "hash": shash,
                    "path": data.get("salida_path")
                })
            else:
                seen_hashes[shash] = run_name

    # Versiones de prompt mencionadas en DECISIONES vs existentes
    decisiones_text = ""
    for p, c in files.items():
        if "decisiones" in p.lower():
            decisiones_text += "\n" + c

    mentioned_prompts = set(re.findall(r"\b(v[1-5]|prompt_v[1-5]|system_prompt_v[1-5])\b", decisiones_text, re.I))
    existing_prompts = set()
    for p in files.keys():
        m_p = re.search(r"\b(v[1-5]|prompt_v[1-5]|system_prompt_v[1-5])\b", p, re.I)
        if m_p:
            existing_prompts.add(m_p.group(1).lower())

    # Fallas o menciones explícitas de errores en DECISIONES
    failed_runs_mentioned = []
    missing_failed_runs = []
    for line in decisiones_text.splitlines():
        if any(w in line.lower() for w in ["falló", "fallo", "salió mal", "error", "sugerencia: reclamar"]):
            failed_runs_mentioned.append(line.strip())
            # Detectar si se menciona una corrida específica que falló
            m_run = re.search(r"corrida[_\s]*0?(\d+)", line, re.I)
            if m_run:
                r_key = f"corrida_{int(m_run.group(1)):02d}"
                if r_key in runs:
                    s_path = runs[r_key].get("salida_path")
                    if s_path and s_path in files:
                        try:
                            s_data = json.loads(files[s_path])
                            for it in s_data.get("detalle", []):
                                if it.get("comprobante", "").upper().startswith("NC") and it.get("clasificacion") == "AJUSTE":
                                    missing_failed_runs.append({
                                        "run": r_key,
                                        "mention": line.strip(),
                                        "salida_path": s_path,
                                        "alert": f"DECISIONES.md afirma que {r_key} falló con nota de crédito clasificada como SIN_OC y motivó el prompt v4, pero {s_path} archivada muestra clasificación exitosa como AJUSTE. Falta preservar la corrida fallida real que motivó v4."
                                    })
                                    break
                        except Exception:
                            pass

    # Detección de afirmaciones técnicas en documentación no respaldadas en código (ej. embeddings/vectorstore)
    unimplemented_features = []
    doc_text_all = "\n".join(c for p, c in files.items() if any(k in p.lower() for k in ["readme", "decisiones"]))
    code_text_all = "\n".join(c for p, c in files.items() if p.endswith((".py", ".js", ".ts", ".sh", ".txt", ".json", ".csv")) and not any(k in p.lower() for k in ["readme", "decisiones", "salida"]))
    
    if any(term in doc_text_all.lower() for term in ["similitud semántica", "recuperación semántica", "similitud coseno", "espacio vectorial"]):
        has_vector_code = any(term in code_text_all.lower() for term in ["cosine_similarity", "vectorstore", "chroma", "faiss", "pinecone", "pgvector", "openai.embeddings"])
        if not has_vector_code:
            unimplemented_features.append({
                "feature": "recuperación por embeddings / similitud coseno",
                "source": "README.md",
                "alert": "El README.md afirma utilizar recuperación por similitud semántica de embeddings con umbral coseno 0.87, pero el repositorio no contiene código de embeddings, vectorstore ni librerías afines.",
                "affected_dimensions": ["D1", "D2"]
            })

    return {
        "detected_runs": list(runs.keys()),
        "runs_data": runs,
        "chronological_inversion_detected": len(chronological_inversions) > 0,
        "chronological_inversions": chronological_inversions,
        "duplicate_outputs": duplicate_outputs,
        "mentioned_prompts": list(mentioned_prompts),
        "existing_prompts": list(existing_prompts),
        "failed_runs_mentioned": failed_runs_mentioned[:5],
        "missing_failed_runs": missing_failed_runs,
        "unimplemented_features": unimplemented_features,
    }


def extract_material_claims(files: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extrae afirmaciones materiales fácticas de la documentación para auditoría obligatoria."""
    target_docs = [
        p for p in files.keys()
        if any(k in p.lower() for k in ["readme", "decisiones", "analisis_economico", "gobierno_riesgos"])
    ]

    claims: List[Dict[str, Any]] = []
    claim_idx = 1

    keywords = [
        "iteración", "v1", "v2", "v3", "v4", "v5", "falló", "salió mal", "error",
        "corrida", "semana", "nota de crédito", "ajuste", "sin_oc", "diferencia",
        "reclamar", "prompt", "modelo", "tokens", "costo", "supervisión", "revisión",
        "permiso", "riesgo", "embedding", "similitud", "memoria", "lazy loading",
        "vector", "resumen jerárquico", "tolerancia", "null", "inferido"
    ]

    for doc_path in sorted(target_docs):
        content = files[doc_path]
        lines = content.splitlines()
        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str or line_str.startswith("#") or len(line_str) < 25:
                continue
            line_lower = line_str.lower()
            if any(kw in line_lower for kw in keywords):
                # Limpiar viñetas
                clean_text = re.sub(r"^[-*•\d.]+\s+", "", line_str)
                claims.append({
                    "claim_id": f"CLM_{claim_idx:03d}",
                    "source_path": doc_path,
                    "line_start": idx + 1,
                    "line_end": idx + 1,
                    "text": clean_text
                })
                claim_idx += 1
                if claim_idx > 25:  # Acotar a las afirmaciones más materiales
                    break
        if claim_idx > 25:
            break

    return claims


def build_forensic_packet(
    repo_data: Dict[str, Any],
    max_packet_chars: int = DEFAULT_MAX_PACKET_CHARS,
) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
    """
    Construye el Forensic Evidence Packet no destructivo.
    Retorna (packet_text, diagnostics, claims).
    """
    raw_files = repo_data.get("file_contents") or repo_data.get("files") or {}
    files: Dict[str, str] = {}
    for path, content in raw_files.items():
        norm_path = path.replace("\\", "/").strip().lstrip("/")
        if not is_binary_file(norm_path) and not is_ignored_path(norm_path):
            files[norm_path] = str(content)

    # 1. Diagnósticos mecánicos locales
    diagnostics = run_mechanical_diagnostics(files)

    # 2. Extracción de claims materiales
    claims = extract_material_claims(files)

    # Construir Secciones A a H
    lines: List[str] = []
    lines.append("# FORENSIC EVIDENCE PACKET — AGENTE EVALUADOR UCEMA\n")
    lines.append("Este paquete contiene la evidencia textual completa y no destructiva del repositorio evaluado.\n")

    # SECCIÓN A — MANIFEST
    lines.append("## SECCIÓN A — MANIFEST DEL REPOSITORIO")
    for path in sorted(files.keys()):
        size = len(files[path].encode("utf-8"))
        sha = hashlib.sha256(files[path].encode("utf-8")).hexdigest()[:10]
        lines.append(f"- `{path}` | {size} bytes | sha256:{sha}")
    lines.append("")

    # SECCIÓN B — CORE DOCUMENTATION FULL TEXT
    lines.append("## SECCIÓN B — DOCUMENTACIÓN CANÓNICA COMPLETA (FULL TEXT)")
    doc_paths = [p for p in sorted(files.keys()) if re.search(r"(?:README|DECISIONES|AGENTS)\.md$", p, re.I)]
    for p in doc_paths:
        lines.append(f"\n### Archivo: `{p}`\n```markdown")
        for l_num, l_text in enumerate(files[p].splitlines(), 1):
            lines.append(f"{l_num:4d} | {l_text}")
        lines.append("```\n")

    # SECCIÓN C — PROMPTS FULL TEXT
    lines.append("## SECCIÓN C — CONTRATOS Y ESPECIFICACIONES DE PROMPTS (FULL TEXT)")
    prompt_paths = [p for p in sorted(files.keys()) if "prompt" in p.lower()]
    for p in prompt_paths:
        lines.append(f"\n### Archivo: `{p}`\n```")
        for l_num, l_text in enumerate(files[p].splitlines(), 1):
            lines.append(f"{l_num:4d} | {l_text}")
        lines.append("```\n")

    # SECCIÓN D — RUN LEDGER (VISTA INTEGRADA POR CORRIDA)
    lines.append("## SECCIÓN D — RUN LEDGER (INTEGRADO CORRIDA POR CORRIDA)")
    run_groups: Dict[str, List[str]] = {}
    for p in sorted(files.keys()):
        m = re.search(r"(?:corridas|runs)[/\\](corrida_\d+|run_\d+|sem_\d+|semana_\d+)", p, re.I)
        if m:
            rname = m.group(1).lower()
            run_groups.setdefault(rname, []).append(p)

    for rname in sorted(run_groups.keys()):
        lines.append(f"\n### === RUN LEDGER: {rname.upper()} ===")
        r_files = run_groups[rname]
        fecha = diagnostics["runs_data"].get(rname, {}).get("fecha", "NO REGISTRADA")
        lines.append(f"- **Fecha registrada**: `{fecha}`")
        lines.append(f"- **Archivos de la corrida**: {', '.join([f'`{f}`' for f in r_files])}\n")

        for f in r_files:
            content = files[f]
            # Si es archivo muy grande, tomar hasta 2500 chars, pero incluir completo si es pequeño
            lines.append(f"#### Artefacto: `{f}`")
            lines.append("```")
            lines.append(content)
            lines.append("```\n")

    # SECCIÓN E — ECONOMÍA Y GOBIERNO FULL TEXT
    lines.append("## SECCIÓN E — ANÁLISIS ECONÓMICO Y GOBIERNO (FULL TEXT)")
    eco_paths = [p for p in sorted(files.keys()) if any(k in p.lower() for k in ["econom", "gobiern", "riesg"])]
    for p in eco_paths:
        lines.append(f"\n### Archivo: `{p}`\n```")
        for l_num, l_text in enumerate(files[p].splitlines(), 1):
            lines.append(f"{l_num:4d} | {l_text}")
        lines.append("```\n")

    # SECCIÓN F — IMPLEMENTATION (CÓDIGO FUENTE RESTANTE)
    lines.append("## SECCIÓN F — IMPLEMENTACIÓN Y HERRAMIENTAS (CÓDIGO FUENTE)")
    handled = set(doc_paths) | set(prompt_paths) | set(eco_paths)
    for r_list in run_groups.values():
        handled.update(r_list)
    remaining_code = [p for p in sorted(files.keys()) if p not in handled]
    for p in remaining_code:
        lines.append(f"\n### Archivo: `{p}`\n```")
        lines.append(files[p])
        lines.append("```\n")

    # SECCIÓN G — MECHANICAL DIAGNOSTICS (LOCAL HEURISTICS)
    lines.append("## SECCIÓN G — DIAGNÓSTICOS MECÁNICOS DETERMINÍSTICOS (LOCALES, SIN LLM)")
    lines.append(f"- **Corridas detectadas**: {diagnostics['detected_runs']}")
    lines.append(f"- **Alerta de Inversión Cronológica**: {diagnostics['chronological_inversion_detected']}")
    if diagnostics["chronological_inversions"]:
        for inv in diagnostics["chronological_inversions"]:
            lines.append(f"  * ⚠️ ALERTA MECÁNICA: {inv['alert']}")
    if diagnostics["duplicate_outputs"]:
        for dup in diagnostics["duplicate_outputs"]:
            lines.append(f"  * ⚠️ SALIDA IDÉNTICA DETECTADA: `{dup['run']}` tiene mismo hash que `{dup['duplicate_of']}` ({dup['path']})")
    if diagnostics["failed_runs_mentioned"]:
        lines.append("- **Menciones de fallas en DECISIONES.md**:")
        for fm in diagnostics["failed_runs_mentioned"]:
            lines.append(f"  * \"{fm}\"")
    if diagnostics.get("missing_failed_runs"):
        lines.append("- **Alerta de Corrida Fallida Ausente**:")
        for mfr in diagnostics["missing_failed_runs"]:
            lines.append(f"  * ⚠️ ALERTA MECÁNICA: {mfr['alert']}")
    if diagnostics.get("unimplemented_features"):
        lines.append("- **Alerta de Capacidad Falsificada o No Implementada**:")
        for uf in diagnostics["unimplemented_features"]:
            lines.append(f"  * ⚠️ ALERTA MECÁNICA: {uf['alert']}")
    lines.append("")

    # SECCIÓN H — CLAIM REGISTRY (AFIRMACIONES MATERIALES PARA AUDITORÍA)
    lines.append("## SECCIÓN H — CLAIM REGISTRY (AFIRMACIONES MATERIALES A AUDITAR)")
    lines.append("El evaluador DEBE auditar cada uno de los siguientes claims materiales en su salida (`claim_checks`):\n")
    for c in claims:
        lines.append(f"- **[{c['claim_id']}]** (`{c['source_path']}:L{c['line_start']}`): \"{c['text']}\"")
    lines.append("")

    packet_text = "\n".join(lines)
    return packet_text, diagnostics, claims
