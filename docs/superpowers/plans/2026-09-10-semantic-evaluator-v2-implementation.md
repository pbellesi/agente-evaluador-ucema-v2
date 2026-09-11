# Plan de Implementación TDD: Agente Evaluador UCEMA V2 (Juez Semántico)

**Fecha:** 2026-09-10  
**Proyecto:** `agente-evaluador-ucema-v2`  
**Estado:** Aprobado / Enfoque Cognitivo "Comprensión Primero"  
**Metodología:** Test-Driven Development (TDD) estricto en pasos pequeños  

---

## Principios del Plan
1. **Comprensión Primero:** Los contratos y pruebas priorizan entender el proyecto y emitir hallazgos observacionales flexibles antes de la evaluación contra la rúbrica.
2. **Integridad Transversal:** Las anomalías de integridad son una categoría más de hallazgo, no el eje excluyente del diseño.
3. **Validación Determinística Estricta:** Prohibido el clamping automático de niveles (si el modelo no devuelve 0, 25, 50, 75 o 100 se rechaza).
4. **YAGNI en Proveedores:** Un solo proveedor en el MVP (Gemini Flash con `google-genai`), con interfaz abstracta desacoplada.
5. **Aislamiento Total de Tests:** Toda prueba unitaria se ejecuta offline con mocks y fixtures sintéticos. Cero llamadas de red en la suite de tests.

---

## Tareas de Implementación Inmediata

### TAREA 1 — Esquemas Pydantic del Juez Semántico (`src/semantic_schema.py`)
- **Contenido:**
  - `ProjectUnderstanding`: `system_summary`, `architecture_observed`, `main_technologies`.
  - `FindingCategory`: `Literal["implementation", "process", "reproducibility", "economics", "governance", "integrity", "other"]`.
  - `FindingSeverity`: `Literal["info", "low", "medium", "high"]`.
  - `FindingItem`: `category`, `severity`, `files`, `finding`, `impact_on_evaluation`.
  - `ValidLevel`: `Literal[0, 25, 50, 75, 100]`.
  - `DimensionEvaluation`: `recommended_level: ValidLevel`, `justification`, `missing_for_next_level`.
  - `SemanticJudgePayload`: modelo raíz que contiene `project_understanding`, `findings: List[FindingItem]`, `dimension_evaluations: Dict[str, DimensionEvaluation]`, `concrete_improvement`.
- **Tests unitarios:** `tests/test_semantic_schema.py`
  - Validar instanciación exitosa de payload completo válido.
  - Validar rechazo estricto si `recommended_level` no pertenece a `{0, 25, 50, 75, 100}` (ej. 40, 60, 85 fallan).
  - Validar categorías y severidades permitidas.
  - Validar serialización/deserialización JSON.

### TAREA 2 — Constructor de Paquete de Evidencia (`src/context_builder.py`)
- **Contenido:**
  - Función `build_evidence_packet(repo_data: dict, token_budget: int = 150000) -> dict`.
  - Inclusión del inventario completo de archivos (clasificados con ruta, categoría y tamaño).
  - Selección priorizada de archivos: documentación clave (`README.md`, `DECISIONES.md`, `docs/*`), prompts (`prompts/*`), código relevante (`main.py`, `agente.py`, etc.), corridas (`corridas/*`), tests (`tests/*`).
  - Delimitación explícita de seguridad: etiquetas `<untrusted_repo_content path="...">...</untrusted_repo_content>`.
  - Truncamiento explícito para archivos o corridas que excedan presupuesto individual (`[TRUNCADO POR TAMAÑO: N BYTES OMITIDOS]`).
  - Inclusión del texto de la rúbrica oficial como marco de evaluación final.
- **Tests unitarios:** `tests/test_context_builder.py`
  - Inventario completo presente aún si el contenido de algunos archivos no se incluye.
  - Priorización correcta: documentación y prompts se cargan antes que archivos secundarios.
  - Delimitación de seguridad presente en cada bloque de archivo.
  - Truncamiento explícito con marcas visibles ante archivos sobredimensionados.

### TAREA 3 — Validador Determinístico y Guardrail Matemático (`src/evaluation_validator.py`)
- **Contenido:**
  - Función `validate_and_score_evaluation(payload: SemanticJudgePayload, repo_data: dict) -> EvaluationResult`.
  - Verificación de citas: cotejar que cada archivo en `findings[*].files` exista en el inventario real de `repo_data`. Si no existe, agregar aviso en notas de integridad sin romper el flujo.
  - Verificación de niveles válidos: confirmación de que están en `{0, 25, 50, 75, 100}` (sin clamping).
  - Cálculo matemático estricto de pesos oficiales:
    - D1 (Sistema completo y funcionando): 30%
    - D2 (Proceso documentado): 25%
    - D3 (Formato y reproducibilidad): 15%
    - D4 (Análisis económico): 15%
    - D5 (Gobierno y riesgo): 15%
  - Consolidación de `integrity_notes`: agrupa hallazgos de categoría `integrity` y avisos de validación.
  - Construcción del objeto final `EvaluationResult` compatible con V1 / Streamlit.
- **Tests unitarios:** `tests/test_evaluation_validator.py`
  - Cálculo exacto de nota final para combinaciones variadas de niveles.
  - Verificación de que niveles inválidos disparan excepción de validación y NO realizan clamping.
  - Cotejo de archivos citados contra el inventario y generación de avisos por citas inexistentes.
  - Formateo correcto de `DimensionResult` e `integrity_notes`.

---

## Tareas Futuras (Posteriores a MVP Inicial)
- **Tarea 4:** Interfaz `SemanticJudge` y `MockSemanticJudge`.
- **Tarea 5:** Adaptador concreto `GeminiJudge` usando `google-genai` (ya instalado en el entorno).
- **Tarea 6:** Integración en `evaluator_engine.py` (manteniendo fallback opcional).
- **Tarea 7:** Ajustes de presentación en `app.py` y `ui_feedback.py`.
- **Tarea 8:** Calibración ciega con casos de prueba sin sobreajuste.
