# ⚖️ Amatia Express — Legal Agent AI

Asistente legal autónomo basado en inteligencia artificial generativa, diseñado para el análisis crítico de normativa colombiana. Utiliza una arquitectura de **Agente Autónomo** con patrones **CRAG** (Corrective RAG) y **Self-RAG** para garantizar la precisión jurídica y eliminar alucinaciones.

---

## 🏗️ Arquitectura Sistémica y Patrones Agénticos

El sistema no es un simple chat con documentos; es un **Agente Autónomo Orquestado** que implementa flujos de razonamiento cíclico para garantizar la veracidad de la información legal.

### 🧠 Patrones de Diseño Utilizados
1.  **CRAG (Corrective Retrieval-Augmented Generation):** El agente evalúa la calidad de los documentos recuperados. Si detecta que la información es irrelevante o de baja confianza, activa un proceso de corrección para evitar contaminar la respuesta final.
2.  **Self-RAG (Self-Reflective RAG):** El sistema realiza una auto-evaluación post-generación. Verifica si la respuesta tiene sustento literal en el documento y si realmente responde a la pregunta del usuario, mitigando alucinaciones en 99%.
3.  **Two-Step Reading (Rethinking):** El agente realiza dos lecturas del contexto: primero extrae pasajes clave y datos técnicos, luego genera la respuesta final citando fuentes.

### 🧬 Algoritmos y Métodos
*   **Búsqueda Híbrida (Hybrid Search):** Combina búsqueda semántica (vectores) con búsqueda por palabras clave (BM25) + reranking con FlashRank para localizar artículos específicos por su numeración exacta.
*   **Recursive Character Chunking:** Fragmentación que respeta la estructura de párrafos y oraciones legales, con separadores jerárquicos (`ARTÍCULO`, `CAPÍTULO`, `SECCIÓN`).
*   **Contextual Header Injection:** Cada fragmento incluye metadata enriquecida: `[Documento: X | Art. Y | Página: Z]`.
*   **Cosine Similarity:** Medición de cercanía conceptual en un espacio vectorial de 1024 dimensiones (Amazon Titan v2).

### 🛠️ Stack Tecnológico
*   **LangGraph:** Orquestador de estados para grafos cíclicos de razonamiento (ciclos de reflexión y corrección).
*   **AWS Bedrock:** Multi-modelo — Amazon Nova Lite (consultas), Llama 3.3 70B (análisis profundo), Nova Pro (juez evaluador).
*   **ChromaDB:** Base de datos vectorial persistente para memoria a largo plazo.
*   **PyMuPDF + Docling:** Motores de extracción PDF. Docling (IBM Research, open source) preserva tablas complejas y columnas múltiples.
*   **FlashRank:** Reranker local cross-encoder para máxima precisión en retrieval.

---

## 🚀 Guía de Instalación Rápida

Sigue estos pasos para configurar el entorno de desarrollo en tu máquina local (**Windows**).

### 1. Clonar y Preparar el Directorio
```powershell
git clone https://github.com/RACPSC2025/legal-rag-analyst.git
cd legal-rag-analyst
```

### 2. Crear y Activar el Entorno Virtual
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Instalación de Dependencias
```powershell
pip install -r requirements.txt
```

### 4. Configuración de Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto:
```env
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_SESSION_TOKEN=tu_session_token    # Si usas credenciales temporales
AWS_REGION=us-east-2
AWS_MODEL_SIMPLE_TEXT=us.amazon.nova-lite-v1:0
AWS_MODEL_LARGE_CONTEXT=us.amazon.nova-pro-v1:0
AWS_MODEL_DEEP_ANALYSIS=us.meta.llama3-3-70b-instruct-v1:0
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=2048
TOP_K_DOCS=4
CHUNK_SIZE=1500
CHUNK_OVERLAP=300
DATA_STORAGE_PATH=./storage/
```

> **Nota:** Si no tienes `AWS_SESSION_TOKEN`, déjalo vacío. El sistema lo detecta automáticamente.

---

## 🛠️ Guía Técnica de Ejecución

### Ejecutar la Aplicación
```powershell
streamlit run app.py
```

### Prueba de Conectividad (Diagnóstico)
```powershell
python src/tests/integration/test_aws_bedrock.py
```

### Ingesta Masiva desde CLI
```powershell
# Un solo PDF con PyMuPDF
python -m src.ingestion.ingest_pipeline --paths data/input/decreto.pdf --loader pymupdf

# Directorio completo con Docling (tablas complejas)
python -m src.ingestion.ingest_pipeline --paths data/input/ --loader docling

# Con OCR activado (PDFs escaneados)
python -m src.ingestion.ingest_pipeline --paths data/input/ --loader docling --ocr
```

### Evaluación del Sistema (RAG Health)
```powershell
python -m src.tests.evaluation.evaluate_rag_health
```

---

## 📖 Estructura del Proyecto

```
Rag_Analista_Legal/
├── app.py                          # Streamlit UI — punto de entrada
├── requirements.txt                # Dependencias
├── .env.example                    # Plantilla de variables
│
├── src/
│   ├── config.py                   # Configuración central + factories LLM/Embeddings
│   │
│   ├── core/                       # Motor LangGraph (CRAG + Self-RAG)
│   │   ├── state.py                # RagState (Pydantic)
│   │   ├── nodes.py                # 5 nodos: retrieve, grade, generate, hallucination, no_answer
│   │   └── graph.py                # StateGraph compilation + singleton
│   │
│   ├── ingestion/                  # Pipeline de carga de PDFs
│   │   ├── base.py                 # Contrato abstracto
│   │   ├── factory.py              # Factory (PyMuPDF / Docling / LlamaParse)
│   │   ├── pdf_simple.py           # PyMuPDF con chunking legal jerárquico
│   │   ├── pdf_docling.py          # Docling → Markdown (tablas complejas)
│   │   ├── pdf_llamaparse.py       # LlamaParse (pago, producción)
│   │   └── ingest_pipeline.py      # Pipeline CLI: PDF → ChromaDB
│   │
│   ├── retrieval/                  # Motor de búsqueda
│   │   ├── __init__.py             # Singleton ChromaDB + reset_vector_store
│   │   ├── hybrid_search.py        # FenixHybridRetriever (BM25 + Vector + FlashRank)
│   │   └── hierarchical_retriever.py # Two-level: summaries → detailed chunks
│   │
│   ├── services/                   # Servicios especializados
│   │   ├── pdf_direct_service.py   # Consulta directa sin vector store
│   │   └── specialized_analysis.py # Análisis crítico en formato JSON
│   │
│   └── tests/                      # Suite de pruebas
│       ├── unit/                   # Tests unitarios
│       ├── integration/            # Tests de integración (AWS Bedrock)
│       └── evaluation/             # Scripts de evaluación RAG
│
├── storage/                        # ChromaDB persistente + cache de modelos
├── session_pdfs/                   # PDFs de sesión (Mesa de Trabajo)
├── temp_uploads/                   # Temporales de ingesta
└── data/input/                     # Documentos base para ingestar
```

---

## 📊 Modos de Operación

### 📚 Modo Biblioteca (RAG Permanente)
Consulta sobre documentos indexados en ChromaDB que persisten entre sesiones. Ideal para normativa base: Decreto 1072, Código Sustantivo del Trabajo, Código General del Proceso.

### 📑 Modo Mesa de Trabajo (Análisis Temporal)
Analiza documentos sin indexarlos permanentemente. Ideal para casos confidenciales, sentencias específicas o contratos de un solo uso.

### 🔬 Análisis Crítico (JSON)
Genera un análisis jurídico estructurado con: obligaciones críticas, plazos, niveles de coerción, ambigüedades, entidades afectadas y referencias cruzadas.

---

## 🛡️ Prevención de Alucinaciones

El sistema implementa 3 capas de verificación:

1.  **Grading pre-retrieval:** El LLM evalúa la relevancia de cada documento recuperado antes de usarlo.
2.  **Two-Step Reading:** Primera lectura para extraer pasajes clave, segunda lectura para generar respuesta citando fuentes.
3.  **Hallucination Check:** Verificador post-generación que compara la respuesta contra los documentos fuente. Si detecta invención, reintenta (máx. 2 intentos).

---

*Nota Legal: Este sistema es una herramienta de apoyo y no sustituye el criterio de un profesional del derecho. Desarrollado bajo los principios de precisión y transparencia informativa.*
