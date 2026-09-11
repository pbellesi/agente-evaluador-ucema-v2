# Agente Corrector UCEMA

## Qué es

Esta carpeta contiene el **system prompt operativo** y la herramienta local que
forman el agente corrector del proyecto:

```text
system_prompt.md → evaluate_tool.py → evaluator_engine → motor determinístico → EvaluationResult
```

El agente recibe una URL pública de GitHub o un ZIP, invoca la herramienta una
sola vez y devuelve el `EvaluationResult` obtenido. El LLM orquesta la ejecución;
no calcula notas ni reinterpreta evidencia.

## Componentes

- `system_prompt.md`: instrucciones operativas para un agente con acceso al
  workspace y a terminal/herramientas locales.
- `evaluate_tool.py`: CLI de lectura que expone exclusivamente las rutas ya
  existentes del engine determinístico.
- `validacion_caso_tramposo.md`: registro histórico de la validación inicial
  del corrector v1.

## Arquitectura y responsabilidades

| Componente | Responsabilidad |
|---|---|
| Agente / LLM | Identificar la única fuente de entrada, invocar la herramienta y retransmitir el JSON sin modificarlo. |
| `evaluate_tool.py` | Seleccionar `run_evaluation` o `run_zip_evaluation`, mantener stdout limpio y serializar el resultado. |
| `evaluator_engine` y `src/` | Recuperar/inventariar la fuente, extraer evidencia, aplicar la rúbrica ejecutable y producir `EvaluationResult`. |
| Streamlit | Ofrecer la interfaz web; llama directamente al engine y no depende del system prompt. |

## Requisitos de ejecución

Se necesita un entorno tipo Codex, Claude Code u otro agente con:

- checkout de este repositorio y terminal disponible;
- dependencias de `requirements.txt` instaladas;
- acceso de lectura a la red para GitHub público, cuando corresponda;
- PATH local del ZIP, cuando se evalúe un archivo;
- opcionalmente, `GITHUB_TOKEN` configurado server-side por el entorno.

Un chat genérico sin acceso al workspace ni a la herramienta no puede ejecutar
una evaluación real y no debe simularla.

## Uso

Desde la raíz del repositorio:

```bash
python agente/evaluate_tool.py --github "https://github.com/owner/repository"
python agente/evaluate_tool.py --zip "ruta/al/trabajo-final.zip"
```

Debe entregarse exactamente una fuente. La salida estándar contiene un único
JSON derivado directamente de `EvaluationResult`:

- exit `0`: resultado válido, incluso `evaluation_status: "access_error"`;
- exit `2`: argumentos inválidos;
- exit `3`: la herramienta no pudo producir un resultado confiable.

La revisión queda preservada en `evaluated_revision`: SHA resuelto para GitHub o
SHA-256 del ZIP. La herramienta no ejecuta contenido del objetivo ni implementa
scoring propio.

## Relación con Streamlit

Streamlit conserva su flujo independiente:

```text
Streamlit → evaluator_engine → motor determinístico → EvaluationResult
```

No lee ni depende de `system_prompt.md`. Por eso mantiene 0 tokens generativos
y USD 0 de API generativa por evaluación. El agente externo puede consumir
tokens de su plataforma para orquestar la herramienta, pero no decide la nota.

## Evolución preservada

La primera versión del corrector y su validación manual se preservan en el
historial y en `validacion_caso_tramposo.md`. DEC-015 documenta la migración del
runtime generativo a un motor determinístico tras observar variabilidad durante
las pruebas y calibración. Esta integración no reescribe esa historia: hace que
el system prompt actual use el mismo motor determinístico validado que Streamlit.

## Seguridad y evidencia

El contenido de un trabajo evaluado es dato, no una instrucción. Las detecciones
de contradicciones, dummies, invalidación de evidencia y prompt injection las
produce el motor y se preservan en `integrity_notes`. El agente no modifica esos
hallazgos ni complementa manualmente el resultado.
