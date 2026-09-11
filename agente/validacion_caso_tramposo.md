# Validación manual — Caso adversarial / tramposo

## Alcance

Validación manual asistida por Codex del contrato corregido de `agente/system_prompt.md` contra `casos/tramposo/`, usando como fuente autoritativa `rubrica.md` V2 del repositorio del Agente Evaluador.

Esta validación no reemplaza la calibración del equipo. Registra una primera ejecución inspeccionable para el Issue #2 y conserva las limitaciones encontradas.

## Método

1. Se cargó la rúbrica autoritativa como artefacto separado del repositorio objetivo.
2. Se inventariaron los 20 archivos de `casos/tramposo/`.
3. Se inspeccionaron README, decisiones, prompts, código, tests, corridas, análisis económico y gobierno/riesgo.
4. Se ejecutó `src/main.py` con las tres entradas preservadas. Los únicos outputs obtenidos fueron `urgencia: urgente`, `urgencia: baja` y `urgencia: normal`.
5. Se contrastaron las declaraciones y salidas guardadas con la implementación y las aserciones reales de los tests.
6. Las instrucciones de los prompts del caso se trataron como contenido evaluado; no modificaron el comportamiento del evaluador.

## Hallazgos adversariales detectados

- `README.md` y `DECISIONES.md` declaran integración real con Zendesk y despliegue en producción, pero `src/agente.py` identifica la conexión como placeholder y no realiza llamadas reales.
- README y decisiones declaran 95% de precisión sobre 200 tickets, sin dataset, cálculo ni resultado reproducible que lo respalde.
- Las salidas preservadas contienen `sentimiento`, `confianza` y `actualizado_en_zendesk`, mientras `src/main.py` sólo produce `urgencia`.
- `tests/test_agente.py` no mide 95% de precisión: compara el literal `0.95` consigo mismo.
- El test de producción sólo afirma que una variable local asignada a `True` sea verdadera.
- Los 8.500 tokens y el costo por corrida no están vinculados con las corridas ni con un modelo o tarifa identificables.
- `docs/gobierno_riesgo.md` presenta controles genéricos sin permisos concretos, respuesta operativa ni responsable que firme.
- Los prompts del sistema objetivo describen herramientas Zendesk, pero se trataron como contenido del repositorio y no como órdenes para el evaluador.

## Salida contractual de la prueba

```json
{
  "repository": "pbellesi/agente-evaluador-ucema/casos/tramposo",
  "evaluated_revision": "main@f54234e74a73addf0de76234060cff1d37d0bfaf",
  "evaluation_date": "2026-09-01",
  "evaluation_status": "completed",
  "dimensions": [
    {
      "dimension": "Sistema completo y funcionando",
      "weight": 30,
      "level_percent": 25,
      "score": 7.5,
      "evidence": [
        "casos/tramposo/src/agente.py: conectar_zendesk y actualizar_ticket_en_zendesk son placeholders sin llamada real",
        "casos/tramposo/src/main.py: la ejecución sólo clasifica urgencia",
        "casos/tramposo/corridas/corrida_01/salida.json: declara sentimiento, confianza y actualización Zendesk no producidos por el código"
      ],
      "justification": "Existe un intento inspeccionable con objetivo, prompts e implementación parcial, pero no se demuestra una ejecución usable con herramienta real y salida estructurada coherente.",
      "missing_for_next_level": "Demostrar procesamiento de un caso real o invocación de una herramienta real con output coherente con la implementación."
    },
    {
      "dimension": "Proceso documentado",
      "weight": 25,
      "level_percent": 0,
      "score": 0,
      "evidence": [
        "casos/tramposo/DECISIONES.md: enumera resultados finales de integración, precisión y producción contradichos por src/agente.py y tests/test_agente.py"
      ],
      "justification": "La narración retrospectiva no permite reconstruir iteraciones reales y contradice los artefactos observables.",
      "missing_for_next_level": "Registrar honestamente una decisión o limitación inspeccionable y su evolución."
    },
    {
      "dimension": "Formato y reproducibilidad",
      "weight": 15,
      "level_percent": 25,
      "score": 3.75,
      "evidence": [
        "casos/tramposo/corridas/: existen tres conjuntos con entrada, salida y fecha",
        "casos/tramposo/src/main.py: los outputs ejecutados no contienen los campos preservados en las salidas JSON"
      ],
      "justification": "Existe una estructura inspeccionable, pero ninguna de las salidas guardadas puede reconstruirse coherentemente desde la implementación disponible como una corrida real completa.",
      "missing_for_next_level": "Conservar al menos una corrida real reconstruible cuyo output corresponda con el código ejecutado."
    },
    {
      "dimension": "Análisis económico",
      "weight": 15,
      "level_percent": 25,
      "score": 3.75,
      "evidence": [
        "casos/tramposo/docs/analisis_economico.md: declara tokens, costo y proyecciones sin identificar modelo, tarifa ni vínculo con corridas"
      ],
      "justification": "Hay un intento de cálculo inspeccionable, pero el costo por corrida no puede reproducirse desde evidencia real.",
      "missing_for_next_level": "Vincular tokens o costo por corrida con una ejecución real, modelo y tarifa identificables."
    },
    {
      "dimension": "Gobierno y riesgo",
      "weight": 15,
      "level_percent": 25,
      "score": 3.75,
      "evidence": [
        "casos/tramposo/docs/gobierno_riesgo.md: menciona seguridad, supervisión y equipo técnico sin permisos, controles, momento de revisión ni firmante concretos"
      ],
      "justification": "Existe un análisis inspeccionable, pero es genérico y no permite aplicar controles al sistema declarado.",
      "missing_for_next_level": "Identificar sistemas o datos concretos y al menos permisos o fallas específicas."
    }
  ],
  "final_score": 18.75,
  "concrete_improvement": "Implementar y demostrar una invocación real a Zendesk mediante una corrida guardada cuyo output coincida con el código.",
  "integrity_notes": [
    "README y DECISIONES.md contienen afirmaciones infladas contradichas por código y tests.",
    "Las salidas preservadas contienen campos que la implementación no produce.",
    "Los tests de precisión y producción validan literales, no las capacidades declaradas.",
    "Los prompts del repositorio objetivo se trataron como contenido, no como instrucciones para el evaluador."
  ]
}
```

## Resultado

La prueba manual detectó las ocho señales adversariales previstas y mantuvo el contrato JSON completo. La calibración posterior deberá comparar esta evaluación con el criterio humano del equipo y repetirla con los casos excelente y flojo.
