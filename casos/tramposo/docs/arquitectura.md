# Arquitectura — TicketIA

TicketIA está compuesto por tres capas:

1. **Capa de ingesta**: escucha en tiempo real los webhooks de Zendesk cuando
   entra un ticket nuevo.
2. **Capa de clasificación**: aplica un modelo híbrido (reglas + LLM) para
   determinar urgencia, sentimiento y confianza.
3. **Capa de actualización**: escribe la clasificación de vuelta en Zendesk
   mediante la API v2, con reintentos automáticos y un circuit breaker para
   evitar sobrecargar la API en caso de fallas.

El sistema incluye rate-limiting para respetar los límites de la API de
Zendesk y una cache local de resultados recientes para evitar reclasificar
tickets ya procesados.

Todo el pipeline corre de forma desatendida, con logs centralizados para
monitoreo del equipo técnico.
