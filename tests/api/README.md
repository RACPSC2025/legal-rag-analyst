# Tests de API — RAG Legal v2.5

## Descripción

Tests de integración end-to-end para los endpoints de la API REST.

## Requisitos

**IMPORTANTE**: Estos tests requieren que el servidor FastAPI esté corriendo.

```bash
# Terminal 1: Iniciar servidor
uvicorn api.main:app --reload

# Terminal 2: Ejecutar tests
pytest tests/api/ -v
```

## Tests Implementados

### 1. TestBasicEndpoints
- `test_root_endpoint`: Verifica endpoint raíz `/`
- `test_health_check`: Verifica health check `/health`

### 2. TestQueryEndpoints
- `test_query_rag_basic`: Consulta RAG básica
- `test_query_validation_error`: Validación de errores
- `test_batch_query`: Consultas en batch

### 3. TestCacheEndpoints
- `test_cache_stats`: Estadísticas de caché

## Ejecución

### Ejecutar todos los tests de API

```bash
pytest tests/api/ -v
```

### Ejecutar un test específico

```bash
pytest tests/api/test_api_endpoints.py::TestQueryEndpoints::test_query_rag_basic -v
```

### Ejecutar con logging visible

```bash
pytest tests/api/ -v -s --log-cli-level=INFO
```

### Ejecutar solo tests marcados como "api"

```bash
pytest -m api -v
```

## Fixtures Disponibles

- `api_client`: Cliente HTTP configurado para `http://localhost:8000`
- `check_server_running`: Verifica automáticamente que el servidor esté corriendo

## Troubleshooting

### Error: "No se pudo conectar al servidor"

**Causa**: El servidor FastAPI no está corriendo.

**Solución**:
```bash
uvicorn api.main:app --reload
```

### Error: "El servidor no está respondiendo correctamente"

**Causa**: El servidor está corriendo pero no responde en el puerto esperado.

**Solución**: Verificar que el servidor esté en `http://localhost:8000`

### Tests muy lentos

**Causa**: Los tests hacen requests HTTP reales.

**Solución**: Estos son tests de integración E2E, es normal que sean más lentos que tests unitarios.

## Migración

Estos tests fueron migrados desde `api/test_api.py` (script manual) a pytest para:
- ✅ Integración con la suite de tests existente
- ✅ Uso de fixtures compartidas
- ✅ Mejor organización y mantenibilidad
- ✅ Ejecución automática en CI/CD

---

**Autor**: Fenix Tech Líder  
**Fecha**: 28/04/2026  
**Migrado desde**: `api/test_api.py`
