# Análisis económico

La herramienta local valida datos y el modelo administrado por Codex en ChatGPT Work realiza la clasificación semántica. Se eligió esta combinación porque las reglas solas no representan el contrato agéntico y el modelo puede interpretar lenguaje regulatorio ambiguo.

La plataforma confirmó la invocación, pero no expuso en esta interfaz el identificador exacto del modelo, tokens de entrada/salida ni tarifa marginal. Por eso el costo por corrida **no puede calcularse de manera reproducible con la evidencia disponible**. Los `metadata.json` registran `null` para esas métricas; no se reemplazaron por estimaciones.

Supuesto: 5 corridas por día, 5 días por semana, 52 semanas.

- Volumen semanal: **25 corridas**.
- Volumen anual: **1.300 corridas**.

La proyección monetaria queda pendiente hasta ejecutar con un proveedor que exponga modelo, tokens y tarifa. En producción se elegirá el modelo más pequeño que mantenga la clasificación aceptable en un conjunto validado por Cumplimiento; esta versión no afirma una comparación que todavía no se realizó.
