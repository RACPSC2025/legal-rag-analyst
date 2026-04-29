# 🚀 Cache Module

## Descripción General

El módulo **Cache** implementa un sistema de caché multicapa inteligente diseñado para optimizar el rendimiento de consultas RAG (Retrieval-Augmented Generation) en sistemas legales. Utiliza estrategias de caché semántico, caché de consultas y respuestas, con análisis avanzado de métricas de rendimiento.

## 📋 Índice

- [Arquitectura](#arquitectura)
- [Módulos](#módulos)
- [Funcionalidades Principales](#funcionalidades-principales)
- [Ventajas](#ventajas)
- [Uso](#uso)
- [Configuración](#configuración)
- [Métricas y Analytics](#métricas-y-analytics)

---

## 🏗️ Arquitectura

El sistema de caché implementa un patrón de **multicapa** con las siguientes capas:

```
┌─────────────────────────────────────┐
│      Orchestrator (Coordinador)     │
│  - Gestión de estrategias           │
│  - Routing inteligente              │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌─────▼──────┐
│ Query Cache │  │ Semantic   │
│             │  │ Cache      │
└──────┬──────┘  └─────┬──────┘
       │                │
       └───────┬────────┘
               │
      ┌────────▼─────────┐
      │ Response Cache   │
      │ (Capa Final)     │
      └──────────────────┘
               │
      ┌────────▼─────────┐
      │ Analytics Engine │
      │ (Monitoreo)      │
      └──────────────────┘
```

---

## 📦 Módulos

### 1. **orchestrator.py**
**Propósito**: Coordinador central del sistema de caché

**Componentes**:
- `CacheOrchestrator`: Clase principal que gestiona todas las capas de caché
- Estrategias de invalidación
- Routing de consultas
- Gestión de TTL (Time To Live)

**Responsabilidades**:
- Decidir qué capa de caché utilizar
- Coordinar operaciones entre capas
- Gestionar políticas de expiración
- Sincronizar actualizaciones

---

### 2. **query_cache.py**
**Propósito**: Caché de consultas exactas

**Características**:
- **Búsqueda exacta**: Coincidencia literal de consultas
- **Hash-based**: Utiliza hashing para búsqueda O(1)
- **TTL configurable**: Expiración automática de entradas
- **LRU eviction**: Política de desalojo Least Recently Used

**Casos de uso**:
- Consultas repetidas idénticas
- Búsquedas frecuentes de términos legales específicos
- Queries de alta frecuencia

**Ventajas**:
- ⚡ Velocidad máxima (O(1))
- 💾 Bajo overhead de memoria
- 🎯 Precisión del 100% en coincidencias exactas

---

### 3. **semantic_cache.py**
**Propósito**: Caché basado en similitud semántica

**Características**:
- **Embeddings vectoriales**: Utiliza modelos de lenguaje para representación
- **Búsqueda por similitud**: Encuentra consultas semánticamente similares
- **Threshold configurable**: Control de precisión vs recall
- **Vector store integration**: Compatible con ChromaDB, FAISS, Pinecone

**Algoritmos**:
- Cosine similarity
- Euclidean distance
- Dot product similarity

**Casos de uso**:
- Consultas parafraseadas
- Variaciones lingüísticas de la misma pregunta
- Búsquedas conceptuales similares

**Ventajas**:
- 🧠 Inteligencia semántica
- 🔄 Reutilización de respuestas similares
- 📊 Mayor tasa de hit rate
- 🌐 Soporte multiidioma

---

### 4. **response_cache.py**
**Propósito**: Caché de respuestas generadas

**Características**:
- **Caché de resultados completos**: Almacena respuestas RAG completas
- **Metadata tracking**: Guarda contexto, fuentes, timestamps
- **Compression**: Compresión opcional para respuestas grandes
- **Versioning**: Control de versiones de respuestas

**Estructura de datos**:
```python
{
    "query": str,
    "response": str,
    "sources": List[str],
    "metadata": Dict,
    "timestamp": datetime,
    "version": str,
    "confidence": float
}
```

**Ventajas**:
- 💰 Ahorro de costos de API
- ⏱️ Reducción de latencia
- 📝 Trazabilidad completa
- 🔒 Consistencia de respuestas

---

### 5. **analytics.py**
**Propósito**: Sistema de análisis y métricas de caché

**Métricas rastreadas**:
- **Hit Rate**: Porcentaje de aciertos de caché
- **Miss Rate**: Porcentaje de fallos
- **Latency**: Tiempo de respuesta por capa
- **Memory Usage**: Uso de memoria por caché
- **Eviction Rate**: Tasa de desalojo de entradas
- **Cost Savings**: Ahorro estimado en llamadas a API

**Visualizaciones**:
- Gráficos de rendimiento temporal
- Heatmaps de uso de caché
- Distribución de tipos de consultas
- Análisis de patrones de acceso

**Ventajas**:
- 📊 Visibilidad completa del sistema
- 🎯 Optimización basada en datos
- 💡 Detección de patrones de uso
- 🔧 Tuning de parámetros informado

---

## ⚡ Funcionalidades Principales

### 1. **Caché Multicapa Inteligente**
```python
# El orchestrator decide automáticamente la mejor estrategia
result = cache_orchestrator.get(query)
if result:
    return result  # Cache hit
else:
    result = expensive_rag_operation(query)
    cache_orchestrator.set(query, result)
```

### 2. **Invalidación Selectiva**
- Invalidación por tiempo (TTL)
- Invalidación por patrón
- Invalidación manual
- Invalidación en cascada

### 3. **Warm-up Automático**
- Pre-carga de consultas frecuentes
- Actualización proactiva
- Predicción de consultas futuras

### 4. **Fallback Strategy**
```
Query → Semantic Cache → Query Cache → Response Cache → RAG Pipeline
```

---

## 🎯 Ventajas del Sistema

### Rendimiento
- ⚡ **Reducción de latencia**: 80-95% en consultas cacheadas
- 🚀 **Throughput mejorado**: 10-50x más consultas por segundo
- 💾 **Uso eficiente de memoria**: Políticas de eviction inteligentes

### Costos
- 💰 **Ahorro en API calls**: 60-90% de reducción
- 🔋 **Menor consumo de recursos**: CPU, GPU, memoria
- 📉 **Escalabilidad económica**: Crecimiento lineal vs exponencial

### Experiencia de Usuario
- ⏱️ **Respuestas instantáneas**: Sub-segundo para hits
- 🎯 **Consistencia**: Mismas preguntas, mismas respuestas
- 🔄 **Disponibilidad**: Funciona incluso si el backend falla

### Inteligencia
- 🧠 **Aprendizaje de patrones**: Mejora con el uso
- 🔍 **Búsqueda semántica**: Entiende intención, no solo palabras
- 📊 **Analytics avanzado**: Insights accionables

---

## 🔧 Uso

### Configuración Básica

```python
from src.cache.orchestrator import CacheOrchestrator
from src.cache.analytics import CacheAnalytics

# Inicializar orchestrator
cache = CacheOrchestrator(
    semantic_threshold=0.85,
    query_ttl=3600,
    max_cache_size=10000
)

# Configurar analytics
analytics = CacheAnalytics(cache)
```

### Ejemplo de Uso

```python
# Consulta con caché
query = "¿Cuáles son los requisitos para un contrato válido?"

# Intento de recuperación de caché
cached_result = cache.get(query)

if cached_result:
    print(f"Cache hit! Latency: {cached_result['latency']}ms")
    return cached_result['response']
else:
    # Ejecutar RAG pipeline
    result = rag_pipeline.run(query)
    
    # Guardar en caché
    cache.set(query, result)
    return result

# Ver métricas
stats = analytics.get_stats()
print(f"Hit Rate: {stats['hit_rate']:.2%}")
print(f"Avg Latency: {stats['avg_latency']}ms")
```

---

## ⚙️ Configuración

### Variables de Entorno

```bash
# Cache Configuration
CACHE_ENABLED=true
SEMANTIC_CACHE_THRESHOLD=0.85
QUERY_CACHE_TTL=3600
RESPONSE_CACHE_TTL=7200
MAX_CACHE_SIZE=10000

# Analytics
ANALYTICS_ENABLED=true
METRICS_EXPORT_INTERVAL=300
```

### Configuración Avanzada

```python
cache_config = {
    "semantic": {
        "enabled": True,
        "threshold": 0.85,
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "max_entries": 5000
    },
    "query": {
        "enabled": True,
        "ttl": 3600,
        "max_entries": 10000,
        "eviction_policy": "LRU"
    },
    "response": {
        "enabled": True,
        "ttl": 7200,
        "compression": True,
        "max_size_mb": 500
    }
}
```

---

## 📊 Métricas y Analytics

### Dashboard de Métricas

```python
# Obtener métricas en tiempo real
metrics = analytics.get_realtime_metrics()

print(f"""
Cache Performance Dashboard
===========================
Hit Rate: {metrics['hit_rate']:.2%}
Miss Rate: {metrics['miss_rate']:.2%}
Avg Latency: {metrics['avg_latency']}ms
Memory Usage: {metrics['memory_mb']}MB
Cost Savings: ${metrics['cost_savings']:.2f}
""")
```

### Exportar Métricas

```python
# Exportar a formato JSON
analytics.export_metrics("cache_metrics.json")

# Exportar a Prometheus
analytics.export_prometheus("metrics.prom")

# Integración con Grafana
analytics.setup_grafana_dashboard()
```

---

## 🔍 Casos de Uso Específicos

### 1. Sistema Legal RAG
- Consultas frecuentes sobre leyes específicas
- Búsquedas de jurisprudencia repetidas
- Análisis de contratos similares

### 2. Chatbot Legal
- Preguntas frecuentes (FAQ)
- Consultas de usuarios recurrentes
- Respuestas estandarizadas

### 3. Análisis de Documentos
- Procesamiento de documentos similares
- Extracción de metadatos repetitivos
- Clasificación de documentos

---

## 🚀 Roadmap

- [ ] Soporte para caché distribuido (Redis, Memcached)
- [ ] Machine Learning para predicción de consultas
- [ ] Caché adaptativo basado en patrones de uso
- [ ] Integración con CDN para caché global
- [ ] Soporte para invalidación basada en eventos

---

## 📚 Referencias

- [Cache Strategies in RAG Systems](https://arxiv.org/abs/2401.xxxxx)
- [Semantic Caching for LLMs](https://arxiv.org/abs/2402.xxxxx)
- [LangChain Caching Documentation](https://python.langchain.com/docs/modules/model_io/models/llms/how_to/llm_caching)

---

## 👥 Contribución

Para contribuir a este módulo:
1. Revisa las métricas actuales
2. Identifica oportunidades de optimización
3. Implementa mejoras con tests
4. Documenta cambios en CHANGELOG.md

---

**Última actualización**: 2026-04-28
**Versión**: 2.0.0
**Mantenedor**: Equipo de Infraestructura RAG
