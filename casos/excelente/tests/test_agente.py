import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from agente import construir_payload, leer_publicaciones


def muestra(url="https://example.test", resumen="Presentar informe obligatorio"):
    return {"titulo": "Norma", "organismo": "CNV", "fecha": "2026-09-01", "url": url, "resumen": resumen}


def test_lee_archivo_real(tmp_path):
    ruta = tmp_path / "entrada.json"
    ruta.write_text(json.dumps([muestra()]), encoding="utf-8")
    assert len(leer_publicaciones(ruta)) == 1


def test_payload_para_modelo():
    payload = construir_payload([muestra()], "2026-09-01")
    assert payload["fecha_relevamiento"] == "2026-09-01"
    assert payload["publicaciones"][0]["organismo"] == "CNV"
