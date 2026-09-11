import sys
from pathlib import Path

texto = Path(sys.argv[1]).read_text(encoding="utf-8")
if "vencimiento" in texto.lower() or "obligatorio" in texto.lower():
    print("IMPORTANTE: revisar esta novedad")
else:
    print("Sin novedades importantes")
