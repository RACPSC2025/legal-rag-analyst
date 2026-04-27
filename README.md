# ⚖️ Fénix Legal v2.5 — Analista Jurídico Experto

Asistente legal autónomo de **Grado Industrial**, diseñado para el análisis crítico de normativa colombiana. Utiliza una arquitectura de **Agente Autónomo** con patrones **CRAG**, **Self-RAG** y un sistema de **Caché de 4 Capas** para máxima velocidad y eficiencia de costos.

---

## 🏗️ Arquitectura Sistémica Avanzada

El sistema ha evolucionado de un RAG simple a un **Cortex Agéntico** orquestado:

### 🧠 Capacidades de Inteligencia (Model Hub)
*   **Enrutamiento Dinámico**: El sistema elige el modelo de AWS Bedrock óptimo para cada tarea (ej: *Nova Lite* para clasificar, *Llama 3.3 70B* para análisis profundo).
*   **Blindaje contra Alucinaciones**: Doble capa de verificación (Hallucination Check + Citation Verifier) para certificar que cada palabra tiene sustento legal.
*   **Compresión Contextual**: Reduce el ruido de los documentos en un 40-60%, enviando solo lo relevante al LLM.

### ⚡ Sistema de Caché de 4 Capas (Cost Optimization)
1.  **L1 (Exact)**: Match idéntico por hash SHA256.
2.  **L2 (Normalized)**: Match semántico-lingüístico (ignora tildes, mayúsculas y puntuación).
3.  **L3 (Semantic)**: Búsqueda vectorial en ChromaDB (detecta intención similar con umbral >90%).
4.  **L0 (Prompt Cache)**: Optimización nativa a través de Bedrock Inference Profiles.

---

## 🚀 Guía de Instalación y Uso

### 1. Preparación del Entorno (Windows)
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Centro de Comando de Pruebas (TUI)
Hemos unificado todas las validaciones en un orquestador interactivo:
```powershell
python tests/run_tests.py
```
*Desde este menú puedes ejecutar pruebas unitarias, de integración y evaluación.*

### 3. Ejecución de la Interfaz (Streamlit)
```powershell
streamlit run app.py
```

---

## 📖 Estructura del Proyecto (Modular v2.5)

```
Rag_Analista_Legal/
├── app.py                # Interfaz de usuario (Streamlit)
├── tests/                # Centro de Pruebas Unificado (Core Testing)
│   ├── unit/             # Componentes aislados
│   ├── integration/      # AWS Bedrock & ChromaDB
│   ├── evaluation/       # Métricas RAGAS
│   └── run_tests.py      # Orquestador TUI
├── src/
│   ├── cache/            # Sistema de Caché de 4 Capas (L1-L3)
│   ├── model_hub/        # Selector dinámico de modelos
│   ├── core/             # Grafo LangGraph (CRAG + Self-RAG)
│   ├── retrieval/        # Hybrid Search & Contextual Compression
│   ├── services/         # Citation Verifier & Specialized Analysis
│   └── schemas/          # Modelos Pydantic centralizados
├── storage/              # Persistencia de Vectores y Caché
└── data/                 # Insumos normativos (PDFs)
```

---

## 🔬 Prevención de Alucinaciones y Citas
El sistema implementa el **CitationVerifier**, un servicio que garantiza que cada artículo citado en la respuesta realmente existe en el texto fuente, verificando su integridad antes de mostrarlo al usuario.

*Nota Legal: Este sistema es una herramienta de apoyo y no sustituye el criterio de un profesional del derecho.*
