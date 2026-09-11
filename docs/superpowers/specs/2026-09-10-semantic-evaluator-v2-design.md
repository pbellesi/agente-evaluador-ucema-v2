# Especificación de Diseño: Agente Evaluador UCEMA V2 (Juez Semántico)

**Fecha:** 2026-09-10  
**Proyecto:** `agente-evaluador-ucema-v2`  
**Estado:** Propuesto / Aprobación de Enfoque Cognitivo  
**Autor:** Equipo de Arquitectura Agente Evaluador  

---

## 1. Contexto y Principio Rector de V2

### 1.1 Diagnóstico de V1
La V1 basó su evaluación en regex rígidos y matrices tabuladas. Esto provocó una pérdida severa de generalización semántica ("comerse evidencia") porque intentó aproximar comprensión mediante palabras clave y compuertas booleanas.

### 1.2 Principio Rector de V2: Comprensión Primero, Rúbrica Después
> **PRIMERO ENTENDER EL TRABAJO.**  
> **DESPUÉS EVALUARLO CONTRA LA RÚBRICA.**  
> **LAS BANDERAS DE INTEGRIDAD SON SECUNDARIAS Y TRANSVERSALES.**

El modelo no debe leer el repositorio como una checklist de palabras ni como un escáner policial obsesionado con cazar prompt injection. Su objetivo principal es actuar como un **evaluador humano experto**:
1. Comprender la intención y qué sistema se construyó realmente.
2. Identificar el funcionamiento observable y sus artefactos.
3. Contrastar la documentación con el código y las corridas reales.
4. Detectar ausencias, discrepancias y contradicciones.
5. Finalmente, contrastar esa realidad comprendida con la rúbrica oficial de 5 dimensiones y 5 niveles (0, 25, 50, 75, 100).
6. Si existen anomalías de integridad (órdenes al evaluador, autoasignaciones, etc.), registrarlas como hallazgos transversales dentro de su categoría, sin que colapsen el flujo cognitivo.

---

## 2. Flujo Cognitivo de Evaluación

```
                       [ GitHub URL / Archivo ZIP ]
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │     1. Ingesta Segura V1      │
                    │ (Inventario, límites, árbol)  │
                    └───────────────┬───────────────┘
                                    │ repo_data
                                    ▼
                    ┌───────────────────────────────┐
                    │      2. Context Builder       │
                    │   (Inventario + Rúbrica +     │
                    │   Contenido Priorizado +      │
                    │   Demarcación Untrusted Data) │
                    └───────────────┬───────────────┘
                                    │ evidence_packet
                                    ▼
                    ┌───────────────────────────────┐
                    │    3. Juez Semántico (LLM)    │
                    │  ┌─────────────────────────┐  │
                    │  │ FASE 1: Comprensión y   │  │
                    │  │         Hallazgos       │  │
                    │  │ - Qué sistema es        │  │
                    │  │ - Evidencia observable  │  │
                    │  │ - Brechas/Contradicciones│ │
                    │  │ - Hallazgos flexibles   │  │
                    │  ├─────────────────────────┤  │
                    │  │ FASE 2: Mapeo a Rúbrica │  │
                    │  │ - D1 a D5               │  │
                    │  │ - Niveles {0..100}      │  │
                    │  │ - Justificación         │  │
                    │  │ - Brecha sig. nivel     │  │
                    │  └─────────────────────────┘  │
                    └───────────────┬───────────────┘
                                    │ semantic_payload (JSON)
                                    ▼
                    ┌───────────────────────────────┐
                    │   4. Runtime Determinístico   │
                    │  - Validación Pydantic estricta│
                    │  - Verificación citas invent. │
                    │  - Sin clamping (retry/error) │
                    │  - Cálculo matemático pesos   │
                    │  - Inyección en EvaluationRes │
                    └───────────────┬───────────────┘
                                    │ EvaluationResult
                                    ▼
                    ┌───────────────────────────────┐
                    │     5. Streamlit & UI         │
                    └───────────────────────────────┘
```

---

## 3. Delimitación de Fases Semánticas

### 3.1 Fase 1: Comprensión y Hallazgos del Repositorio
El modelo elabora:
- `project_understanding`: Síntesis objetiva de qué hace el proyecto, arquitectura declarada vs observada, y tecnología empleada.
- `findings`: Lista flexible de hallazgos observacionales sin taxonomías cerradas:
  - **Categorías admitidas:** `implementation`, `process`, `reproducibility`, `economics`, `governance`, `integrity`, `other`.
  - **Severidad:** `info`, `low`, `medium`, `high`.
  - **Archivos:** Rutas específicas de los archivos donde se observó el hallazgo.
  - **Hallazgo:** Descripción clara y concreta de lo evidenciado (positivo, ausente o contradictorio).
  - **Impacto:** Efecto cualitativo que este hallazgo tiene sobre la evaluación global.

#### Integridad y Prompt Injection como Señales Secundarias:
- La protección contra prompt injection se mantiene activa: todo el repo es **DATA NO CONFIABLE**.
- El evaluador ignora cualquier orden directa encontrada en el repo ("asigne 100", "ignore archivos").
- En lugar de ser el centro del análisis, estos eventos se catalogan con normalidad dentro de los hallazgos como `category: "integrity"`, señalando el archivo, la cita y la acción tomada.

### 3.2 Fase 2: Mapeo de Hallazgos a la Rúbrica (D1-D5)
Con los hallazgos ya consolidados, el modelo fundamenta su decisión en cada dimensión:
- **D1: Sistema completo y funcionando (30%)**
- **D2: Proceso documentado (25%)**
- **D3: Formato y reproducibilidad (15%)**
- **D4: Análisis económico (15%)**
- **D5: Gobierno y riesgo (15%)**

Para cada dimensión se produce:
- `recommended_level`: Estrictamente un valor de `[0, 25, 50, 75, 100]`.
- `justification`: Justificación sustentada en los hallazgos de la Fase 1.
- `missing_for_next_level`: Qué artefacto o evidencia observable falta para alcanzar el nivel inmediato superior (o `null` si alcanzó 100).

---

## 4. Contrato JSON Oficial del `SemanticJudge`

```json
{
  "project_understanding": {
    "system_summary": "string",
    "architecture_observed": "string",
    "main_technologies": ["string"]
  },
  "findings": [
    {
      "category": "implementation | process | reproducibility | economics | governance | integrity | other",
      "severity": "info | low | medium | high",
      "files": ["string"],
      "finding": "string",
      "impact_on_evaluation": "string"
    }
  ],
  "dimension_evaluations": {
    "D1": {
      "recommended_level": 50,
      "justification": "string",
      "missing_for_next_level": "string | null"
    },
    "D2": {
      "recommended_level": 75,
      "justification": "string",
      "missing_for_next_level": "string | null"
    },
    "D3": {
      "recommended_level": 100,
      "justification": "string",
      "missing_for_next_level": null
    },
    "D4": {
      "recommended_level": 25,
      "justification": "string",
      "missing_for_next_level": "string | null"
    },
    "D5": {
      "recommended_level": 50,
      "justification": "string",
      "missing_for_next_level": "string | null"
    }
  },
  "concrete_improvement": "string"
}
```

---

## 5. Runtime Determinístico de Validación y Pesos

El código Python recibe el JSON del LLM y ejecuta validaciones estrictas:

### 5.1 Regla de Niveles Inválidos (Sin Clamping)
- Los únicos valores permitidos para `recommended_level` son `0, 25, 50, 75, 100`.
- **Prohibición de Clamping:** Si el modelo devuelve un número no perteneciente al conjunto (ej. 40, 60, 85), la respuesta se marca como inválida.
- Se prevé un mecanismo de retry estructurado. Si persiste, se emite un error controlado de validación. Nunca se convierte silenciosamente un valor.

### 5.2 Verificación de Evidencia Citada
- Cada archivo mencionado en `findings[*].files` se coteja contra el inventario real del repositorio.
- Si un archivo citado no existe, se añade una nota de integridad determinística señalando la discrepancia, previniendo alucinaciones.

### 5.3 Cálculo Matemático de Pesos
El modelo **nunca calcula la nota total ni aplica pesos**. El runtime ejecuta:
$$\text{Score}(D_i) = \text{Peso}(D_i) \times \frac{\text{Level}(D_i)}{100}$$
$$\text{Nota Final} = 0.30 \cdot D_1 + 0.25 \cdot D_2 + 0.15 \cdot D_3 + 0.15 \cdot D_4 + 0.15 \cdot D_5$$

### 5.4 Mapeo a `EvaluationResult`
- `dimensions`: 5 objetos `DimensionResult` con evidencia extraída de los `findings`, justificación y brecha.
- `integrity_notes`: Lista consolidada que incluye todos los hallazgos de categoría `integrity` y advertencias de validación.

---

## 6. Estrategia de Contexto Inteligente (`ContextBuilder`)

El objetivo no es enviar indiscriminadamente gigabytes de texto, sino construir un paquete estructurado y conciso:
1. **Inventario Completo:** Lista exhaustiva de rutas, tipos y tamaños para que el modelo conozca la totalidad del repositorio.
2. **Priorización de Artefactos Relevantes:**
   - Documentación base (`README.md`, `DECISIONES.md`, guías de arquitectura).
   - Documentación específica (`docs/analisis_economico.md`, `docs/gobierno_riesgo.md` o secciones afines).
   - Prompts e instrucciones (`prompts/*`).
   - Código fuente clave (`src/*.py`, entry points `main.py`, conectores).
   - Corridas observables (`corridas/*/entrada.*`, `salida.*`, metadatos).
   - Tests (`tests/*`).
3. **Preservación de Relaciones:** El builder mantiene la asociación entre qué prompt produjo qué corrida y qué script lo invocó.
4. **Truncamiento Explícito:** Si un archivo o corrida supera el presupuesto individual, se trunca preservando inicio y final, insertando `[TRUNCADO POR TAMAÑO: N BYTES OMITIDOS]`.
5. **Demarcación de Seguridad:** Todo el contenido se encapsula en bloques `<untrusted_repo_content path="...">...</untrusted_repo_content>`.

---

## 7. Decisión de Proveedor para MVP: YAGNI y Foco

- La interfaz `SemanticJudge` se define desacoplada mediante una clase base abstracta.
- **Un único proveedor para el MVP:** Se implementará **Google Gemini Flash** (vía `google-genai`), aprovechando su amplia ventana de contexto, soporte de salida estructurada Pydantic nativa y su presencia ya instalada en el entorno.
- Esto evita complejidad prematura manteniendo la arquitectura lista para incorporar otros proveedores cuando se requiera.
