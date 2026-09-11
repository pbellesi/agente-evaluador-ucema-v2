# Validación end-to-end del System Prompt operativo

## Objetivo

Demostrar la ruta operativa completa:

`system_prompt.md` → agente con workspace y terminal → `evaluate_tool` →
`evaluator_engine` → motor determinístico → `EvaluationResult`.

La validación comprueba además que el LLM no interviene en scoring: sólo
orquesta la herramienta y retransmite su resultado estructurado.

## Intento inicial bloqueado por entorno

El primer intento end-to-end no pudo ejecutar el engine porque el runtime
Codex disponible (Python 3.12.14) falló al importar `requests` con
`ModuleNotFoundError`. No había `python` ni `py` en PATH ni un entorno virtual
local. `requirements.txt` sí declaraba `requests`, `pydantic` y `streamlit`.

Esto se clasificó como bloqueo de entorno, no como fallo funcional del agente:
no se modificó código para resolverlo. Las pruebas posteriores usaron un venv
temporal fuera del repositorio con esas dependencias instaladas.

## Validación ZIP

Fuente: `casos/excelente`, empaquetado temporalmente.

- SHA-256 del ZIP: `a3a3815d33e383985297808da69879604f8c6428ec0283634ab1bb5809fcaeac`.
- Ejecución directa: `evaluation_status: completed`; total `88.75`; D1–D5
  `100 / 100 / 100 / 25 / 100`.
- Ejecución mediante el agente: una invocación de `evaluate_tool`, exit code
  `0` y stdout con un único JSON válido.
- El `EvaluationResult` fue semánticamente idéntico al baseline directo. No
  hubo scoring de LLM, evidencia agregada ni modificación de improvements o
  `integrity_notes`.

## Validación GitHub real

URL exacta: [PULSO en SHA fijo](https://github.com/pbellesi/pulso-agente-planificador-ucema/tree/0f0092a004169e6b64b0f0701eba3baf904cf7db).

- SHA evaluado: `0f0092a004169e6b64b0f0701eba3baf904cf7db`.
- Ejecución directa: `evaluation_status: completed`; total `85.0`; D1–D5
  `100 / 100 / 75 / 75 / 50`.
- Ejecución mediante el agente: una invocación de `evaluate_tool`, exit code
  `0` y stdout con un único JSON válido.
- El `EvaluationResult` fue semánticamente idéntico al baseline directo. No
  hubo scoring de LLM, evidencia agregada ni modificación de improvements o
  `integrity_notes`.

## Conclusión

- System Prompt operativo: **VALIDADO**.
- Ruta ZIP: **VALIDADA**.
- Ruta GitHub: **VALIDADA**.
- `evaluator_engine` permanece como fuente autoritativa; el LLM sólo
  orquesta.
- Streamlit no depende del System Prompt.
- Estas pruebas no modificaron scoring ni motor.

La ejecución requiere un agente con workspace, terminal y la herramienta local
disponible; no se afirma funcionamiento en un chat web genérico sin ellas.
