# RESUMEN EJECUTIVO Y PLAN DE EJECUCIÓN
## Agente Evaluador - Parcial Grupal · MBA UCEMA · 2026 2T

**Equipo**: Diego Méndez, Pablo Bellesi, Franco Forziati, Franco Gambini, Sofía Mapelli, Melisa Clark

**Fecha de Elaboración**: [HOY]

**Entrega Final**: Jueves 10/9/2026, 18:59

**Prueba de Fuego**: Jueves 10/9/2026, 22:00 (en vivo, con casos desconocidos)

---

## PARTE A: QUÉ HEMOS CREADO

Se han creado **3 documentos maestros** (prompts especializados) que guiarán la construcción del agente evaluador:

### **Documento 1: PIC-AE (Prompt de Evaluador Completo)**
**Archivo**: `1_PIC-AE_PROMPT_EVALUADOR_COMPLETO.md`

**Qué es**: El rigor absoluto. Las 5 dimensiones de evaluación con todos sus criterios, pesos (25-25-20-15-15), y cómo verificar cada uno.

**Quién lo usa**: 
- **Primariamente**: El agente evaluador (será entrenado con este prompt).
- **Secundariamente**: El grupo, para validar que su trabajo cumple con lo esperado.
- **Terciariamente**: El profesor, para calificar el trabajo del grupo.

**Características clave**:
- 5 dimensiones ponderadas según lo oficial.
- Criterios de discriminación REFORZADOS (nuevo vs. versión anterior).
- Tolerancia cero a ambigüedades.
- Salida obligatoria estructurada (6 secciones).
- Verificación total y exhaustiva.

**¿Cuándo usarlo?**: AHORA, para entrenar al agente. Después, como checklist de validación.

---

### **Documento 2: Guía para Desarrollar Casos de Prueba**
**Archivo**: `2_PIC-AE_DESARROLLO_CASOS_PRUEBA.md`

**Qué es**: Un prompt con interrogantes y pasos prácticos para construir tres repositorios reales (excelente, flojo, tramposo).

**Quién lo usa**: 
- **Responsables designados**: Sofía Mapelli (Rol D), casos excelente y flojo; Franco Forziati (Rol E), caso adversarial / tramposo.
- **Entrada**: Los otros prompts, la rúbrica oficial de trabajos finales, ejemplos de trabajos previos.
- **Salida**: Tres carpetas `casos/excelente/`, `casos/flojo/`, `casos/tramposo/` con contenido real.

**Estructura del documento**:
- Parte 0: Contexto (por qué importa)
- Parte 1: Análisis previo (preguntas que responder antes de empezar)
- Partes 2-4: Construcción de cada caso (paso a paso, muy detallado)
- Parte 5: Documentación de cada caso (README explicativo)
- Parte 6: Validación cruzada con el grupo
- Parte 7: Checklist de entrega

**¿Cuándo usarlo?**: INMEDIATAMENTE. Este es el primer hito real. Sin casos, no hay nada que evaluar.

**Tiempo estimado**: 3-4 días de trabajo (puede ser paralelo a otras tareas).

---

### **Documento 3: Guía para Desarrollar Calibración**
**Archivo**: `3_PIC-AE_DESARROLLO_CALIBRACION.md`

**Qué es**: Un prompt paso a paso para comparar puntuaciones del agente vs. criterio humano, identificar desacuerdos, ajustar rúbrica/agente, y documentar TODO el proceso.

**Quién lo usa**: 
- **Responsable designada**: Melisa Clark (Rol F - Calibración y QA).
- **Entrada**: Casos de prueba (terminados), rúbrica ejecutable, agente funcional.
- **Salida**: Archivo `calibracion.md` que documenta iteración completa.

**Estructura del documento**:
- Parte 0: Contexto
- Parte 1: Preparación (confirmar ingredientes, entender rúbrica)
- Parte 2: Corrida 1 del agente (pre-calibración)
- Parte 3: Comparación inicial (humano vs. agente V1)
- Parte 4: Identificación de desacuerdos y decisiones de ajuste
- Parte 5: Corrida 2 del agente (post-ajustes)
- Parte 6: Análisis de convergencia
- Parte 7: Decisión final (sellar o iterar V3)
- Parte 8: Redacción del `calibracion.md` final
- Parte 9: Checklist de entrega

**¿Cuándo usarlo?**: DESPUÉS de que existan rúbrica, agente y casos. Probablemente última semana (5-7/9).

**Tiempo estimado**: 2-3 días de trabajo iterativo.

---

## PARTE B: CRONOLOGÍA RECOMENDADA

### **Fase 1: Preparación (27-28 de agosto)**

**Hitos**:
1. ✅ Crear estructura GitHub del repositorio (carpetas, README inicial).
2. ✅ Asignar roles específicos a cada integrante (ver Parte C).
3. ✅ Primera reunión de alineación (75 minutos, según guía de Pablo):
   - Acordar objetivo único: un agente, una fuente de verdad.
   - Inventario de herramientas (quién tiene Codex/Claude/Antigravity).
   - Pensar primeras versiones de rúbrica y casos.

**Responsable**: Pablo Bellesi (Rol A - Coordinación).

**Entregables**: README.md inicial, AGENTS.md, estructura de carpetas.

---

### **Fase 2: Rúbrica Ejecutable v1 (28-30 de agosto)**

**Hitos**:
1. ✅ Leer documentos de consigna oficial del trabajo final.
2. ✅ Usando PIC-AE como referencia, redactar rúbrica.md v1.
3. ✅ Revisar cruzada dentro del grupo (autor + revisor).
4. ✅ Cometer a GitHub con historia clara.

**Responsable**: Rol C (Rúbrica) + Rol F (Calibración/QA).

**Entregables**: `rubrica.md` v1 que cumpla A1.1 a A1.4 (precisión, escalas, evidencia, ejemplos).

**Validación**: Checklist de PIC-AE, Sección A, Dimensión 1.

---

### **Fase 3: Casos de Prueba (30/8 - 5/9)**

**Hitos**:
1. ✅ Leer documento "Desarrollo de Casos de Prueba" (Documento 2).
2. ✅ Analizar: ¿Qué es "excelente", "flojo", "tramposo" en contexto del trabajo final?
3. ✅ Construir casos/excelente/ (Parte 2 del documento).
4. ✅ Construir casos/flojo/ (Parte 3 del documento).
5. ✅ Construir casos/tramposo/ con trampa pensada (Partes 4-5 del documento).
6. ✅ Documentar cada caso con README explicativo.
7. ✅ Validación cruzada con rúbrica y agente (Parte 6 del documento).

**Responsable**: Rol D (casos excelente/flojo) + Rol E (caso tramposo) + revisor técnico.

**Entregables**: Tres carpetas en `casos/` con contenido real y completo.

**Validación**: Checklist de PIC-AE, Sección A, Dimensión 3.

---

### **Fase 4: Agente Corrector v1 (30/8 - 7/9)**

**Hitos**:
1. ✅ Leer rúbrica.md (ya debe estar terminada).
2. ✅ Construir system_prompt del agente (agnóstico de herramienta).
3. ✅ Especificar qué herramientas necesita (file reading, etc.).
4. ✅ Testearlo sobre casos (debe funcionar end-to-end).
5. ✅ Ajustar hasta que produce salida estructurada (JSON/MD/tabla).
6. ✅ Documentar agente/ con README de configuración.

**Responsable**: Rol B (Integración técnica) + Rol A (Coordinación).

**Entregables**: `agente/system_prompt.md` + `agente/README.md`.

**Validación**: Checklist de PIC-AE, Sección A, Dimensión 2.

---

### **Fase 5: Calibración (5-9 de septiembre)**

**Hitos**:
1. ✅ Leer documento "Desarrollo de Calibración" (Documento 3).
2. ✅ **Reunión pre-calibración**: Grupo asigna puntuaciones humanas a los 3 casos (Parte 1, Sección 1.3).
3. ✅ Corre agente sobre los 3 casos (Parte 2).
4. ✅ Compara humano vs. agente V1 (Parte 3).
5. ✅ Identifica desacuerdos y analiza causas (Parte 4, Secciones 4.1-4.2).
6. ✅ Decide ajustes (rúbrica y/o agente).
7. ✅ Implementa ajustes con commits.
8. ✅ Corre agente nuevamente (Parte 5).
9. ✅ Verifica convergencia (Parte 6).
10. ✅ Redacta `calibracion.md` final (Parte 8).

**Responsable**: Rol F (Calibración) + equipo completo (reunión).

**Entregables**: `calibracion.md` con historia completa de iteraciones.

**Validación**: Checklist de PIC-AE, Sección A, Dimensión 4.

---

### **Fase 6: Proceso Grupal y Cierre (10 de septiembre)**

**Hitos**:
1. ✅ Revisar historial de GitHub (commits, PRs, mensajes).
2. ✅ Actualizar/completar ESTADO_PROYECTO.md, DECISIONES.md.
3. ✅ Hacer último commit y push.
4. ✅ Subir link del repositorio al campus antes de 18:59.
5. ✅ Prepararse para prueba de fuego (22:00 esa misma noche).

**Responsable**: Pablo Bellesi (Rol A - Coordinación).

**Entregables**: Repositorio completamente funcional, historia clara de commits, todos los archivos presentes.

**Validación**: Checklist de PIC-AE, Sección A, Dimensión 5.

---

## PARTE C: ASIGNACIÓN DEFINITIVA DE ROLES

La asignación definitiva del equipo es:

| Rol | Responsable | Responsabilidad Principal | Herramienta |
|-----|---------------------|--------------------------|-------------|
| **A - Coordinación** | Pablo Bellesi | Backlog, reuniones, decisiones, estado, merge final | ChatGPT/GitHub |
| **B - Integración Técnica** | Diego Mendez | Arquitectura, system prompt del agente, coherencia técnica | Codex/Claude/Antigravity |
| **C - Rúbrica ejecutable** | Franco Gambini | Criterios, escalas, ejemplos, precisión | Cualquiera (preferible sin IA) |
| **D - Casos excelente y flojo** | Sofia Mapelli | Construir y documentar dos casos bases | GitHub + IA para revisión |
| **E - Caso adversarial / tramposo** | Franco Forziati | Diseñar y construir caso tramposo | Claude/ChatGPT (para idear trampas) |
| **F - Calibración y QA** | Melisa Clark | Comparar humano vs. agente, ajustes, documentación | Cualquiera (análisis crítico) |

**Notas**:
- Cada rol tiene 1 responsable principal, pero puede haber revisores.
- Las herramientas son sugerencias; pueden cambiar.
- B es el rol más técnico y requiere acceso a herramientas pagadas (idealmente).
- F requiere capacidad de análisis crítico y síntesis (tal vez alguien del área de management/análisis).

---

## PARTE D: CAMBIOS RESPECTO AL PROMPT ORIGINAL (TFM)

| Aspecto | Prompt TFM Original | Prompt PIC-AE (Nuevo) |
|--------|-------------------|----------------------|
| **Unidad de Análisis** | 1 capítulo de texto (Contexto Conceptual) | 1 repositorio GitHub completo |
| **Estructura de Contenido** | Párrafo Intro + patrón F-F-C + Conclusión | 5 dimensiones ponderadas (25-25-20-15-15) |
| **Reglas de Párrafo** | 85-105 palabras, 3 oraciones, 27-35 palabras/oración | Formato variable (no restrictivo), pero contenido riguroso |
| **Foco de Evaluación** | Redacción académica, claridad, citas APA | Funcionalidad, rigor, discriminación, reproducibilidad |
| **Método de Corrección** | Análisis párrafo por párrafo | Análisis dimensión por dimensión + historial GitHub |
| **Criterios de Desempeño** | Precisión redaccional, paráfrasis, citación | Precisión funcional, capacidad de discriminación, honestidad de calibración |
| **Iteración** | Una versión, feedback linear | Múltiples iteraciones (V1, V2, posible V3) con ajustes documentados |

---

## PARTE E: CRITERIOS DE ÉXITO

Tu agente evaluador habrá **triunfado** si:

### **Criterio 1: Funciona End-to-End**
- ✅ Corre sobre un repositorio real sin errores.
- ✅ Lee archivos, código, documentación.
- ✅ Genera puntuaciones estructuradas.
- ✅ Justifica cada puntuación con evidencia específica.

### **Criterio 2: Discrimina Correctamente**
- ✅ Caso excelente recibe puntuación significativamente más alta que flojo.
- ✅ Caso tramposo recibe puntuación más baja que excelente (detecta trampa).
- ✅ Diferencias de puntuación reflejan diferencias reales de calidad.

### **Criterio 3: Converge con Criterio Humano**
- ✅ Desacuerdos iniciales (V1) se reducen post-ajustes (V2).
- ✅ Tasa de convergencia >70%.
- ✅ Desacuerdos residuales son leves (<2 puntos) o documentados como legítimos.

### **Criterio 4: Es Reproducible**
- ✅ Múltiples corridas sobre el mismo caso producen puntajes idénticos/muy similares.
- ✅ Justificaciones son consistentes.
- ✅ No hay "suerte" o aleatoriedad en las evaluaciones.

### **Criterio 5: Es Verificable**
- ✅ Cada afirmación en la evaluación es verificable en el repositorio.
- ✅ No hay "suposiciones" sin evidencia.
- ✅ Un humano puede seguir la lógica del agente.

### **Criterio 6: Proceso es Transparente**
- ✅ Historia de GitHub muestra trabajo colaborativo real.
- ✅ Decisiones están documentadas con justificación.
- ✅ Calibración es honesta (admite desacuerdos, itera, aprende).

---

## PARTE F: RECOMENDACIONES FINALES

### **1. Comienza AHORA con Casos de Prueba**
No esperes a que TODO esté perfecto. Casos y rúbrica pueden avanzar en paralelo. Los casos informarán a la rúbrica.

### **2. Comunica Claramente en GitHub**
- Commits con mensajes descriptivos.
- PRs que expliquen QUÉ y POR QUÉ.
- Issues que describan tareas concretas.

Esto demostra **proceso grupal** (15% de la nota).

### **3. Haz Pruebas Tempranas**
No esperes a la última semana para "testear". Corre el agente sobre casos mientras aún estás construyendo. Eso alimenta la calibración.

### **4. Documenta Desacuerdos**
Un desacuerdo honesto bien resuelto es MEJOR que una "perfección" que se logró sin pensar. La calibración honesta vale más.

### **5. Prepárate para la Prueba de Fuego**
El agente será testeado en vivo contra casos nuevos que nunca vio. Si tu agente solo funciona en casos que conoce, fracasará.

### **6. Considera Edge Cases**
En tu caso tramposo y calibración, piensa en:
- ¿Qué si el repositorio está mal formado?
- ¿Qué si hay archivos no estándar?
- ¿Qué si el código está en otro lenguaje?

Tu agente debe ser robusto.

---

## PARTE G: CONTACTO Y DUDAS

**Si durante la construcción surge una duda sobre**:

- **Qué debe evaluarse exactamente**: Consulta `1_PIC-AE_PROMPT_EVALUADOR_COMPLETO.md`.
- **Cómo construir casos realistas**: Consulta `2_PIC-AE_DESARROLLO_CASOS_PRUEBA.md`.
- **Cómo calibrar correctamente**: Consulta `3_PIC-AE_DESARROLLO_CALIBRACION.md`.
- **Decisiones del grupo**: Pregunta en reunión y documenta en DECISIONES.md.
- **Interpretación oficial de la consigna**: Pregunta al profesor.

---

## PARTE H: TIMELINE VISUAL

```
Hoy (27/8)          1/9          5/9          9/9          10/9
│────────────────────│────────────────────│────────────────────│
FASE 1              FASE 2-3            FASE 4-5              CIERRE
Prep                Rúbrica +            Agente +              Entrega
                    Casos 1              Calibración
                    (V1)                 (V1 → V2)
```

---

**Fin del Resumen Ejecutivo**

El equipo está listo. Los prompts están listos. El camino es claro. ¡A trabajar! 🚀
