# Estado del Proyecto

## Fecha de actualización

El motor integrado en `main` permanece congelado. La vía operativa del System Prompt está integrada en `main` mediante el PR #52, mergeado en `d39592ea76891a50f16f33c47bf65ac37eabea52`; fue validada end-to-end por ZIP y GitHub real.

## Fase actual

Cierre de entrega: motor final y System Prompt operativo integrados y congelados, sin alterar Streamlit ni scoring.

## Equipo y responsables

| Rol | Responsable | Alcance principal |
|---|---|---|
| A | Pablo Bellesi | Coordinación e integración del avance |
| B | Diego Mendez | Integración técnica; agente corrector v1 preservado y System Prompt operativo integrado |
| C | Franco Gambini | Rúbrica ejecutable completada; disponible para consulta |
| D | Sofia Mapelli | Casos excelente y flojo completados |
| E | Franco Forziati | Caso adversarial / tramposo completado; disponible para consulta |
| F | Melisa Clark | Calibración inicial y QA documentados; limitaciones preservadas |

## Completado

- Repositorio público, estructura obligatoria, fuentes, roles, reglas operativas y `.gitignore` disponibles.
- Rúbrica ejecutable V2 completa en `rubrica.md`; cinco niveles como convención del equipo.
- Agente corrector v1 preservado en `agente/`, con contrato JSON y validación inicial contra Tramposo.
- `agente/evaluate_tool.py` implementado y `agente/system_prompt.md` operacionalizado: un agente con workspace y terminal puede invocar el mismo `evaluator_engine`; Streamlit y scoring no cambiaron.
- PR #52 mergeado en `main` (`d39592ea76891a50f16f33c47bf65ac37eabea52`): System Prompt operativo integrado sin cambios en Streamlit ni scoring.
- Validación de esta implementación: 115/115 pruebas verdes. E2E ZIP: PASS sobre `casos/excelente` (88,75; D1–D5 100/100/100/25/100). E2E GitHub real: PASS sobre PULSO en SHA `0f0092a004169e6b64b0f0701eba3baf904cf7db` (85,0; D1–D5 100/100/75/75/50). Ambas pruebas retransmitieron un `EvaluationResult` semánticamente idéntico a la ejecución directa y no modificaron código ni scoring.
- Runtime final determinístico integrado en `src/` y expuesto por `app.py`: no usa APIs generativas, registra la revisión SHA evaluada y trata el contenido objetivo como evidencia.
- Los tres casos completos e integrados: excelente, flojo y tramposo.
- Calibración humano/agente realizada y registrada en `calibracion.md`, con desacuerdos y limitaciones de trazabilidad explícitos.
- Contrato sintético de aceptación completado: 31/31 acceptance tests y 69/69 pruebas de la suite completa.
- Casos oficiales coherentes: Excelente 88,75; Flojo 28,75; Tramposo 21,25.
- Regresión externa completada: PULSO 85,0; SACME 96,25; Lapeque26 92,5; tubidj10 85,0; SilA066 85,0; FSio 92,5; El-Diegote 92,5.

### Issues cerrados y PRs mergeados

| Trabajo | Issue cerrado | PR mergeado hacia main |
|---|---|---|
| Rúbrica original | [#1](https://github.com/pbellesi/agente-evaluador-ucema/issues/1) | [#6](https://github.com/pbellesi/agente-evaluador-ucema/pull/6) |
| Escala V2 | [#7](https://github.com/pbellesi/agente-evaluador-ucema/issues/7) | [#8](https://github.com/pbellesi/agente-evaluador-ucema/pull/8) |
| Documentación post-rúbrica | [#9](https://github.com/pbellesi/agente-evaluador-ucema/issues/9) | [#10](https://github.com/pbellesi/agente-evaluador-ucema/pull/10) |
| Caso tramposo | [#4](https://github.com/pbellesi/agente-evaluador-ucema/issues/4) | [#11](https://github.com/pbellesi/agente-evaluador-ucema/pull/11) |
| Estado post-tramposo | [#12](https://github.com/pbellesi/agente-evaluador-ucema/issues/12) | [#13](https://github.com/pbellesi/agente-evaluador-ucema/pull/13) |
| Agente corrector | [#2](https://github.com/pbellesi/agente-evaluador-ucema/issues/2) | [#14](https://github.com/pbellesi/agente-evaluador-ucema/pull/14) |
| Casos excelente y flojo | [#3](https://github.com/pbellesi/agente-evaluador-ucema/issues/3) | [#15](https://github.com/pbellesi/agente-evaluador-ucema/pull/15) |
| Calibración y QA | [#5](https://github.com/pbellesi/agente-evaluador-ucema/issues/5) | [#16](https://github.com/pbellesi/agente-evaluador-ucema/pull/16) |

## En curso

- Revisión de despliegue/documentación y preparación de defensa/entrega; la publicación en el campus no está acreditada por GitHub.

## Pendiente inmediato

- Revisión de despliegue/documentación y preparación de defensa/entrega; la publicación en el campus no está acreditada por GitHub.

## Bloqueos / inconsistencias conocidas

- La primera calibración no preservó un baseline humano previo independiente ni outputs brutos completos. Esa limitación histórica se conserva en `calibracion.md`; el contrato sintético posterior no la reescribe.
- El runtime trata instrucciones del repositorio como datos y reporta contradicciones; esto no demuestra inmunidad absoluta a prompt injection.
- Las guías internas conservan checkmarks y ejemplos históricos que no acreditan ejecución ni agregan requisitos oficiales.

## Próximo milestone

Entrega documentalmente consistente, con motor congelado, E2E del agente validado, revisión de despliegue y enlace presentado en el campus.

## Próximo paso

Completar la revisión de despliegue/documentación y preparar la defensa/entrega.
