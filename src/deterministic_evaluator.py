import os
from datetime import datetime
from typing import List, Dict

from src.schema import EvaluationResult, DimensionResult
from src.evidence_extractor import extract_objective_evidence


def _coverage_limited(ev: dict, key: str) -> bool:
    return ev.get("coverage", {}).get(key, {}).get("status") == "skipped"


def evaluate_repository_deterministically(repo_data: dict) -> EvaluationResult:
    """
    Ejecuta la evaluación determinística de un repositorio aplicando
    estrictamente la Matriz por Gates de Evidencia Objetiva de rubrica.md V2.
    - Cero variabilidad estocástica.
    - Cero invocaciones a modelos LLM en runtime.
    - Respeta la jerarquía de evidencia e invalidaciones por contradicción.
    """
    ev = extract_objective_evidence(repo_data)

    dimensions_results: List[DimensionResult] = []
    
    # -------------------------------------------------------------------------
    # Dimensión 1: Sistema completo y funcionando (30 pts)
    # -------------------------------------------------------------------------
    w1 = 30.0
    ev1 = []
    missing1 = None
    
    if not ev["has_code"]:
        lvl1 = 0
        if _coverage_limited(ev, "implementation"):
            just1 = "Hay archivos de implementación en el inventario, pero no fueron inspeccionados completamente por límites de recuperación."
            missing1 = "Reevaluar con cobertura de recuperación suficiente para inspeccionar los archivos de implementación existentes."
        else:
            just1 = "No se encontraron scripts de código ejecutable ni estructura básica de sistema."
            missing1 = "Incorporar la implementación del agente o script de procesamiento ejecutable."
    elif ev["has_dummy_connectors"]:
        lvl1 = 25
        ev1 = ev["found_dummies"]
        just1 = "Existe un intento de código/script, pero contiene conectores o funciones dummy/simuladas que no procesan ni envían datos a un conector o herramienta real."
        missing1 = "Demostrar la invocación efectiva de un conector o herramienta real sin simulación."
    elif ev.get("run_input_output_inconsistency_count", 0) > 0:
        lvl1 = 50
        ev1 = ["Las corridas estructuradas contienen entradas y salidas incompatibles"]
        just1 = "El código invoca una herramienta, pero las salidas observadas no son coherentes con los identificadores de entrada y no demuestran procesamiento correcto de casos reales."
        missing1 = "Conservar corridas cuya salida estructurada pueda vincularse inequívocamente con la entrada procesada."
    elif ev["system_type"] == "rule_based_local" and ev["corrida_count"] < 1:
        lvl1 = 25
        ev1 = [f"Código ejecutable en {f}" for f in ev["code_files"][:3]]
        just1 = "Existe un script de procesamiento por reglas locales, pero carece de corridas reales con salidas observables."
        missing1 = "Generar corridas reales observables y conservarlas en el repositorio."
    elif ev["system_type"] == "rule_based_local" and ev["corrida_count"] >= 1:
        lvl1 = 50
        ev1 = [f"Código en {f}" for f in ev["code_files"][:2]] + [f"{ev['corrida_count']} corrida(s) observable(s)"]
        just1 = "El sistema demuestra procesamiento por reglas locales y corridas observables, pero carece de la integración con herramientas o conectores reales exigida por la rúbrica para niveles superiores (75%/100%)."
        missing1 = "Incorporar la invocación efectiva de un conector o herramienta real (API, modelo de IA o integración remota)."
    elif ev["has_substantive_prompts"] and ev["corrida_count"] >= 1 and ev["has_dummy_connectors"]:
        lvl1 = 50
        ev1 = ev["found_dummies"] + ["Prompts sustantivos presentes en prompts/"]
        just1 = "Existen prompts sustantivos y corridas, pero la integración con herramientas contiene componentes simulados."
        missing1 = "Implementar la llamada o conector real sin simulación."
    elif (ev["has_substantive_prompts"] and 
          ev["corrida_count"] >= 1 and 
          not ev["has_dummy_connectors"] and 
          ev["system_type"] == "real_execution" and 
          ev["gov_axes"].get("human_review", False) and 
          not any("corridas" in c or "agente" in c for c in ev["contradictions"])):
        lvl1 = 100
        ev1 = [f"Código en {f}" for f in ev["code_files"][:2]] + ["Prompts sustantivos en prompts/", f"{ev['corrida_count']} corrida(s) en corridas/", "Supervisión humana documentada"]
        just1 = "El sistema demuestra ejecución real verificable con herramientas, prompts sustantivos, corridas respaldadas y esquema de supervisión humana documentada."
        missing1 = "Mantener la observabilidad y trazabilidad del sistema en producción."
    elif (ev["has_substantive_prompts"] and 
          ev["corrida_count"] >= 1 and 
          not ev["has_dummy_connectors"] and 
          ev["system_type"] == "real_execution"):
        lvl1 = 75
        ev1 = [f"Código en {f}" for f in ev["code_files"][:2]] + ["Prompts sustantivos en prompts/", f"{ev['corrida_count']} corrida(s) en corridas/"]
        just1 = "El sistema cuenta con código ejecutable, prompts sustantivos con rol/instrucciones y corridas reales con salidas estructuradas."
        missing1 = "Demostrar integración completa con conector real y supervisión documentada."
    else:
        lvl1 = 25
        just1 = "Existe un intento inspeccionable, pero no se demuestran los gates obligatorios de niveles superiores."
        missing1 = "Completar la implementación ejecutable y sus corridas respaldadas."

    score1 = w1 * (lvl1 / 100.0)
    dimensions_results.append(DimensionResult(
        dimension="Sistema completo y funcionando",
        weight=w1,
        level_percent=lvl1,
        score=score1,
        evidence=ev1,
        justification=just1,
        missing_for_next_level=missing1
    ))

    # -------------------------------------------------------------------------
    # Dimensión 2: Proceso documentado (25 pts)
    # -------------------------------------------------------------------------
    w2 = 25.0
    ev2 = []
    missing2 = None

    if not ev["mandatory_structure"]["decisiones"]:
        lvl2 = 0
        just2 = "No se encontró el archivo DECISIONES.md en el repositorio."
        missing2 = "Crear el archivo DECISIONES.md documentando las decisiones significativas."
    elif any("DECISIONES.md" in c for c in ev["contradictions"]):
        lvl2 = 25
        ev2 = [c for c in ev["contradictions"] if "DECISIONES.md" in c]
        just2 = "DECISIONES.md está presente, pero contiene contradicciones severas entre las decisiones declaradas y la implementación real del código (aplica Regla de Invalidez de Evidencia)."
        missing2 = "Alinear las decisiones documentadas con el código ejecutable real sin declarar migraciones o capacidades no verificables."
    elif ev["decision_count"] < 1:
        lvl2 = 25
        ev2 = ["DECISIONES.md presente, sin decisiones sustantivas reconstruibles"]
        just2 = "Existe un registro, pero no permite reconstruir una decisión con contexto, cambio y motivo o impacto."
        missing2 = "Documentar una decisión sustantiva con contexto/problema, cambio y motivo/impacto."
    # La cantidad de decisiones es evidencia auxiliar de amplitud histórica,
    # no un mínimo para los niveles altos. Una unidad sustantiva puede reunir
    # por sí sola contexto, falla, corrección, resultado y trazabilidad.
    elif (ev["has_process_iteration"] and ev["has_process_change"]
          and ev["has_decision_artifact_links"] and ev["mandatory_structure"]["is_complete"]):
        lvl2 = 100
        ev2 = [f"Historia con {ev['decision_count']} decisiones sustantivas, iteraciones, cambios y artefactos vinculados"]
        just2 = "Las decisiones, correcciones y cambios documentados forman una historia coherente y trazable con los artefactos disponibles."
        missing2 = "Mantener la trazabilidad de decisiones y artefactos en nuevas iteraciones."
    elif ((ev["has_process_iteration"] and ev["has_process_change"] and ev["has_decision_artifact_links"])
          or ev["decision_count"] >= 2):
        lvl2 = 75
        ev2 = [f"DECISIONES.md con {ev['decision_count']} decisiones sustantivas"]
        just2 = "Hay múltiples decisiones o iteraciones sustantivas, pero la trazabilidad completa del proceso permanece incompleta."
        missing2 = "Vincular de forma completa decisiones, iteraciones, fallas y artefactos pertinentes."
    elif ev["decision_count"] >= 1:
        lvl2 = 50
        ev2 = ["Una decisión sustantiva reconstruible en DECISIONES.md"]
        just2 = "Existe una decisión con contexto, cambio y motivo o impacto, pero no una historia completa del proceso."
        missing2 = "Documentar iteraciones, correcciones o decisiones adicionales y su vínculo con artefactos relevantes."
    else:
        lvl2 = 25
        just2 = "Existe documentación de decisiones pero carece de la sustancia o estructura requerida por los gates obligatorios."
        missing2 = "Documentar al menos 3 decisiones significativas vinculadas a artefactos."

    score2 = w2 * (lvl2 / 100.0)
    dimensions_results.append(DimensionResult(
        dimension="Proceso documentado",
        weight=w2,
        level_percent=lvl2,
        score=score2,
        evidence=ev2,
        justification=just2,
        missing_for_next_level=missing2
    ))

    # -------------------------------------------------------------------------
    # Dimensión 3: Formato y reproducibilidad (15 pts)
    # -------------------------------------------------------------------------
    w3 = 15.0
    ev3 = []
    missing3 = None
    invalidated_run_outputs = [
        item for item in ev["invalidated_evidence"]
        if "corridas/" in item.lower() and "salida" in item.lower()
    ]

    if not ev["mandatory_structure"]["prompts"] or not ev["mandatory_structure"]["corridas"]:
        lvl3 = 0
        just3 = "Faltan carpetas obligatorias (prompts/ o corridas/) en el repositorio."
        missing3 = "Incorporar las carpetas obligatorias prompts/ y corridas/ con sus contenidos correspondientes."
    elif invalidated_run_outputs:
        lvl3 = 25
        ev3 = invalidated_run_outputs
        just3 = "Las salidas preservadas afirman ejecución real, pero esa afirmación fue invalidada por contradicción objetiva con la implementación observable."
        missing3 = "Conservar corridas reales cuya salida pueda producirse y contrastarse con la implementación ejecutable."
    elif ev["identified_run_count"] < 1:
        lvl3 = 25
        ev3 = ["Estructura obligatoria presente, 0 corridas encontradas"]
        just3 = "La estructura obligatoria está presente, pero no se encontraron corridas en corridas/."
        missing3 = "Guardar al menos una corrida real en corridas/."
    elif ev["complete_trace_count"] >= 1 and ev["identified_run_count"] < 3:
        lvl3 = 50
        ev3 = [f"Estructura presente con {ev['corrida_count']} corrida(s) que conserva(n) entrada, salida y fecha"]
        just3 = "Existe al menos una corrida real con la triada completa (entrada, salida, fecha), pero no se alcanza el mínimo oficial de 3 corridas."
        missing3 = "Incorporar al menos tres corridas reales completas que conserven entrada, salida y fecha."
    elif ev["identified_run_count"] >= 3 and ev["complete_trace_count"] < 3:
        lvl3 = 75
        ev3 = [f"{ev['identified_run_count']} corridas identificables, de las cuales {ev['complete_trace_count']} conservan la triada completa"]
        just3 = "Hay tres o más corridas identificables, pero al menos una no vincula inequívocamente entrada, salida y fecha."
        missing3 = "Conservar la triada completa y vinculada para cada corrida identificable."
    elif (ev["mandatory_structure"]["is_complete"] and 
          ev["complete_trace_count"] >= 3 and
          not any("salida" in c or "corridas" in c for c in ev["contradictions"])):
        lvl3 = 100
        ev3 = [f"Estructura completa y {ev['corrida_count']} corridas reales que conservan entrada, salida y fecha de forma transparente"]
        just3 = "La estructura obligatoria está completa y existen al menos 3 corridas reales identificables con preservación completa de entrada, salida y fecha."
        missing3 = "Mantener la actualización de corridas al incorporar nuevas iteraciones."
    elif ev["identified_run_count"] >= 3 and ev["complete_trace_count"] >= 3:
        lvl3 = 75
        ev3 = [f"{ev['corrida_count']} corridas físicamente presentes, pero con salidas invalidadas por contradicción con el código ejecutable"]
        just3 = "La estructura obligatoria está presente y existen al menos 3 corridas, pero las salidas declaradas son contradichas por el código real, impidiendo la reproducibilidad plena a 100% (aplica Regla de Invalidez de Evidencia)."
        missing3 = "Asegurar que las salidas conservadas en corridas/ puedan ser producidas de forma transparente por el código ejecutable."
    else:
        lvl3 = 25
        just3 = "La estructura básica está presente pero las corridas están incompletas o inaccesibles."
        missing3 = "Completar la triada de entrada, salida y fecha para al menos 3 corridas."

    score3 = w3 * (lvl3 / 100.0)
    dimensions_results.append(DimensionResult(
        dimension="Formato y reproducibilidad",
        weight=w3,
        level_percent=lvl3,
        score=score3,
        evidence=ev3,
        justification=just3,
        missing_for_next_level=missing3
    ))

    # -------------------------------------------------------------------------
    # Dimensión 4: Análisis económico (15 pts)
    # -------------------------------------------------------------------------
    w4 = 15.0
    ev4 = []
    missing4 = None
    econ = ev["econ"]

    if any("analisis_economico" in c for c in ev["contradictions"]):
        lvl4 = 0
        ev4 = [c for c in ev["contradictions"] if "analisis_economico" in c]
        just4 = "docs/analisis_economico.md declara consumo de tokens por corrida, pero la implementación ejecutable del sistema no invoca ni consume modelos de IA (aplica Regla de Invalidez de Evidencia)."
        missing4 = "Alinear las métricas económicas con ejecuciones reales de un modelo de IA o presentar una estimación cualitativa genuina."
    elif not econ["has_tokens_num"] and not econ["has_cost_num"] and not econ["has_projections"]:
        lvl4 = 0
        if _coverage_limited(ev, "economics"):
            just4 = "Existe documentación económica en el inventario, pero no fue inspeccionada completamente por límites de recuperación."
            missing4 = "Reevaluar con cobertura de recuperación suficiente para inspeccionar la documentación económica existente."
        else:
            just4 = "No se encontraron cifras verificables ni estimaciones de tokens, costos o proyecciones."
            missing4 = "Crear el archivo docs/analisis_economico.md con estimación o medición de costos."
    elif econ["has_model_choice"] and not (econ["has_tokens_num"] and econ["has_cost_num"]):
        lvl4 = 25
        ev4 = ["Mención cualitativa de modelo o costo en documentación"]
        just4 = "Existe un intento cualitativo de justificación o mención de costos, pero no permite calcular un costo reproducible por corrida."
        missing4 = "Vincular tokens consumidos por corrida y tarifa del modelo para calcular el costo por corrida."
    elif econ["has_tokens_num"] and econ["has_cost_num"] and not econ["has_projections"]:
        lvl4 = 50
        ev4 = ["Tokens y costo por corrida identificados en documentación"]
        just4 = "El costo por corrida está identificado a partir de tokens y tarifa, pero no se presentan las proyecciones de uso semanal y anual."
        missing4 = "Incorporar las proyecciones de costo semanal y anual con volumen y supuestos explícitos."
    elif econ["has_tokens_num"] and econ["has_cost_num"] and econ["has_projections"] and not econ["has_model_choice"]:
        lvl4 = 75
        ev4 = ["Costo por corrida y proyecciones semanal y anual calculadas"]
        just4 = "El costo por corrida y las proyecciones semanal y anual están explícitos, pero no se fundamenta la selección del modelo bajo el criterio 'el más chico que hace bien la tarea'."
        missing4 = "Justificar por qué el modelo elegido es el más chico adecuado para la tarea."
    elif (econ["has_tokens_num"] and econ["has_cost_num"] and econ["has_projections"]
          and econ["has_model_choice"] and ev["has_verified_economic_metadata"]):
        lvl4 = 100
        ev4 = ["Metadata verificable de corrida con consumo, modelo y costo; cálculos y proyecciones documentados"]
        just4 = "Los consumos de corrida, modelo, costo reproducible, proyecciones y justificación económica están trazados a metadata verificable."
        missing4 = "Mantener la evidencia de corrida y actualizar los supuestos al cambiar el modelo o volumen."
    elif econ["has_tokens_num"] and econ["has_cost_num"] and econ["has_projections"] and econ["has_model_choice"]:
        lvl4 = 75
        ev4 = ["Costo por corrida, proyecciones semanal/anual y elección de modelo presentadas"]
        just4 = "Las cifras de consumo, costo por corrida, proyecciones y elección del modelo están calculadas de forma completa."
        missing4 = "Acompañar los datos declarados con logs o metadata original exportada del proveedor."
    else:
        lvl4 = 25
        just4 = "Existe documentación económica cualitativa pero carece de desgloses numéricos por corrida."
        missing4 = "Incorporar cálculos numéricos de tokens y tarifa por corrida."

    score4 = w4 * (lvl4 / 100.0)
    dimensions_results.append(DimensionResult(
        dimension="Análisis económico",
        weight=w4,
        level_percent=lvl4,
        score=score4,
        evidence=ev4,
        justification=just4,
        missing_for_next_level=missing4
    ))

    # -------------------------------------------------------------------------
    # Dimensión 5: Gobierno y riesgo (15 pts)
    # -------------------------------------------------------------------------
    w5 = 15.0
    ev5 = []
    missing5 = None
    g = ev["gov_axes"]
    operational_g = ev["gov_operational_axes"]

    active_axes_count = sum(1 for v in g.values() if v)
    operational_axes_count = sum(1 for v in operational_g.values() if v)

    if active_axes_count == 0:
        lvl5 = 0
        if _coverage_limited(ev, "governance"):
            just5 = "Existe documentación de gobierno o riesgo en el inventario, pero no fue inspeccionada completamente por límites de recuperación."
            missing5 = "Reevaluar con cobertura de recuperación suficiente para inspeccionar la documentación de gobierno existente."
        else:
            just5 = "No se encontró documentación de gobierno y riesgo ni mención de controles de seguridad."
            missing5 = "Crear el archivo docs/gobierno_riesgo.md detallando sistemas, permisos, fallas y supervisión."
    elif ev.get("governance_execution_contradiction_count", 0) > 0:
        lvl5 = 50 if operational_axes_count > 0 else 25
        ev5 = [c for c in ev["contradictions"] if "gobierno" in c.lower()]
        just5 = "La política de supervisión está documentada, pero una corrida observable contradice su aplicación; la evidencia favorable de ese control no es válida."
        missing5 = "Alinear las salidas de corrida con las condiciones documentadas de revisión o aprobación humana."
    elif operational_axes_count >= 5 and not any("gobierno" in c for c in ev["contradictions"]):
        lvl5 = 100
        ev5 = ["Todos los 5 ejes de gobierno identificados (permisos, fallas, respuesta, supervisión y firma/responsable) sin contradicciones"]
        just5 = "Los ejes de gobierno y riesgo (permisos, fallas, respuesta, supervisión y responsable explícito) están documentados y alineados con el sistema."
        missing5 = "Mantener la actualización de la matriz de gobierno ante cambios en la arquitectura."
    elif active_axes_count >= 5:
        lvl5 = 75
        ev5 = ["Los cinco ejes están presentes, pero falta precisión operativa en al menos uno"]
        just5 = "La cobertura de gobierno es amplia, pero alguna respuesta, supervisión o responsabilidad no define un mecanismo aplicable."
        missing5 = "Precisar los mecanismos operativos de permisos, respuesta, revisión y responsabilidad."
    elif operational_axes_count == 0:
        lvl5 = 25
        ev5 = ["Menciones genéricas de gobierno sin controles operativos verificables"]
        just5 = "Existe una mención cualitativa o genérica de gobierno, pero no se detallan permisos ni modos de falla concretos."
        missing5 = "Detallar sistemas y permisos concretos y fallas específicas con sus consecuencias."
    elif operational_axes_count < 4:
        lvl5 = 50
        ev5 = [f"Ejes identificados: {[k for k,v in g.items() if v]}"]
        just5 = "Se identifican sistemas/permisos o fallas concretas, pero faltan la respuesta prevista o el punto de supervisión humana."
        missing5 = "Definir la respuesta/acción prevista ante una falla y especificar qué revisa una persona y en qué momento."
    elif active_axes_count >= 4 and not g["responsible"]:
        lvl5 = 75
        ev5 = [f"4 ejes de gobierno identificados (permisos, fallas, respuesta y supervisión humana)"]
        just5 = "Sistemas/permisos, fallas, respuesta prevista y supervisión humana están definidos, pero no se asigna un responsable o firma explícita por el resultado."
        missing5 = "Especificar quién firma o asume la responsabilidad final por el resultado del agente."
    elif active_axes_count >= 4 and g["responsible"]:
        lvl5 = 75
        ev5 = [f"Ejes de gobierno identificados, pero con contradicciones o especificación incompleta"]
        just5 = "Los ejes de gobierno y riesgo están documentados pero contienen contradicciones puntuales con la implementación real."
        missing5 = "Resolver las contradicciones entre la documentación de riesgo y la implementación real del sistema."
    else:
        lvl5 = 25
        just5 = "Existe documentación básica de riesgo pero carece de la especificación operativa de los gates."
        missing5 = "Completar la especificación de los ejes de gobierno y riesgo."

    score5 = w5 * (lvl5 / 100.0)
    dimensions_results.append(DimensionResult(
        dimension="Gobierno y riesgo",
        weight=w5,
        level_percent=lvl5,
        score=score5,
        evidence=ev5,
        justification=just5,
        missing_for_next_level=missing5
    ))


    # -------------------------------------------------------------------------
    # Cálculo de Puntaje Final y Notas de Integridad
    # -------------------------------------------------------------------------
    total_score = sum(d.score for d in dimensions_results if d.score is not None)

    # Determinación de sugerencia concreta única
    lowest_dim = min(dimensions_results, key=lambda d: d.level_percent if d.level_percent is not None else 0)
    concrete_improvement = (
        lowest_dim.missing_for_next_level or 
        f"Mejorar la dimensión '{lowest_dim.dimension}' para alcanzar el nivel siguiente."
    )

    integrity_notes = list(ev["contradictions"])
    if ev["invalidated_evidence"]:
        integrity_notes.append(f"Evidencia invalidada por contradicción: {', '.join(ev['invalidated_evidence'])}")
    integrity_notes.extend(ev.get("prompt_injection_attempts", []))

    return EvaluationResult(
        repository=repo_data["repository"],
        evaluated_revision=repo_data.get("evaluated_revision", "main@unknown"),
        evaluation_date=datetime.now().strftime("%Y-%m-%d"),
        evaluation_status="completed",
        dimensions=dimensions_results,
        final_score=round(total_score, 2),
        concrete_improvement=concrete_improvement,
        integrity_notes=integrity_notes
    )
