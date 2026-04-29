# ⚙️ Configuration Module

## Descripción General

El módulo **Config** centraliza toda la configuración del sistema RAG legal, incluyendo logging, variables de entorno, parámetros de modelos, y configuraciones de servicios externos. Implementa un patrón de configuración jerárquica con soporte para múltiples entornos (desarrollo, staging, producción).

## 📋 Índice

- [Arquitectura](#arquitectura)
- [Módulos](#módulos)
- [Funcionalidades Principales](#funcionalidades-principales)
- [Ventajas](#ventajas)
- [Uso](#uso)
- [Configuración por Entorno](#configuración-por-entorno)

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────┐
│     Configuration Manager           │
│  - Carga de variables               │
│  - Validación de configuración      │
│  - Gestión de secretos              │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌─────▼──────┐
│ Environment │  │ Logging    │
│ Variables   │  │ Config     │
└─────────────┘  └────────────┘
       │                │
       └───────┬────────┘
               │
      ┌────────▼─────────┐
      │ Validation Layer │
      │ (Pydantic)       │
      └──────────────────┘
```

---

## 📦 Módulos

### 1. **__init__.py**
**Propósito**: Punto de entrada y configuración central

**Componentes**:
- `Settings`: Clase principal de configuración usando Pydantic
- `get_settings()`: Factory function con singleton pattern
- Validación automática de tipos
- Carga de variables de entorno

**Estructura de Settings**:
```python
class Settings(BaseSettings):
    # API Configuration
    API_HOST: str
    API_PORT: int
    API_VERSION: str
    
    # Database
    DATABASE_URL: str
    VECTOR_STORE_TYPE: str
    
    # LLM Configuration
    LLM_PROVIDER: str
    LLM_MODEL: str
    LLM_TEMPERATURE: float
    LLM_MAX_TOKENS: int
    
    # RAG Configuration
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int
    TOP_K_RESULTS: int
    
    # Cache
    CACHE_ENABLED: bool
    CACHE_TTL: int
    
    # Security
    SECRET_KEY: str
    API_KEY: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

**Ventajas**:
- ✅ **Validación automática**: Pydantic valida tipos y valores
- 🔒 **Type safety**: Autocompletado y type hints
- 🔄 **Hot reload**: Recarga configuración sin reiniciar
- 📝 **Documentación automática**: Genera docs de configuración

---

### 2. **logging.py**
**Propósito**: Configuración centralizada de logging

**Características**:
- **Múltiples handlers**: Console, File, Rotating File, Syslog
- **Niveles configurables**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Formateo estructurado**: JSON logging para producción
- **Contexto enriquecido**: Request ID, User ID, Timestamps
- **Integración con servicios**: Sentry, CloudWatch, ELK Stack

**Configuración de Loggers**:
```python
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json"
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/error.log",
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "json",
            "level": "ERROR"
        }
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "file"],
            "level": "INFO"
        },
        "src": {
            "handlers": ["console", "file", "error_file"],
            "level": "DEBUG",
            "propagate": False
        }
    }
}
```

**Funcionalidades**:

#### 1. **Logging Estructurado**
```python
logger.info(
    "RAG query processed",
    extra={
        "query": query,
        "latency_ms": latency,
        "sources_count": len(sources),
        "cache_hit": cache_hit
    }
)
```

#### 2. **Context Manager para Logging**
```python
with log_context(request_id="req-123", user_id="user-456"):
    logger.info("Processing request")  # Incluye contexto automáticamente
```

#### 3. **Performance Logging**
```python
@log_performance
def expensive_operation():
    # Automáticamente logea tiempo de ejecución
    pass
```

#### 4. **Error Tracking**
```python
try:
    risky_operation()
except Exception as e:
    logger.exception(
        "Operation failed",
        extra={
            "error_type": type(e).__name__,
            "stack_trace": traceback.format_exc()
        }
    )
```

**Ventajas**:
- 📊 **Observabilidad completa**: Trazabilidad de todas las operaciones
- 🔍 **Debugging facilitado**: Logs estructurados y buscables
- 🚨 **Alertas automáticas**: Integración con sistemas de monitoreo
- 📈 **Análisis de rendimiento**: Métricas de latencia y throughput
- 🔒 **Auditoría**: Registro completo de acciones

---

## ⚡ Funcionalidades Principales

### 1. **Gestión de Entornos**

```python
# Configuración por entorno
class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    class Config:
        env_file = f".env.{os.getenv('ENVIRONMENT', 'development')}"
```

### 2. **Validación de Configuración**

```python
from pydantic import validator, Field

class Settings(BaseSettings):
    LLM_TEMPERATURE: float = Field(ge=0.0, le=2.0)
    CHUNK_SIZE: int = Field(gt=0, le=4096)
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "sqlite://")):
            raise ValueError("Invalid database URL")
        return v
    
    @validator("API_KEY")
    def validate_api_key(cls, v):
        if len(v) < 32:
            raise ValueError("API key too short")
        return v
```

### 3. **Configuración Dinámica**

```python
# Actualización en tiempo real
settings = get_settings()
settings.update_config({
    "LLM_TEMPERATURE": 0.5,
    "TOP_K_RESULTS": 10
})
```

### 4. **Secretos y Seguridad**

```python
from cryptography.fernet import Fernet

class SecureSettings(Settings):
    _cipher: Fernet = None
    
    def get_secret(self, key: str) -> str:
        """Desencripta secretos"""
        encrypted = getattr(self, key)
        return self._cipher.decrypt(encrypted).decode()
    
    def set_secret(self, key: str, value: str):
        """Encripta y guarda secretos"""
        encrypted = self._cipher.encrypt(value.encode())
        setattr(self, key, encrypted)
```

---

## 🎯 Ventajas del Sistema

### Mantenibilidad
- 📝 **Configuración centralizada**: Un solo lugar para toda la config
- 🔄 **Fácil actualización**: Cambios sin modificar código
- 📚 **Documentación automática**: Pydantic genera docs

### Seguridad
- 🔒 **Gestión de secretos**: Encriptación de datos sensibles
- 🚫 **No hardcoding**: Todas las credenciales en variables de entorno
- ✅ **Validación estricta**: Previene configuraciones inválidas

### Desarrollo
- 🚀 **Desarrollo rápido**: Configuración por entorno
- 🧪 **Testing facilitado**: Mocks de configuración
- 🔍 **Debugging mejorado**: Logs detallados y estructurados

### Producción
- 📊 **Monitoreo completo**: Integración con herramientas de observabilidad
- 🚨 **Alertas automáticas**: Notificaciones de errores críticos
- 📈 **Métricas de rendimiento**: Análisis de performance

---

## 🔧 Uso

### Configuración Básica

```python
from src.config import get_settings
from src.config.logging import setup_logging

# Inicializar configuración
settings = get_settings()

# Configurar logging
setup_logging(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT
)

# Usar configuración
logger = logging.getLogger(__name__)
logger.info(f"Starting application in {settings.ENVIRONMENT} mode")
```

### Ejemplo Completo

```python
import logging
from src.config import get_settings

# Obtener configuración
settings = get_settings()

# Configurar logger
logger = logging.getLogger(__name__)

# Usar configuración en la aplicación
def initialize_rag_system():
    logger.info("Initializing RAG system")
    
    # Configuración de LLM
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        api_key=settings.OPENAI_API_KEY
    )
    
    # Configuración de vector store
    vector_store = ChromaDB(
        persist_directory=settings.VECTOR_STORE_PATH,
        collection_name=settings.COLLECTION_NAME
    )
    
    logger.info(
        "RAG system initialized",
        extra={
            "llm_model": settings.LLM_MODEL,
            "vector_store": settings.VECTOR_STORE_TYPE
        }
    )
    
    return llm, vector_store
```

---

## 🌍 Configuración por Entorno

### Desarrollo (.env.development)
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7

# Database
DATABASE_URL=sqlite:///./dev.db
VECTOR_STORE_PATH=./data/chroma_dev

# Cache
CACHE_ENABLED=true
CACHE_TTL=300
```

### Staging (.env.staging)
```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.5

# Database
DATABASE_URL=postgresql://user:pass@staging-db:5432/rag
VECTOR_STORE_PATH=/data/chroma_staging

# Cache
CACHE_ENABLED=true
CACHE_TTL=600
```

### Producción (.env.production)
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.3

# Database
DATABASE_URL=postgresql://user:pass@prod-db:5432/rag
VECTOR_STORE_PATH=/data/chroma_prod

# Cache
CACHE_ENABLED=true
CACHE_TTL=3600

# Security
SECRET_KEY=${SECRET_KEY}
API_KEY=${API_KEY}

# Monitoring
SENTRY_DSN=${SENTRY_DSN}
DATADOG_API_KEY=${DATADOG_API_KEY}
```

---

## 📊 Logging Avanzado

### Integración con Sentry

```python
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

def setup_sentry():
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR
    )
    
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[sentry_logging],
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0 if settings.is_development else 0.1
    )
```

### Logging a CloudWatch

```python
import watchtower

def setup_cloudwatch_logging():
    cloudwatch_handler = watchtower.CloudWatchLogHandler(
        log_group=f"/rag-system/{settings.ENVIRONMENT}",
        stream_name=f"{settings.SERVICE_NAME}-{settings.INSTANCE_ID}"
    )
    
    logger.addHandler(cloudwatch_handler)
```

### Métricas Personalizadas

```python
from prometheus_client import Counter, Histogram

# Contadores
rag_queries_total = Counter(
    'rag_queries_total',
    'Total RAG queries processed'
)

# Histogramas
rag_query_duration = Histogram(
    'rag_query_duration_seconds',
    'RAG query duration in seconds'
)

# Uso
@rag_query_duration.time()
def process_query(query: str):
    rag_queries_total.inc()
    # Process query
    pass
```

---

## 🚀 Mejores Prácticas

1. **Nunca hardcodear credenciales**: Siempre usar variables de entorno
2. **Validar configuración al inicio**: Fallar rápido si hay errores
3. **Usar logging estructurado**: Facilita búsqueda y análisis
4. **Separar configuración por entorno**: Dev, staging, prod
5. **Documentar todas las variables**: Mantener .env.example actualizado
6. **Rotar logs regularmente**: Evitar llenar disco
7. **Monitorear errores en producción**: Integrar con Sentry/Datadog

---

## 📚 Referencias

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [12-Factor App Configuration](https://12factor.net/config)

---

**Última actualización**: 2026-04-28
**Versión**: 2.0.0
**Mantenedor**: Equipo de Infraestructura
