# Plan de Implementación: Calificación Determinística V2

## Objetivo
Garantizar la reproducibilidad estricta de las evaluaciones:
$$\text{Mismo Trabajo} + \text{Misma Versión del Evaluador} \implies \text{Mismos D1..D5 y Misma Nota Total, SIEMPRE}.$$

## Tareas

### Fase 1: Tests RED (TDD)
- [ ] Crear `tests/test_deterministic_scoring_v2.py` con pruebas unitarias e integración:
  - Test 1: Mismo ZIP con tres payloads de mock judge contradictorios ($D=0$, $D=100$, aleatorio) genera exactamente los mismos puntajes $D1..D5$ y `final_score`.
  - Test 2: Error 429 de Gemini no hace fallar la evaluación, retorna nota determinística válida con aviso y `status="OK"`.
  - Test 3: Error 503 / timeout de LLM retorna nota determinística sin crashear.
  - Test 4: Validación de niveles $\{0, 25, 50, 75, 100\}$ y pesos $30, 25, 15, 15, 15$.
  - Test 5: Cache key versionado con `EVALUATOR_VERSION`.

### Fase 2: Implementación de Código Productivo
- [ ] Definir `EVALUATOR_VERSION = "v2-deterministic-score-1"` en `src/evaluator_engine.py` (y exportar en `src/batch_evaluator.py`).
- [ ] Modificar `evaluate_project_zip` en `src/batch_evaluator.py` para calcular primero la evaluación determinística (`evaluate_repository_deterministically`) como autoridad inmutable de puntajes y niveles, y consultar el juez semántico como analista cualitativo encapsulado en `try/except`.
- [ ] Si el juez falla por cuota o red, preservar el resultado determinístico con aviso informativo, devolviendo `status="OK"`.
- [ ] Ajustar `validate_and_score_evaluation` en `src/evaluation_validator.py` para asegurar que el scoring determinístico sea respetado cuando hay datos completos de repositorio, manteniendo compatibilidad con tests unitarios existentes.
- [ ] Actualizar `app_v2.py` para utilizar `cache_key = f"{EVALUATOR_VERSION}:{zip_sha256}"` y permitir evaluación aun sin API key LLM.
- [ ] Actualizar `agente/evaluate_v2.py` para utilizar el flujo determinístico con análisis semántico adjunto.

### Fase 3: Verificación y Test-Retest
- [ ] Ejecutar toda la suite de pruebas (`pytest`) y verificar 100% PASS sin regresiones.
- [ ] Ejecutar 3 corridas offline de los 7 ZIPs reales comprobando variabilidad exactamente 0.
- [ ] Ejecutar 1 corrida mínima con Gemini real (`caso-02.zip`) verificando enriquecimiento semántico.
- [ ] Verificar funcionamiento en Streamlit (`app_v2.py`) mediante script de simulación/AppTest.
- [ ] Actualizar documentación (`DECISIONES.md`, `README.md`, `ESTADO_PROYECTO.md`).
- [ ] Commits y push a la rama `feat/deterministic-scoring-v2`.
