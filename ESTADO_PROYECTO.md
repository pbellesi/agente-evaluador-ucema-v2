# Estado del Proyecto

## Fecha de actualización

11 de septiembre de 2026. La arquitectura final queda CONGELADA y validada: pipeline simplificado LLM-as-a-judge con Google Gemini (`gemini-3.6-flash`, $T=0.0$), rúbrica completa, evidencia observable delimitada, salida estructurada y validación matemática determinística externa en Python.

## Fase actual

Cierre y entrega final: arquitectura LLM simple congelada, validada mediante test-retest idéntico (delta 0.00) sobre `caso-02.zip` y 177/177 pruebas automatizadas en verde.

## Equipo y responsables

| Rol | Responsable | Alcance principal |
|---|---|---|
| A | Pablo Bellesi | Coordinación e integración del avance |
| B | Diego Mendez | Integración técnica; pipeline simple LLM-as-a-judge y validación matemática |
| C | Franco Gambini | Rúbrica ejecutable completada; disponible para consulta |
| D | Sofia Mapelli | Casos excelente y flojo completados |
| E | Franco Forziati | Caso adversarial / tramposo completado; disponible para consulta |
| F | Melisa Clark | Calibración inicial, test-retest y QA documentados |

## Completado

- **Evolución documentada con honestidad:**
  - V1 (juez semántico directo con prompts libres) $\to$ dispersión en evaluaciones.
  - V2 determinístico (reglas fijas e inspección sintáctica) $\to$ reproducible pero sobreajustaba fuertemente a estructuras de repositorios y nombres específicos de archivos.
  - Experimento intermedio híbrido (21 unidades de evidencia) $\to$ descartado por sobreingeniería y complejidad innecesaria.
  - **Decisión final congelada:** Evaluador LLM simple con Gemini (`gemini-3.6-flash`, $T=0.0$), rúbrica completa, `system_prompt.md`, principio EVIDENCIA > DECLARACIÓN, niveles discretos en $\{0, 25, 50, 75, 100\}$ y validación matemática en Python.
- **Validación determinística y contrato:** Python valida la presencia de D1–D5, restringe niveles a la escala oficial y calcula el total exacto ($30\% D_1 + 25\% D_2 + 15\% D_3 + 15\% D_4 + 15\% D_5$), corrigiendo cualquier suma errónea del LLM sin alterar sus niveles.
- **Seguridad e integridad:** Contenido del repositorio tratado exclusivamente como DATO delimitado en `<untrusted_repo_content>`. Las inyecciones de prompt se asientan en `integrity_notes` y se ignoran para el scoring. Las fallas de API nunca se transforman en nota 0.
- **Test-retest confirmado:** Dos corridas independientes sobre `caso-02.zip` con delta exacto de 0.00 puntos (Corrida 1: 22.50 vs Corrida 2: 22.50; D1=25, D2=0, D3=75, D4=0, D5=25).
- **Suite de pruebas:** 177/177 pruebas pasando (`pytest -q`), compilación estática limpia (`compileall`) y sin advertencias en `git diff --check`.

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
