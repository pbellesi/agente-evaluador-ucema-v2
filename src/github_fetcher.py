"""Recuperación determinística y auditable de repositorios públicos de GitHub.

No usa APIs generativas. La selección de contenido conserva cobertura mínima de
evidencia antes de expandir el presupuesto disponible.
"""

import io
import os
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, urlparse

import requests


EXCLUDED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf", ".zip", ".tar",
    ".gz", ".7z", ".exe", ".dll", ".so", ".dylib", ".pyc", ".pyo", ".db",
    ".sqlite", ".sqlite3", ".mp4", ".mp3", ".wav", ".avi", ".mov", ".woff",
    ".woff2", ".ttf", ".eot", ".bin", ".dat",
}
EXCLUDED_DIRECTORIES = {
    ".git", "node_modules", "venv", ".venv", "env", "__pycache__",
    "dist", "build", ".idea", ".vscode", ".pytest_cache",
}
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".cs", ".go",
    ".rs", ".rb", ".php", ".sh", ".ps1", ".ipynb",
}
CRITICAL_CATEGORIES = ("structure", "implementation", "documentation", "prompts", "runs", "tests")
EXPANSION_ORDER = ("implementation", "documentation", "prompts", "tests", "runs", "structure", "other")
ECONOMICS_KEYWORDS = ("econom", "costo", "cost", "token", "pricing", "price", "budget", "presupuesto")
GOVERNANCE_KEYWORDS = (
    "gobierno", "governance", "riesgo", "risk", "seguridad", "security", "permiso",
    "permission", "supervision", "supervisión", "control", "auditoria", "auditoría",
)
TRUNCATION_MARKER = b"\n... [TRUNCADO POR LIMITE DE RECUPERACION]"
GITHUB_API_ROOT = "https://api.github.com"


class GitHubRequestError(RuntimeError):
    """Error de acceso a GitHub con categoría segura para usuarios y batch."""

    def __init__(self, category: str, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.category = category
        self.details = details or {}

# Defaults configurables: las cuotas sólo garantizan cobertura durante fase 1.
DEFAULT_RETRIEVAL_CONFIG = {
    "total_budget_bytes": 500 * 1024,
    "max_file_bytes": 64 * 1024,
    "max_archive_file_bytes": 8 * 1024 * 1024,
    "run_file_bytes": 24 * 1024,
    "run_directory_bytes": 32 * 1024,
    "phase1_category_budgets": {
        "structure": 48 * 1024, "implementation": 160 * 1024, "documentation": 88 * 1024,
        "prompts": 32 * 1024, "runs": 96 * 1024, "tests": 48 * 1024, "other": 40 * 1024,
    },
    "phase1_min_files": {
        "structure": 2, "implementation": 6, "documentation": 4,
        "prompts": 2, "runs": 3, "tests": 2, "other": 0,
    },
    # None/ausente permite que fase 2 redistribuya el presupuesto restante.
    "category_max_bytes": {},
}


def _merged_config(overrides: Optional[dict] = None) -> dict:
    config = deepcopy(DEFAULT_RETRIEVAL_CONFIG)
    for key, value in (overrides or {}).items():
        if key in {"phase1_category_budgets", "phase1_min_files", "category_max_bytes"}:
            config[key].update(value)
        else:
            config[key] = value
    return config


def _github_token() -> Optional[str]:
    """Obtiene un token opcional sin exponerlo ni persistirlo."""
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        return token
    try:
        import streamlit as st
        secret = st.secrets.get("GITHUB_TOKEN", "")
        return secret.strip() if isinstance(secret, str) and secret.strip() else None
    except Exception:
        return None


def _github_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "agente-evaluador-ucema",
    }
    token = _github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _header(response, name: str) -> Optional[str]:
    headers = getattr(response, "headers", {}) or {}
    for key, value in headers.items():
        if key.lower() == name.lower():
            return str(value)
    return None


def classify_github_error(response) -> dict:
    """Clasifica respuestas fallidas sin incorporar datos sensibles al mensaje."""
    status_code = int(getattr(response, "status_code", 0) or 0)
    try:
        payload = response.json() or {}
    except Exception:
        payload = {}
    github_message = payload.get("message") if isinstance(payload, dict) else None
    message_lower = str(github_message or "").lower()
    details = {
        "status_code": status_code,
        "rate_limit_limit": _header(response, "X-RateLimit-Limit"),
        "rate_limit_remaining": _header(response, "X-RateLimit-Remaining"),
        "rate_limit_used": _header(response, "X-RateLimit-Used"),
        "rate_limit_reset": _header(response, "X-RateLimit-Reset"),
        "retry_after": _header(response, "Retry-After"),
        "github_message": github_message,
    }
    if status_code == 404:
        category = "NOT_FOUND"
    elif status_code in {403, 429} and details["rate_limit_remaining"] == "0":
        category = "PRIMARY_RATE_LIMIT"
    elif status_code in {403, 429} and (
        details["retry_after"] or "secondary rate limit" in message_lower
    ):
        category = "SECONDARY_RATE_LIMIT"
    elif status_code == 403:
        category = "FORBIDDEN_OTHER"
    else:
        category = "UNKNOWN"
    return {"category": category, **details}


def _github_error_message(details: dict) -> str:
    category = details["category"]
    if category == "PRIMARY_RATE_LIMIT":
        reset = details.get("rate_limit_reset")
        if reset and reset.isdigit():
            reset_at = datetime.fromtimestamp(int(reset), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            return f"Límite temporal de consultas a GitHub alcanzado. Reintentá después de {reset_at}."
        return "Límite temporal de consultas a GitHub alcanzado. Reintentá más tarde."
    if category == "SECONDARY_RATE_LIMIT":
        return "GitHub limitó temporalmente la frecuencia de consultas. Reintentá en unos minutos."
    if category == "FORBIDDEN_OTHER":
        return "GitHub rechazó el acceso al repositorio o recurso solicitado."
    if category == "NOT_FOUND":
        return "GitHub no encontró el repositorio o la referencia solicitada."
    return "GitHub no pudo completar la consulta solicitada."


def _github_get(url: str, timeout: int):
    response = requests.get(url, headers=_github_headers(), timeout=timeout)
    if 200 <= response.status_code < 300:
        return response
    details = classify_github_error(response)
    raise GitHubRequestError(details["category"], _github_error_message(details), details)


def parse_github_url(url: str) -> Tuple[str, str, Optional[str], str]:
    """Retorna owner, repo, referencia solicitada y subruta para URLs GitHub usuales."""
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    parsed = urlparse(cleaned)
    if parsed.netloc.lower() != "github.com":
        raise ValueError(f"URL de GitHub no válida: {url}")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"URL de GitHub no válida: {url}")
    owner, repo = parts[:2]
    revision, subpath = None, ""
    if len(parts) >= 4 and parts[2] == "tree":
        revision, subpath = parts[3], "/".join(parts[4:])
    elif len(parts) >= 4 and parts[2] == "commit":
        revision = parts[3]
    return owner, repo, revision, subpath.strip("/")


def _extension(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def _is_excluded_path(path: str) -> bool:
    return any(part in EXCLUDED_DIRECTORIES for part in path.split("/"))


def _is_text_candidate(path: str) -> bool:
    return _extension(path) not in EXCLUDED_EXTENSIONS


def _path_depth(path: str) -> int:
    return path.count("/")


def _path_labels(path: str, extension: Optional[str] = None) -> List[str]:
    lower = path.lower()
    ext = extension if extension is not None else _extension(path)
    labels: List[str] = []
    if any(keyword in lower for keyword in ECONOMICS_KEYWORDS):
        labels.append("economics")
    if any(keyword in lower for keyword in GOVERNANCE_KEYWORDS):
        labels.extend(["governance", "risk"])
    if any(keyword in lower for keyword in ("arquitect", "architecture")):
        labels.append("architecture")
    if any(keyword in lower for keyword in ("supervision", "supervisión", "human_review", "revision_humana")):
        labels.append("supervision")
    if ext in CODE_EXTENSIONS:
        labels.append("code")
    if ext == ".html":
        labels.append("html_candidate")
    return sorted(set(labels))


def classify_path(path: str, size: int = 0) -> dict:
    """Clasifica una ruta sólo con información determinística de inventario."""
    normalized = path.strip("/")
    lower = normalized.lower()
    ext = _extension(normalized)
    filename = normalized.rsplit("/", 1)[-1].lower()
    root = normalized.split("/", 1)[0].lower()
    if any(token in filename for token in ("readme", "decisiones", "agents", "estado")):
        category = "structure"
    elif root in {"prompts", "prompt"} or "prompt" in filename:
        category = "prompts"
    elif root in {"corridas", "runs", "outputs", "logs"} or any(part in {"corridas", "runs", "outputs", "logs"} for part in lower.split("/")):
        category = "runs"
    elif root in {"tests", "test"} or "/tests/" in f"/{lower}" or "/test/" in f"/{lower}" or "test" in filename:
        category = "tests"
    elif root in {"agente", "agent", "src", "app", "lib", "scripts"} or ext in CODE_EXTENSIONS:
        category = "implementation"
    elif root == "docs" or ext in {".md", ".rst", ".adoc"}:
        category = "documentation"
    else:
        category = "other"
    return {"path": normalized, "size": int(size), "extension": ext, "category": category, "labels": _path_labels(normalized, ext)}


def _entrypoint_rank(record: dict) -> int:
    filename = record["path"].rsplit("/", 1)[-1].lower()
    score = sum(3 for token in ("agent", "client", "provider", "server", "handler", "generator") if token in filename)
    return score + sum(1 for token in ("main", "index", "run", "app") if token in filename)


def _record_sort_key(record: dict) -> tuple:
    labels = set(record.get("labels", []))
    critical = sum(label in labels for label in ("economics", "governance", "risk", "architecture", "supervision"))
    return (-critical, -_entrypoint_rank(record), _path_depth(record["path"]), record["path"].lower())


def _run_group(path: str) -> str:
    parts = path.split("/")
    return "/".join(parts[:2]) if len(parts) > 1 else path


def _run_member_rank(record: dict) -> tuple:
    filename = record["path"].rsplit("/", 1)[-1].lower()
    if "metadata" in filename or "date" in filename or "fecha" in filename:
        rank = 0
    elif "input" in filename or "entrada" in filename:
        rank = 1
    elif any(token in filename for token in ("output", "salida", "result")):
        rank = 2
    elif filename == "run.json" or "run" in filename:
        rank = 3
    else:
        rank = 4
    return rank, _path_depth(record["path"]), record["path"].lower()


def _diverse_implementation_order(records: List[dict]) -> List[dict]:
    grouped: Dict[str, List[dict]] = {}
    for record in sorted(records, key=_record_sort_key):
        grouped.setdefault(record["path"].split("/", 1)[0].lower(), []).append(record)
    ordered: List[dict] = []
    while any(grouped.values()):
        for family in sorted(grouped):
            if grouped[family]:
                ordered.append(grouped[family].pop(0))
    return ordered


def _phase1_order(category: str, records: List[dict]) -> List[dict]:
    if category == "structure":
        def structure_key(record: dict) -> tuple:
            path = record["path"]
            filename = path.rsplit("/", 1)[-1].lower()
            is_root = _path_depth(path) == 0
            if is_root and filename == "readme.md":
                rank = 0
            elif is_root and "decisiones" in filename:
                rank = 1
            elif is_root and ("agents" in filename or "estado" in filename):
                rank = 2
            elif is_root:
                rank = 3
            elif "readme" in filename:
                rank = 4
            else:
                rank = 5
            return rank, _path_depth(path), path.lower()
        return sorted(records, key=structure_key)
    if category == "runs":
        groups: Dict[str, List[dict]] = {}
        for record in records:
            groups.setdefault(_run_group(record["path"]), []).append(record)
        names = sorted(groups)
        sampled = []
        if names:
            sampled.append(names[0])
        if len(names) > 2:
            sampled.append(names[len(names) // 2])
        if len(names) > 1:
            sampled.append(names[-1])
        sampled = list(dict.fromkeys(sampled))
        ordered = [record for name in sampled for record in sorted(groups[name], key=_run_member_rank)]
        remaining = [record for name in names if name not in sampled for record in sorted(groups[name], key=_run_member_rank)]
        return ordered + remaining
    if category == "implementation":
        return _diverse_implementation_order(records)
    return sorted(records, key=_record_sort_key)


def _load_cost(record: dict, config: dict, directory_remaining: Optional[int] = None) -> int:
    if record["size"] > config["max_archive_file_bytes"]:
        return 0
    maximum = config["max_file_bytes"]
    if record["category"] == "runs":
        maximum = min(maximum, config["run_file_bytes"], directory_remaining if directory_remaining is not None else config["run_file_bytes"])
    payload = min(record["size"], maximum)
    if record["size"] > payload:
        payload = max(0, payload - len(TRUNCATION_MARKER)) + len(TRUNCATION_MARKER)
    return payload


def build_retrieval_plan(inventory: List[dict], config_overrides: Optional[dict] = None) -> dict:
    """Selecciona evidencia por cobertura mínima y expansión sin leer contenido."""
    config = _merged_config(config_overrides)
    records = [dict(record) for record in sorted(inventory, key=lambda item: item["path"].lower())]
    selected: Dict[str, dict] = {}
    skipped: Dict[str, dict] = {}
    category_bytes = {category: 0 for category in (*CRITICAL_CATEGORIES, "other")}
    run_directory_bytes: Dict[str, int] = {}
    total = 0
    for record in records:
        if _is_excluded_path(record["path"]):
            skipped[record["path"]] = {**record, "reason": "excluded_directory"}
        elif not _is_text_candidate(record["path"]):
            skipped[record["path"]] = {**record, "reason": "binary"}
        elif record["size"] > config["max_archive_file_bytes"]:
            skipped[record["path"]] = {**record, "reason": "file_too_large"}

    eligible = [record for record in records if record["path"] not in skipped]

    def try_select(record: dict, phase: str, category_budget: Optional[int] = None) -> bool:
        nonlocal total
        path, category = record["path"], record["category"]
        if path in selected or path in skipped:
            return False
        directory = _run_group(path) if category == "runs" else None
        remaining = config["run_directory_bytes"] - run_directory_bytes.get(directory, 0) if directory else None
        if remaining is not None and remaining <= 0:
            return False
        cost = _load_cost(record, config, remaining)
        if cost <= 0 or (category_budget is not None and category_bytes[category] + cost > category_budget):
            return False
        maximum = config["category_max_bytes"].get(category)
        if maximum is not None and category_bytes[category] + cost > maximum:
            return False
        if total + cost > config["total_budget_bytes"]:
            return False
        selected[path] = {**record, "byte_limit": cost, "selection_phase": phase}
        total += cost
        category_bytes[category] += cost
        if directory:
            run_directory_bytes[directory] = run_directory_bytes.get(directory, 0) + cost
        return True

    for category in (*CRITICAL_CATEGORIES, "other"):
        candidates = [record for record in eligible if record["category"] == category]
        minimum = config["phase1_min_files"].get(category, 0)
        selected_count = 0
        for record in _phase1_order(category, candidates):
            if selected_count >= minimum and category != "runs":
                break
            if try_select(record, "phase1", config["phase1_category_budgets"].get(category, 0)):
                selected_count += 1

    for category in EXPANSION_ORDER:
        for record in _phase1_order(category, [item for item in eligible if item["category"] == category]):
            try_select(record, "phase2")

    for record in eligible:
        if record["path"] in selected or record["path"] in skipped:
            continue
        maximum = config["category_max_bytes"].get(record["category"])
        reason = "category_quota" if maximum is not None and category_bytes[record["category"]] >= maximum else "global_budget"
        skipped[record["path"]] = {**record, "reason": reason}
    return {"config": config, "selected": [selected[path] for path in sorted(selected)], "skipped": [skipped[path] for path in sorted(skipped)], "category_bytes_planned": category_bytes}


def _decode_content(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1", errors="replace")


def _coverage(records: Iterable[dict], loaded_paths: set, label: Optional[str] = None, category: Optional[str] = None) -> dict:
    candidates = [record for record in records if (label is None or label in record.get("labels", [])) and (category is None or record["category"] == category)]
    paths = sorted(record["path"] for record in candidates)
    loaded = [path for path in paths if path in loaded_paths]
    return {"status": "loaded" if loaded else ("skipped" if paths else "absent"), "inventory_paths": paths, "loaded_paths": loaded}


def _resolve_revision(owner: str, repo: str, requested_revision: str) -> Tuple[str, str]:
    try:
        response = _github_get(
            f"{GITHUB_API_ROOT}/repos/{owner}/{repo}/commits/{quote(requested_revision, safe='')}",
            timeout=10,
        )
    except GitHubRequestError as error:
        if error.category == "NOT_FOUND":
            raise GitHubRequestError(
                error.category,
                f"No se pudo resolver la referencia '{requested_revision}' en {owner}/{repo}. {error}",
                error.details,
            ) from error
        raise
    sha = response.json().get("sha")
    if sha:
        return requested_revision, sha
    raise GitHubRequestError(
        "UNKNOWN",
        f"GitHub respondió sin SHA al resolver la referencia '{requested_revision}' en {owner}/{repo}.",
    )


def _get_default_branch(owner: str, repo: str) -> str:
    response = _github_get(f"{GITHUB_API_ROOT}/repos/{owner}/{repo}", timeout=10)
    default_branch = response.json().get("default_branch")
    if not isinstance(default_branch, str) or not default_branch.strip():
        raise RuntimeError(f"La metadata de {owner}/{repo} no informa una rama por defecto válida.")
    return default_branch.strip()


def fetch_repository_data(github_url: str, revision: Optional[str] = None, retrieval_config: Optional[dict] = None) -> dict:
    """Descarga branch, tag o SHA y recupera evidencia con cobertura balanceada."""
    owner, repo, url_revision, subpath = parse_github_url(github_url)
    requested_revision = revision if revision is not None else url_revision
    if not requested_revision:
        requested_revision = _get_default_branch(owner, repo)
    resolved_ref, commit_sha = _resolve_revision(owner, repo, requested_revision)
    response = _github_get(f"{GITHUB_API_ROOT}/repos/{owner}/{repo}/zipball/{commit_sha}", timeout=30)
    inventory: List[dict] = []
    zip_members: Dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        if not names:
            raise RuntimeError("El repositorio está vacío.")
        root_prefix = names[0].split("/")[0] + "/"
        for member in archive.infolist():
            if member.is_dir():
                continue
            rel_path = member.filename[len(root_prefix):] if member.filename.startswith(root_prefix) else member.filename
            if subpath:
                if not (rel_path.startswith(subpath + "/") or rel_path == subpath):
                    continue
                target_path = rel_path[len(subpath):].lstrip("/")
            else:
                target_path = rel_path
            if target_path:
                inventory.append(classify_path(target_path, member.file_size))
                zip_members[target_path] = member.filename
        if not inventory:
            raise RuntimeError(f"No se encontraron archivos en la subcarpeta '{subpath}'.")
        inventory.sort(key=lambda record: record["path"].lower())
        plan = build_retrieval_plan(inventory, retrieval_config)
        file_contents: Dict[str, str] = {}
        loaded_files: List[dict] = []
        truncated_files: List[dict] = []
        bytes_loaded = 0
        for selected in plan["selected"]:
            try:
                raw_bytes = archive.read(zip_members[selected["path"]])
                truncated = len(raw_bytes) > selected["byte_limit"]
                if truncated:
                    raw_bytes = raw_bytes[:max(0, selected["byte_limit"] - len(TRUNCATION_MARKER))] + TRUNCATION_MARKER
                file_contents[selected["path"]] = _decode_content(raw_bytes)
                item = {"path": selected["path"], "size": selected["size"], "category": selected["category"], "bytes_loaded": len(raw_bytes), "truncated": truncated, "selection_phase": selected["selection_phase"]}
                loaded_files.append(item)
                bytes_loaded += len(raw_bytes)
                if truncated:
                    truncated_files.append(item)
            except Exception as error:
                plan["skipped"].append({**selected, "reason": "read_error", "error": str(error)})

    loaded_paths = set(file_contents)
    skipped_files = []
    for record in plan["skipped"]:
        clean = {key: value for key, value in record.items() if key not in {"byte_limit", "selection_phase", "error"}}
        if "error" in record:
            clean["error"] = record["error"]
        skipped_files.append(clean)
    skipped_files.sort(key=lambda record: record["path"].lower())
    categories = {}
    for category in (*CRITICAL_CATEGORIES, "other"):
        records = [record for record in inventory if record["category"] == category]
        categories[category] = {"discovered": len(records), "loaded": sum(record["path"] in loaded_paths for record in records), "skipped": sum(record["path"] not in loaded_paths for record in records), "bytes_loaded": sum(item["bytes_loaded"] for item in loaded_files if item["category"] == category)}
    retrieval_audit = {
        "retrieval_version": "coverage-v1", "evaluated_revision": commit_sha, "requested_revision": requested_revision,
        "resolved_ref": resolved_ref, "budget_bytes": plan["config"]["total_budget_bytes"], "bytes_loaded": bytes_loaded,
        "discovered_count": len(inventory), "loaded_count": len(loaded_files), "skipped_count": len(skipped_files),
        "categories": categories, "loaded_files": sorted(loaded_files, key=lambda item: item["path"].lower()),
        "skipped_files": skipped_files, "truncated_files": sorted(truncated_files, key=lambda item: item["path"].lower()),
        "critical_coverage": {
            "implementation": _coverage(inventory, loaded_paths, category="implementation"),
            "economics": _coverage(inventory, loaded_paths, label="economics"),
            "governance": _coverage(inventory, loaded_paths, label="governance"),
            "prompts": _coverage(inventory, loaded_paths, category="prompts"),
            "runs": _coverage(inventory, loaded_paths, category="runs"),
            "tests": _coverage(inventory, loaded_paths, category="tests"),
        },
    }
    tree_inventory = "\n".join(f"{record['path']} ({record['size']} bytes)" for record in inventory)
    formatted_parts = [f"=== TRABAJO EVALUADO: {os.path.basename(subpath) if subpath else f'{owner}/{repo}'} ===", tree_inventory, "\n=== CONTENIDO DE ARCHIVOS INSPECCIONADOS ==="]
    for path in sorted(file_contents):
        formatted_parts.extend([f"\n--- ARCHIVO: {path} ---", file_contents[path]])
    canonical_repo_id = f"{owner}/{repo}::{subpath}" if subpath else f"{owner}/{repo}"
    return {
        "repository": canonical_repo_id, "display_name": os.path.basename(subpath) if subpath else f"{owner}/{repo}",
        "branch": resolved_ref, "commit_sha": commit_sha, "evaluated_revision": commit_sha, "subpath": subpath,
        "repository_inventory": inventory, "tree_inventory": tree_inventory, "file_contents": file_contents,
        "skipped_files": skipped_files, "retrieval_audit": retrieval_audit, "formatted_context": "\n".join(formatted_parts),
    }
