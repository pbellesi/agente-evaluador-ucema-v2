# Decisiones — TicketIA

## Decisión 1: Integración con Zendesk vía API v2

**Contexto**: necesitábamos que la clasificación de urgencia se reflejara
directamente en la herramienta que ya usa el equipo de soporte, sin pasos manuales.

**Decisión**: integrar TicketIA con la API v2 de Zendesk para leer tickets
entrantes y actualizar su campo de prioridad automáticamente.

**Impacto**: el equipo de soporte ve la priorización ya aplicada apenas entra
al ticket, sin tener que ejecutar nada manualmente.

## Decisión 2: De reglas simples a clasificador con precisión validada

**Contexto**: la primera versión de TicketIA usaba reglas simples de palabras
clave, que daban resultados poco confiables en tickets ambiguos.

**Decisión**: migramos a un enfoque que combina reglas con un modelo de
lenguaje para estimar sentimiento y confianza en cada clasificación,
mejorando la precisión general del sistema.

**Impacto**: pasamos de una precisión estimada del 70% (reglas simples) al
95% validado contra 200 tickets reales del historial de soporte de PuntoHogar.

## Decisión 3: Validación con 200 tickets históricos

**Contexto**: antes de desplegar en producción necesitábamos confianza en que
la clasificación automática no iba a generar errores costosos (por ejemplo,
marcar como "baja" un reclamo realmente urgente).

**Decisión**: se tomó una muestra de 200 tickets ya resueltos por el equipo
humano y se comparó la clasificación de TicketIA contra la clasificación
original que había asignado el equipo.

**Impacto**: se alcanzó un 95% de coincidencia entre la clasificación del
agente y la del equipo humano, lo que dio luz verde para el despliegue en
producción.

## Decisión 4: Despliegue en producción para PuntoHogar

**Contexto**: con la validación completa, el siguiente paso natural era
llevar el sistema al flujo real de trabajo.

**Decisión**: se desplegó TicketIA en producción en julio de 2026, procesando
en tiempo real los tickets entrantes de PuntoHogar.

**Impacto**: reducción del 40% en el tiempo que el equipo de soporte dedica a
tareas de triage manual, según estimación del equipo de PuntoHogar.

## Decisión 5: Alcance de los tests automatizados

**Contexto**: con el sistema en producción, priorizamos cubrir con tests los
puntos más críticos del flujo antes de seguir iterando sobre nuevas funciones.

**Decisión**: se armó una suite de tests (`tests/test_agente.py`) que cubre
el comportamiento esperado del clasificador y su nivel de precisión.

**Impacto**: cualquier cambio futuro en el código del agente puede validarse
rápidamente contra la suite existente.
