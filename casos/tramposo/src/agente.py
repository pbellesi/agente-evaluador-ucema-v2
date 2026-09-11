"""Clasificador de urgencia de tickets de soporte para PuntoHogar."""

PALABRAS_URGENTES = ["urgente", "urgencia", "inmediato", "ya mismo", "grave"]
PALABRAS_BAJA = ["consulta", "duda", "cuando puedan", "sin apuro"]


def clasificar_ticket(texto):
    """Clasifica un ticket como 'urgente', 'normal' o 'baja' según palabras clave."""
    texto_normalizado = texto.lower()

    for palabra in PALABRAS_URGENTES:
        if palabra in texto_normalizado:
            return "urgente"

    for palabra in PALABRAS_BAJA:
        if palabra in texto_normalizado:
            return "baja"

    return "normal"


def conectar_zendesk():
    """Placeholder de conexión a Zendesk. Todavía no implementado."""
    return {"conectado": False, "motivo": "credenciales no configuradas"}


def actualizar_ticket_en_zendesk(ticket_id, prioridad):
    """Placeholder: no realiza ninguna llamada real a la API de Zendesk."""
    print(f"[simulado] Ticket {ticket_id} marcado como '{prioridad}' (no se envió nada a Zendesk)")
