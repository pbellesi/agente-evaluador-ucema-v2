# Reconstrucción de las corridas

Cada carpeta conserva de forma inequívoca:

1. `entrada.json`: archivo leído por la herramienta.
2. `resultado_herramienta.json`: payload producido por `src/main.py`.
3. `fecha.txt`: momento de ejecución.
4. `metadata.json`: proveedor, hashes de prompts y limitaciones de métricas.
5. `salida.json`: respuesta estructurada del modelo preservada tal como se obtuvo.

Procedimiento aplicado en las tres corridas:

- Se cargó `prompts/system_prompt.md` como contrato del modelo.
- Se completó `prompts/user_prompt.md` con la ruta y la fecha.
- Se ejecutó la herramienta local y se entregó su JSON al modelo como contenido de la publicación.
- Codex en ChatGPT Work devolvió únicamente el objeto JSON guardado como `salida.json`.
- Se comprobó que título, organismo, fecha y URL coincidieran con la entrada; esa comprobación no reescribió la salida.

Los hashes de los prompts permiten verificar qué versiones participaron. La interfaz usada no expuso ID exacto de modelo, tokens ni tarifa; esos valores permanecen `null`.
