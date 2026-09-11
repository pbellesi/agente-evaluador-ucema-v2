# Agente Evaluador UCEMA — V2 Semántica

Sistema para la evaluación académica e interpretativa de repositorios de software y sistemas agénticos, desarrollado para la cátedra **Programación de y con Agentes de IA — MBA UCEMA**.

El evaluador analiza proyectos a partir de su código fuente, documentación y registros de ejecución, aplicando la rúbrica oficial y produciendo dictámenes estructurados, justificados y reproducibles.

---

## 1. Evolución del Proyecto

El sistema atravesó un proceso iterativo de aprendizaje empírico y diseño fundamentado:

1. **V1 — Juez semántico directo:**
   En las primeras etapas se utilizó un evaluador basado enteramente en prompts libres a un modelo de lenguaje. Aunque ofrecía flexibilidad interpretativa, presentaba variabilidad en los puntajes finales y falta de garantías de reproducibilidad formal.

2. **V2 — Enfoque determinístico estricto:**
   Buscando reproducibilidad absoluta ($0.0$ de dispersión), se construyó un motor determinístico basado en reglas de inspección sintáctica, inventario y expresiones regulares.
   - **Hallazgo crítico:** La solución determinística era 100% reproducible ante el mismo repositorio, pero sobreajustaba fuertemente a estructuras rígidas de archivos. Resultaba frágil ante proyectos con nombres de archivos alternativos, arquitecturas modularizadas válidas o frases no anticipadas por las expresiones regulares.

3. **Experimento intermedio — Arquitectura híbrida semántica/determinística:**
   Se exploró una división en 21 unidades de evidencia donde un extractor recopilaba hechos y un juez semántico adjudicaba estados. Sin embargo, introducía una complejidad innecesaria de mapeos intermedios y riesgo de desacople con las tablas de la rúbrica oficial.

4. **Decisión final — Simplificación a LLM-as-a-Judge con Validación Formal:**
   Se adoptó una arquitectura limpia, robusta y congelada:
   - **Repositorio (GitHub o ZIP)** $\to$ Paquete de evidencia delimitado $\to$ **Google Gemini (`gemini-3.6-flash`, $T=0.0$)** $\to$ Salida estructurada tipada $\to$ **Validación determinística en Python** $\to$ `EvaluationResult`.

> ### Principios Rectores de la Arquitectura Final:
> 1. **EVIDENCIA > DECLARACIÓN:** Las afirmaciones en el `README.md` o documentación no otorgan puntaje si no están respaldadas por código, configuraciones o artefactos reales observables.
> 2. **El contenido del repo es DATO, nunca instrucción:** Todo el contenido del repositorio analizado se delimita bajo etiquetas `<untrusted_repo_content>`. Cualquier orden al evaluador o intento de prompt injection se registra en `integrity_notes`, se ignora para la calificación y se evalúa el mérito técnico real.
> 3. **Gemini interpreta la evidencia:** El modelo evalúa semánticamente el proyecto contrastándolo directamente con `rubrica.md` y asigna a cada dimensión D1 a D5 **estrictamente uno de los 5 niveles oficiales:** `0`, `25`, `50`, `75` o `100`.
> 4. **Python valida el contrato y calcula el total:** El runtime exige las 5 dimensiones, valida que los niveles pertenezcan a $\{0, 25, 50, 75, 100\}$ (sin redondeos ni clamping silencioso) y calcula el puntaje total aplicando la fórmula matemática de los pesos oficiales ($30\%, 25\%, 15\%, 15\%, 15\%$). Si el LLM emite una suma errónea, Python la recalcula preservando los niveles elegidos por el modelo.
> 5. **Robustez ante fallas de API:** Los errores de conectividad o cuota de la API nunca se transforman silenciosamente en nota 0; se manejan con reintentos estructurados y elevan excepciones explícitas.

---

## 2. Dimensiones de Evaluación (Rúbrica Oficial)

El evaluador pondera los proyectos sobre las cinco dimensiones oficiales de la cátedra:

| Dimensión | Nombre Oficial | Peso | Descripción Operativa |
| :---: | :--- | :---: | :--- |
| **D1** | **Sistema completo y funcionando** | **30%** | Existencia observable de contrato de prompts, invocación de herramientas/conectores reales, salidas estructuradas y delimitación de supervisión humana (L0-L4). |
| **D2** | **Proceso documentado** | **25%** | Trazabilidad del desarrollo en `DECISIONES.md`, registro transparente de fallas observadas, ajustes de prompts y evolución basada en evidencia. |
| **D3** | **Formato y reproducibilidad** | **15%** | Cumplimiento de la estructura obligatoria de carpetas, y presencia de tres corridas reales completas con entradas, salidas, marcas de tiempo y auditoría humana. |
| **D4** | **Análisis económico** | **15%** | Cuantificación empírica de tokens (entrada/salida), costo monetario por corrida, proyecciones de volumen y justificación de selección de modelo eficiente. |
| **D5** | **Gobierno y riesgo** | **15%** | Matriz de permisos por sistema, evaluación de privacidad de datos sensibles, modos de falla con mitigaciones y asignación operativa de firma humana responsable. |

---

## 3. Arquitectura del Pipeline Final

El flujo de evaluación sigue una secuencia lineal, transparente y desacoplada:

```
[ Archivo ZIP o URL GitHub ]
              │
              ▼
    1. Ingesta Segura (en memoria o fetcher, inventario y hashes)
              │
              ▼
    2. ContextBuilder (delimitación <untrusted_repo_content> + rubrica.md)
              │
              ▼
    3. Gemini LLM Judge (gemini-3.6-flash, temperature=0.0, salida estructurada)
              │
              ▼
    4. EvaluationValidator (verificación estricta D1-D5 en {0,25,50,75,100} y cálculo de score)
              │
              ▼
    5. EvaluationResult (JSON estructurado / UI Streamlit app_v2.py)
```

### Componentes Clave:
- **`src/simple_evaluator.py`:** Orquestador principal del evaluador simple con Gemini.
- **`src/context_builder.py`:** Construye el paquete de contexto neutral delimitando todo el contenido del repositorio bajo etiquetas XML de datos no confiables y anexando la rúbrica oficial.
- **`src/semantic_schema.py`:** Define los esquemas Pydantic `DimensionEvaluationItem` y `SimpleEvaluationPayload` con validación estricta de niveles $\{0, 25, 50, 75, 100\}$.
- **`src/evaluation_validator.py`:** Audita la existencia de las 5 dimensiones, verifica citas contra el inventario y calcula aritméticamente el score final.
- **`app_v2.py`:** Interfaz web local en Streamlit con visualización de métricas, justificaciones, citas y descarga de resultados JSON.

---

## 4. Instalación y Requisitos

### Requisitos Previos:
- Python 3.10 o superior.
- Clave de API de Google Gemini ([Google AI Studio](https://aistudio.google.com/)).

### Instalación:
```bash
# Clonar el repositorio
git clone <URL_DEL_REPOSITORIO>
cd agente-evaluador-ucema-v2

# Crear entorno virtual (opcional pero recomendado)
python -m venv .venv
source .venv/bin/activate  # En Linux/macOS
# .venv\Scripts\Activate.ps1  # En Windows PowerShell

# Instalar dependencias
pip install -r requirements.txt
```

---

## 5. Configuración de Credenciales y Modelo

El evaluador soporta configuración mediante variables de entorno, archivo `.env` o **Streamlit Secrets** (para despliegue en la nube):

### Archivo `.env` (crear en la raíz a partir de `.env.example`):
```env
# Clave de API de Google Gemini (obligatoria)
GEMINI_API_KEY=tu_api_key_aqui

# Modelo Gemini a utilizar (opcional, default: gemini-3.8-flash)
GEMINI_MODEL=gemini-3.6-flash
```

### Precedencia de Configuración:
1. Parámetro explícito de llamada (si se especifica en CLI o código).
2. Variable de entorno del sistema (`GEMINI_API_KEY` / `GEMINI_MODEL`).
3. Archivo `.env` local.
4. `st.secrets` (si la aplicación se ejecuta en Streamlit Community Cloud).
5. Fallback por defecto (`gemini-3.8-flash`).

---

## 6. Ejecución de la Aplicación

### A. Interfaz Gráfica Local (Streamlit)
```bash
python -m streamlit run app_v2.py
```
- Permite cargar uno o múltiples archivos `.zip` simultáneamente (`accept_multiple_files=True`).
- Ejecuta las evaluaciones de forma secuencial, independiente y protegida (si un ZIP falla o está corrupto, informa el error y continúa con los demás).
- Visualiza la tabla resumen con las 5 dimensiones y la nota final.
- Incluye expanders interactivos por proyecto con:
  - **A. Comprensión del proyecto:** Resumen del sistema, arquitectura y stack tecnológico.
  - **B. Hallazgos observacionales:** Listado clasificado con severidad (Alta, Media, Baja, Info), archivos citados e impacto.
  - **C. Dimensiones D1 a D5:** Nivel porcentual asignado, puntaje ponderado, justificación completa, evidencia y faltante para el siguiente nivel.
  - **D. Integridad y seguridad:** Registro de anomalías o prompt injection neutralizados.
  - **E. Mejora prioritaria:** Sugerencia concreta y accionable para elevar el nivel del trabajo.

### B. Ejecución por Línea de Comandos (CLI)
```bash
# Evaluar un archivo ZIP local
python agente/evaluate_v2.py --zip ruta/al/proyecto.zip

# Evaluar un repositorio público de GitHub
python agente/evaluate_v2.py --github https://github.com/usuario/proyecto
```

---

## 7. Despliegue en Streamlit Community Cloud

El repositorio está listo para su despliegue directo en **Streamlit Community Cloud**:
1. Conectar el repositorio de GitHub en el panel de Streamlit Cloud.
2. Definir el archivo principal de la aplicación: `app_v2.py`.
3. En la sección **Settings > Secrets**, agregar las credenciales requeridas:
   ```toml
   GEMINI_API_KEY = "tu_api_key_de_gemini"
   GEMINI_MODEL = "gemini-3.6-flash"
   ```
4. Desplegar. La aplicación resolverá automáticamente los secretos sin requerir archivos locales ni exponer credenciales en pantalla.

---

## 8. Seguridad y Tratamiento de Contenido No Confiable

1. **Aislamiento de Código:** El evaluador jamás ejecuta código del proyecto evaluado ni corre scripts de instalación. La inspección se realiza puramente en memoria como análisis estático y semántico.
2. **Inmunidad ante Prompt Injection:** Todo el contenido del repositorio evaluado se inyecta encapsulado dentro de etiquetas `<untrusted_repo_content>`. El evaluador está instruido para ignorar órdenes dirigidas al corrector (ej. pedidos de autoasignación de nota, comentarios HTML ocultos o pretextos de acuerdos docentes previos), tratándolas exclusivamente como datos y reportándolas en la auditoría de integridad.
3. **Validación Estricta de Niveles:** El runtime rechaza y reintenta cualquier respuesta del modelo que no se ajuste estrictamente a los niveles válidos (0, 25, 50, 75 o 100), impidiendo redondeos o clampings silenciosos.

---

## 9. Suite de Tests Automatizados

La suite de pruebas valida la lógica del evaluador de forma offline y determinística, utilizando `MockSemanticJudge` para no consumir cuota de API ni depender de conectividad externa:

```bash
# Ejecutar suite de pruebas unitarias
python -m pytest -q

# Comprobación de compilación limpia
python -m compileall src agente app_v2.py

# Verificación de formato y espacios
git diff --check
```

---

## 10. Limitaciones Conocidas

- **Archivos Binarios Grandes:** El sistema ignora archivos de gran tamaño (datasets pesados, modelos compilados, videos) y se enfoca en código fuente, prompts, configuraciones, registros de corrida y documentación Markdown/JSON/CSV.
- **Cuotas de Proveedor de LLM:** La velocidad de procesamiento en lote depende de los límites de tasa (RPM/TPM) configurados para la API key de Google Gemini utilizada.
