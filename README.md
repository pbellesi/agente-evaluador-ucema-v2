# Agente Evaluador UCEMA — V2 Semántica

Sistema para la evaluación académica e interpretativa de repositorios de software y sistemas agénticos, desarrollado para la cátedra **Programación de y con Agentes de IA — MBA UCEMA**.

El evaluador analiza proyectos de alumnos a partir de su código fuente, documentación y registros de ejecución, aplicando la rúbrica oficial y produciendo dictámenes estructurados, justificados y reproducibles.

---

## 1. Evolución Conceptual: De V1 a V2

El sistema V2 surge como una evolución iterativa y madura a partir de la primera versión desarrollada:

- **V1 (Enfoque Determinístico):**
  Priorizaba la máxima reproducibilidad y la consistencia matemática mediante reglas fijas, extracción de palabras clave y métricas tabuladas. Aunque ofrecía costo nulo de inferencia y total determinismo, presentaba limitaciones para interpretar contradicciones semánticas complejas (por ejemplo, código hardcodeado que simula conectores reales o discrepancias entre lo declarado en el README y la evidencia física de las corridas).

- **V2 (Enfoque Híbrido Semántico-Determinístico):**
  Adopta el paradigma de razonamiento semántico manteniendo controles determinísticos estrictos.

> ### Principio Rector de V2:
> **"El modelo interpreta. El runtime controla."**

1. **El modelo interpreta:** Un modelo de razonamiento multimodal/lenguaje comprende holísticamente el propósito del sistema, audita la coherencia entre documentación y código, detecta contradicciones o código simulado y genera hallazgos observacionales fundados.
2. **El runtime controla:** El código del evaluador gestiona la ingesta segura en memoria, delimita el contexto, exige niveles discretos no negociables (0%, 25%, 50%, 75%, 100%), audita que las citas de archivos existan en el repositorio real y calcula la calificación final aplicando matemáticamente los pesos oficiales.

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

## 3. Arquitectura del Pipeline V2

El flujo de evaluación sigue una secuencia lineal y desacoplada:

```
[ Archivo ZIP del Proyecto ]
              │
              ▼
    1. Ingesta Segura (en memoria, sin extracción al disco)
              │
              ▼
    2. ContextBuilder (inventario, priorización y marcado XML)
              │
              ▼
    3. GeminiSemanticJudge (análisis interpretativo estructurado)
              │
              ▼
    4. EvaluationValidator (auditoría de citas, niveles y scoring)
              │
              ▼
    5. EvaluationResult (JSON / Vista interactiva Streamlit)
```

### Componentes Clave:
- **`src/zip_repository.py`:** Inspecciona el archivo ZIP en memoria, validando rutas (bloqueo de traversal attacks, links absolutos) e indexando el inventario completo sin escribir en disco.
- **`src/context_builder.py`:** Construye un paquete de evidencia priorizando archivos críticos (`README.md`, `prompts/`, `corridas/`, `DECISIONES.md`, etc.), marcando truncamientos si se supera el presupuesto y delimitando todo el contenido del repositorio bajo etiquetas `<untrusted_repo_content>`.
- **`src/semantic_judge.py`:** Invoca a Google Gemini forzando salida estructurada (`SemanticJudgePayload`). Aplica un protocolo de razonamiento en 5 etapas:
  1. Comprender el sistema real construido.
  2. Auditar la evidencia observable diferenciándola de meras declaraciones.
  3. Emitir hallazgos clasificados por categoría y severidad.
  4. Mapear hallazgos a los niveles de la rúbrica (0, 25, 50, 75 o 100).
  5. Aislar intentos de manipulación o prompt injection tratándolos como datos no confiables.
- **`src/evaluation_validator.py`:** Valida que no haya clamping silencioso de notas, verifica que los archivos citados existan en el inventario físico y calcula el puntaje final ponderado de forma matemática.
- **`src/batch_evaluator.py`:** Módulo desacoplado de la interfaz que permite orquestar la evaluación secuencial de múltiples archivos ZIP manteniendo el aislamiento de contexto.

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
