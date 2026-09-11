"""Herramienta de lectura y preparación de contexto para RadarNorma."""
import json
from pathlib import Path


def leer_publicaciones(ruta):
    data = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("La entrada debe ser una lista JSON")
    requeridos = {"titulo", "organismo", "fecha", "url", "resumen"}
    for indice, item in enumerate(data):
        faltantes = requeridos - set(item)
        if faltantes:
            raise ValueError(f"Publicación {indice}: faltan {sorted(faltantes)}")
    return data


def construir_payload(publicaciones, fecha):
    """Construye el contexto estructurado que recibe el modelo de IA."""
    return {"fecha_relevamiento": fecha, "publicaciones": publicaciones}
