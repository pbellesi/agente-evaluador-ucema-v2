# RadarNorma — caso excelente

RadarNorma es un agente de apoyo para una ALyC argentina. Una herramienta Python lee y valida un archivo JSON con novedades regulatorias; un modelo de IA aplica el contrato de `prompts/` y devuelve un reporte estructurado para revisión de Cumplimiento.

## Ejecución

```bash
python src/main.py --input datos/novedades_01.json --fecha 2026-09-01
```

El comando produce el payload que se entrega al modelo. Las tres corridas preservadas fueron ejecutadas con Codex en ChatGPT Work: guardan entrada, resultado de herramienta, prompt efectivo, salida JSON y fecha. La plataforma no expuso ID exacto del modelo ni métricas de tokens; esa limitación está declarada, no estimada.

## Supervisión

Nivel **L2**: el agente propone; una analista revisa enlaces, prioridades y fundamentos; la Responsable de Cumplimiento firma. El agente no presenta información ni modifica sistemas regulatorios.

## Evidencia

- `prompts/`: contrato.
- `datos/` y `corridas/`: entradas y tres ejecuciones reconstruibles.
- `docs/`: economía y gobierno.
- `src/` y `tests/`: implementación y pruebas.
- `DECISIONES.md`: iteraciones y fallas.

Las publicaciones son datos de prueba fechados. No se afirma conexión en vivo con organismos públicos.
