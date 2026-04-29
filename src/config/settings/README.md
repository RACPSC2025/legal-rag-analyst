# Settings Multi-Ambiente — RAG Legal v2.5

## Descripción

Sistema de configuración multi-ambiente inspirado en Django, que permite tener configuraciones separadas para desarrollo, producción y testing.

## Estructura

```
src/config/settings/
├── __init__.py          # Loader de configuración
├── base.py              # Configuración base (común a todos)
├── development.py       # Configuración de desarrollo
├── production.py        # Configuración de producción
└── README.md            # Este archivo
```

## Uso

### Forma Recomendada (Nueva)

```python
from src.config.settings import get_settings

config = get_settings()
print(config.ENVIRONMENT)  # 'development' o 'production'
print(config.API_HOST)     # '127.0.0.1' en dev, '0.0.0.0' en prod
```

### Forma Antigua (Backward Compatible)

```python
from src.config import settings

print(settings.AWS_REGION)  # Sigue funcionando
```

## Configuración por Ambiente

### Development (Desarrollo Local)

**Activar**: `ENVIRONMENT=development` en `.env` (o no definir, es el default)

**Características**:
- ✅ Debug habilitado
- ✅ Logging verbose (DEBUG level)
- ✅ Cache deshabilitado (para ver cambios inmediatos)
- ✅ Rate limiting permisivo (1000 req/min)
- ✅ CORS permisivo (localhost:*)
- ✅ Hot reload habilitado
- ✅ 1 worker
- ✅ Batch size pequeño (5) para testing rápido

**Uso típico**: Desarrollo local, debugging, testing manual

### Production (Producción)

**Activar**: `ENVIRONMENT=production` en `.env`

**Características**:
- ✅ Debug deshabilitado
- ✅ Logging estructurado (JSON, INFO level)
- ✅ Cache habilitado (7 días TTL)
- ✅ Rate limiting estricto (100 req/min)
- ✅ CORS restrictivo (solo dominios específicos)
- ✅ Hot reload deshabilitado
- ✅ 4 workers (múltiples procesos)
- ✅ Batch size grande (40) para eficiencia
- ✅ Seguridad reforzada (HTTPS, HSTS, CSP)

**Uso típico**: Servidor de producción, deployment real

## Variables de Entorno

### Variables Comunes (Todos los Ambientes)

Definidas en `base.py`:

```env
# AWS Bedrock
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-2

# Modelos
AWS_MODEL_SIMPLE_TEXT=us.amazon.nova-lite-v1:0
AWS_MODEL_DEEP_ANALYSIS=us.meta.llama3-3-70b-instruct-v1:0

# LLM
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=2048

# RAG
CHUNK_SIZE=1500
CHUNK_OVERLAP=300
TOP_K_DOCS=6

# Vector DB
VECTOR_DB_COLLECTION_NAME=my_collection
```

### Variables Específicas de Ambiente

Definidas en `development.py` o `production.py`:

```env
# Ambiente
ENVIRONMENT=development  # o 'production'

# API
API_HOST=127.0.0.1       # 0.0.0.0 en prod
API_PORT=8000
API_WORKERS=1            # 4 en prod

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8501

# Logging
LOG_LEVEL=DEBUG          # INFO en prod
LOG_FORMAT=text          # json en prod

# Cache
CACHE_ENABLED=false      # true en prod
CACHE_TTL_DAYS=1         # 7 en prod

# Rate Limiting
RATE_LIMIT_ENABLED=false # true en prod
RATE_LIMIT_REQUESTS=1000 # 100 en prod
```

## Migración desde Configuración Antigua

### Código Existente (Sigue Funcionando)

```python
# ✅ Esto sigue funcionando sin cambios
from src.config import settings

print(settings.AWS_REGION)
print(settings.CHUNK_SIZE)
```

### Código Nuevo (Recomendado)

```python
# ✅ Nueva forma recomendada
from src.config.settings import get_settings

config = get_settings()
print(config.AWS_REGION)
print(config.CHUNK_SIZE)
print(config.ENVIRONMENT)  # Nueva variable disponible
```

## Ventajas de la Nueva Estructura

1. **Separación Clara**: Configuración de dev y prod separadas
2. **Seguridad**: Producción puede usar AWS Secrets Manager
3. **Flexibilidad**: Fácil agregar nuevos ambientes (staging, testing)
4. **Mantenibilidad**: Cambios en prod no afectan dev
5. **Type Safety**: Configuración tipada y validada
6. **Estándar**: Sigue convenciones de Django/Rails/Spring Boot
7. **Backward Compatible**: Código existente sigue funcionando

## Agregar Nuevo Ambiente

Para agregar un nuevo ambiente (ej: `staging`):

1. Crear `src/config/settings/staging.py`:

```python
from .base import BaseConfig

class StagingConfig(BaseConfig):
    ENVIRONMENT: str = "staging"
    DEBUG: bool = False
    # ... configuración específica
```

2. Actualizar `src/config/settings/__init__.py`:

```python
from .staging import StagingConfig

@lru_cache()
def get_settings():
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionConfig()
    elif environment == "staging":
        return StagingConfig()
    elif environment == "development":
        return DevelopmentConfig()
    # ...
```

3. Usar: `ENVIRONMENT=staging` en `.env`

## AWS Secrets Manager (Producción)

Para usar AWS Secrets Manager en producción:

```python
from src.config.settings import get_settings

config = get_settings()

if config.ENVIRONMENT == "production":
    # Cargar secretos desde AWS
    secrets = config.load_secrets_from_aws()
    
    # Usar secretos
    config.AWS_ACCESS_KEY_ID = secrets.get("AWS_ACCESS_KEY_ID")
    config.AWS_SECRET_ACCESS_KEY = secrets.get("AWS_SECRET_ACCESS_KEY")
```

## Troubleshooting

### Error: "No module named 'src.config.settings'"

**Causa**: Imports antiguos no actualizados.

**Solución**: El código antiguo sigue funcionando. Usa:
```python
from src.config import settings  # ✅ Funciona
```

### Error: "AttributeError: 'DevelopmentConfig' object has no attribute 'X'"

**Causa**: Variable no definida en la configuración del ambiente.

**Solución**: Agregar la variable a `base.py` o al archivo específico del ambiente.

### ¿Cómo sé qué ambiente estoy usando?

```python
from src.config.settings import get_settings

config = get_settings()
print(f"Ambiente actual: {config.ENVIRONMENT}")
```

---

**Autor**: Fenix Tech Líder  
**Fecha**: 28/04/2026  
**Versión**: 1.0.0
