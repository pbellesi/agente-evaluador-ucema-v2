# Especificación de Diseño: Calificación Determinística V2

## 1. Contexto y Diagnóstico del Problema

En las evaluaciones del Agente Evaluador UCEMA V2 sobre proyectos de alumnos (en particular `caso-02.zip`), se constató una variabilidad inaceptable en el puntaje final entre corridas consecutivas utilizando el modelo LLM Gemini Flash:
- **Corrida A:** 26.25 / 100
- **Corrida B:** 15.00 / 100

A pesar de que el código base, los archivos del repositorio y la evidencia objetiva eran estrictamente idénticos, la asignación de niveles en dimensiones clave (D3 y D5) fluctuó entre 25% y 75% debido a la naturaleza estocástica del LLM.

Esta variabilidad vulnera el principio rector de justicia académica:
$$\text{Mismo Trabajo} + \text{Misma Versión del Evaluador} \implies \text{Mismos D1..D5 y Misma Nota Total, SIEMPRE}.$$

## 2. Principio Arquitectónico Fundamental

1. **Autoridad Absoluta del Motor Determinístico:**
   - La única fuente autorizada para el cálculo de notas ($D1, D2, D3, D4, D5$, pesos y nota final) es el motor determinístico en Python (`evaluate_repository_deterministically` y la matriz de gates de evidencia objetiva).
   - Mismo repositorio $\implies$ misma evidencia objetiva extraída $\implies$ mismos gates satisfechos $\implies$ misma calificación exacta, con cero variabilidad estocástica y cero dependencia de cuotas de LLM.

2. **Rol del LLM: Analista Semántico Cualitativo:**
   - El LLM (Gemini / NVIDIA) actúa exclusivamente como **analista cualitativo**, no como calificador.
   - Su función es generar:
     - `project_understanding`: resumen interpretativo y arquitectura observada.
     - `findings`: hallazgos detallados con citas de archivos y severidades.
     - `concrete_improvement`: recomendación de mejora pedagógica y verificable.
     - `integrity_notes`: detección cualitativa de intentos de inyección de prompt o inconsistencias semánticas.
   - Las recomendaciones numéricas de nivel que el LLM devuelva (`recommended_level`) **nunca modifican ni reemplazan** los puntajes determinísticos calculados por los gates.

3. **Tolerancia a Fallos y Modo Sin Conexión / Sin API (Zero-API Resilience):**
   - Si la llamada al LLM falla (HTTP 429 cuota diaria, HTTP 503 saturación, timeout, falta de API key, o `judge=None`):
     - La evaluación **NO falla** ni arroja excepción.
     - La nota **NO se vuelve 0**.
     - Se retorna el resultado determinístico completo ($D1..D5$, niveles, justificaciones de gates y nota final) con una nota clara indicando que el análisis semántico no estuvo disponible.

4. **Versionado de Evaluador e Invalidación de Caché:**
   - Se define `EVALUATOR_VERSION = "v2-deterministic-score-1"`.
   - La clave de caché en memoria de Streamlit y en pipelines por lotes es:
     $$\text{cache\_key} = \text{f"\{EVALUATOR\_VERSION\}:\{zip\_sha256\}"}$$
   - Cualquier cambio futuro en la matriz de gates o versionado invalida automáticamente las respuestas cacheadas anteriores.

## 3. Componentes Modificados

### 3.1 `src/batch_evaluator.py`
- `evaluate_project_zip`:
  1. Ingesta segura en memoria (`build_repository_data_from_zip`).
  2. Ejecución inmediata del motor determinístico (`evaluate_repository_deterministically`) como baseline autorizado de scoring.
  3. Si `judge` está presente: intento de evaluación semántica encapsulado en bloque seguro `try/except`.
  4. Si el juez responde exitosamente: fusión controlada de hallazgos semánticos, citas verificadas y sugerencia concreta, preservando los niveles y notas determinísticas.
  5. Si el juez falla (por 429, 503, etc.): retorno del resultado determinístico con aviso informativo y `status="OK"`.

### 3.2 `src/evaluation_validator.py`
- `validate_and_score_evaluation`:
  - Prioriza la evaluación determinística cuando los datos del repositorio contienen contenido inspeccionable (`file_contents`).
  - Audita citas de archivos y banderas de integridad.
  - Asegura que los niveles pertenezcan estrictamente a $\{0, 25, 50, 75, 100\}$.
  - Aplica los pesos oficiales: $D1=30, D2=25, D3=15, D4=15, D5=15$.

### 3.3 `app_v2.py`
- Uso del cache key con versión: `f"{EVALUATOR_VERSION}:{zip_sha256}"`.
- Permite ejecución aun si no hay API key configurada, informando modo determinístico en la interfaz.

### 3.4 `agente/evaluate_v2.py`
- CLI adaptada para utilizar la calificación determinística autorizada, incorporando análisis semántico si el modelo está disponible.

## 4. Plan de Pruebas y Criterios de Aceptación
1. **Prueba de Inmutabilidad ante Payloads Semánticos Variables:**
   - Ejecutar el pipeline con un mismo proyecto y tres payloads simulados contradictorios ($D=0$, $D=100$, niveles aleatorios).
   - Verificar que $D1..D5$ y `final_score` son idénticos en los 3 casos.
2. **Prueba de Resiliencia ante Errores 429 / 503 del LLM:**
   - Simular error de cuota 429 en `judge.evaluate`.
   - Verificar que `outcome.status == "OK"`, el puntaje es mayor que 0 y coincide con el determinístico.
3. **Prueba de Invalidación de Caché por Versión:**
   - Verificar que cambiar `EVALUATOR_VERSION` produce cache miss.
4. **Prueba Test-Retest en los 7 Casos Reales:**
   - Ejecutar 3 corridas de los 7 ZIPs y comprobar variabilidad exactamente 0.
