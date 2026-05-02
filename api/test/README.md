# Tests de API — RAG Legal Colombiano

## 📋 Descripción

Esta carpeta contiene scripts de prueba para la API REST del sistema RAG Legal Colombiano.

## 🧪 Tests Disponibles

### 1. `test_api_consolidated.py` (RECOMENDADO)
**Script consolidado que reemplaza todos los anteriores:**

- ✅ **Diagnóstico del sistema** - Verifica entorno, imports y conectividad
- ✅ **Tests de endpoints básicos** - Root, health check
- ✅ **Tests de query RAG** - Consultas individuales y batch con validación de calidad
- ✅ **Smoke test con PDF** - Upload, ingesta y consultas específicas sobre documentos
- ✅ **Tests de caché** - Estadísticas y funcionamiento
- ✅ **Validación de calidad** - Verificación de estructura, citas, discrepancias numéricas y scores

**Uso:**
```bash
python api/test/test_api_consolidated.py
```

### 2. `tests/api/test_api_endpoints.py` (Tests Formales Pytest)
**Tests de integración formales usando pytest:**

- ✅ **Fixtures** - Cliente HTTP configurado automáticamente
- ✅ **Marcadores** - Ejecución selectiva con `pytest -m api`
- ✅ **Logging estructurado** - Output detallado para debugging
- ✅ **Integración con CI/CD** - Compatible con pipelines de testing

**Uso:**
```bash
# Ejecutar todos los tests de API
pytest tests/api/ -v

# Ejecutar solo tests marcados como "api"
pytest -m api -v

# Ejecutar test específico
pytest tests/api/test_api_endpoints.py::TestQueryEndpoints::test_query_rag_basic -v
```

## 🚀 Flujo de Testing Recomendado

### Desarrollo Local
1. **Iniciar servidor:**
   ```bash
   uvicorn api.main:app --reload
   ```

2. **Ejecutar test consolidado (rápido):**
   ```bash
   python api/test/test_api_consolidated.py
   ```

3. **Ejecutar tests formales (completo):**
   ```bash
   pytest tests/api/ -v
   ```

### CI/CD Pipeline
```yaml
# Ejemplo de configuración
steps:
  - name: Run API Tests
    run: |
      # Iniciar servidor en background
      uvicorn api.main:app --host 127.0.0.1 --port 8000 &
      SERVER_PID=$!
      
      # Esperar que el servidor esté listo
      sleep 5
      
      # Ejecutar tests
      pytest tests/api/ -v --tb=short
      
      # Terminar servidor
      kill $SERVER_PID
```

## 📊 Validación de Calidad

El test consolidado incluye validaciones de calidad para respuestas RAG:

### Estructura de Respuesta
- ✅ `query_id` presente
- ✅ `answer` válida (más de 10 caracteres)
- ✅ `sources` presente

### Citas y Verificación
- ✅ Conteo de citas generadas
- ✅ Citas verificadas vs no verificadas
- ✅ Mensajes de verificación

### Discrepancias Numéricas
- ✅ Detección de discrepancias
- ✅ Tipos de datos (currency, days, percentages, etc.)
- ✅ Valores esperados vs encontrados

### Scores de Confianza
- ✅ `confidence_score` presente
- ✅ Validación de rangos (alto: ≥0.7, medio: ≥0.5, bajo: <0.5)

## 🔧 Herramientas de Diagnóstico

### `debug_swagger.py`
Script para debug de Swagger UI y OpenAPI.

### `start_api_debug.bat`
Batch script para Windows para iniciar API en modo debug.

### `test_swagger.html`
Página HTML para test manual de Swagger UI.

## 📝 Notas Importantes

### Requisitos Previos
1. **Servidor corriendo** - Los tests requieren que la API esté activa
2. **Variables de entorno** - Configuración AWS Bedrock en `.env`
3. **PDF de prueba** - `data/input/Decreto_1072_2015.pdf` para smoke test

### Troubleshooting
- **Error de conexión**: Verificar que el servidor esté corriendo en `localhost:8000`
- **Timeout en tests**: Aumentar `TIMEOUT` en los scripts si es necesario
- **PDF no encontrado**: El smoke test creará un PDF de prueba automáticamente

## 🎯 Objetivos de Testing

| Tipo de Test | Objetivo | Frecuencia |
|-------------|----------|------------|
| **Smoke Test** | Validar flujo completo (upload → ingesta → query) | Antes de cada release |
| **Regression Test** | Verificar que cambios no rompan funcionalidad existente | Después de cada cambio |
| **Performance Test** | Validar latencia y throughput | Mensual |
| **Security Test** | Verificar autenticación y autorización | Trimestral |

---

**Autor**: Fenix Tech Líder  
**Última actualización**: 01/05/2026  
**Versión**: 2.0 (Consolidada)