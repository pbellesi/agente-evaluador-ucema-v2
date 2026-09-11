# Decisiones — RadarNorma

## Resumen libre → JSON

La primera versión pedía “resumir novedades importantes”. Una prueba manual omitió enlaces y produjo categorías variables. Se definieron categorías, prioridades y un esquema JSON; las tres salidas conservan esa estructura.

## Navegación en vivo → archivos + modelo real

Se consideró navegar organismos en vivo, pero el prototipo no tenía credenciales ni política de disponibilidad. Se redujo el alcance a lectura y validación real de JSON local, seguida por una invocación real a Codex en ChatGPT Work usando el contrato de `prompts/`. Evidencia: `src/agente.py`, `datos/` y los artefactos completos de `corridas/`.

## Revisión humana del diseño determinístico

La primera implementación clasificaba con reglas y no hacía participar los prompts. La revisión humana de coordinación determinó que un caso excelente debía demostrar una invocación real a IA. Se preservó la herramienta de lectura, se retiró el clasificador determinístico y se ejecutaron tres corridas reales con Codex. Como la plataforma no expone tokens ni el ID exacto del modelo, la limitación quedó documentada sin inventar métricas.

## Supervisión

Se adoptó L2: el sistema propone, una analista revisa y la Responsable de Cumplimiento firma. Una clasificación puede omitir contexto jurídico y no debe circular sin validación.
