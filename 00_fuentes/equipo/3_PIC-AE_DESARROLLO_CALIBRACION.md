# PIC-AE: GUÍA EXHAUSTIVA PARA DESARROLLAR CALIBRACIÓN
## Comparación Humano vs. Agente, Identificación de Desacuerdos y Ajustes Iterativos
### Parcial Grupal - Agente Evaluador · MBA UCEMA · 2026 2T

**Responsable designada**: Melisa Clark - Rol F - Calibración y QA.

---

## PARTE 0: CONTEXTO Y PROPÓSITO

Tu tarea es **calibrar el agente evaluador contra el criterio humano del grupo**. Esto significa:

1. **Correr el agente** sobre los tres casos de prueba.
2. **Asignar puntuaciones humanas** (lo que TÚ y el grupo creen que merece cada caso).
3. **Comparar**: ¿Qué puntuaciones dio el agente? ¿Qué puntuaciones dieron ustedes? ¿Dónde coinciden? ¿Dónde difieren?
4. **Identificar desacuerdos**: ¿Por qué hay diferencias? ¿Es un error del agente, una ambigüedad de la rúbrica, o diferencias legítimas de criterio?
5. **Ajustar**: ¿Cambiamos la rúbrica para que sea más clara? ¿Mejoramos el agente para que entienda mejor? ¿O aceptamos el desacuerdo como legítimo?
6. **Re-testear**: Corremos el agente nuevamente y vemos si los ajustes funcionaron.
7. **Documentar TODO**: Queda constancia de este proceso iterativo, no de una "calibración perfecta de primer intento".

**Por qué importa**:
- La calibración es 15% de la calificación del parcial.
- Demuestra que el grupo reflexionó críticamente sobre su agente.
- Un desacuerdo **honesto y bien resuelto** vale más que un acuerdo "perfecto" que nunca existió.
- La historia de ajustes muestra trabajo real y pensamiento colaborativo.

**Entrega Final**:
Un archivo `calibracion.md` en la raíz del repositorio que documentar TODO este proceso, paso a paso.

---

## PARTE 1: PREPARACIÓN

### **1.1 - Confirma que Tienes los Ingredientes**

Antes de empezar, asegúrate de que existe (en el repositorio):

- ✅ `rubrica.md` (la rúbrica ejecutable que el agente usará)
- ✅ `agente/` (la carpeta con el system prompt del agente)
- ✅ `casos/excelente/` (caso 1)
- ✅ `casos/flojo/` (caso 2)
- ✅ `casos/tramposo/` (caso 3)

Si alguno falta, **espera a que se construya** antes de continuar.

### **1.2 - Entiende la Rúbrica (Punto 0: Línea Base)**

Lee la rúbrica ejecutable (`rubrica.md`) **MUY cuidadosamente**.

Para CADA DIMENSIÓN en la rúbrica, responde:

**Formato**: Usa una tabla como esta:

| Dimensión | Definición | Niveles de Escala | Evidencia por Nivel |
|-----------|-----------|------------------|-------------------|
| Dim 1: [Nombre] | [Qué es] | 1pt: X, 2pts: Y, ... | Para 1pt: busca Z, Para 2pts: busca W, ... |
| Dim 2: ... | ... | ... | ... |

**Escribe esta tabla en un documento llamado `ENTENDER_RUBRICA.md`.** Esto será tu "cheat sheet" para la calibración.

### **1.3 - Acuerda Criterio Previo del Grupo (Reunión Breve)**

Antes de correr el agente, el grupo debe llegar a un **consenso PREVIO** sobre qué puntuación debería recibir cada caso.

**Instrucción para el grupo**:

Hagan una reunión rápida (30-45 minutos) donde:

1. **Leen los tres casos de prueba** (excelente, flojo, tramposo).
2. **Aplican la rúbrica manualmente** a cada caso (por dimensión, sin la ayuda del agente).
3. **Cada integrante da su puntuación** (escala 1-10 o 0-100, según la rúbrica).
4. **Discuten desacuerdos**: Si alguien da 8 y otro da 6, ¿por qué? ¿Quién tiene razón?
5. **Llegan a una puntuación final del grupo** (por consenso o votación).

**Resultado**: Un documento temporal llamado `PUNTUACIONES_HUMANAS_V1.md` con:

```markdown
# Puntuaciones Humanas - Versión 1 (Pre-Agente)

## Caso Excelente

| Dimensión | Puntaje | Justificación |
|-----------|---------|---------------|
| Dim 1 | 9/10 | Porque [razón clara] |
| Dim 2 | 8/10 | Porque [razón clara] |
| Dim 3 | 10/10 | Porque [razón clara] |
| **TOTAL** | **27/30** | |

## Caso Flojo

| Dimensión | Puntaje | Justificación |
|-----------|---------|---------------|
| Dim 1 | 4/10 | Porque [razón clara] |
| Dim 2 | 3/10 | Porque [razón clara] |
| Dim 3 | 2/10 | Porque [razón clara] |
| **TOTAL** | **9/30** | |

## Caso Tramposo

| Dimensión | Puntaje | Justificación |
|-----------|---------|---------------|
| Dim 1 | 2/10 | Porque [razón clara + menciona la trampa detectada] |
| Dim 2 | 3/10 | Porque [razón clara] |
| Dim 3 | 5/10 | Porque [razón clara] |
| **TOTAL** | **10/30** | |
```

**Guarda este documento**, lo necesitarás para comparar.

---

## PARTE 2: CORRIDA 1 DEL AGENTE (Pre-Calibración)

### **2.1 - Configura el Agente**

Lee el `agente/` del repositorio:

- ¿Cuál es el system prompt exacto?
- ¿Qué herramientas/modelos usa?
- ¿Cómo se ejecuta? (¿Línea de comando? ¿API? ¿Chat?)

Si no está claro, **pregunta a quien construyó el agente** antes de continuar.

### **2.2 - Ejecuta el Agente en los Tres Casos**

Para CADA caso (excelente, flojo, tramposo):

1. **Corre el agente** contra el repositorio del caso.
   - Input: Ruta o acceso al repositorio del caso.
   - Output: Puntuaciones + justificaciones del agente.

2. **Captura la salida completa** (screenshot, copy-paste, o archivo JSON si lo proporciona el agente).

3. **Guarda la salida en un archivo**: `CORRIDA_AGENTE_V1_[CASO].txt`

**Ejemplo de salida esperada**:
```
EVALUACIÓN DEL CASO: EXCELENTE
===============================

Dimensión 1: Rúbrica Ejecutable
Puntaje: 9/10
Justificación: El repositorio incluye archivo rubrica.md bien estructurado con escalas claras y ejemplos por nivel. Encuentra evidencia de buena cobertura en todos los criterios [FILE: rubrica.md, LINEAS 1-50].

Dimensión 2: Agente Corrector Funcional
Puntaje: 8/10
Justificación: El agente corre sin errores, genera salida estructurada, pero podría incluir más detalles en las justificaciones. [FILE: agente/system_prompt.md].

...

TOTAL ESTIMADO: 27/30
```

### **2.3 - Registra Todas las Corridas**

Crea un documento llamado `CORRIDAS_AGENTE_V1.md` con la salida de TODAS las corridas:

```markdown
# Corridas del Agente - Versión 1 (Pre-Calibración)

## Caso Excelente
[Copia completa de la salida del agente]

## Caso Flojo
[Copia completa de la salida del agente]

## Caso Tramposo
[Copia completa de la salida del agente]
```

---

## PARTE 3: COMPARACIÓN INICIAL (V1 vs. V1)

### **3.1 - Construye una Tabla Comparativa**

Crea un documento llamado `COMPARACION_V1.md`:

```markdown
# Comparación Humano vs. Agente - Versión 1

## Caso Excelente

| Dimensión | Humano | Agente | Diferencia | Acuerdo? |
|-----------|--------|--------|-----------|----------|
| Dim 1 | 9/10 | 9/10 | 0 | ✅ SÍ |
| Dim 2 | 8/10 | 7/10 | -1 | ⚠️ LEVE |
| Dim 3 | 10/10 | 9/10 | -1 | ⚠️ LEVE |
| **TOTAL** | 27/30 | 25/30 | **-2** | |

## Caso Flojo

| Dimensión | Humano | Agente | Diferencia | Acuerdo? |
|-----------|--------|--------|-----------|----------|
| Dim 1 | 4/10 | 3/10 | -1 | ⚠️ LEVE |
| Dim 2 | 3/10 | 2/10 | -1 | ⚠️ LEVE |
| Dim 3 | 2/10 | 5/10 | +3 | ❌ DESACUERDO |
| **TOTAL** | 9/30 | 10/30 | **+1** | |

## Caso Tramposo

| Dimensión | Humano | Agente | Diferencia | Acuerdo? |
|-----------|--------|--------|-----------|----------|
| Dim 1 | 2/10 | 4/10 | +2 | ❌ DESACUERDO |
| Dim 2 | 3/10 | 3/10 | 0 | ✅ SÍ |
| Dim 3 | 5/10 | 6/10 | +1 | ⚠️ LEVE |
| **TOTAL** | 10/30 | 13/30 | **+3** | |
```

**Usa estos símbolos**:
- ✅ SÍ (acuerdo perfecto, diferencia 0)
- ⚠️ LEVE (diferencia de 1-2 puntos)
- ❌ DESACUERDO (diferencia >2 puntos o muy significativa)

### **3.2 - Identifica Desacuerdos**

Para CADA desacuerdo (⚠️ LEVE o ❌ DESACUERDO), responde estas preguntas:

**Formato**:

```markdown
### DESACUERDO #1: [Dimensión X, Caso Y]

**Puntuaciones**:
- Humano: Z puntos
- Agente: W puntos
- Diferencia: +/- D puntos

**¿Por qué el humano puntuó así?**
[Explicación del razonamiento del grupo]

**¿Por qué el agente puntuó diferente?**
[Intenta inferir el razonamiento del agente basándote en su justificación]

**Análisis de la brecha**:
- [ ] ¿El agente pasó por alto evidencia que el humano vio?
- [ ] ¿El humano fue demasiado indulgente/severo?
- [ ] ¿La rúbrica es ambigua, permitiendo interpretaciones diferentes?
- [ ] ¿El agente interpretó correctamente pero llegó a conclusión diferente?
- [ ] ¿Es un bug del agente (no funciona correctamente)?

**Conclusión provisional**:
[ ] Es un error del agente → AJUSTAR AGENTE
[ ] Es ambigüedad en la rúbrica → AJUSTAR RÚBRICA
[ ] Es diferencia legítima de criterio → ACEPTAR (documentar por qué)
```

**Haz esto para TODOS los desacuerdos.**

---

## PARTE 4: DECISIONES Y AJUSTES

### **4.1 - Reunión de Ajustes**

Convoca al grupo completo + quien construyó la rúbrica + quien construyó el agente.

**Agenda (60-90 minutos)**:

1. **Revisa todos los desacuerdos** identificados en Parte 3.
2. **Para cada desacuerdo**:
   - **Investiga**: ¿Cuál es la causa? (ver checklist en 3.2)
   - **Discute**: ¿Cuál es la solución? (3 opciones por desacuerdo)
   - **Decide**: ¿Qué hacemos?

### **4.2 - Opciones de Ajuste para Cada Desacuerdo**

Para CADA desacuerdo, el grupo elige UNA de estas opciones:

#### **Opción A: Ajustar la Rúbrica**
Si el problema es que la rúbrica es ambigua o incompleta:

**Ejemplos de ajustes**:
- Hacer una escala más específica (menos "interpretable").
- Añadir ejemplos que clariquen qué buscar.
- Redefinir la evidencia requerida por nivel.
- Combinar/dividir dimensiones si se superponen.

**Acción**: 
1. Describe exactamente QUÉ cambia en la rúbrica.
2. Escribe las nuevas líneas en la rúbrica.
3. Registra el cambio en un documento `AJUSTES_RUBRICA_V1.md`.

**Ejemplo**:
```markdown
### Ajuste 1: Dimensión 3 - "Agente Funcional"

**Problema**: La escala de "funcionamiento" era vaga. Agente puntuó 5/10, Humano 2/10.

**Rúbrica Original**:
Agente Funcional: 
- 1-2 pts: Agente no funciona
- 5-6 pts: Agente funciona parcialmente
- 8-10 pts: Agente funciona completamente

**Nuevo texto**:
Agente Funcional:
- 1-2 pts: Agente no corre, genera errores, no produce salida.
- 3-4 pts: Agente corre en algunos casos, pero produce errores o salida incompleta.
- 5-6 pts: Agente corre sin errores en todos los casos, produce salida estructurada, pero justificaciones son vagas.
- 7-8 pts: Agente corre sin errores, produce salida estructurada con justificaciones concretas citando evidencia.
- 9-10 pts: Agente corre sin errores, produce salida consistente con ejemplos y detecta casos tramposos.

**Evidencia específica**: Buscar en agente/system_prompt.md la definición de "salida estructurada". En casos/[caso], ejecutar y verificar que salida cumple con estos criterios.
```

#### **Opción B: Ajustar el Agente**
Si el problema es que el agente no entiende o aplica la rúbrica correctamente:

**Ejemplos de ajustes**:
- Mejorar el system prompt para ser más explícito.
- Añadir herramientas que le faltan al agente (ej: "parser de código").
- Cambiar la lógica del agente (ej: primero detecta si hay cierta evidencia, LUEGO puntúa).
- Entrenar al agente con ejemplos (few-shot prompting).

**Acción**:
1. Describe exactamente QUÉ cambia en el agente.
2. Escribe las nuevas líneas del system prompt.
3. Registra el cambio en `AJUSTES_AGENTE_V1.md`.

**Ejemplo**:
```markdown
### Ajuste 1: Mejorar Detección de "Agente Funcional"

**Problema**: El agente asignó 5/10 a un caso donde el agente literalmente no corre. Debería haber sido 1/10.

**Agente Original**:
[... system prompt ...]
Evalúa si el agente funciona. Si produce alguna salida, da puntos. Si no produce, da puntos bajos.

**Agente Nuevo**:
[... system prompt ...]
PASO 1: Verifica si agente/system_prompt.md existe y es accesible. [SÍ/NO]
PASO 2: Intenta ejecutar lógicamente el agente con un caso de ejemplo del repositorio.
PASO 3: Si la ejecución lógica falla o no produce salida, puntuación máxima 2/10.
PASO 4: Si produce salida pero incompleta, máximo 6/10.
PASO 5: Si produce salida completa y estructurada, evalúa si cita evidencia específica.

Esta jerarquía asegura que casos no funcionales nunca reciben 5+ puntos.
```

#### **Opción C: Aceptar el Desacuerdo como Legítimo**
Si ninguno de los anteriores aplica, acepta que humano y agente pueden diferir legítimamente.

**Cuándo elegir esto**:
- La rúbrica es clara pero permite interpretaciones.
- El agente interpretó correctamente pero aplicó criterios ligeramente diferentes.
- Es una "diferencia de estilo" evaluador, no un error.

**Acción**:
1. Documenta POR QUÉ es legítimo el desacuerdo.
2. Registra en `DESACUERDOS_ACEPTADOS_V1.md`.
3. No cambies rúbrica ni agente para este punto.

**Ejemplo**:
```markdown
### Desacuerdo Aceptado 1: Dimensión 2 - "Rigor de Calibración"

**Puntuaciones**: Humano 7/10, Agente 6/10. Diferencia: -1.

**Razón por la que es legítimo**:
- Ambos reconocen que la calibración fue iterativa y honesta.
- La diferencia es si fue "muy buena" (7) o "buena" (6).
- Esto depende del peso que cada uno da a la "cantidad" vs. "calidad" de iteraciones.
- No hay una respuesta "correcta", es juicio interpretativo.

**Decisión**: Aceptamos ambas puntuaciones como válidas. En reporte final, usaremos el promedio o el criterio del grupo (vote).
```

### **4.3 - Registra TODOS los Ajustes**

Antes de continuar, crea tres documentos:

- `AJUSTES_RUBRICA_V1.md` (todos los cambios a la rúbrica)
- `AJUSTES_AGENTE_V1.md` (todos los cambios al agente)
- `DESACUERDOS_ACEPTADOS_V1.md` (desacuerdos que se aceptan como legítimos)

---

## PARTE 5: CORRIDA 2 DEL AGENTE (Post-Ajustes)

### **5.1 - Implementa los Ajustes**

1. **Si hay ajustes de rúbrica**: Edita `rubrica.md` directamente en el repositorio.
2. **Si hay ajustes de agente**: Edita `agente/system_prompt.md` (o lo que corresponda).
3. **Haz commits**: Cada cambio debe tener su propio commit descriptivo.

### **5.2 - Corre el Agente Nuevamente**

Repite la Parte 2 (ejecutar agente en los tres casos) **PERO AHORA CON LOS AJUSTES IMPLEMENTADOS**.

**Guarda las salidas**:
- `CORRIDA_AGENTE_V2_[CASO].txt` (para cada caso)
- `CORRIDAS_AGENTE_V2.md` (resumen de todas las corridas V2)

### **5.3 - Compara V2 vs. V1 (Humano)**

Crea `COMPARACION_V2.md` igual que en Parte 3, pero con los nuevos números del agente V2:

```markdown
# Comparación Humano vs. Agente - Versión 2 (Post-Ajustes)

## Caso Excelente

| Dimensión | Humano | Agente V1 | Agente V2 | Mejoró? |
|-----------|--------|-----------|-----------|---------|
| Dim 1 | 9/10 | 9/10 | 9/10 | ✅ (sin cambios) |
| Dim 2 | 8/10 | 7/10 | 8/10 | ✅ MEJORÓ |
| Dim 3 | 10/10 | 9/10 | 10/10 | ✅ MEJORÓ |
| **TOTAL** | 27/30 | 25/30 | 27/30 | ✅ CONVERGIÓ |

...
```

---

## PARTE 6: ANÁLISIS DE CONVERGENCIA

### **6.1 - ¿Convergieron los Desacuerdos?**

Para CADA desacuerdo anterior, responde:

```markdown
### Desacuerdo #1: [Dimensión X, Caso Y]

**Estado anterior**: Humano Z, Agente V1 W (diferencia D)
**Estado actual**: Humano Z, Agente V2 W' (diferencia D')

**¿Convergió?**:
- [ ] SÍ: Agente V2 ahora coincide con humano (D' = 0)
- [ ] MEJORÓ: Brecha se redujo (|D'| < |D|)
- [ ] SIN CAMBIOS: Agente V2 igual a V1 (D' = D)
- [ ] EMPEORÓ: Brecha aumentó (|D'| > |D|)

**Si NO convergió completamente, ¿por qué?**:
[ ] Ajuste no fue suficiente. Necesita otro ajuste.
[ ] Ajuste fue en la dirección equivocada. Revertir y probar otra opción.
[ ] Es un desacuerdo legítimo que no se resolverá. Aceptar.

**Acción próxima**:
[ ] Iteración 3 (más ajustes)
[ ] Aceptar desacuerdo residual
[ ] Investigar más a fondo
```

### **6.2 - ¿Convergió el Grupo Entero?**

Calcula métricas simples:

```markdown
# Análisis de Convergencia

## Métrica 1: Desacuerdos Resueltos

- Desacuerdos iniciales: 5 (3 DESACUERDO, 2 LEVE)
- Desacuerdos post-ajuste: 2 (1 DESACUERDO, 1 LEVE)
- **Tasa de resolución: 60%**

## Métrica 2: Diferencia Promedio

**Caso Excelente**:
- V1: Diferencia promedio entre humano y agente = (0 + 1 + 1) / 3 = 0.67 puntos
- V2: Diferencia promedio = (0 + 0 + 0) / 3 = 0 puntos
- **Mejora: 100%**

**Caso Flojo**:
- V1: Diferencia promedio = (1 + 1 + 3) / 3 = 1.67 puntos
- V2: Diferencia promedio = (0 + 0 + 2) / 3 = 0.67 puntos
- **Mejora: 60%**

**Caso Tramposo**:
- V1: Diferencia promedio = (2 + 0 + 1) / 3 = 1 punto
- V2: Diferencia promedio = (1 + 0 + 1) / 3 = 0.67 puntos
- **Mejora: 33%**

## Conclusión

El agente V2 es significativamente más cercano al criterio humano. Caso Excelente: convergencia completa. Casos Flojo y Tramposo: mejora sustancial pero no perfecta.
```

---

## PARTE 7: DECISIÓN FINAL: ¿Otro Ciclo o Sellar?

### **7.1 - Criterio de Parada**

El grupo decide si hacer otra iteración (V3) o sellar la calibración en V2.

**Haz otra iteración (V3) si**:
- Hay desacuerdos significativos (>2 puntos) sin resolver.
- El agente está siendo engañado por el caso tramposo (no debería ser).
- La tasa de resolución es baja (<70%).

**Sella la calibración (V2) si**:
- Desacuerdos residuales son leves (<2 puntos).
- Agente detecta caso tramposo correctamente (o documenta por qué no).
- Tasa de resolución es alta (>70%).
- Los ajustes tomaron suficiente tiempo/esfuerzo.

### **7.2 - Documentar la Decisión**

```markdown
# Decisión Final de Calibración

**Versión final elegida**: V2

**Razones**:
1. Convergencia completa en caso excelente.
2. Desacuerdos residuales (Dim X, Caso Y) son leves y aceptables porque [RAZÓN].
3. Agente detecta/no detecta caso tramposo de la siguiente forma: [DESCRIPCIÓN].
4. Tiempo/esfuerzo invertido es razonable para valor obtenido.

**Compromisos**:
- Si hubiera más tiempo, habríamos iterado V3 en [DIMENSIÓN], pero es OK por ahora.

**Lecciones aprendidas**:
1. [Qué aprendimos del proceso de calibración]
2. [Qué haríamos diferente la próxima vez]
3. [Qué salió especialmente bien o mal]
```

---

## PARTE 8: REDACTAR calibracion.md FINAL

Ahora, crea el archivo `calibracion.md` en la raíz del repositorio que **documente TODO el proceso**.

### **Estructura del `calibracion.md` Final**

```markdown
# Calibración del Agente Evaluador

## Resumen Ejecutivo

[1 párrafo resumiendo: qué se hizo, cuáles fueron los hallazgos principales, resultado final]

---

## 1. Puntuaciones Humanas Iniciales (Pre-Agente)

### Caso Excelente

| Dimensión | Puntaje | Justificación |
|-----------|---------|---------------|
| Rúbrica Ejecutable | 9/10 | [Razón clara] |
| ... | ... | ... |
| **TOTAL** | **XX/100** | |

**Consenso del grupo**: [Breve descripción de cómo se llegó a estas puntuaciones]

### Caso Flojo

[Tabla similar]

### Caso Tramposo

[Tabla similar]

---

## 2. Corridas del Agente - Versión 1

### Caso Excelente

**Salida del agente**:
```
[Copiar salida completa del agente]
```

**Observaciones**: [Qué se destaca]

### Caso Flojo

[Similar]

### Caso Tramposo

[Similar]

---

## 3. Comparación Inicial: Humano vs. Agente V1

### Tabla de Desacuerdos

| Caso | Dimensión | Humano | Agente V1 | Diff | Tipo |
|------|-----------|--------|-----------|------|------|
| Excelente | Dim 2 | 8 | 7 | -1 | LEVE |
| Flojo | Dim 3 | 2 | 5 | +3 | DESACUERDO |
| ... | ... | ... | ... | ... | ... |

**Desacuerdos identificados**: [Número y naturaleza]

---

## 4. Análisis Profundo de Desacuerdos

### Desacuerdo #1: Caso Flojo, Dimensión 3 "Agente Funcional"

**Puntuaciones**:
- Humano: 2/10 (el agente "no funciona, tiene bugs críticos")
- Agente V1: 5/10 (el agente "funciona parcialmente")

**¿Por qué el humano puntuó 2?**:
- Leyó agente/system_prompt.md.
- Intentó ejecutar lógicamente el agente sobre un repositorio.
- El agente no podía acceder a ciertos archivos, generaba errores.
- Conclusión: "No es funcional en su estado actual".

**¿Por qué el agente V1 puntuó 5?**:
- Detectó que agente/system_prompt.md existe.
- Asumió que si existe un prompt, "algo de funcionalidad hay".
- No verificó realmente si el agente corre sin errores.

**Raíz del problema**: 
- La rúbrica original decía "Agente Funcional: 5-6 pts = Agente funciona parcialmente".
- "Funciona parcialmente" era ambiguo: ¿significa "a veces funciona"? ¿"Tiene bugs"? ¿"Falta completar"?
- Agente V1 interpretó como "existe pero incompleto" (5 pts).
- Humano interpretó como "en su estado actual no funciona" (2 pts).

**Solución elegida**: AJUSTAR RÚBRICA (Option A)

---

## 5. Ajustes Realizados

### Ajuste 1: Rúbrica Dimensión "Agente Funcional"

**Cambio**:

Antes:
```
Agente Funcional:
- 1-2 pts: No funciona
- 5-6 pts: Funciona parcialmente
- 8-10 pts: Funciona completamente
```

Después:
```
Agente Funcional:
- 1-2 pts: No corre, genera errores críticos, no produce salida. Evidencia: errores en agente/system_prompt.md o cuando se intenta ejecutar lógicamente.
- 3-4 pts: Corre en algunos casos pero no en otros, o produce salida incompleta/con errores.
- 5-6 pts: Corre en todos los casos sin errores, produce salida estructurada, pero justificaciones son vagas.
- 7-8 pts: Corre sin errores, produce salida estructurada con justificaciones concretas que citan evidencia.
- 9-10 pts: Corre sin errores, detecta casos tramposos, es reproducible en corridas múltiples.
```

**Justificación**: Las escalas ahora son específicas a "cómo verificar" en el repositorio, no interpretables.

**Commit asociado**: `commit abc123 - Ajustar escala Dimensión "Agente Funcional" para mayor precisión`

### Ajuste 2: System Prompt del Agente

**Cambio**:

Antes:
```
El agente evalúa si el system_prompt.md existe y es accesible. Si sí, da puntos.
```

Después:
```
El agente:
PASO 1: Verifica que agente/system_prompt.md existe.
PASO 2: Lee el prompt. Si está vacío o es un placeholder, máx 2 pts.
PASO 3: Intenta ejecutar mentalmente el agente contra uno de los casos. ¿Produce salida sin errores? ¿Cita evidencia? ¿Es reproducible?
PASO 4: Asigna puntuación basada en estos criterios.
```

**Justificación**: El agente V1 no verificaba realmente funcionamiento, solo existencia.

**Commit asociado**: `commit def456 - Mejorar system prompt para verificar realmente funcionalidad del agente`

---

## 6. Corridas del Agente - Versión 2

### Caso Excelente

[Salida del agente V2]

### Caso Flojo

[Salida del agente V2]

### Caso Tramposo

[Salida del agente V2]

---

## 7. Comparación Post-Ajustes: Humano vs. Agente V2

### Tabla de Convergencia

| Caso | Dimensión | Humano | Agente V1 | Agente V2 | Mejoró? |
|------|-----------|--------|-----------|-----------|---------|
| Excelente | Dim 2 | 8 | 7 | 8 | ✅ SÍ |
| Flojo | Dim 3 | 2 | 5 | 2 | ✅ SÍ (¡convergió!) |
| ... | ... | ... | ... | ... | ... |

**Desacuerdos residuales**: [Número y descripción]

### Análisis de Desacuerdos Post-Ajustes

[Para cada desacuerdo residual, explica por qué persiste y si es aceptable]

---

## 8. Conclusión y Validación

### Convergencia Alcanzada

- **Desacuerdos resueltos**: X de Y (ZZ%)
- **Diferencia promedio (todos los casos)**: W puntos (reducido de V puntos)
- **Agente detecta caso tramposo**: SÍ/NO/PARCIALMENTE

### Validación Final

[El grupo certifica que la calibración fue seria y honesta]

**Firmantes** (opcional): [Integrantes del grupo]

**Fecha**: [Fecha de finalización de calibración]

---

## Apéndices

### Apéndice A: Cronología de Commits

[Lista de todos los commits relacionados con calibración]

### Apéndice B: Decisiones Rechazadas

[Alternativas que se consideraron pero se rechazaron, y por qué]

### Apéndice C: Preguntas Abiertas

[Si algo quedó sin resolver o requiere seguimiento en futuro]
```

---

## PARTE 9: CHECKLIST DE ENTREGA

Antes de dar por finalizada tu tarea, verifica:

- [ ] `calibracion.md` existe en la raíz del repositorio.
- [ ] Contiene puntuaciones humanas iniciales (pre-agente) de los 3 casos.
- [ ] Contiene salida completa del agente V1 para los 3 casos.
- [ ] Contiene tabla de desacuerdos identificados (humano vs. agente V1).
- [ ] Documenta análisis profundo de al menos 2 desacuerdos.
- [ ] Documenta ajustes realizados (rúbrica y/o agente) con justificación.
- [ ] Contiene salida completa del agente V2 para los 3 casos.
- [ ] Contiene tabla de convergencia post-ajustes.
- [ ] Explica por qué desacuerdos residuales persisten (si los hay).
- [ ] Contiene conclusión clara: versión final elegida (V1, V2, o V3+).
- [ ] Los ajustes están committeados en GitHub con mensajes claros.
- [ ] El archivo `calibracion.md` es legible, bien formateado, con tablas donde corresponda.

---

## PARTE 10: PRÓXIMOS PASOS

Una vez completes la calibración:

1. **Comparte con el equipo** en el repositorio.
2. **Espera feedback** del grupo: ¿Alguien desacuerda con la calibración?
3. **Si hay feedback crítico**, puede requerir iteración V3 (vuelve a Parte 4).
4. **Si está OK**, procede a la "prueba de fuego" (evaluación en vivo en clase).

---

**Fin de la Guía para Desarrollar Calibración**

Preguntas de contacto: Si la calibración genera dudas, consulta al coordinador del equipo o al profesor.
