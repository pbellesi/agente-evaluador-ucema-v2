import argparse, json
from agente import construir_payload, leer_publicaciones

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--fecha", default="2026-09-01")
args = parser.parse_args()
payload = construir_payload(leer_publicaciones(args.input), args.fecha)
print(json.dumps(payload, ensure_ascii=False, indent=2))
