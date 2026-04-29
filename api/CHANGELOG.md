# 📝 Changelog — API REST RAG Legal Colombiano

Registro de cambios y versiones de la API.

---

## [1.0.0] - 2026-04-27

### 🎉 Lanzamiento Inicial

Primera versión completa de la API REST para el sistema RAG Analista Legal.

### ✨ Características Implementadas

#### Core API
- **FastAPI Application** con lifespan events para inicialización de componentes
- **CORS Middleware** configurado para frontend React/Vue
- **Documentación Automática** con Swagger UI (`/docs`) y ReDoc (`/redoc`)
- **OpenAPI Schema** generado automáticamente

#### Endpoints

**Query (Consultas RAG)**
- `POST /api/v1/query` - Consulta individual con caché integrado
- `POST /api/v1/query/batch` - Procesamiento de múltiples consultas
- `POST /api/v1/query/stream` - Streaming de respuestas con SSE
- `GET /api/v1/query/history` - Historial de consultas (placeholder)

**Ingestion (Ingesta de Documentos)**
- `POST /api/v1/ingestion` - Iniciar job de ingesta asíncrono
- `GET /api/v1/ingestion/status/{job_id}` - Consultar estado de job
- `GET /api/v1/ingestion/jobs` - Listar jobs recientes

**Cache (Gestión de Caché)**
- `GET /api/v1/cache/stats` - Estadísticas del sistema de caché
- `POST /api/v1/cache/clear` - Limpiar caché (requiere confirmación)
- `GET /api/v1/cache/info` - Información de configuración

**Health (Monitoreo)**
- `GET /health` - Health check general del sistema
- `GET /health/ready` - Readiness probe para Kubernetes
- `GET /health/live` - Liveness probe para Kubernetes
- `GET /health/metrics` - Métricas del sistema

#### Schemas Pydantic

**Request Models**
- `QueryRequest` - Validación de consultas RAG
- `BatchQueryRequest` - Validación de consultas en batch
- `IngestionRequest` - Validación de ingesta de documentos
- `CacheClearRequest` - Validación de limpieza de caché
- `FeedbackRequest` - Validación de feedback de usuarios

**Response Models**
- `QueryResponse` - Respuesta estándar con citas verificadas
- `BatchQueryResponse` - Respuesta de batch con estadísticas
- `IngestionResponse` - Respuesta de ingesta con job tracking
- `CacheStatsResponse` - Estadísticas de caché
- `HealthResponse` - Health check con componentes
- `ErrorResponse` - Formato estándar de errores
- `CitationResponse` - Citas verificadas en respuestas

#### Middleware

**Error Handler**
- Manejo global de excepciones con formato estándar
- Request ID para trazabilidad completa
- Logging detallado de errores
- Modo desarrollo vs producción (exposición de detalles)

**Logging Middleware**
- Logging automático de requests y responses
- Métricas de latencia por request
- Detección de requests lentos (> 5s)
- Skip de rutas de health checks

#### Características Técnicas

- **Validación Automática** con Pydantic v2
- **Background Tasks** para ingesta asíncrona
- **Server-Sent Events** para streaming
- **Request ID** en todos los logs y responses
- **Error Handling** robusto con fallbacks
- **Type Hints** completos para IDE support
- **Docstrings** detallados en todos los endpoints

### 📚 Documentación

- **README.md** - Guía completa de uso de la API
- **requirements.txt** - Dependencias específicas de la API
- **.env.example** - Plantilla de configuración
- **test_api.py** - Script de pruebas de endpoints
- **CHANGELOG.md** - Este archivo

### 🏗️ Arquitectura

```
api/
├── main.py                      # Aplicación FastAPI principal
├── routes/                      # Endpoints por dominio
│   ├── query.py                 # Consultas RAG
│   ├── ingestion.py             # Ingesta de documentos
│   ├── health.py                # Health checks
│   └── cache.py                 # Gestión de caché
├── schemas/                     # Modelos Pydantic
│   ├── request_models.py        # Validación de entrada
│   └── response_models.py       # Serialización de salida
├── middleware/                  # Middlewares personalizados
│   ├── error_handler.py         # Manejo de errores
│   └── logging_middleware.py   # Logging de requests
└── requirements.txt             # Dependencias
```

### 🔧 Dependencias Principales

- `fastapi==0.115.0` - Framework web
- `uvicorn==0.32.0` - ASGI server
- `pydantic==2.9.2` - Validación de datos
- `sse-starlette==2.1.3` - Server-Sent Events
- `httpx==0.27.2` - Cliente HTTP para testing

### 🚀 Deployment

**Desarrollo**
```bash
python api/main.py
# o
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Producción**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Docker**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r api/requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 📊 Métricas

- **Endpoints Totales**: 15
- **Request Models**: 5
- **Response Models**: 8
- **Middleware**: 3
- **Líneas de Código**: ~1500
- **Cobertura de Tests**: Pendiente

### 🎯 Próximos Pasos

- [ ] Suite de tests unitarios y de integración
- [ ] Autenticación JWT o OAuth2
- [ ] Rate limiting para prevenir abuso
- [ ] Integración con Prometheus para métricas
- [ ] Frontend React/Vue consumiendo la API
- [ ] WebSockets para streaming bidireccional
- [ ] CI/CD pipeline automatizado

### 🤝 Contribuidores

- **Fenix Tech Líder** - Diseño e implementación completa

---

## Formato de Versiones

Este proyecto sigue [Semantic Versioning](https://semver.org/):
- **MAJOR**: Cambios incompatibles en la API
- **MINOR**: Nueva funcionalidad compatible con versiones anteriores
- **PATCH**: Correcciones de bugs compatibles

---

*Changelog mantenido por Fenix Tech Líder — Calidad de Producción 2026.*
