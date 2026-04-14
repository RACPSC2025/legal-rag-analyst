# 📘 Guía de Uso — Amatia Express Legal Agent AI

> **Versión:** 1.0  
> **Fecha:** 14 de abril de 2026  
> **Público:** Usuarios finales — abogados, analistas jurídicos, consultores

---

## Índice

1. [Primeros pasos](#1-primeros-pasos)
2. [Modo Biblioteca — Consultar normativa indexada](#2-modo-biblioteca--consultar-normativa-indexada)
3. [Modo Mesa de Trabajo — Analizar documentos temporales](#3-modo-mesa-de-trabajo--analizar-documentos-temporales)
4. [Ingestar documentos a la Biblioteca](#4-ingestar-documentos-a-la-biblioteca)
5. [Análisis Crítico (formato JSON)](#5-análisis-crítico-formato-json)
6. [Gestión del Chat](#6-gestión-del-chat)
7. [Preguntas frecuentes](#7-preguntas-frecuentes)

---

## 1. Primeros pasos

### Abrir la aplicación

1. Abre una terminal (PowerShell) en la carpeta del proyecto.
2. Activa el entorno virtual:
   ```
   .\venv\Scripts\activate
   ```
3. Instala las dependencias (solo la primera vez o después de una actualización):
   ```
   pip install -r requirements.txt
   ```
4. Ejecuta la aplicación:
   ```
   streamlit run app.py
   ```
5. Se abrirá automáticamente en tu navegador. Si no, copia la URL que aparece en la terminal (generalmente `http://localhost:8501`).

### Conocer la interfaz

La pantalla se divide en 3 zonas:

| Zona | Contenido |
|------|-----------|
| **Barra lateral (izquierda)** | Selector de modo, contador de documentos, toggle de análisis, botón de limpiar chat |
| **Pestaña "Centro de Consultas"** | Chat interactivo para hacer preguntas legales |
| **Pestaña "Gestión de Datos"** | Carga de documentos: ingesta permanente (Biblioteca) o temporal (Mesa de Trabajo) |

---

## 2. Modo Biblioteca — Consultar normativa indexada

> **Para qué sirve:** Consultar leyes, decretos y normas que ya están guardadas en la memoria del sistema de forma permanente.

### Paso a paso

1. En la **barra lateral**, selecciona **"📚 Biblioteca Jurídica"**.
2. Ve a la pestaña **"💬 Centro de Consultas"**.
3. Escribe tu pregunta en el campo de texto inferior.  
   Ejemplos:
   - *"¿Qué dice el Artículo 2.2.4.6.16?"*
   - *"¿Cuáles son las obligaciones del empleador respecto a riesgos laborales?"*
   - *"¿Cuántos negociadores sindicales permite la ley en el ámbito nacional?"*
4. Presiona **Enter** o haz clic en el botón de enviar.
5. El sistema procesará tu pregunta y mostrará la respuesta con citas de fuentes.

### Entender la respuesta

- **Texto de la respuesta:** Responde directamente a tu pregunta con lenguaje claro y preciso.
- **Citas entre paréntesis:** Cada punto clave incluye la fuente. Ejemplo: `(Art. 2.2.4.6.16, pág. 145)`.
- **Fuentes y citas:** Haz clic en **"🔍 Ver fuentes y citas"** para ver los fragmentos exactos del documento que respaldan la respuesta.
- **Metadatos de calidad** (solo en modo Biblioteca):
  - **Intentos:** Número de intentos del sistema para verificar la respuesta (1-2).
  - **Calidad:** Resultado de la verificación anti-alucinación ("útil", "no_útil" o "alucinación").

---

## 3. Modo Mesa de Trabajo — Analizar documentos temporales

> **Para qué sirve:** Analizar documentos específicos (sentencias, contratos, demandas) sin guardarlos permanentemente en la base de datos.

### Paso a paso

1. En la **barra lateral**, selecciona **"📑 Mesa de Trabajo (Caso)"**.
2. Ve a la pestaña **"⚙️ Gestión de Datos"**.
3. Haz clic en **"Seleccionar archivos"** y elige los PDFs del caso.
4. Haz clic en **"🔍 Preparar para Análisis"**.
5. Aparecerá un mensaje de confirmación con la cantidad de documentos cargados.
6. Ve a la pestaña **"💬 Centro de Consultas"** y haz tus preguntas sobre esos documentos.

### Limpiar la Mesa de Trabajo

Cuando termines con el caso:
1. En **"⚙️ Gestión de Datos"**, verás la lista de archivos activos.
2. Haz clic en **"🗑️ Limpiar Mesa"**.
3. Los documentos se eliminan del sistema.

---

## 4. Ingestar documentos a la Biblioteca

> **Para qué sirve:** Agregar documentos al conocimiento permanente del sistema para que estén disponibles en futuras sesiones.

### Paso a paso

1. En la **barra lateral**, selecciona **"📚 Biblioteca Jurídica"**.
2. Ve a la pestaña **"⚙️ Gestión de Datos"**.
3. En **"Motor de extracción PDF"**, elige una opción:

   | Motor | Cuándo usarlo |
   |-------|---------------|
   | **PyMuPDF** | La mayoría de decretos y leyes en texto digital. Es rápido y recomendado para uso general. |
   | **Docling** | PDFs con tablas complejas, columnas múltiples o gacetas oficiales. Es más lento pero preserva mejor la estructura. |

4. Si elegiste **Docling** y tu PDF es escaneado (sin texto seleccionable), marca la casilla **"Activar OCR"** (aumenta significativamente el tiempo de procesamiento).
5. Haz clic en **"Seleccionar archivos"** y elige los PDFs.
6. Haz clic en **"🚀 Incorporar a Biblioteca"**.

### Ver el progreso

Durante la ingesta verás una **barra de progreso** con mensajes:

| Etapa | Qué está pasando |
|-------|-----------------|
| 📄 Cargando PDFs... | El sistema lee y extrae el texto de los archivos |
| 🧠 Generando embeddings... | Los fragmentos se convierten en vectores semánticos |
| 🧠 Indexando lote X/Y... | Se guardan los vectores en la base de datos (puede tomar varios minutos) |
| ✅ Finalizando... | Se completa la indexación y se refresca el contador |

7. Al terminar, verás un mensaje de éxito: `"✅ X fragmentos indexados desde Y archivo(s)"`.
8. El contador de **"Documentos Indexados"** en la barra lateral se actualizará automáticamente.

---

## 5. Análisis Crítico (formato JSON)

> **Para qué sirve:** Obtener un análisis jurídico estructurado que identifica riesgos, obligaciones, plazos y ambigüedades en un documento. Ideal para auditorías de contratos.

### Paso a paso

1. Activa el toggle **"🔬 Análisis Crítico (JSON)"** en la barra lateral.
2. Asegúrate de estar en **Modo Mesa de Trabajo** con documentos cargados.
3. Ve a **"💬 Centro de Consultas"** y escribe tu pregunta.
4. La respuesta se mostrará como un **objeto JSON interactivo** que puedes expandir y colapsar.

### Campos del análisis JSON

| Campo | Descripción |
|-------|-------------|
| `tipo_documento` | Tipo de documento identificado |
| `tono_general` | Imperativo, informativo, regulatorio |
| `nivel_urgencia` | Escala 0-5 |
| `nivel_coercion` | Escala 0-5 (presencia de sanciones) |
| `obligaciones_criticas` | Lista con: texto, responsable, plazo, consecuencia, criticidad |
| `temas_principales` | Temas clave del documento |
| `plazos_inmediatos` | Plazos urgentes mencionados |
| `ambigüedades_identificadas` | Imprecisiones o puntos confusos |
| `definiciones_clave` | Términos y sus definiciones |
| `entidades_afectadas` | Organismos o sectores afectados |
| `referencias_internas` | Artículos o secciones cruzadas |
| `menciones_de_otras_leyes` | Otras leyes mencionadas |
| `analisis_critico` | Análisis estratégico de aspectos no evidentes |

---

## 6. Gestión del Chat

### Ver historial de conversación

El chat mantiene el historial de la sesión actual. Puedes hacer preguntas de seguimiento que consideran las respuestas anteriores.

### Limpiar el chat

Haz clic en **"🔄 Limpiar Chat"** en la barra lateral para borrar todo el historial y empezar de nuevo.

### Ver fuentes de una respuesta

Cada respuesta tiene un desplegable **"🔍 Ver fuentes y citas"**. Haz clic para ver los fragmentos del documento que respaldan la respuesta.

---

## 7. Preguntas frecuentes

### ❓ ¿Qué tipo de documentos puedo cargar?
Solo archivos **PDF**. El sistema soporta PDFs con texto digital y PDFs escaneados (con OCR activado en modo Docling).

### ❓ ¿Los documentos de la Mesa de Trabajo se guardan permanentemente?
No. Se usan solo durante la sesión activa y se eliminan al limpiar la mesa.

### ❓ ¿Cuántos documentos puedo ingestar a la vez?
El sistema procesa documentos en lotes. No hay un límite estricto, pero se recomienda ingestar de 1 a 5 documentos a la vez para tiempos de respuesta razonables.

### ❓ ¿Por qué la respuesta dice "No dispongo de información suficiente"?
El sistema está diseñado para responder **únicamente** con información contenida en los documentos indexados. Si la respuesta no está en los documentos, lo indica explícitamente en lugar de inventar.

### ❓ ¿Cómo sé que la respuesta es confiable?
Cada respuesta incluye citas de fuentes. Además, el sistema muestra los metadatos de **Intentos** y **Calidad** para que veas el resultado de la verificación anti-alucinación.

### ❓ ¿Puedo hacer preguntas de seguimiento?
Sí. El sistema mantiene el contexto de la conversación. Puedes preguntar *"¿Y cuál es el plazo para cumplir eso?"* y entenderá la referencia.

---

*Amatia Express Legal Agent AI — Tu consultor jurídico experto e inteligente.*
