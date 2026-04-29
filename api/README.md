# 🚀 API REST — RAG Legal Colombiano

API REST profesional para el sistema RAG Analista Legal. Proporciona endpoints para consultas, ingesta de documentos, gestión de caché y monitoreo de salud.

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Endpoints](#-endpoints)
- [Ejemplos](#-ejemplos)
- [Configuración](#-configuración)
- [Testing](#-testing)
- [Deployment](#-deployment)

---

## ✨ Características

- **RESTful API** con FastAPI y documentación OpenAPI automática
- **Validación automática** con Pydantic v2
- **Streaming de respuestas** con Server-Sent Events (SSE)
- **Sistema de caché** integrado (L1/L2/L3)
- **Health checks** para Kubernetes (readiness/liveness)
- **Error handling** global con formato estándar
- **Logging estructurado** con request ID para trazabilidad
- **CORS configurado** para frontend React/Vue
- **Background tasks** para ingesta asíncrona

---

## 🏗️ Arquitectura

```
api/
├── main.py                      # Aplicación FastAPI principal
├── routes/                      # Endpoints organizados por dominio
│   ├── query.py                 # Consultas RAG
│   ├── ingestion.py             # Ingesta de documentos
│   ├── health.py                # Health checks
│   └── cache.py                 # Gestión de caché
├── schemas/                     # Modelos Pydantic
│   ├── request_models.py        # Modelos de entrada
│   └── response_models.py       # Modelos de salida
├── middleware/                  # Middlewares personalizados
│   ├── error_handler.py         # Manejo global de errores
│   └── logging_middleware.py   # Logging de requests/responses
└── requirements.txt             # Dependencias de la API
```

### Principios de Diseño

- **SOLID**: Separación de responsabilidades, interfaces claras
- **DRY**: Reutilización de código, helpers compartidos
- **Fail-Safe**: Manejo robusto de errores con fallbacks
- **Observabilidad**: Logging detallado y métricas

---

## 📦 Instalación

### 1. Instalar Dependencias

```bash
# Desde la raíz del proyecto
pip install -r api/requirements.txt
```

### 2. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```bash
# AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# ChromaDB
STORAGE_PATH=./storage
COLLECTION_NAME=legal_docs

# API
ENVIRONMENT=development  # development | production
```

---

## 🚀 Uso

### Iniciar el Servidor

```bash
# Desarrollo (con hot reload)
python api/main.py

# O usando uvicorn directamente
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Producción

```bash
# Con múltiples workers
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Acceder a la Documentación

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## 📡 Endpoints

### 🔍 Query (Consultas RAG)

#### `POST /api/v1/query`
Realiza una consulta individual al sistema RAG.

**Request:**
```json
{
  "question": "¿Cuáles son los requisitos para una concesión de aguas?",
  "top_k": 10,
  "use_cache": true,
  "stream": false
}
```

**Response:**
```json
{
  "query_id": "q_20260427_143022_a1b2c3d4",
  "question": "¿Cuáles son los requisitos...",
  "answer": "Los requisitos para obtener una concesión de aguas son...",
  "sources": ["Decreto 1076 de 2015", "Artículo 2.2.3.2.9.1"],
  "citations": [
    {
      "article_id": "Art. 2.2.3.2.9.1",
      "source": "Decreto 1076 de 2015",
      "page": 45,
      "verified": true,
      "confidence": 0.95
    }
  ],
  "requirements": [
    {
      "description": "Presentar solicitud de concesión ante la autoridad ambiental",
      "deadline": "N/A",
      "responsible": "Interesado"
    }
  ],
  "confidence_score": 0.98,
  "metadata": {
    "attempts": 1,
    "grade": "útil",
    "hallucination_score": 0.0
  },
  "is_cached": false,
  "cache_layer": null,
  "timestamp": "2026-04-27T14:30:22Z"
}
```

#### `POST /api/v1/query/batch`
Procesa múltiples consultas en un solo request.

#### `POST /api/v1/query/stream`
Consulta con respuesta en streaming (SSE).

---

### 📥 Ingestion (Ingesta de Documentos)

#### `POST /api/v1/ingestion`
Inicia un job de ingesta de documentos.

**Request:**
```json
{
  "file_paths": [
    "data/input/decreto_1076.pdf",
    "data/input/ley_99.pdf"
  ],
  "force_reconvert": false,
  "collection_name": "legal_docs"
}
```

**Response:**
```json
{
  "job_id": "ing_20260427_143022_a1b2c3d4",
  "status": "queued",
  "processed_files": [],
  "failed_files": [],
  "total_chunks": 0,
  "indexed_chunks": 0,
  "errors": []
}
```

#### `GET /api/v1/ingestion/status/{job_id}`
Consulta el estado de un job de ingesta.

---

### 💾 Cache (Gestión de Caché)

#### `GET /api/v1/cache/stats`
Obtiene estadísticas del sistema de caché.

**Response:**
```json
{
  "total_requests": 1250,
  "total_hits": 875,
  "total_misses": 375,
  "hit_rate": "70.0%",
  "hits_by_layer": {
    "L1": 450,
    "L2": 325,
    "L3": 100
  },
  "estimated_savings_usd": 13.13,
  "timestamp": "2026-04-27T14:30:22Z"
}
```

#### `POST /api/v1/cache/clear`
Limpia el sistema de caché (requiere confirmación).

---

### 🏥 Health (Monitoreo)

#### `GET /health`
Health check general del sistema.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "chromadb": "healthy",
    "model_hub": "healthy",
    "cache": "healthy"
  },
  "uptime_seconds": 3600.5,
  "timestamp": "2026-04-27T14:30:22Z"
}
```

#### `GET /health/ready`
Readiness probe para Kubernetes.

#### `GET /health/live`
Liveness probe para Kubernetes.

---

## 💡 Ejemplos

### Python (httpx)

```python
import httpx

# Consulta simple
response = httpx.post(
    "http://localhost:8000/api/v1/query",
    json={
        "question": "¿Qué es una licencia ambiental?",
        "top_k": 10,
        "use_cache": True
    }
)

result = response.json()
print(result["answer"])
```

### cURL

```bash
# Consulta simple
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Qué es una licencia ambiental?",
    "top_k": 10,
    "use_cache": true
  }'

# Health check
curl "http://localhost:8000/health"

# Estadísticas de caché
curl "http://localhost:8000/api/v1/cache/stats"
```

### JavaScript (fetch)

```javascript
// Consulta simple
const response = await fetch('http://localhost:8000/api/v1/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    question: '¿Qué es una licencia ambiental?',
    top_k: 10,
    use_cache: true
  })
});

const result = await response.json();
console.log(result.answer);
```

### Streaming (SSE)

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/query/stream?question=¿Qué es una licencia ambiental?'
);

eventSource.addEventListener('chunk', (event) => {
  const data = JSON.parse(event.data);
  console.log(data.text);
});

eventSource.addEventListener('end', (event) => {
  console.log('Streaming completado');
  eventSource.close();
});
```

---

## ⚙️ Configuración

### CORS

Modificar en `api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React dev
        "https://mi-dominio.com",     # Producción
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Logging

Configurar nivel de logging en `api/middleware/logging_middleware.py`:

```python
logging.basicConfig(
    level=logging.INFO,  # DEBUG | INFO | WARNING | ERROR
    format=log_format,
)
```

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Tests unitarios
pytest api/tests/

# Tests con cobertura
pytest api/tests/ --cov=api --cov-report=html
```

### Test Manual con Swagger

1. Abrir http://localhost:8000/docs
2. Expandir endpoint deseado
3. Click en "Try it out"
4. Completar parámetros
5. Click en "Execute"

---

## 🚢 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copiar dependencias
COPY requirements.txt api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r api/requirements.txt

# Copiar código
COPY . .

# Exponer puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-legal-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-legal-api
  template:
    metadata:
      labels:
        app: rag-legal-api
    spec:
      containers:
      - name: api
        image: rag-legal-api:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: AWS_REGION
          value: "us-east-1"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

---

## 📚 Recursos Adicionales

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Uvicorn Docs**: https://www.uvicorn.org/

---

## 🤝 Contribución

Para contribuir a la API:

1. Seguir principios SOLID
2. Añadir docstrings completos
3. Validar con Pydantic
4. Añadir tests unitarios
5. Actualizar documentación

---

## 📝 Licencia

Proyecto interno — Codelatin + Freelance Ronny Camacho

---

*API REST diseñada y desarrollada por Fenix Tech Líder — Calidad de Producción 2026.*
