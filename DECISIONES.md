# Registro de Decisiones

Este archivo documenta decisiones significativas del proyecto: su contexto, criterio humano, apoyo de IA, impacto y eventual revisión. No transcribe chats completos con IA; registra interacciones significativas cuando influyeron en una decisión. Cada decisión puede revisarse posteriormente: si cambia, no se borra la versión anterior, sino que se documenta su evolución.

Cuando resulte relevante, cada decisión puede vincularse con Issue, rama, commit y Pull Request. Los identificadores se registran cuando existen y aportan trazabilidad.

## DEC-001 — Asignación definitiva de roles

**Estado:** Vigente  
**Responsable / participantes:** Pablo Bellesi (Rol A - Coordinación; validación humana).  
**IA utilizada:** Codex, para inspección y normalización documental bajo instrucciones y aprobación humana.  
**Contexto:** La documentación interna contenía propuestas anteriores y responsables alternativos.  
**Decisión:** A - Pablo Bellesi: Coordinación; B - Diego Mendez: Integración técnica; C - Franco Gambini: Rúbrica ejecutable; D - Sofia Mapelli: Casos excelente y flojo; E - Franco Forziati: Caso adversarial / tramposo; F - Melisa Clark: Calibración y QA.  
**Motivo:** Establecer una única asignación de responsabilidades antes de inicializar Git.  
**Impacto esperado:** Evitar ambigüedad de ownership y orientar el trabajo y la revisión cruzada.  
**Evidencia / archivos relacionados:** `AGENTS.md`; `ESTADO_PROYECTO.md`; `00_fuentes/equipo/0_RESUMEN_Y_PLAN_EJECUCION.md`; `00_fuentes/equipo/2_PIC-AE_DESARROLLO_CASOS_PRUEBA.md`; `00_fuentes/equipo/3_PIC-AE_DESARROLLO_CALIBRACION.md`.  
**Revisión futura:** Revisar solo mediante decisión humana explícita; esta normalización reemplazó propuestas anteriores antes de inicializar Git.

## DEC-002 — GitHub será la fuente común de trabajo colaborativo

**Estado:** Vigente  
**Responsable / participantes:** Pablo Bellesi (Rol A - Coordinación; validación humana).  
**IA utilizada:** Codex, para documentar reglas operativas definidas por instrucción humana.  
**Contexto:** El proyecto requiere evidenciar colaboración y evolución real; Git todavía no está inicializado.  
**Decisión:** El proyecto utilizará un único repositorio GitHub como fuente compartida. Una vez iniciado el trabajo colaborativo, no se trabajará directamente sobre `main`; las tareas relevantes se vincularán a Issues, se utilizarán ramas, los cambios se integrarán mediante Pull Requests y se promoverá revisión cruzada antes del merge.  
**Motivo:** Hacer visible la contribución de cada integrante y la evolución del proyecto.  
**Impacto esperado:** Trazabilidad verificable de cambios, revisiones y decisiones.  
**Evidencia / archivos relacionados:** `AGENTS.md`; `ESTADO_PROYECTO.md`; `00_fuentes/docente/prompts_github.html`.  
**Revisión futura:** Aplicar estas reglas al inicializar Git y ajustar su operación solo con acuerdo humano documentado.

## DEC-003 — Estrategia multiherramienta de IA

**Estado:** Vigente  
**Responsable / participantes:** Pablo Bellesi (Rol A - Coordinación; validación humana).  
**IA utilizada:** Codex, como herramienta de asistencia documental.  
**Contexto:** El equipo puede contar con acceso, costo/cuota y capacidades diferentes según la herramienta y la tarea.  
**Decisión:** Se podrán utilizar Codex, Claude, Antigravity, ChatGPT u otras herramientas justificadas. La herramienta no define la fuente de verdad: todas deben respetar `AGENTS.md`, las decisiones vigentes, la rúbrica, la estructura común y GitHub. La disponibilidad de una herramienta no reasigna roles.  
**Motivo:** Mantener flexibilidad operativa sin perder consistencia ni responsabilidad humana.  
**Impacto esperado:** Compatibilidad entre herramientas y continuidad del proyecto ante cambios de acceso.  
**Evidencia / archivos relacionados:** `AGENTS.md`; `00_fuentes/equipo/0_RESUMEN_Y_PLAN_EJECUCION.md`.  
**Revisión futura:** Registrar herramientas adicionales solo si su uso resulta significativo para una decisión o resultado.

## DEC-004 — Trazabilidad del uso de IA y de las iteraciones

**Estado:** Vigente  
**Responsable / participantes:** Pablo Bellesi (Rol A - Coordinación; validación humana).  
**IA utilizada:** Codex, para documentar esta decisión solicitada por el coordinador.  
**Contexto:** El proceso del parcial debe mostrar trabajo real, revisiones e iteración, sin simular una historia perfecta.  
**Decisión:** El repositorio deberá permitir observar el problema abordado, responsable, IA utilizada cuando sea relevante, primera propuesta o implementación, revisión, errores o desacuerdos detectados, correcciones y resultado posterior. No se guardarán conversaciones completas con IA.  
**Motivo:** Conservar evidencia útil del criterio humano y de la evolución real del trabajo.  
**Impacto esperado:** Un proceso auditable y honesto, incluyendo correcciones e iteraciones valiosas.  
**Evidencia / archivos relacionados:** Futuramente, combinación de Issues, commits, Pull Requests, reviews, `DECISIONES.md`, `calibracion.md` y resultados de pruebas; actualmente, `AGENTS.md` y este registro.  
**Revisión futura:** Precisar el nivel de detalle tras las primeras tareas versionadas, sin sustituir evidencia por narración.

## DEC-005 — Principio EVIDENCIA > DECLARACIÓN

**Estado:** Vigente  
**Responsable / participantes:** Pablo Bellesi (Rol A - Coordinación; validación humana).  
**IA utilizada:** Codex, para incorporar el principio operativo bajo instrucciones humanas.  
**Contexto:** Un repositorio evaluado puede afirmar capacidades sin artefactos que las demuestren.  
**Decisión:** Una afirmación en README, documentación o prompts no constituye automáticamente evidencia suficiente si puede verificarse mediante artefactos observables. El evaluador priorizará archivos, configuraciones, corridas, outputs, historial, pruebas y otros artefactos verificables.  
**Motivo:** Reducir evaluaciones basadas en declaraciones no comprobables.  
**Impacto esperado:** Mayor rigor de evaluación y detección de afirmaciones engañosas, especialmente en el caso tramposo.  
**Evidencia / archivos relacionados:** `AGENTS.md`; futura implementación de `rubrica.md` y caso `casos/tramposo/`.  
**Revisión futura:** Convertir el principio en criterios observables al elaborar la rúbrica ejecutable.

## DEC-006 — Jerarquía de fuentes

**Estado:** Vigente  
**Responsable / participantes:** Pablo Bellesi (Rol A - Coordinación; validación humana).  
**IA utilizada:** Codex, para documentar la jerarquía indicada por el coordinador.  
**Contexto:** El proyecto contiene consignas oficiales, material docente, documentación operativa y guías internas.  
**Decisión:** La jerarquía es: 1) consigna oficial del parcial; 2) consigna/rúbrica oficial del trabajo final; 3) material docente; 4) decisiones aprobadas por el equipo; 5) documentación operativa; 6) guías internas PIC-AE. Las guías PIC-AE son apoyo interno y no requisitos oficiales por sí mismas.  
**Motivo:** Resolver contradicciones sin presentar recomendaciones internas como normativa.  
**Impacto esperado:** Interpretación consistente de requisitos y menor riesgo de desviación.  
**Evidencia / archivos relacionados:** `AGENTS.md`; `00_fuentes/consigna/`; `00_fuentes/docente/`; `00_fuentes/equipo/`.  
**Revisión futura:** Mantener la jerarquía salvo instrucción oficial o decisión humana documentada que requiera actualizarla.

## DEC-007 — Separación de las dos rúbricas

**Estado:** Vigente  
**Responsable / participantes:** Pablo Bellesi (Rol A - Coordinación; validación humana).  
**IA utilizada:** Codex, para registrar la separación solicitada por el coordinador.  
**Contexto:** Existen una rúbrica para evaluar el parcial grupal y otra para evaluar los trabajos finales individuales.  
**Decisión:** La rúbrica del parcial evalúa el proyecto grupal Agente Evaluador. La rúbrica del trabajo final es la que nuestro agente deberá aplicar posteriormente a repositorios individuales. Nunca se mezclarán sus dimensiones, pesos ni escalas.  
**Motivo:** Evitar que el agente o la documentación apliquen criterios al objeto equivocado.  
**Impacto esperado:** Rúbrica ejecutable y calibración alineadas con el objeto correcto de evaluación.  
**Evidencia / archivos relacionados:** `AGENTS.md`; `00_fuentes/consigna/parcial_agente_evaluador.pdf`; `00_fuentes/consigna/trabajo_final.pdf`.  
**Revisión futura:** Verificar esta separación al redactar `rubrica.md` y al construir los casos.

## DEC-008 — Evolución y cierre de la rúbrica ejecutable V2

**Estado:** Vigente<br>
**Responsable / participantes:** Pablo Bellesi (Rol A - coordinación y validación humana); Franco Gambini (Rol C - rúbrica ejecutable).<br>
**IA utilizada:** Codex, para auditorías, edición y verificación bajo instrucciones y aprobación humanas.<br>
**Contexto:** La primera versión de la rúbrica utilizaba un scoring interno `CUMPLE / PARCIAL / NO CUMPLE`. Una auditoría identificó que ese mecanismo podía dejar margen insuficiente para una asignación determinística. La corrección se integró como una primera versión ejecutable mediante el PR #6, que cerró el Issue #1. Posteriormente, durante una clase se observó un ejemplo pedagógico de escala discreta 0% / 25% / 50% / 75% / 100%. Inicialmente se le atribuyó un peso normativo mayor al que correspondía.<br>
**Decisión:** Tras la aclaración humana de que el ejemplo de clase no amplía ni modifica las consignas oficiales, el equipo conserva la escala de cinco niveles como **convención de diseño propia**. La rúbrica V2 deja explícito que el ejemplo fue una inspiración pedagógica no normativa; las consignas oficiales continúan siendo la fuente normativa.<br>
**Motivo:** La escala discreta mejora la precisión y la repetibilidad de la rúbrica sin atribuir al docente un requisito que no estableció.<br>
**Impacto esperado:** Permitir que humanos y agentes apliquen niveles y evidencia de manera consistente, manteniendo la jerarquía correcta de fuentes.<br>
**Evidencia / archivos relacionados:** `rubrica.md` V2; Issue #1 y PR #6; Issue #7 y PR #8; auditoría final contra las consignas oficiales con veredicto MERGE.<br>
**Revisión futura:** Revisar únicamente ante una modificación de la consigna oficial o una nueva decisión humana documentada. No convertir el ejemplo pedagógico en normativa por iniciativa propia.

## Historial inicial de asistencia con IA

- Codex realizó una inspección inicial del workspace en modo lectura.
- Codex identificó inconsistencias documentales y roles desactualizados.
- Tras aprobación humana, Codex normalizó los roles en documentos internos.
- Codex generó `AGENTS.md` a partir de instrucciones y fuentes seleccionadas.
- Codex generó `ESTADO_PROYECTO.md` reflejando el estado real.

Las acciones fueron solicitadas y validadas por el coordinador. Codex no tomó decisiones autónomas sobre roles, rúbricas ni Git. Este registro describe el período inicial, previo a la inicialización de Git; la evolución posterior quedó trazable mediante Issues, ramas, commits y Pull Requests.

## DEC-009 — Preservar la validez del caso adversarial

**Estado:** Vigente<br>
**Responsable / participantes:** Pablo Bellesi, revisión y autorización de la corrección; Franco Forziati, responsable humano del caso.<br>
**IA utilizada:** Claude en el trabajo original; Codex en la corrección solicitada por coordinación.<br>
**Contexto:** La revisión del PR #11 detectó que `casos/tramposo/NOTA.md` explicaba las trampas y la puntuación esperada dentro del propio objetivo evaluado.<br>
**Decisión:** Eliminar únicamente esa nota del árbol del caso y conservar sus contradicciones, afirmaciones infladas, código, tests y corridas.<br>
**Motivo:** Evitar que la prueba entregue la respuesta al corrector sin suavizar su contenido adversarial.<br>
**Impacto esperado:** Evaluar el contraste de evidencia; la eliminación no borra el archivo del historial Git, que se conserva como evidencia de la revisión.<br>
**Evidencia / archivos relacionados:** [Issue #4](https://github.com/pbellesi/agente-evaluador-ucema/issues/4), [PR #11 y comentario de revisión](https://github.com/pbellesi/agente-evaluador-ucema/pull/11); original `59fae77`, corrección `5567657`; `casos/tramposo/`.<br>
**Revisión futura:** Conservar la historia y distinguir los artefactos del caso de las notas y resultados de su evaluación.

## DEC-010 — Recuperación técnica mediante Git bundles

**Estado:** Vigente<br>
**Responsable / participantes:** Pablo Bellesi, integración/publicación; Franco Forziati, Sofia Mapelli y Melisa Clark, responsables humanos de los trabajos recibidos.<br>
**IA utilizada:** Claude para el caso tramposo; Codex para excelente/flojo, calibración y asistencia de integración.<br>
**Contexto:** Algunas integraciones de IA presentaron restricciones de escritura. El PR #11 documenta específicamente la falta de permiso `contents: write` de Claude web. Los trabajos de los tres responsables se recibieron mediante bundles.<br>
**Decisión:** Importar las ramas y publicar los commits originales, preservando hashes, autoría técnica, committer y relaciones de parentesco, sin amend, rebase ni cherry-pick que los sustituyera. Pablo actuó como integrador/publicador de esos trabajos.<br>
**Motivo:** Recuperar el trabajo sin convertir a quien hace el push en autor de toda la implementación.<br>
**Impacto esperado:** Conservar la división de responsabilidades y una historia verificable; los cambios de revisión posteriores se incorporan como commits nuevos.<br>
**Evidencia / archivos relacionados:** [PR #11](https://github.com/pbellesi/agente-evaluador-ucema/pull/11) / Issue #4: `59fae77`; [PR #15](https://github.com/pbellesi/agente-evaluador-ucema/pull/15) / Issue #3: `ba10117`; [PR #16](https://github.com/pbellesi/agente-evaluador-ucema/pull/16) / Issue #5: `bb5d256` y `5bde10e`. Git identifica a Claude o Codex como autores técnicos de esos commits; las descripciones de Issues/PRs identifican a sus responsables humanos.<br>
**Revisión futura:** Usar el mismo criterio de preservación si vuelve a ser necesaria una recuperación, sin atribuir una causa técnica no comprobada a cada integración.

## DEC-011 — Endurecimiento del contrato del agente tras revisión

**Estado:** Vigente<br>
**Responsable / participantes:** Diego Mendez, responsable humano del agente; Pablo Bellesi, revisión y autorización de las correcciones.<br>
**IA utilizada:** Claude en la versión original; Codex en la revisión, corrección y validación manual posterior.<br>
**Contexto:** La primera versión del PR #14 dejaba ambigüedades en acceso a la rúbrica, inspección, salida JSON y manejo de evidencia insuficiente.<br>
**Decisión:** Separar la rúbrica autoritativa del evaluador y el repositorio objetivo; exigir inventario y contraste de artefactos; fijar el JSON completo también ante problemas de acceso; eliminar la penalización automática inventada de 0%. Mantener el nivel más alto completamente demostrado por la rúbrica.<br>
**Motivo:** Reducir crédito por declaraciones sin evidencia y asegurar una salida contractual consistente.<br>
**Impacto esperado:** Corrector más verificable. La validación inicial registró contradicciones concretas del Tramposo, con las limitaciones que después documentó la calibración.<br>
**Evidencia / archivos relacionados:** [Issue #2](https://github.com/pbellesi/agente-evaluador-ucema/issues/2), [PR #14](https://github.com/pbellesi/agente-evaluador-ucema/pull/14); original `98df88c`, corrección `aed9d9a` y limpieza `9c1be5a`; `agente/system_prompt.md`, `agente/validacion_caso_tramposo.md`.<br>
**Revisión futura:** Cualquier ajuste funcional posterior debe basarse en evidencia nueva y decisión humana; este registro no cambia el contrato.

## DEC-012 — Casos diferenciados sin notas prefijadas

**Estado:** Vigente<br>
**Responsable / participantes:** Sofia Mapelli, responsable humana de excelente/flojo; Pablo Bellesi, coordinación, revisión e integración.<br>
**IA utilizada:** Codex para implementación y asistencia de revisión.<br>
**Contexto:** Los dos casos debían distinguir calidad mediante evidencia observable. La revisión documentada del excelente incorporó la participación real del modelo y conservó la limitación de métricas económicas no expuestas.<br>
**Decisión:** Mantener un excelente fuerte pero no perfecto y un flojo incompleto, realista y evaluable; no construirlos para forzar 100/0 ni cambiar artefactos para alcanzar una nota objetivo.<br>
**Motivo:** Probar la discriminación del corrector con resultados observados y faltantes reconocibles.<br>
**Impacto esperado:** Separación útil para calibración sin ocultar debilidades. El PR #15 conserva 83,75 como validación inicial y 82,5 como auditoría posterior del excelente; registra 28,75 para Flojo. No se reemplaza la historia por un único resultado retrospectivo.<br>
**Evidencia / archivos relacionados:** [Issue #3](https://github.com/pbellesi/agente-evaluador-ucema/issues/3), [PR #15](https://github.com/pbellesi/agente-evaluador-ucema/pull/15), commit preservado `ba10117`; `casos/excelente/DECISIONES.md`, sus corridas y análisis económico; `casos/flojo/`; comparación posterior en `calibracion.md`.<br>
**Revisión futura:** Mantener separados resultados históricos y nuevas evaluaciones; no inferir que la etiqueta del caso garantiza una puntuación.

## DEC-013 — Calibración con desacuerdos y trazabilidad limitada

**Estado:** Vigente<br>
**Responsable / participantes:** Melisa Clark, responsable humana de calibración y QA; Pablo Bellesi, revisión y autorización de la aclaración documental.<br>
**IA utilizada:** Codex para análisis y asistencia documental.<br>
**Contexto:** La calibración registró humano/agente: Excelente 82,5/82,5; Flojo 21,25/28,75; Tramposo 26,25/26,25. La revisión detectó falta de baseline humano independiente previo y outputs brutos completos, inconsistencia humana entre Flojo y Tramposo y variación del agente en Tramposo respecto de 18,75.<br>
**Decisión:** Preservar todos los puntajes y reconocer las limitaciones. El procedimiento relatado fue humano primero y agente después, pero esa secuencia no puede verificarse independientemente en Git. No inventar registros retroactivos ni modificar rúbrica, agente o casos sólo para forzar coincidencia.<br>
**Motivo:** Conservar los desacuerdos reales y el aprendizaje sobre el límite 25%/50% de Sistema.<br>
**Impacto esperado:** Registro honesto de la primera calibración. ±10 es un criterio interno de análisis, no aceptación docente; la diferencia histórica de +7,5 no demuestra una mejora del caso; la causa se presenta como probable. No hubo ajuste funcional ni re-test, y no se documentó una prueba dirigida de prompt injection.<br>
**Evidencia / archivos relacionados:** [Issue #5](https://github.com/pbellesi/agente-evaluador-ucema/issues/5), [PR #16](https://github.com/pbellesi/agente-evaluador-ucema/pull/16); originales `bb5d256` y `5bde10e`, aclaración `6ab8230`; `calibracion.md` y `agente/validacion_caso_tramposo.md`.<br>
**Revisión futura:** El criterio uniforme 25%/50% sigue abierto a decisión humana. Una ronda posterior deberá identificarse como nueva, conservando la evidencia original; no se la da por realizada en este cierre documental.

## DEC-014 — Confirmación de fuentes para el cierre documental

**Estado:** Vigente<br>
**Responsable / participantes:** Pablo Bellesi, coordinación y confirmación del criterio de fuentes para este cierre.<br>
**IA utilizada:** Codex, para contraste y documentación.<br>
**Contexto:** La interpretación inicial del ejemplo de clase atribuyó demasiado peso normativo a la escala de cinco niveles. DEC-008 y la rúbrica V2 registran su corrección; el cierre documental debe conservarla.<br>
**Decisión:** Las consignas oficiales del parcial y del trabajo final mantienen prioridad normativa. Los ejemplos adicionales del docente son referencia pedagógica y no agregan obligaciones. La escala 0/25/50/75/100 continúa como convención del equipo. Las guías PIC-AE no acreditan pruebas realizadas ni requisitos oficiales.<br>
**Motivo:** Evitar que ejemplos, checkmarks históricos o recomendaciones se confundan con evidencia de ejecución o exigencias de la materia.<br>
**Impacto esperado:** Portada y estado final coherentes con las fuentes, sin borrar las decisiones históricas ni presentar una historia perfecta.<br>
**Evidencia / archivos relacionados:** Consignas en `00_fuentes/consigna/`; DEC-006 y DEC-008; `rubrica.md`; commit `7de9dad` del [PR #8](https://github.com/pbellesi/agente-evaluador-ucema/pull/8); [Issue #17](https://github.com/pbellesi/agente-evaluador-ucema/issues/17).<br>
**Revisión futura:** Mantener visible la jerarquía y documentar cualquier nueva aclaración respaldada, sin reinterpretar retroactivamente la historia.

## DEC-015 — Migración del runtime generativo a motor determinístico Zero-API

**Estado:** Vigente<br>
**Responsable / participantes:** Pablo Bellesi, coordinación y arquitectura.<br>
**IA utilizada:** Antigravity (Google DeepMind) durante desarrollo, auditoría y calibración.<br>
**Contexto:**
- La primera interfaz ejecutable utilizaba la API de Gemini para interpretar `rubrica.md` y `agente/system_prompt.md`.
- En corridas consecutivas de test-retest se observó variabilidad del LLM (flojo: 21.25 vs 25.00; tramposo: 22.50 vs 33.75; delta de hasta 11.25 pts).
- Se tomó en cuenta la recomendación docente de evitar depender de APIs generativas por la variabilidad del resultado y para permitir la evaluación masiva de trabajos.
- Se fijó como restricción de arquitectura que la aplicación final debe funcionar sin costo por uso de APIs generativas para el usuario final y sin requerir API keys, sujeto a los límites normales del hosting y GitHub.

**Decisión:**
- Mantener `rubrica.md` como fuente normativa de evaluación.
- Sustituir el scoring generativo en runtime por un motor determinístico en Python basado en Gates de Evidencia Objetiva (matriz 5x5).
- Mantener acceso de red exclusivamente para obtener e inspeccionar repositorios públicos de GitHub.
- Eliminar la dependencia en runtime de APIs generativas (Gemini, OpenAI, Anthropic) y la exigencia de claves de API.
- Resolver y registrar el commit SHA exacto de cada trabajo evaluado.
- Mantener y automatizar las reglas de invalidez por contradicción de evidencia.
- La IA puede utilizarse durante el desarrollo, auditoría y calibración, pero no decide la nota en producción.

**Evidencia / Resultado:**
- Test-retest V2:
  - `excelente`: 82.50 / 82.50
  - `flojo`: 32.50 / 32.50
  - `tramposo`: 32.50 / 32.50
  - Delta = 0.00 en todos los casos.
- El runtime V2 no utiliza modelos generativos; tokens generativos por evaluación = 0.
- Costo generativo por evaluación: USD 0.

**Impacto / Consecuencias:**
- Scoring determinístico: para el mismo commit evaluado y la misma versión del evaluador, el test-retest produjo delta = 0.00 en los benchmarks.
- Eliminación de costos operativos de APIs generativas y dependencias de cuotas o credenciales externas.
- Posibilidad de uso público directo sin ingresar API keys.
- Riesgo restante: los gates determinísticos requieren calibración continua sobre repositorios reales para evitar falsos positivos/negativos.

## DEC-016 — Depuración de falsos positivos de conectores dummy con validación externa

**Estado:** Vigente<br>
**Responsable / participantes:** Pablo Bellesi, coordinación, diagnóstico y validación de integración; revisión humana de la corrección.<br>
**IA utilizada:** Codex, para inspección, implementación acotada de los detectores y ejecución de pruebas bajo instrucciones humanas.<br>
**Contexto:** Durante validaciones sobre repositorios externos se detectaron falsos positivos al clasificar conectores dummy. En PULSO (`0f0092a004169e6b64b0f0701eba3baf904cf7db`), una regla genérica de `placeholder` interpretó un uso legítimo de UI —incluido el identificador `LibraryPlaceholder` en la observación inicial— como simulación; el resultado pasó de 48,75 a 86,25 tras el primer refinamiento. La validación posterior de `Lapeque26/agente-trabajo-final` (`2ec026cae6d4e2b75081db80d21c02f3a40e8118`) obtuvo 82,5 con 22 archivos inventariados, 22 cargados y 0 omitidos. Un segundo caso, `tubidj10/FinalAgentesIA` (`107448a35eee3161665c8e9eb7e4a189470b4e31`), mostró que `placeholder="checkout-api, payments-db, checkout-worker..."` en un atributo de UI era tomado como dummy por cercanía con `api`; el inventario completo (55/55 archivos cargados, 0 omitidos) confirmó que no era un problema de retrieval.<br>
**Decisión:** Refinar exclusivamente la detección de `placeholder`: los atributos, props, variables e identificadores de UI no prueban una integración simulada; sólo se clasifican como dummy las frases que vinculan `placeholder` con conector, API o integración mediante contexto técnico explícito. Se mantuvieron sin cambios scoring, pesos, gates, reglas de invalidez, retrieval, rúbrica y casos.<br>
**Alternativas descartadas:** No aumentar presupuestos de recuperación —el segundo caso tenía cobertura completa—, no eliminar por completo la señal `placeholder` —seguiría ocultando placeholders reales de integración— y no ajustar puntajes ni reglas de invalidez para un repositorio particular.<br>
**Motivo:** Corregir una clasificación generalizable sin sobreajustar el evaluador a un caso ni dar crédito por declaraciones no verificadas.<br>
**Impacto esperado:** Evitar contradicciones e invalidaciones artificiales cuando una interfaz usa placeholders legítimos, conservando la detección de expresiones como `API placeholder pendiente de implementar`, `placeholder connector`, `integración placeholder` y `placeholder de conector`.<br>
**Evidencia / archivos relacionados:** Tests de regresión (20/20 OK) en `tests/test_placeholder_false_positive.py`; `src/evidence_extractor.py`; validaciones externas PULSO, Lapeque26 y tubidj10. No regresión: Excelente 82,5 → 82,5; Flojo 32,5 → 32,5; Tramposo 32,5 → 32,5; PULSO 86,25 → 86,25; Lapeque26 82,5 → 82,5; tubidj10 40,0 → 90,0. La validación final en producción registró PULSO 86,25 y tubidj10 90,0.<br>
**Revisión futura:** Tratar estos resultados como evidencia de comportamiento y no como notas correctas absolutas. Mantener pruebas externas y benchmarks internos al modificar detectores de evidencia; el evaluador no se considera infalible.

## DEC-017 — Contrato sintético de aceptación y congelamiento del motor

**Estado:** Vigente<br>
**Responsable / participantes:** Pablo Bellesi, coordinación y validación de integración; revisión humana de los criterios de aceptación.<br>
**IA utilizada:** Codex para asistencia de diagnóstico, implementación acotada y ejecución de pruebas bajo instrucciones humanas.<br>
**Contexto:** Las reglas de extracción inicialmente dependían en exceso de formatos y palabras clave. Las revisiones de repositorios reales permitieron detectar posibles falsos negativos y falsos positivos, pero no debían convertirse en ajustes dirigidos a subir o conservar la nota de un repositorio particular.<br>
**Decisión:** Congelar primero un contrato de aceptación derivado de la rúbrica. Cada posible bug observado sigue el método: repositorios reales detectan una clase de error → la clase se expresa primero como caso sintético con expectativa fijada → se ajusta el motor sólo contra ese contrato → los repositorios reales se usan después para comprobar generalización y regresión.<br>
**Motivo:** Separar la interpretación de la rúbrica de los puntajes concretos de terceros, preservar el principio EVIDENCIA > DECLARACIÓN y evitar sobreajustar detectores para obtener notas deseadas.<br>
**Resultado:** 31/31 acceptance tests y 69/69 pruebas de la suite completa. Los casos oficiales quedaron coherentes: Excelente 88,75; Flojo 28,75; Tramposo 21,25. La regresión externa final fue estable en PULSO (85,0), SACME (96,25), Lapeque26 (92,5), tubidj10 (85,0), SilA066 (85,0), FSio (92,5) y El-Diegote (92,5).<br>
**Consecuencia:** El motor queda congelado salvo evidencia de un bug objetivo nuevo, que deberá seguir el mismo recorrido sintético antes de modificar implementación, scoring, gates, rúbrica o casos.<br>
**Evidencia / archivos relacionados:** `rubrica.md`; `tests/test_acceptance_matrix.py`; `src/evidence_extractor.py`; `src/deterministic_evaluator.py`; PR #31, merge `8b11d81`.<br>

## DEC-018 — System Prompt operativo sobre herramienta determinística

**Estado:** Vigente<br>
**Responsable / participantes:** Pablo Bellesi, coordinación y validación de integración; Diego Mendez, integración técnica del agente corrector.<br>
**IA utilizada:** Codex, para implementación acotada, documentación y ejecución de pruebas bajo instrucciones humanas.<br>
**Contexto:** La consigna exige un system prompt más las herramientas necesarias. El motor determinístico ya realizaba la corrección funcional, pero `agente/system_prompt.md` no participaba de una vía operativa actual.<br>
**Decisión:** Exponer `evaluator_engine` mediante `agente/evaluate_tool.py` y definir `agente/system_prompt.md` como orquestador de esa herramienta. La herramienta devuelve el `EvaluationResult` del motor sin duplicar scoring; el LLM no recalcula ni modifica puntajes o evidencia.<br>
**Razones:** Alinear literalmente la arquitectura con la consigna, preservar el determinismo, mantener una única fuente autoritativa de puntajes, no duplicar scoring y no introducir costo generativo en Streamlit.<br>
**Alternativas descartadas:** Scorer LLM paralelo; reemplazar el motor por un LLM; insertar un LLM dentro del runtime Streamlit.<br>
**Consecuencias:** El agente es ejecutable sólo en un entorno con workspace y terminal; un chat genérico sin herramientas no puede realizar una evaluación real. Streamlit permanece independiente y el scoring no cambia.<br>
**Evidencia / archivos relacionados:** `agente/evaluate_tool.py`; `agente/system_prompt.md`; `agente/README.md`; commits `9527ede987eccfa9607fad818a8e2ee6b43e14e1` y `93468d713453f6293860005fbab220f840082b76`.<br>


