import json
import re
from typing import Dict, List

from src.github_fetcher import CODE_EXTENSIONS, classify_path


def _inventory_records(repo_data: dict, file_contents: Dict[str, str]) -> List[dict]:
    """Mantiene compatibilidad con entradas anteriores sin inventario estructurado."""
    inventory = repo_data.get("repository_inventory")
    if inventory:
        return sorted(inventory, key=lambda record: record["path"].lower())
    return [classify_path(path, len(content.encode("utf-8"))) for path, content in sorted(file_contents.items())]


def _coverage(records: List[dict], loaded_paths: List[str], label: str = "", category: str = "") -> dict:
    candidates = [
        record for record in records
        if (not label or label in record.get("labels", [])) and (not category or record["category"] == category)
    ]
    paths = [record["path"] for record in candidates]
    loaded = [path for path in paths if path in loaded_paths]
    return {
        "status": "loaded" if loaded else ("skipped" if paths else "absent"),
        "inventory_paths": paths,
        "loaded_paths": loaded,
    }


def _combined_content(paths: List[str], file_contents: Dict[str, str]) -> str:
    return "\n\n".join(f"--- {path} ---\n{file_contents[path]}" for path in paths if path in file_contents)


def _is_code_file(path: str, content: str) -> bool:
    extension = path[path.rfind("."):].lower() if "." in path.rsplit("/", 1)[-1] else ""
    if extension in CODE_EXTENSIONS:
        return True
    return extension == ".html" and bool(re.search(r"<script|type=['\"]module|onclick=|addEventListener", content, re.IGNORECASE))


def _has_instantiated_sdk_call(content: str) -> bool:
    """Reconoce SDKs sólo cuando cliente e invocación aparecen en el mismo código."""
    sdk_calls = [
        (r"\bnew\s+OpenAI\s*\(", r"\b\w+\.responses\.(?:create|stream)\s*\("),
        (r"\bnew\s+OpenAI\s*\(", r"\b\w+\.chat\.completions\.create\s*\("),
        (r"\b(?:anthropic\.)?Anthropic\s*\(", r"\b\w+\.messages\.(?:create|stream)\s*\("),
        (r"\bGoogleGenerativeAI\s*\(", r"\b\w+\.getGenerativeModel\s*\("),
    ]
    return any(re.search(client, content, re.IGNORECASE) and re.search(call, content, re.IGNORECASE)
               for client, call in sdk_calls)


def _executable_code(content: str) -> str:
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    content = re.sub(r"(?s)(['\"`])(?:\\.|(?!\1).)*\1", "''", content)
    content = re.sub(r"(?m)#.*$", "", content)
    return re.sub(r"(?m)//[^\n]*$", "", content)


def _run_groups(corrida_files: List[str]) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = {}
    for path in corrida_files:
        parts = path.split("/")
        grouped.setdefault("/".join(parts[:2]) if len(parts) > 1 else path, []).append(path)
    return grouped


def _structured_object(content: str) -> dict:
    try:
        value = json.loads(content)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _normalized_key(key: str) -> str:
    camel_separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", camel_separated.lower()).strip("_")


def _identifier_values(value: dict) -> Dict[str, object]:
    identifiers = {}
    base_names = {"id", "uuid", "request", "case", "ticket", "order", "transaction", "reference", "ref"}
    for key, item in value.items():
        normalized = _normalized_key(key)
        if not isinstance(item, (str, int, float)) or isinstance(item, bool):
            continue
        parts = set(normalized.split("_"))
        if normalized in base_names or normalized.endswith("_id") and parts & base_names:
            identifiers[normalized] = item
    return identifiers


def _numeric_field_values(value: object) -> List[tuple[str, float]]:
    values: List[tuple[str, float]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = _normalized_key(key)
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                values.append((normalized, float(item)))
            values.extend(_numeric_field_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_numeric_field_values(item))
    return values


def _output_rejects_human_review(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = _normalized_key(key)
            is_review_flag = normalized in {
                "human_review_required", "requires_human_review",
                "human_approval_required", "requires_approval",
            } or ("human" in normalized and ("review" in normalized or "approval" in normalized))
            if is_review_flag and (item is False or str(item).strip().lower() in {"false", "no", "none", "not_required"}):
                return True
            if normalized == "approved_without_review" and item is True:
                return True
            if _output_rejects_human_review(item):
                return True
    elif isinstance(value, list):
        return any(_output_rejects_human_review(item) for item in value)
    return False


def _structured_run_consistency(corrida_files: List[str], file_contents: Dict[str, str]) -> dict:
    inconsistent_groups = set()
    reused_groups = set()
    records = []
    for group, paths in _run_groups(corrida_files).items():
        inputs = [_structured_object(file_contents.get(path, "")) for path in paths if "entrada" in path.lower() or "input" in path.lower()]
        outputs = [_structured_object(file_contents.get(path, "")) for path in paths if any(token in path.lower() for token in ("salida", "output", "result"))]
        input_data = next((item for item in inputs if item), {})
        output_data = next((item for item in outputs if item), {})
        input_ids = _identifier_values(input_data)
        output_ids = _identifier_values(output_data)
        if any(input_ids[key] != output_ids[key] for key in input_ids.keys() & output_ids.keys()):
            inconsistent_groups.add(group)
        records.append({
            "group": group,
            "input": input_data,
            "output": output_data,
            "input_ids": input_ids,
            "output_ids": output_ids,
        })

    output_index: Dict[tuple[str, object], List[dict]] = {}
    for record in records:
        for key, value in record["output_ids"].items():
            output_index.setdefault((key, value), []).append(record)
    for (key, _), matching_records in output_index.items():
        input_values = {record["input_ids"].get(key) for record in matching_records if key in record["input_ids"]}
        if len(matching_records) > 1 and len(input_values) > 1:
            reused_groups.update(record["group"] for record in matching_records)

    inconsistent_groups.update(reused_groups)
    return {
        "inconsistent_groups": inconsistent_groups,
        "reused_groups": reused_groups,
        "records": records,
    }


def _human_review_policies(content: str) -> List[tuple[set[str], float]]:
    fields = r"(?:amount|monto|importe|refund(?:_amount)?|price|value|total)"
    comparison = r"(?:mayor(?:es)?\s+(?:que|a)|superior(?:es)?\s+a|above|greater\s+than|>)"
    requirement = r"(?:requiere|require(?:s|d)?|necesita|must).{0,60}(?:revisi[oó]n|supervisi[oó]n|approval|aprobaci[oó]n)"
    policies = []
    for match in re.finditer(
        rf"\b(?P<field>{fields})\b.{{0,100}}?{comparison}\s*(?:a\s*)?(?P<limit>\d+(?:[.,]\d+)?).{{0,100}}?{requirement}",
        content,
        re.IGNORECASE,
    ):
        policies.append(({_review_field_group(match.group("field"))}, float(match.group("limit").replace(",", "."))))
    return policies


def _review_field_group(field: str) -> str:
    normalized = _normalized_key(field)
    if normalized in {"amount", "monto", "importe", "refund", "refund_amount", "price", "value", "total"}:
        return "monetary_value"
    return normalized


def _review_execution_conflicts(gov_content: str, records: List[dict]) -> List[str]:
    conflicts = []
    for fields, limit in _human_review_policies(gov_content):
        for record in records:
            if not record["output"] or not _output_rejects_human_review(record["output"]):
                continue
            for key, value in _numeric_field_values(record["input"]):
                if _review_field_group(key) in fields and value > limit:
                    conflicts.append(record["group"])
                    break
    return sorted(set(conflicts))


def _has_token_measurement(content: str) -> bool:
    """Detecta mediciones etiquetadas y tablas, sin inferir tokens de texto libre."""
    labeled_measurement = re.search(
        r"(?:input|output|entrada|salida)\s*tokens?|tokens?\s*(?:de\s+)?(?:input|output|entrada|salida)\s*[:=]?\s*\**\s*\d",
        content,
        re.IGNORECASE,
    )
    legacy_measurement = re.search(r"\d+[\.,]?\d*\s*tokens", content, re.IGNORECASE)
    economic_context = bool(re.search(r"\b(?:modelo|model|api|tarifa|pricing|costo\s+por\s+corrida|corrida)\b", content, re.IGNORECASE))
    if (labeled_measurement or legacy_measurement) and economic_context:
        return True

    lines = content.splitlines()
    for index, line in enumerate(lines[:-1]):
        if "|" not in line or "token" not in line.lower():
            continue
        headers = [cell.strip().lower() for cell in line.strip().strip("|").split("|")]
        has_link_column = any(any(term in cell for term in ("modelo", "model", "corrida", "run", "costo", "cost")) for cell in headers)
        token_columns = [index for index, cell in enumerate(headers) if "token" in cell]
        if not has_link_column:
            continue
        for row in lines[index + 1:index + 5]:
            cells = [cell.strip() for cell in row.strip().strip("|").split("|")] if "|" in row else []
            if "|" in row and len(cells) == len(headers) and any(re.search(r"\d", cells[column]) for column in token_columns) and not re.fullmatch(r"[\s|:-]+", row):
                return True
    return False


def _has_cost_measurement(content: str) -> bool:
    has_cost = bool(re.search(r"(?:costo|cost)\D{0,40}(?:usd|\$)\s*\d+|(?:usd|\$)\s*\d+\D{0,40}(?:costo|cost)", content, re.IGNORECASE))
    has_ai_context = bool(re.search(r"\b(?:token|modelo|model|api|corrida|run|tarifa|pricing)\b", content, re.IGNORECASE))
    if has_cost and has_ai_context:
        return True
    lines = content.splitlines()
    for index, line in enumerate(lines[:-1]):
        if "|" not in line:
            continue
        headers = [cell.strip().lower() for cell in line.strip().strip("|").split("|")]
        token_columns = [i for i, cell in enumerate(headers) if "token" in cell]
        cost_columns = [i for i, cell in enumerate(headers) if "costo" in cell or "cost" in cell]
        has_model_or_run = any(any(term in cell for term in ("modelo", "model", "corrida", "run", "caso")) for cell in headers)
        if not (token_columns and cost_columns and has_model_or_run):
            continue
        for row in lines[index + 1:index + 5]:
            cells = [cell.strip() for cell in row.strip().strip("|").split("|")] if "|" in row else []
            if len(cells) == len(headers) and any(re.search(r"\d", cells[i]) for i in token_columns) and any(re.search(r"\d", cells[i]) for i in cost_columns):
                return True
    return False


def _table_operational_governance_axes(content: str) -> Dict[str, bool]:
    """Reconoce controles operativos cuando encabezado y celda los vinculan."""
    axes = {"permissions": False, "failures": False, "action_plan": False, "human_review": False, "responsible": False}
    lines = content.splitlines()
    for index, line in enumerate(lines[:-1]):
        if "|" not in line:
            continue
        headers = [cell.strip().lower() for cell in line.strip().strip("|").split("|")]
        column_for = {
            "permissions": next((i for i, cell in enumerate(headers) if "permiso" in cell or "acceso" in cell), None),
            "failures": next((i for i, cell in enumerate(headers) if any(word in cell for word in ("falla", "riesgo", "error"))), None),
            "action_plan": next((i for i, cell in enumerate(headers) if any(word in cell for word in ("respuesta", "mitigación", "mitigacion", "acción", "accion"))), None),
            "human_review": next((i for i, cell in enumerate(headers) if "supervisión" in cell or "supervision" in cell or "revisión" in cell or "revision" in cell), None),
            "responsible": next((i for i, cell in enumerate(headers) if "responsable" in cell or "firma" in cell), None),
        }
        for row in lines[index + 2:index + 8]:
            if "|" not in row:
                break
            cells = [cell.strip().lower() for cell in row.strip().strip("|").split("|")]
            if len(cells) != len(headers) or re.fullmatch(r"[\s|:-]+", row):
                continue
            values = {axis: cells[column] if column is not None else "" for axis, column in column_for.items()}
            axes["permissions"] |= bool(re.search(r"\b(?:solo|sólo|lectura|escritura|restringid\w*|rol|autoriz\w*)\b", values["permissions"]))
            axes["failures"] |= bool(re.search(r"\b(?:consecuencia|impacto|puede|afecta\w*)\b", values["failures"]))
            axes["action_plan"] |= bool(re.search(r"\b(?:bloquear|detener|abrir|notificar|escalar|revisar|corregir)\b", values["action_plan"]))
            axes["human_review"] |= bool(re.search(r"\b(?:analista|persona|humana|equipo)\b", values["human_review"]) and re.search(r"\b(?:cada|antes|revisa\w*|valid\w*)\b", values["human_review"]))
            axes["responsible"] |= bool(re.search(r"\b(?:final|firma|asume|rol)\b", values["responsible"]))
    return axes


def _run_trace_summary(corrida_files: List[str], file_contents: Dict[str, str], inconsistent_groups: set[str] | None = None) -> tuple[int, int]:
    """Devuelve corridas identificables y trazas completas, sin mezclar directorios."""
    date_pattern = r"(?:fecha(?:\s+de\s+ejecuci[oó]n)?|date|timestamp|generado_utc|startedat|finishedat)[\"']?\s*[:=].*\d{4}[-/]\d{2}[-/]\d{2}"
    grouped = _run_groups(corrida_files)
    inconsistent_groups = inconsistent_groups or set()

    identifiable_groups = 0
    complete_groups = 0
    for group, paths in grouped.items():
        lower_paths = [path.lower() for path in paths]
        has_input = any("entrada" in path or "input" in path for path in lower_paths)
        has_output = any(any(token in path for token in ("salida", "output", "result")) for path in lower_paths)
        has_date = any(any(token in path for token in ("fecha", "time", "date", "metadata")) for path in lower_paths)
        if not has_date:
            has_date = any(re.search(date_pattern, file_contents.get(path, ""), re.IGNORECASE) for path in paths)
        components = sum((has_input, has_output, has_date))
        if components >= 2:
            identifiable_groups += 1
        if components == 3 and group not in inconsistent_groups:
            complete_groups += 1

    metadata_traces = 0
    for path in corrida_files:
        content = file_contents.get(path, "")
        has_date = bool(re.search(date_pattern, content, re.IGNORECASE))
        input_match = re.search(r"(?:caso|input|entrada|solicitud)\s*:\s*`?([^`\n]+)", content, re.IGNORECASE)
        input_reference = input_match and input_match.group(1).strip().split()[0]
        has_input_reference = bool(input_reference and any(candidate.endswith(input_reference) for candidate in file_contents))
        has_complete_output = "raw" in path.lower() and len(content) > 200
        has_narrative_output = bool(re.search(r"salida\s+del\s+agente|salida\s+tras", content, re.IGNORECASE))
        if has_date and has_input_reference and (has_complete_output or has_narrative_output):
            metadata_traces += 1
    return max(identifiable_groups, metadata_traces), max(complete_groups, metadata_traces)


def extract_objective_evidence(repo_data: dict) -> dict:
    """
    Extrae evidencias objetivas y agnósticas del repositorio objetivo.
    Devuelve un diccionario estructurado con métricas de presencia,
    incompatibilidades y contradicciones verificables.
    """
    file_contents: Dict[str, str] = repo_data.get("file_contents", {})
    all_paths = sorted(file_contents)
    inventory = _inventory_records(repo_data, file_contents)

    # Normalización de paths a minúsculas para comparaciones agnósticas
    path_map = {p.lower(): p for p in all_paths}
    
    # -------------------------------------------------------------------------
    # 1. Inspección de Estructura Obligatoria
    # -------------------------------------------------------------------------
    has_readme = any("readme" in p for p in path_map)
    has_decisiones = any("decisiones" in p for p in path_map)
    has_prompts_dir = any("prompts/" in p for p in path_map)
    has_corridas_dir = any("corridas/" in p for p in path_map)
    
    mandatory_structure = {
        "readme": has_readme,
        "decisiones": has_decisiones,
        "prompts": has_prompts_dir,
        "corridas": has_corridas_dir,
        "is_complete": has_readme and has_decisiones and has_prompts_dir and has_corridas_dir
    }

    # -------------------------------------------------------------------------
    # 2. Análisis de Código e Implementación (Agnóstico de lenguaje y SDK)
    # -------------------------------------------------------------------------
    code_files = [p for p in all_paths if _is_code_file(p, file_contents.get(p, ""))]

    has_code = len(code_files) > 0

    # Detección de conectores o retornos DUMMY / PLACEHOLDER en código
    dummy_patterns = [
        r'conectado"\s*:\s*false',
        r'return\s*\{\s*"conectado"\s*:\s*false',
        # Un placeholder de UI o texto aislado no demuestra un conector simulado.
        # Exigir una frase técnica con separadores léxicos evita atravesar atributos
        # HTML como placeholder="checkout-api".
        r'\bplaceholder\s+(?:de\s+)?(?:conector|connector|api|integraci[oó]n)\b',
        r'\b(?:conector|connector|api|integraci[oó]n)\b(?:\s+\w+){0,4}\s+placeholder\b',
        r'\[simulado\]',
        r'no\s+se\s+envió\s+nada',
        r'credenciales\s+no\s+configuradas',
        r'pass\s*$'
    ]
    
    found_dummies = []
    for cf in code_files:
        content = file_contents.get(cf, "").lower()
        for pat in dummy_patterns:
            if re.search(pat, content):
                found_dummies.append(f"{cf}: detectado patrón de simulación/dummy ('{pat}')")

    has_dummy_connectors = len(found_dummies) > 0

    # Detección de llamadas a API / herramientas / procesamiento real
    real_execution_patterns = [
        r'requests\.(post|get|put)',
        r'urllib\.request',
        r'fetch\(',
        r'axios\.',
        r'client\.models',
        r'openai\.',
        r'anthropic\.',
        r'generate_content',
        r'chat_completion',
        r'clasificar_',
        r'json\.load'
    ]

    found_real_execution = []
    for cf in code_files:
        content = _executable_code(file_contents.get(cf, ""))
        if _has_instantiated_sdk_call(content):
            found_real_execution.append(f"{cf}: SDK instanciado con invocación efectiva")
        for pat in real_execution_patterns:
            if re.search(pat, content, re.IGNORECASE):
                found_real_execution.append(f"{cf}: patrón de ejecución/procesamiento ('{pat}')")

    # Clasificación objetiva del sistema
    if not has_code:
        system_type = "no_code"
    elif has_dummy_connectors and not found_real_execution:
        system_type = "dummy_placeholder_only"
    elif found_real_execution and has_dummy_connectors:
        system_type = "partial_simulated_tool"
    elif found_real_execution:
        system_type = "real_execution"
    else:
        system_type = "rule_based_local"

    # -------------------------------------------------------------------------
    # 3. Análisis de Prompts
    # -------------------------------------------------------------------------
    prompt_files = [p for p in all_paths if "prompts/" in p.lower() or "prompt" in p.lower()]
    has_substantive_prompts = False
    
    for pf in prompt_files:
        content = file_contents.get(pf, "").strip()
        # Se considera sustantivo si tiene > 100 caracteres y define rol o instrucciones
        if len(content) > 100 and any(kw in content.lower() for kw in ["rol", "tarea", "instrucción", "instrucciones", "sistema", "usuario", "prompt"]):
            has_substantive_prompts = True
            break

    # -------------------------------------------------------------------------
    # 4. Análisis de Corridas y Trazas (corridas/)
    # -------------------------------------------------------------------------
    corrida_files = [p for p in all_paths if "corridas/" in p.lower() or "runs/" in p.lower() or "outputs/" in p.lower()]
    
    # Identificar carpetas o conjuntos de corridas
    corrida_dirs = set()
    for cf in corrida_files:
        parts = cf.split("/")
        if len(parts) > 1:
            corrida_dirs.add(parts[0] + "/" + parts[1])

    corrida_count = len(corrida_dirs) if corrida_dirs else (1 if corrida_files else 0)

    # Verificar presencia de triada: entrada, salida, fecha. Además de los
    # nombres convencionales, admitir metadata y referencias a inputs reales.
    has_entrada = any("entrada" in p.lower() or "input" in p.lower() for p in corrida_files)
    has_salida = any("salida" in p.lower() or "output" in p.lower() or "result" in p.lower() for p in corrida_files)
    has_fecha = any("fecha" in p.lower() or "time" in p.lower() or "date" in p.lower() or "metadata" in p.lower() for p in corrida_files)
    run_consistency = _structured_run_consistency(corrida_files, file_contents)
    identifiable_run_count, complete_trace_count = _run_trace_summary(
        corrida_files, file_contents, run_consistency["inconsistent_groups"]
    )
    # La triada no puede componerse con artefactos de corridas distintas.
    # Para el nivel alto basta demostrar tres trazas completas, no cada log legado.
    has_complete_triad = complete_trace_count >= 3
    corrida_count = max(corrida_count, identifiable_run_count)

    # -------------------------------------------------------------------------
    # 5. Análisis de Decisiones (DECISIONES.md)
    # -------------------------------------------------------------------------
    decisiones_content = ""
    decisiones_file_path = next((p for p in all_paths if "decisiones.md" in p.lower()), None)
    if decisiones_file_path:
        decisiones_content = file_contents.get(decisiones_file_path, "")

    valid_decisions = []
    if decisiones_content:
        sections = re.split(r'\n(?=#{2,3}\s+)', decisiones_content)
        for sec in sections:
            sec_text = sec.strip()
            if not sec_text or len(sec_text) < 30:
                continue
            if sec_text.startswith('# ') and not sec_text.startswith('## '):
                continue

            sec_lower = sec_text.lower()
            is_explicit = bool(re.search(r'#{2,3}\s*decisi[óo]n\s*\d*', sec_lower))
            is_iteration = bool(re.search(r'#{2,3}\s*iteraci[óo]n\s*\d*', sec_lower))

            has_context = any(kw in sec_lower for kw in [
                "contexto", "problema", "primera versión", "anteriormente", "necesitábamos", "por qué", "por que",
                "se consideró", "prueba", "situación", "desafío", "issue", "caso", "versión inicial", "primera implementación"
            ])
            has_change = any(kw in sec_lower for kw in [
                "decisión", "decidimos", "cambio", "se definió", "se definieron", "se redujo", 
                "elegimos", "migramos", "adoptamos", "incorporamos", "implementamos", "solución", "integrar", "determinó", "diseño", "se adoptó", "se retiró", "se ejecutaron", "corrección", "se agregó", "se agrego", "se cambió", "se cambio", "se actualizó", "se actualizo"
            ])
            has_impact = any(kw in sec_lower for kw in [
                "impacto", "motivo", "resultado", "evidencia", "efecto", "beneficio", 
                "permite", "produjo", "evita", "consecuencia", "ahorro", "mejora", "conservan", "garantizar", "asegurar", "calificación",
                "limitación", "documentada", "documentado", "registrada", "registrado", "quedó", "quedaron", "mantiene", "firma", "revisa", "reproducibilidad", "trazabilidad", "cumplir"
            ])

            if is_explicit or (has_context and has_change and has_impact):
                valid_decisions.append(sec_text)

        # Una tabla es una colección de decisiones si explicita columnas de
        # cambio/decisión y motivo/impacto, y cada fila aporta ambos campos.
        lines = decisiones_content.splitlines()
        for index, header in enumerate(lines):
            if "|" not in header:
                continue
            columns = [cell.strip().lower() for cell in header.strip().strip("|").split("|")]
            change_index = next((i for i, cell in enumerate(columns) if any(word in cell for word in ("cambio", "decisión", "decision", "solución", "solucion"))), None)
            impact_index = next((i for i, cell in enumerate(columns) if any(word in cell for word in ("motivo", "impacto", "resultado", "razón", "razon"))), None)
            if change_index is None or impact_index is None:
                continue
            for row in lines[index + 2:]:
                if "|" not in row:
                    break
                cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
                if len(cells) <= max(change_index, impact_index):
                    continue
                if len(cells[change_index]) >= 12 and len(cells[impact_index]) >= 12:
                    valid_decisions.append(row)

    # Deduplicación conservadora: sólo fusiona unidades que comparten la mayor
    # parte de sus términos sustantivos, como tabla-resumen y desarrollo posterior.
    stopwords = {"la", "el", "los", "las", "de", "del", "y", "en", "por", "para", "que", "se", "una", "un", "con", "al", "como", "su", "es"}
    unique_decisions = []
    fingerprints = []
    for decision in valid_decisions:
        terms = {term for term in re.findall(r"[a-záéíóúñ0-9]{4,}", decision.lower()) if term not in stopwords}
        duplicate = any(terms and existing and len(terms & existing) / min(len(terms), len(existing)) >= 0.75 for existing in fingerprints)
        if not duplicate:
            unique_decisions.append(decision)
            fingerprints.append(terms)
    decision_count = len(unique_decisions)
    decisions_lower = decisiones_content.lower()
    has_process_iteration = bool(re.search(r"\biteraci[oó]n|correcci[oó]n|versi[oó]n\b", decisions_lower))
    process_change_patterns = (
        r"\b(?:falla|fall[oó]|problema|desv[ií]o|cambio de alcance)\b",
        r"\b(?:problemas?|errores?|fallas?|desv[ií]os?)\b.{0,140}\b(?:detectad\w*|encontrad\w*|correg\w*|llev\w*|motiv\w*|ajust\w*|reemplaz\w*|cambi\w*|actualiz\w*)\b",
        r"\b(?:detectad\w*|encontrad\w*)\b.{0,140}\b(?:problemas?|errores?|fallas?|desv[ií]os?)\b",
        r"\bomit[ií]\w*\b.{0,100}\b(?:informaci[oó]n|campo|dato|contexto)\b",
        r"\b(?:no\s+(?:ten[ií]a|contaba)|sin)\b.{0,100}\b(?:credenciales|acceso|permisos|configuraci[oó]n)\b",
        r"\b(?:clasificaba|respond[ií]a|procesaba|generaba)\b.{0,100}\b(?:incorrectamente|mal|err[oó]neamente)\b",
        r"\b(?:fue necesario|se tuvo que)\b.{0,100}\b(?:corregir|reemplazar|ajustar)\b",
    )
    has_process_change = any(re.search(pattern, decisions_lower, re.IGNORECASE) for pattern in process_change_patterns)
    linked_artifacts = [path for path in all_paths if path.lower() != (decisiones_file_path or "").lower()]
    has_decision_artifact_links = any(path.lower() in decisions_lower for path in linked_artifacts)

    # -------------------------------------------------------------------------
    # 6. Análisis Económico (docs/analisis_economico.md o README)
    # -------------------------------------------------------------------------
    econ_coverage = _coverage(inventory, all_paths, label="economics")
    econ_paths = econ_coverage["loaded_paths"]
    if econ_paths:
        econ_content = _combined_content(econ_paths, file_contents)
    elif econ_coverage["status"] == "absent" and has_readme:
        econ_paths = [next(p for p in all_paths if "readme" in p.lower())]
        econ_content = _combined_content(econ_paths, file_contents)
    else:
        econ_content = ""

    has_tokens_num = _has_token_measurement(econ_content)
    has_cost_num = _has_cost_measurement(econ_content)
    has_projections = bool(re.search(r'(semanal|anual|mes|mensual|proyección)', econ_content, re.IGNORECASE))
    has_model_choice = bool(re.search(r'(modelo|elección|chico|adecuado)', econ_content, re.IGNORECASE))
    has_verified_economic_metadata = any(
        re.search(r'"?(?:model|modelo)"?\s*[:=]', file_contents.get(path, ''), re.IGNORECASE)
        and re.search(r'"?(?:prompt_tokens|input_tokens|tokens_?entrada|completion_tokens|output_tokens|tokens_?salida)"?\s*[:=]\s*\d', file_contents.get(path, ''), re.IGNORECASE)
        and re.search(r'"?(?:cost_usd|costo(?:_usd)?)"?\s*[:=]\s*\d', file_contents.get(path, ''), re.IGNORECASE)
        for path in corrida_files
    )

    # -------------------------------------------------------------------------
    # 7. Análisis de Gobierno y Riesgo (docs/gobierno_riesgo.md o README)
    # -------------------------------------------------------------------------
    gov_coverage = _coverage(inventory, all_paths, label="governance")
    gov_paths = gov_coverage["loaded_paths"]
    if gov_paths:
        gov_content = _combined_content(gov_paths, file_contents)
    elif gov_coverage["status"] == "absent" and has_readme:
        gov_paths = [next(p for p in all_paths if "readme" in p.lower())]
        gov_content = _combined_content(gov_paths, file_contents)
    else:
        gov_content = ""

    gov_axes = {
        "permissions": bool(re.search(r'(permiso|sistema|datos|acceso)', gov_content, re.IGNORECASE)),
        "failures": bool(re.search(r'(falla|riesgo|error|consecuencia)', gov_content, re.IGNORECASE)),
        "action_plan": bool(re.search(r'(respuesta|mitigación|acción|eventualidad)', gov_content, re.IGNORECASE)),
        "human_review": bool(re.search(r'(revisión|supervisión|humana|persona)', gov_content, re.IGNORECASE)),
        "responsible": bool(re.search(r'(responsable|firma|asume)', gov_content, re.IGNORECASE))
    }
    gov_operational_axes = {
        "permissions": bool(re.search(r'(permiso|acceso).{0,80}(solo|lectura|escritura|restringid|rol|autoriza)|(solo|lectura|escritura|restringid|rol|autoriza).{0,80}(permiso|acceso)', gov_content, re.IGNORECASE)),
        "failures": bool(re.search(r'(falla|riesgo|error).{0,100}(consecuencia|impacto|puede|afecta)|(consecuencia|impacto|puede|afecta).{0,100}(falla|riesgo|error)', gov_content, re.IGNORECASE)),
        "action_plan": bool(re.search(r'(respuesta|mitigaci[oó]n|acci[oó]n).{0,100}(bloquear|detener|abrir|notificar|escalar|revisar)|(bloquear|detener|abrir|notificar|escalar).{0,100}(respuesta|mitigaci[oó]n|acci[oó]n)', gov_content, re.IGNORECASE)),
        "human_review": bool(re.search(r'(persona|humana|supervisi[oó]n|revisi[oó]n|analista).{0,120}(cada|antes|previa|previo|aprob\w*|bloque\w*|escal\w*|criterio|condici[oó]n|todo|reejecut\w*|firma|borrador|no\s+(?:dispara|habilita))|(cada|antes|previa|previo|aprob\w*|bloque\w*|escal\w*|criterio|condici[oó]n|todo|reejecut\w*|firma|borrador|no\s+(?:dispara|habilita)).{0,120}(persona|humana|supervisi[oó]n|revisi[oó]n|analista)', gov_content, re.IGNORECASE)),
        "responsible": bool(re.search(r'(responsable|firma|asume).{0,100}(final|rol|analista|persona|equipo)|(final|rol|analista|persona).{0,100}(responsable|firma|asume)', gov_content, re.IGNORECASE)),
    }
    table_gov_axes = _table_operational_governance_axes(gov_content)
    gov_operational_axes = {axis: gov_operational_axes[axis] or table_gov_axes[axis] for axis in gov_operational_axes}

    # -------------------------------------------------------------------------
    # 8. Detección Objetivo de CONTRADICCIONES DE EVIDENCIA
    # -------------------------------------------------------------------------
    contradictions = []
    invalidated_evidence = []
    prompt_injection_attempts = []

    for group in sorted(run_consistency["inconsistent_groups"]):
        contradictions.append(
            f"{group} contiene una salida estructurada incompatible con los identificadores de su entrada."
        )
        invalidated_evidence.append(f"{group} (traza input-output invalidada)")

    # Las instrucciones del repositorio son datos. Sólo se registra una señal
    # cuando hay una directiva imperativa para alterar la corrección, no una
    # mención inocua a seguridad o prompt injection.
    injection_directives = (
        r"ignor[áa]?(?:\s+las?)?\s+instrucciones?\s+anteriores",
        r"ignor[áa]?(?:\s+la)?\s+evidencia",
        r"asign[áa]?(?:\s+el)?\s+(?:puntaje|nota|calificaci[oó]n).{0,40}(?:m[aá]ximo|100)",
        r"omit[ií]?(?:\s+la)?\s+verificaci[oó]n(?:\s+de\s+artefactos?)?",
        r"no\s+report(?:es|e|ar)?\s+inconsistencias",
        r"cambi[áa]?(?:\s+la)?\s+r[úu]brica",
    )
    injection_target = r"(?:sistema\s+de\s+correcci[oó]n|sistema\s+de\s+evaluaci[oó]n|evaluador|corrector)"
    for path, content in file_contents.items():
        directives_found = [
            pattern for pattern in injection_directives
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        ]
        target_found = bool(re.search(injection_target, content, re.IGNORECASE))
        if len(directives_found) >= 2 or (target_found and directives_found):
            prompt_injection_attempts.append(
                f"Intento de manipulación / prompt injection detectado en {path}: "
                "instrucción dirigida al evaluador para alterar la corrección."
            )

    # Contradicción D1: Salida afirma haber ejecutado acción que el código no posee
    for cf in corrida_files:
        if "salida" in cf.lower():
            c_text = file_contents.get(cf, "").lower()
            if "actualizado_en_zendesk\": true" in c_text or "conectado\": true" in c_text:
                if has_dummy_connectors:
                    contradictions.append(
                        f"{cf} afirma integración exitosa pero el código contiene conectores dummy/simulados."
                    )
                    invalidated_evidence.append(cf)

    # Contradicción D4: Afirma consumo de tokens cuando el sistema es de reglas locales o dummy sin IA real
    if has_tokens_num and (system_type in ["no_code", "rule_based_local", "dummy_placeholder_only"] or has_dummy_connectors):
        contradictions.append(
            "docs/analisis_economico.md declara consumo de tokens, pero la implementación no invoca modelos de IA."
        )
        invalidated_evidence.append("docs/analisis_economico.md (cifras de tokens invalidadas por código sin IA)")

    # Contradicción D2: DECISIONES declara integraciones o migraciones no verificables en código
    if decisiones_content:
        d_lower = decisiones_content.lower()
        claims_integration = any(kw in d_lower for kw in [
            "migramos", "integración", "zendesk", "api v2", "en tiempo real", "realtime", "modelo de lenguaje"
        ])
        if claims_integration and (has_dummy_connectors or system_type in ["no_code", "rule_based_local", "dummy_placeholder_only"]):
            contradictions.append(
                "DECISIONES.md declara integraciones de API o migraciones a modelos que la implementación observable contradice o mantiene simuladas."
            )
            invalidated_evidence.append("DECISIONES.md (declaraciones de integración/migración invalidadas por código dummy/sin IA)")

    # Contradicción D5: Si el sistema posee conectores dummy/simulados, invalidar el eje de permisos/acceso a sistemas
    if has_dummy_connectors or system_type in ["dummy_placeholder_only", "partial_simulated_tool"]:
        if gov_axes.get("permissions", False):
            contradictions.append(
                "docs/gobierno_riesgo.md declara controles sobre permisos de sistemas que la implementación mantiene simuladas/dummy."
            )
            invalidated_evidence.append("docs/gobierno_riesgo.md (eje de permisos de sistema invalidado por código simulado)")
            gov_axes["permissions"] = False

    review_execution_conflicts = _review_execution_conflicts(gov_content, run_consistency["records"])
    if review_execution_conflicts:
        for group in review_execution_conflicts:
            contradictions.append(
                f"Contradicción de gobierno: {group} supera el umbral documentado y declara que no requiere supervisión humana."
            )
            invalidated_evidence.append(f"{group} (evidencia de supervisión invalidada)")
        gov_axes["human_review"] = False
        gov_operational_axes["human_review"] = False

    return {
        "mandatory_structure": mandatory_structure,
        "has_code": has_code,
        "code_files": code_files,
        "found_dummies": found_dummies,
        "has_dummy_connectors": has_dummy_connectors,
        "found_real_execution": found_real_execution,
        "system_type": system_type,
        "has_substantive_prompts": has_substantive_prompts,
        "corrida_count": corrida_count,
        "identified_run_count": identifiable_run_count,
        "complete_trace_count": complete_trace_count,
        "has_complete_triad": has_complete_triad,
        "run_input_output_inconsistency_count": len(run_consistency["inconsistent_groups"]),
        "reused_incompatible_output_count": len(run_consistency["reused_groups"]),
        "governance_execution_contradiction_count": len(review_execution_conflicts),
        "decision_count": decision_count,
        "has_process_iteration": has_process_iteration,
        "has_process_change": has_process_change,
        "has_decision_artifact_links": has_decision_artifact_links,
        "econ": {
            "has_tokens_num": has_tokens_num,
            "has_cost_num": has_cost_num,
            "has_projections": has_projections,
            "has_model_choice": has_model_choice
        },
        "has_verified_economic_metadata": has_verified_economic_metadata,
        "gov_axes": gov_axes,
        "gov_operational_axes": gov_operational_axes,
        "prompt_injection_attempts": prompt_injection_attempts,
        "coverage": {
            "implementation": _coverage(inventory, all_paths, category="implementation"),
            "economics": econ_coverage,
            "governance": gov_coverage,
            "prompts": _coverage(inventory, all_paths, category="prompts"),
            "runs": _coverage(inventory, all_paths, category="runs"),
            "tests": _coverage(inventory, all_paths, category="tests"),
        },
        "evidence_sources": {"economics": econ_paths, "governance": gov_paths},
        "contradictions": contradictions,
        "invalidated_evidence": invalidated_evidence
    }

