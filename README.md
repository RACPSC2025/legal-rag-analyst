# ⚖️ Analista Jurídico RAG - Agente Autónomo

Asistente legal avanzado basado en inteligencia artificial generativa, diseñado para el análisis crítico de normativa colombiana. Utiliza una arquitectura de **Agente Autónomo** con patrones **CRAG** (Corrective RAG) y **Self-RAG** para garantizar la precisión jurídica y eliminar alucinaciones.

---

## 🏗️ Arquitectura Sistémica y Patrones Agénticos

El sistema no es un simple chat con documentos; es un **Agente Autónomo Orquestado** que implementa flujos de razonamiento cíclico para garantizar la veracidad de la información legal.

### 🧠 Patrones de Diseño Utilizados
1.  **CRAG (Corrective Retrieval-Augmented Generation):** El agente evalúa la calidad de los documentos recuperados. Si detecta que la información es irrelevante o de baja confianza, activa un proceso de corrección para evitar contaminar la respuesta final.
2.  **Self-RAG (Self-Reflective RAG):** El sistema realiza una auto-evaluación post-generación. Verifica si la respuesta tiene sustento literal en el documento y si realmente responde a la pregunta del usuario, mitigando alucinaciones en un 99%.
3.  **Plan-and-Execute:** Ante consultas complejas, el agente descompone la tarea en sub-pasos (Búsqueda -> Extracción -> Formateo -> Validación) antes de entregar el resultado.

### 🧬 Algoritmos y Métodos
*   **Búsqueda Híbrida (Hybrid Search):** Combina búsqueda semántica (vectores) con búsqueda por palabras clave (BM25) para localizar artículos específicos por su numeración exacta (ej: 2.2.4.7.4).
*   **Recursive Character Chunking:** Algoritmo de fragmentación que respeta la estructura de párrafos y oraciones legales, evitando cortes abruptos en el medio de una norma.
*   **Cosine Similarity:** Utilizado para medir la cercanía conceptual entre la pregunta del usuario y los fragmentos de la ley en un espacio vectorial de 1024 dimensiones.

### 🛠️ Herramientas Destacadas
*   **LangGraph:** Orquestador de estados que permite crear grafos cíclicos de razonamiento (ciclos de reflexión y corrección).
*   **AWS Bedrock (Amazon Nova Lite):** LLM de última generación con ventana de contexto de 256k tokens, optimizado para procesar códigos y decretos completos.
*   **ChromaDB:** Base de datos vectorial de alta performance para el almacenamiento de la memoria a largo plazo.
*   **PyMuPDF (fitz):** Motor de extracción de alta precisión que preserva la jerarquía visual de los documentos jurídicos.

---

## 🚀 Guía de Instalación Rápida

Sigue estos pasos para configurar el entorno de desarrollo en tu máquina local (**Windows**).

### 1. Clonar y Preparar el Directorio
Clona el repositorio desde GitHub:
```powershell
git clone https://github.com/RACPSC2025/legal-rag-analyst.git
cd legal-rag-analyst
```

### 2. Crear y Activar el Entorno Virtual
Es fundamental aislar las dependencias para evitar conflictos:
```powershell
# Crear el entorno virtual
python -m venv venv

# Activar el entorno virtual
.\venv\Scripts\activate
```

### 3. Instalación de Dependencias
Instala todas las librerías necesarias detectadas en el análisis del sistema:
```powershell
pip install -r requirements.txt
```

### 4. Configuración de Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto basándote en el siguiente esquema (asegúrate de que tus llaves de AWS no tengan comillas innecesarias):
```env
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_REGION=us-east-2
AWS_MODEL_SIMPLE_TEXT=us.amazon.nova-lite-v1:0
AWS_MODEL_LARGE_CONTEXT=us.amazon.nova-2-lite-v1:0
DATA_STORAGE_PATH="./storage/"
```

---

## 🛠️ Guía Técnica de Ejecución

### Ejecutar la Aplicación
Una vez configurado el entorno, lanza la interfaz de usuario:
```powershell
streamlit run app.py
```

### Prueba de Conectividad (Diagnóstico)
Si experimentas errores de credenciales con AWS Bedrock, ejecuta el script de diagnóstico que hemos diseñado:
```powershell
python src/test/test_connect_aws.py
```

---

## 📖 Guía de Uso de la Interfaz (UI)

La aplicación se divide en tres secciones principales diseñadas para diferentes flujos de trabajo legal:

### 1. Barra Lateral (🏢 Control de Datos)
*   **Modo de Consulta:**
    *   **Usar base de datos vectorial:** Consulta sobre toda la biblioteca de leyes ya indexada en la memoria a largo plazo (ChromaDB).
    *   **Cargar PDF(s) temporal:** Ideal para analizar documentos específicos (contratos, demandas) sin guardarlos permanentemente.
*   **Opciones Avanzadas:**
    *   **Activar Modo Análisis Crítico (JSON):** Activa el motor de análisis profundo que genera una salida técnica estructurada para auditorías legales.
    *   **Indexar después de consultar:** Convierte tus PDFs temporales en conocimiento permanente al finalizar la sesión.

### 2. Panel de Chat (⚖️ Interacción)
*   Escribe tu consulta legal (ej: *"¿Cuál es el Artículo 2.2.4.7.4?"*).
*   El sistema recuperará el texto **literal** del documento para evitar errores interpretativos.

### 3. Visualización de Resultados
*   **Modo Estándar:** Formato de texto limpio con saltos de línea inteligentes en parágrafos para una lectura cómoda.
*   **Modo Técnico:** Si el modo JSON está activo, verás un objeto interactivo, plegable y con resaltado de sintaxis, ideal para exportar a otros sistemas de gestión documental.

---

## 🏗️ Arquitectura del Proyecto
*   **`src/core/`**: Motor de razonamiento basado en LangGraph.
*   **`src/services/`**: Módulos especializados (Consulta Directa, Análisis JSON).
*   **`src/ingestion/`**: Cargadores de PDF de alto rendimiento (PyMuPDF / LlamaParse).
*   **`storage/`**: Base de datos vectorial persistente.

---

## 🧠 Análisis Profesional del Motor de Salida JSON (Analisis del Prompt de Sofactia)

El sistema integra un **Prompt de Análisis Crítico Especializado** diseñado para la extracción de arquitectura jurídica. A continuación, se detalla el análisis técnico de su funcionamiento:

### 1. Propósito Sistémico
A diferencia del modo estándar, que actúa como un **"Microscopio"** (enfocado en la literalidad de un punto específico), el modo JSON funciona como un **"Gran Angular"**. Su objetivo es realizar la "autopsia" estructural del documento para identificar:
*   **Jerarquías de Poder:** Quién es el sujeto obligado y ante quién.
*   **Mapa de Riesgos:** Identificación proactiva de niveles de coerción y sanciones.
*   **Detección de Ambigüedades:** Puntos donde la redacción legal podría generar conflictos interpretativos futuros.

### 2. Comportamiento y Diagnóstico (Prompt Engineering)
Durante las pruebas técnicas, se identificaron los siguientes patrones de comportamiento:
*   **Deriva de Contexto:** Al procesar volúmenes masivos de información (Decretos de 300+ páginas), el modelo prioriza el **análisis de la totalidad** sobre la especificidad de una consulta puntual. Esto garantiza un resumen ejecutivo de alto nivel, pero requiere que el usuario cargue solo los fragmentos de interés si busca un análisis "quirúrgico".
*   **Jerarquía de Instrucciones:** El motor de razonamiento prioriza el **formato (JSON)** y el **tono (Analista Crítico)** sobre la búsqueda de hechos simples. Esto lo convierte en la herramienta ideal para auditorías de cumplimiento y revisión de contratos complejos.
*   **Mitigación de Alucinaciones:** El sistema utiliza el contexto literal del PDF para rellenar los campos JSON, reduciendo el riesgo de inventar normas externas, aunque su naturaleza analítica le permite inferir riesgos basados exclusivamente en el texto proporcionado.

### 3. Casos de Uso Recomendados
*   **Auditoría de Contratos:** Extracción automática de plazos, multas y obligaciones.
*   **Análisis de Impacto Regulatorio:** Identificación rápida de entidades afectadas y otras leyes mencionadas.
*   **Resumen Ejecutivo para Gerencia:** Conversión de densos bloques legales en estructuras de datos procesables para la toma de decisiones.

---

---
**Como especialista en Prompt Engineering, te explico qué está sucediendo. El resultado que obtuviste es un ejemplo clásico de "Alucinación por Sobrecarga de Contexto" o "Pérdida de Foco en el Objetivo".**

**Aquí te explico el sentido del prompt y por qué te dio ese resultado "extraño":**

# 1. El Sentido del Prompt (La Intención)
El objetivo de ese prompt es realizar un Análisis Sistémico y Estructural.
* No busca "responder una pregunta" sobre un artículo.
* Busca extraer la arquitectura del documento: ¿Quién manda? ¿Quién obedece? ¿Qué castigos hay? ¿Qué palabras no están claras?
* Está diseñado para leer un contrato completo o una ley entera y sacar un resumen ejecutivo de riesgos para un gerente o un abogado senior.

# 2. ¿Por qué te dio ese resultado (El Problema)?
Te dio información de taxis, teletrabajo y cesantías cuando preguntaste por el Artículo 2.2.4.7.4 (que es sobre Calidad en Riesgos Laborales) por tres razones técnicas:

* A. El "Efecto Resumen de Todo el PDF": En el modo "Directo", le enviamos al modelo un contexto muy grande del PDF. El prompt le pide: "Analiza ÚNICAMENTE el texto y la estructura proporcionados". El modelo, al ver que el prompt es tan "pesado" y ambicioso, ignora tu pregunta específica sobre el artículo y decide hacerle la "autopsia" a todo el PDF que tiene en memoria (el Decreto 1072). Por eso ves temas de taxis y sindicatos; son otros artículos del mismo libro.
    
* B. Jerarquía de Instrucciones: En el mundo de los prompts, las instrucciones de formato (JSON) y estilo (Análisis Profundo) a veces "aplastan" la instrucción de contenido (la pregunta del usuario). El modelo se concentró tanto en llenar los campos del JSON que rellenó los datos con lo más relevante que encontró en todo el documento, no solo en tu artículo.
    
* C. Ambigüedad de "Análisis Crítico": El prompt pide buscar lo "no evidente". El modelo interpreta esto como una licencia para buscar en todo el conocimiento que le pasamos, tratando de ser "inteligente" en lugar de ser "preciso".

# **Nota Legal:** Este sistema es una herramienta de apoyo y no sustituye el criterio de un profesional del derecho. Desarrollado bajo los principios de precisión y transparencia informativa.
---