"""
Evidence Dossier Module (src/evidence_dossier.py).

Responsabilidad única: Extraer y organizar evidencia del repositorio localmente
de forma estructurada, compacta y neutral para alimentar a Gemini en UNA llamada.

PRINCIPIOS:
- NO CALIFICAR ni decidir niveles.
- NO inferir calidad.
- No asumir lenguaje específico (soporta Python, JS/TS, prompts+tools, no-code, conectores, YAML/JSON).
- Control estricto de tamaño (~30.000 a 70.000 caracteres, máximo ~90.000).
- Exclusión estricta de binarios, .git, caches, build artifacts.
"""

import json
import posixpath
import re
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

# Límites de presupuesto por defecto (en caracteres)
DEFAULT_MAX_DOSSIER_CHARS: int = 80000
DEFAULT_MAX_FILE_CHARS: int = 6000
DEFAULT_RUN_FILE_CHARS: int = 4000


def is_binary_file(path: str) -> bool:
    """Detecta si un archivo es binario por su extensión."""
    ext = posixpath.splitext(path.lower())[1]
    return ext in BINARY_EXTENSIONS


def is_ignored_path(path: str) -> bool:
    """Verifica si la ruta corresponde a directorios de cache, build o VCS."""
    parts = [p.lower() for p in path.replace("\\", "/").split("/") if p]
    for part in parts:
        if part in IGNORED_DIR_PATTERNS or part.endswith(".egg-info"):
            return True
    return False


def _extract_notebook_code(content: str) -> str:
    """Extrae celdas de código y markdown de un archivo .ipynb si es JSON válido."""
    try:
        data = json.loads(content)
        cells = data.get("cells", [])
        extracted_lines = []
        for idx, cell in enumerate(cells):
            cell_type = cell.get("cell_type", "")
            source = "".join(cell.get("source", []))
            if cell_type == "code" and source.strip():
                extracted_lines.append(f"# [Notebook Cell {idx} - Code]\n{source}")
            elif cell_type == "markdown" and source.strip():
                extracted_lines.append(f"# [Notebook Cell {idx} - Markdown]\n{source}")
        return "\n\n".join(extracted_lines)
    except Exception:
        return content


class EvidenceDossier:
    """
    Extractor y organizador de evidencia en memoria.
    Produce un dossier textual estructurado en 6 secciones canónicas.
    """

    def __init__(
        self,
        repo_data: Dict[str, Any],
        max_dossier_chars: int = DEFAULT_MAX_DOSSIER_CHARS,
        max_file_chars: int = DEFAULT_MAX_FILE_CHARS,
    ):
        self.repo_data = repo_data
        self.max_dossier_chars = max_dossier_chars
        self.max_file_chars = max_file_chars

        # Resolver mapa de archivos normalizado
        raw_files = repo_data.get("file_contents") or repo_data.get("files") or {}
        self.files: Dict[str, str] = {}
        for path, content in raw_files.items():
            norm_path = path.replace("\\", "/").strip().lstrip("/")
            if not is_binary_file(norm_path) and not is_ignored_path(norm_path):
                self.files[norm_path] = str(content)

        # Resolver inventario completo
        raw_inv = repo_data.get("repository_inventory", [])
        self.inventory: List[Dict[str, Any]] = []
        seen_inv_paths = set()
        for item in raw_inv:
            p = item.get("path", "").replace("\\", "/").strip().lstrip("/")
            if p and not is_ignored_path(p):
                seen_inv_paths.add(p)
                self.inventory.append({
                    "path": p,
                    "size": item.get("size", len(self.files.get(p, ""))),
                    "category": item.get("category", "file"),
                    "is_binary": is_binary_file(p),
                })

        for p, content in raw_files.items():
            norm_p = p.replace("\\", "/").strip().lstrip("/")
            if norm_p not in seen_inv_paths and not is_ignored_path(norm_p):
                is_bin = is_binary_file(norm_p)
                self.inventory.append({
                    "path": norm_p,
                    "size": len(content.encode("utf-8")) if isinstance(content, str) else len(content),
                    "category": "binary" if is_bin else "file",
                    "is_binary": is_bin,
                })

        self.inventory.sort(key=lambda x: x["path"].lower())
        self.included_files: Set[str] = set()
        self.truncation_notes: List[str] = []

    def _truncate_content(self, path: str, content: str, limit: int) -> str:
        """Trunca contenido excedente dejando nota explícita."""
        if len(content) <= limit:
            return content
        omitted = len(content) - limit
        self.truncation_notes.append(f"{path}: omitidos {omitted} caracteres por límite de sección")
        return content[:limit] + f"\n... [TRUNCADO: {omitted} caracteres omitidos por presupuesto] ..."

    def build_inventory_section(self) -> str:
        """SECCIÓN A: Inventario completo de archivos (sin binarios en el cuerpo)."""
        lines = ["=== SECCIÓN A: INVENTARIO COMPLETO DEL REPOSITORIO ==="]
        lines.append(f"Total de archivos detectados: {len(self.inventory)}")
        for item in self.inventory:
            bin_tag = " [BINARIO]" if item["is_binary"] else ""
            lines.append(f"- {item['path']} ({item['size']} bytes){bin_tag}")
        return "\n".join(lines)

    def build_documentation_section(self) -> str:
        """SECCIÓN B: Documentación principal (README, DECISIONES, prompts, docs)."""
        lines = ["\n=== SECCIÓN B: DOCUMENTACIÓN PRINCIPAL Y PROMPTS ==="]
        doc_patterns = [
            re.compile(r"^readme(\.md|\.txt)?$", re.I),
            re.compile(r"^decisiones(\.md|\.txt)?$", re.I),
            re.compile(r"^prompts/", re.I),
            re.compile(r"^agente/", re.I),
            re.compile(r"^docs/", re.I),
        ]

        doc_paths = []
        for p in sorted(self.files.keys()):
            filename = posixpath.basename(p)
            if any(pat.search(p) or pat.search(filename) for pat in doc_patterns):
                doc_paths.append(p)

        if not doc_paths:
            lines.append("[No se encontraron archivos de documentación en rutas estándar]")
            return "\n".join(lines)

        for p in doc_paths:
            content = self.files[p]
            self.included_files.add(p)
            is_priority = any(k in p.lower() for k in ["readme", "decisiones", "system_prompt"])
            limit = self.max_file_chars if is_priority else min(self.max_file_chars, 4000)
            clean_content = self._truncate_content(p, content, limit)
            lines.append(f"\n--- ARCHIVO: {p} ---")
            lines.append(clean_content)

        return "\n".join(lines)

    def build_implementation_section(self) -> str:
        """
        SECCIÓN C: Implementación del sistema agéntico.
        Soporta Python, JS/TS, notebooks, YAML/JSON, schemas, manifests y scripts.
        NO asume exclusivamente Python.
        """
        lines = ["\n=== SECCIÓN C: IMPLEMENTACIÓN Y HERRAMIENTAS ==="]
        impl_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".ipynb", ".sh", ".bash", ".ps1"}
        config_names = {"config.yaml", "config.yml", "config.json", "manifest.json", "package.json", "pyproject.toml", "tools.json", "actions.json"}

        impl_paths = []
        for p in sorted(self.files.keys()):
            if p in self.included_files:
                continue
            ext = posixpath.splitext(p.lower())[1]
            fname = posixpath.basename(p).lower()
            if ext in impl_exts or fname in config_names or p.startswith("src/") or p.startswith("app/") or p.startswith("lib/"):
                if not any(folder in p.lower() for folder in ["corridas/", "runs/", "tests/", "test/"]):
                    impl_paths.append(p)

        if not impl_paths:
            lines.append("[No se encontraron archivos de código/herramientas convencionales en src/ o raíz. Verifique SECCIÓN B o SECCIÓN D si el proyecto utiliza arquitectura de prompts o conectores]")
            return "\n".join(lines)

        for p in impl_paths:
            raw_content = self.files[p]
            self.included_files.add(p)
            if p.endswith(".ipynb"):
                raw_content = _extract_notebook_code(raw_content)
            clean_content = self._truncate_content(p, raw_content, self.max_file_chars)
            lines.append(f"\n--- ARCHIVO: {p} ---")
            lines.append(clean_content)

        return "\n".join(lines)

    def build_runs_section(self) -> str:
        """
        SECCIÓN D: Corridas del sistema (entradas, salidas, fechas, tool calls).
        Detecta corridas independientemente del naming exacto (corridas/, runs/, outputs/).
        Relaciona por carpeta o prefijo y entrega contenido para comparar entrada -> salida.
        """
        lines = ["\n=== SECCIÓN D: REGISTRO DE CORRIDAS (ENTRADAS Y SALIDAS) ==="]
        run_indicators = ["corridas/", "runs/", "outputs/", "ejecuciones/", "traces/"]
        
        run_files = [
            p for p in sorted(self.files.keys())
            if any(ind in p.lower() for ind in run_indicators)
        ]

        if not run_files:
            lines.append("[No se encontraron carpetas ni archivos correspondientes a corridas (corridas/, runs/, outputs/)]")
            return "\n".join(lines)

        groups: Dict[str, List[str]] = {}
        for p in run_files:
            parts = p.split("/")
            group_key = "/".join(parts[:2]) if len(parts) > 1 else "root_runs"
            groups.setdefault(group_key, []).append(p)

        lines.append(f"Grupos de corridas detectados: {list(groups.keys())}")
        for group_name, paths in sorted(groups.items()):
            lines.append(f"\n--- CORRIDA: {group_name} ---")
            for p in paths:
                self.included_files.add(p)
                content = self.files[p]
                clean = self._truncate_content(p, content, DEFAULT_RUN_FILE_CHARS)
                lines.append(f"[{p}]\n{clean}")

        return "\n".join(lines)

    def build_economics_section(self) -> str:
        """
        SECCIÓN E: Evidencia de análisis económico y costos.
        Busca tokens, costos, modelos, tarifas, proyecciones semanales/anuales por paths Y por contenido.
        """
        lines = ["\n=== SECCIÓN E: EVIDENCIA ECONÓMICA Y CONSUMO DE TOKENS ==="]
        econ_keywords = ["token", "costo", "tarifa", "pricing", "gasto", "presupuesto", "usd", "precio", "proyeccion", "semanal", "anual"]

        econ_paths = [
            p for p in sorted(self.files.keys())
            if any(k in p.lower() for k in ["analisis_economico", "costo", "pricing", "tokens", "economia"])
        ]

        found_any = False
        for p in econ_paths:
            found_any = True
            content = self.files[p]
            self.included_files.add(p)
            lines.append(f"\n--- DOCUMENTO ECONÓMICO: {p} ---")
            lines.append(self._truncate_content(p, content, self.max_file_chars))

        snippets = []
        for p, content in sorted(self.files.items()):
            if p in econ_paths:
                continue
            matches = [line.strip() for line in content.splitlines() if any(kw in line.lower() for kw in econ_keywords)]
            if len(matches) >= 2:
                sample = "\n  ".join(matches[:8])
                snippets.append(f"- En '{p}':\n  {sample}")

        if snippets:
            found_any = True
            lines.append("\n[Menciones económicas detectadas en otros archivos:]")
            lines.extend(snippets[:6])

        if not found_any:
            lines.append("[No se detectó evidencia documental de análisis económico, tokens ni proyecciones]")

        return "\n".join(lines)

    def build_governance_section(self) -> str:
        """
        SECCIÓN F: Evidencia de gobierno, permisos y riesgos.
        Busca sistemas afectados, permisos lectura/escritura, riesgos, catálogo de fallas,
        supervisión humana L0-L4, rol responsable y firmas por paths Y por contenido.
        """
        lines = ["\n=== SECCIÓN F: GOBIERNO, RIESGOS, PERMISOS Y SUPERVISIÓN ==="]
        gov_keywords = ["riesgo", "gobierno", "permiso", "falla", "supervision", "l0", "l1", "l2", "l3", "l4", "responsable", "firma", "humano", "seguridad"]

        gov_paths = [
            p for p in sorted(self.files.keys())
            if any(k in p.lower() for k in ["gobierno", "riesgo", "governance", "seguridad", "permisos"])
        ]

        found_any = False
        for p in gov_paths:
            found_any = True
            content = self.files[p]
            self.included_files.add(p)
            lines.append(f"\n--- DOCUMENTO DE GOBIERNO: {p} ---")
            lines.append(self._truncate_content(p, content, self.max_file_chars))

        snippets = []
        for p, content in sorted(self.files.items()):
            if p in gov_paths:
                continue
            matches = [line.strip() for line in content.splitlines() if any(kw in line.lower() for kw in gov_keywords)]
            if len(matches) >= 2:
                sample = "\n  ".join(matches[:8])
                snippets.append(f"- En '{p}':\n  {sample}")

        if snippets:
            found_any = True
            lines.append("\n[Menciones de gobierno y supervisión detectadas en otros archivos:]")
            lines.extend(snippets[:6])

        if not found_any:
            lines.append("[No se detectó evidencia documental de gobierno, matriz de riesgos ni supervisión humana]")

        return "\n".join(lines)

    def generate_dossier(self) -> Tuple[str, Dict[str, Any]]:
        """
        Genera el Evidence Dossier completo integrando las 6 secciones.
        Retorna (dossier_text, dossier_metrics).
        """
        sections = [
            self.build_inventory_section(),
            self.build_documentation_section(),
            self.build_implementation_section(),
            self.build_runs_section(),
            self.build_economics_section(),
            self.build_governance_section(),
        ]

        dossier_text = "\n\n".join(sections)

        if len(dossier_text) > self.max_dossier_chars:
            omitted = len(dossier_text) - self.max_dossier_chars
            dossier_text = dossier_text[:self.max_dossier_chars] + f"\n\n... [AVISO: {omitted} caracteres globales omitidos por presupuesto máximo de {self.max_dossier_chars} chars] ..."

        metrics = {
            "dossier_chars": len(dossier_text),
            "file_count": len(self.files),
            "inventory_count": len(self.inventory),
            "included_files_count": len(self.included_files),
            "truncation_notes": list(self.truncation_notes),
        }

        return dossier_text, metrics


def build_evidence_dossier(repo_data: Dict[str, Any], max_dossier_chars: int = DEFAULT_MAX_DOSSIER_CHARS) -> Tuple[str, Dict[str, Any]]:
    """Función de conveniencia para instanciar y generar el dossier estructurado."""
    dossier = EvidenceDossier(repo_data, max_dossier_chars=max_dossier_chars)
    return dossier.generate_dossier()
