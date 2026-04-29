# 🏗️ Source Code Architecture

## Descripción General

Este directorio contiene el código fuente completo del sistema **RAG Legal Colombiano**, un sistema de recuperación y generación aumentada especializado en normativa legal. La arquitectura está diseñada siguiendo principios de **modularidad**, **escalabilidad** y **mantenibilidad**.

## 📋 Índice

- [Estructura de Módulos](#estructura-de-módulos)
- [Arquitectura General](#arquitectura-general)
- [Flujo de Datos](#flujo-de-datos)
- [Principios de Diseño](#principios-de-diseño)
- [Guía de Navegación](#guía-de-navegación)

---

## 📦 Estructura de Módulos

```
src/
├── cache/              # Sistema de caché multicapa
├── config/             # Configuración y logging
├── core/               # Grafo RAG (LangGraph)
├── data/               # Datos y modelos
├── ingestion/          # Pipeline de ingestión
├── model_hub/          # Gestión de modelos LLM
├── retrieval/          # Técnicas de recuperación
├── schemas/            # Modelos de datos (Pydantic)
├── services/           # Servicios especializados
├── storage/            # Almacenamiento (ChromaDB)
└── utils/              # Utilidades comunes
```

---

## 🏗️ Arquitectura General

### Capas de la Aplicación

```
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER                               │
│                   (FastAPI / Streamlit)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    CORE LAYER                                │
│              (LangGraph State Machine)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Retrieve │→ │  Grade   │→ │ Generate │→ │  Verify  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  RETRIEVAL LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Query        │→ │ Hybrid       │→ │ Contextual   │      │
│  │ Expansion    │  │ Search       │  │ Compression  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   STORAGE LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Vector Store │  │ Cache        │  │ Golden MD    │      │
│  │ (ChromaDB)   │  │ (Semantic)   │  │ Library      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Datos

### 1. Ingestión de Documentos

```
PDF → Quality Detection → Loader Selection → Golden MD Conversion
  → Text Cleaning → Adaptive Chunking → Metadata Extraction
  → Vector Indexing → ChromaDB Storage
```

**Módulos involucrados**: `ingestion`, `services`, `storage`

---

### 2. Procesamiento de Consultas

```
User Query → Query Expansion (HyDE + Multi-Query)
  → Hybrid Search (BM25 + Vector + RRF)
  → FlashRank Reranking
  → Contextual Compression
  → Document Grading (CRAG)
  → Response Generation
  → Hallucination Check (Self-RAG)
  → Citation Verification
  → Final Response
```

**Módulos involucrados**: `core`, `retrieval`, `cache`, `services`

---

## 🎯 Principios de Diseño

### 1. **Modularidad**
Cada módulo tiene una responsabilidad única y bien definida:
- `core`: Orquestación del flujo RAG
- `retrieval`: Técnicas de recuperación
- `ingestion`: Procesamiento de documentos
- `cache`: Optimización de performance
- `services`: Funcionalidades especializadas

### 2. **Separación de Concerns**
- **Lógica de negocio**: En `core` y `services`
- **Acceso a datos**: En `storage` y `retrieval`
- **Configuración**: En `config`
- **Modelos de datos**: En `schemas`

### 3. **Dependency Injection**
```python
# Malo: Dependencias hardcodeadas
def retrieve(query):
    vector_store = ChromaDB(...)  # ❌ Acoplamiento fuerte
    
# Bueno: Inyección de dependencias
def retrieve(query, vector_store):  # ✅ Desacoplado
    ...
```

### 4. **Fail-Safe Design**
Cada componente tiene fallbacks:
- Query Expansion falla → Usa query original
- LLM Compression falla → Usa sentence-level
- Cache falla → Ejecuta operación normal
- Reranking falla → Usa RRF puro

### 5. **Observable by Default**
Logging estructurado en cada paso:
```python
logger.info(
    "Query processed",
    extra={
        "query": query,
        "latency_ms": latency,
        "cache_hit": cache_hit,
        "docs_retrieved": len(docs)
    }
)
```

---

## 📚 Guía de Navegación

### Para Desarrolladores Nuevos

**Comienza aquí**:
1. `config/` - Entiende la configuración del sistema
2. `schemas/` - Conoce los modelos de datos
3. `core/` - Comprende el flujo principal
4. `retrieval/` - Aprende las técnicas de búsqueda

### Para Agregar Funcionalidades

**Según el tipo de feature**:
- **Nueva técnica de retrieval** → `retrieval/`
- **Nuevo tipo de documento** → `ingestion/loaders/`
- **Nuevo procesador** → `ingestion/processors/`
- **Nuevo servicio** → `services/`
- **Nueva validación** → `schemas/`

### Para Debugging

**Puntos de entrada**:
1. `core/graph.py` - Punto de entrada principal
2. `core/nodes.py` - Lógica de cada nodo
3. `config/logging.py` - Configuración de logs
4. `cache/analytics.py` - Métricas de performance

---

## 📖 Documentación por Módulo

Cada módulo tiene su propio README detallado:

### Core Modules
- [📋 cache/README.md](cache/README.md) - Sistema de caché multicapa
- [⚙️ config/README.md](config/README.md) - Configuración y logging
- [🧠 core/README.md](core/README.md) - Grafo RAG y nodos

### Data Processing
- [📥 ingestion/README.md](ingestion/README.md) - Pipeline de ingestión
- [🔍 retrieval/README.md](retrieval/README.md) - Técnicas de recuperación

### Infrastructure
- [🤖 model_hub/README.md](model_hub/README.md) - Gestión de modelos
- [📋 schemas/README.md](schemas/README.md) - Modelos de datos
- [🛠️ services/README.md](services/README.md) - Servicios especializados
- [🔧 utils/README.md](utils/README.md) - Utilidades comunes

---

## 🚀 Quick Start

### Ejecutar una Consulta

```python
from src.core.graph import query

# Consulta simple
result = query("¿Cuáles son los requisitos del artículo 2.2.2.4.11?")

print(result["answer"])
print(f"Fuentes: {result['source_docs']}")
print(f"Confiabilidad: {1 - result['hallucination_score']:.1%}")
```

### Ingestar Documentos

```python
from src.ingestion.pipeline import run_ingestion_pipeline

# Procesar directorio de PDFs
result = run_ingestion_pipeline(
    paths=["data/raw/decretos/"],
    force_reconvert=False
)

print(f"Procesados: {len(result['processed_files'])}")
print(f"Chunks indexados: {result['indexed_chunks']}")
```

### Configurar Sistema

```python
from src.config import get_settings

settings = get_settings()

# Modificar configuración
settings.LLM_TEMPERATURE = 0.5
settings.TOP_K_RESULTS = 10
```

---

## 🧪 Testing

### Estructura de Tests

```
tests/
├── unit/               # Tests unitarios por módulo
│   ├── test_cache.py
│   ├── test_retrieval.py
│   └── ...
├── integration/        # Tests de integración
│   ├── test_pipeline.py
│   └── test_graph.py
└── e2e/               # Tests end-to-end
    └── test_full_flow.py
```

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Tests de un módulo específico
pytest tests/unit/test_retrieval.py

# Tests con coverage
pytest --cov=src --cov-report=html
```

---

## 📊 Métricas y Monitoreo

### Métricas Clave

```python
from src.cache.analytics import get_cache_stats
from src.retrieval import get_retrieval_metrics

# Métricas de caché
cache_stats = get_cache_stats()
print(f"Hit Rate: {cache_stats['hit_rate']:.2%}")

# Métricas de retrieval
retrieval_metrics = get_retrieval_metrics()
print(f"Avg Latency: {retrieval_metrics['avg_latency_ms']}ms")
```

### Logging

```python
import logging
from src.config.logging import setup_logging

# Configurar logging
setup_logging(level="INFO", format="json")

logger = logging.getLogger(__name__)
logger.info("Sistema iniciado", extra={"version": "2.0.0"})
```

---

## 🔒 Seguridad

### Mejores Prácticas

1. **Nunca hardcodear credenciales**: Usar variables de entorno
2. **Validar inputs**: Usar Pydantic para validación
3. **Sanitizar outputs**: Prevenir inyección de código
4. **Rate limiting**: Controlar llamadas a APIs
5. **Logging seguro**: No loggear datos sensibles

### Gestión de Secretos

```python
from src.config import get_settings

settings = get_settings()

# ✅ Bueno: Desde variables de entorno
api_key = settings.OPENAI_API_KEY

# ❌ Malo: Hardcodeado
api_key = "sk-..."  # NUNCA hacer esto
```

---

## 🚀 Roadmap

### Próximas Funcionalidades

- [ ] Soporte para más tipos de documentos (DOCX, HTML)
- [ ] Memoria conversacional
- [ ] Multi-hop reasoning
- [ ] Fine-tuning de modelos
- [ ] Dashboard de analytics
- [ ] API REST completa
- [ ] Deployment en cloud (AWS, Azure, GCP)

---

## 📚 Referencias

### Papers Implementados
- [CRAG: Corrective RAG](https://arxiv.org/abs/2401.15884)
- [Self-RAG](https://arxiv.org/abs/2310.11511)
- [HyDE](https://arxiv.org/abs/2212.10496)
- [RRF](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)

### Frameworks Utilizados
- [LangChain](https://python.langchain.com/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [ChromaDB](https://www.trychroma.com/)
- [Pydantic](https://docs.pydantic.dev/)

---

## 👥 Contribución

### Cómo Contribuir

1. **Fork** el repositorio
2. **Crea** una rama para tu feature (`git checkout -b feature/amazing-feature`)
3. **Commit** tus cambios (`git commit -m 'Add amazing feature'`)
4. **Push** a la rama (`git push origin feature/amazing-feature`)
5. **Abre** un Pull Request

### Estándares de Código

- **PEP 8**: Seguir guía de estilo de Python
- **Type hints**: Siempre especificar tipos
- **Docstrings**: Documentar todas las funciones públicas
- **Tests**: Agregar tests para nuevas funcionalidades
- **Logging**: Usar logging estructurado

---

## 📞 Soporte

Para preguntas o issues:
- **Issues**: GitHub Issues
- **Documentación**: Ver READMEs de cada módulo
- **Email**: [tu-email@ejemplo.com]

---

**Última actualización**: 2026-04-28  
**Versión**: 2.0.0  
**Mantenedor**: Equipo RAG Legal  
**Licencia**: MIT
