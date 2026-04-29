# Tests — RAG Analista Legal v2.5

## 📋 Descripción General

Sistema completo de testing para el **RAG Analista Legal Colombiano**, organizado en 5 categorías principales con **Test Center** interactivo para ejecución y monitoreo.

## 🎯 Arquitectura de Tests

```
tests/
├── README.md                    # 📖 Esta documentación
├── conftest.py                  # 🔧 Fixtures compartidas
├── run_tests.py                 # 🎮 Test Center (Orquestador)
├── __init__.py
│
├── unit/                        # 🧪 Tests Unitarios (Componentes aislados)
│   ├── test_contextual_compression.py
│   ├── test_hybrid_search_v2.py
│   ├── test_metadata_filters.py
│   ├── test_model_hub_v2.py
│   ├── test_query_expansion.py
│   └── test_table_processor.py         # TASK-015 (20 tests)
│
├── integration/                 # 🔗 Tests de Integración (Grafo y AWS)
│   ├── test_aws_bedrock.py
│   ├── test_integration.py
│   ├── test_retrieve_integration.py
│   └── test_table_integration.py       # TASK-015 (7 tests)
│
├── api/                         # 🌐 Tests de API (End-to-End)
│   ├── README.md
│   ├── test_api_endpoints.py           # 6 tests E2E
│   └── __init__.py
│
├── evaluation/                  # 📊 Tests de Evaluación (RAGAS y Salud)
│   ├── README.md
│   ├── golden_dataset.json             # 22 preguntas reales
│   ├── ragas_evaluator.py
│   ├── metrics_dashboard.py
│   ├── run_evaluation.py
│   └── evaluate_rag_health.py
│
├── retrieval/                   # 🔍 Tests de Retrieval (Tablas)
│   ├── README.md
│   ├── test_table_processor.py         # Tests unitarios
│   └── test_table_integration.py       # Tests de integración
│
└── scripts/                     # 🛠️ Scripts de Utilidad
    ├── test_conversion.py
    ├── test_docling_simple.py
    ├── test_preprocessor.py
    └── verify_imports.py
```

---

## 🎮 Test Center — Orquestador Interactivo

El **Test Center** (`run_tests.py`) es un menú interactivo con Rich UI para ejecutar y monitorear tests.

### Iniciar Test Center:
```bash
python tests/run_tests.py
```

### Menú Principal:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                    FÉNIX LEGAL — TEST ORCHESTRATOR                        ║
║                    ANALISTA LEGAL v2.5                                    ║
╚═══════════════════════════════════════════════════════════════════════════╝

1. 🧪 Pruebas Unitarias (Componentes aislados)
2. 🔗 Pruebas de Integración (Grafo y AWS)
3. 📊 Pruebas de Evaluación (RAGAS y Salud)
4. 📋 Pruebas de Tablas (TASK-015 Completo)
5. 🔥 EJECUTAR TODO EL SUITE
6. 📂 Ver Scripts de Utilidad
q. 🚪 Salir
```

### Submenú de Tests Unitarios:

```
═══ PRUEBAS UNITARIAS ═══

1. 🔍 Contextual Compression
2. 🔎 Hybrid Search
3. 📋 Metadata Filters
4. 🤖 Model Hub
5. 🔄 Query Expansion
6. 📊 Table Processor (TASK-015)
7. 🔥 TODOS los tests unitarios
b. ⬅️  Volver al menú principal
```

### Submenú de Tests de Integración:

```
═══ PRUEBAS DE INTEGRACIÓN ═══

1. ☁️  AWS Bedrock Integration
2. 🔗 General Integration Tests
3. 🔍 Retrieve Integration
4. 📊 Table Integration (TASK-015)
5. 🌐 API Endpoints (E2E)
6. 🔥 TODAS las pruebas de integración
b. ⬅️  Volver al menú principal
```

---

## 🧪 Categorías de Tests

### 1. **Tests Unitarios** (`unit/`)

**Objetivo:** Verificar componentes individuales de forma aislada.

| Test | Componente | Descripción |
|------|-----------|-------------|
| `test_contextual_compression.py` | Contextual Compression | Compresión de contexto con LLM |
| `test_hybrid_search_v2.py` | Hybrid Search | Búsqueda híbrida (vector + keyword) |
| `test_metadata_filters.py` | Metadata Filters | Filtros por metadata legal |
| `test_model_hub_v2.py` | Model Hub | Gestión de modelos LLM |
| `test_query_expansion.py` | Query Expansion | Expansión de consultas |
| `test_table_processor.py` | Table Processor | Procesamiento de tablas (20 tests) |

**Ejecutar:**
```bash
# Todos los tests unitarios
pytest tests/unit/ -v

# Un test específico
pytest tests/unit/test_table_processor.py -v

# Con cobertura
pytest tests/unit/ -v --cov=src --cov-report=html
```

**Características:**
- ✅ Rápidos (< 1s por test)
- ✅ No requieren AWS
- ✅ No requieren servidor corriendo
- ✅ Usan mocks y fixtures

---

### 2. **Tests de Integración** (`integration/`)

**Objetivo:** Verificar interacción entre componentes y servicios externos.

| Test | Componente | Descripción |
|------|-----------|-------------|
| `test_aws_bedrock.py` | AWS Bedrock | Conexión con modelos AWS |
| `test_integration.py` | General | Integración general del sistema |
| `test_retrieve_integration.py` | Retrieval | Pipeline de recuperación |
| `test_table_integration.py` | Table Integration | Tablas end-to-end (7 tests) |

**Ejecutar:**
```bash
# Todos los tests de integración
pytest tests/integration/ -v

# Un test específico
pytest tests/integration/test_table_integration.py -v
```

**Características:**
- ⚠️ Más lentos (5-30s por test)
- ⚠️ Requieren credenciales AWS
- ⚠️ Pueden consumir recursos (API calls)
- ✅ Verifican comportamiento real

---

### 3. **Tests de API** (`api/`)

**Objetivo:** Verificar endpoints REST de la API FastAPI.

| Test | Endpoint | Descripción |
|------|----------|-------------|
| `test_api_endpoints.py` | `/`, `/health`, `/query`, `/batch`, `/cache/stats` | 6 tests E2E |

**Ejecutar:**
```bash
# IMPORTANTE: Iniciar servidor primero
# Terminal 1:
uvicorn api.main:app --reload

# Terminal 2:
pytest tests/api/ -v
```

**Características:**
- ⚠️ Requiere servidor corriendo
- ⚠️ Tests E2E (end-to-end)
- ✅ Verifica API completa
- ✅ Usa cliente HTTP real

**Ver documentación completa:** [`tests/api/README.md`](api/README.md)

---

### 4. **Tests de Evaluación** (`evaluation/`)

**Objetivo:** Evaluar calidad del RAG con métricas RAGAS.

| Componente | Descripción |
|-----------|-------------|
| `golden_dataset.json` | 22 preguntas reales de derecho colombiano |
| `ragas_evaluator.py` | Motor de evaluación RAGAS |
| `metrics_dashboard.py` | Visualización de métricas |
| `run_evaluation.py` | Orquestador de evaluación |
| `evaluate_rag_health.py` | Health check del sistema |

**Ejecutar:**
```bash
# Evaluación completa (22 preguntas)
python tests/evaluation/run_evaluation.py

# Evaluación rápida (5 preguntas)
python tests/evaluation/run_evaluation.py --quick

# Ver dashboard de reporte
python tests/evaluation/metrics_dashboard.py ragas_report_*.json
```

**Métricas RAGAS:**
1. **Faithfulness** (Fidelidad): ¿La respuesta está fundamentada?
2. **Answer Relevancy** (Relevancia): ¿La respuesta es relevante?
3. **Context Precision** (Precisión): ¿Los docs recuperados son relevantes?
4. **Context Recall** (Cobertura): ¿El contexto cubre todo?
5. **Answer Correctness** (Exactitud): ¿La respuesta es correcta?

**Ver documentación completa:** [`tests/evaluation/README.md`](evaluation/README.md)

---

### 5. **Tests de Retrieval** (`retrieval/`)

**Objetivo:** Tests específicos para componentes de retrieval (TASK-015).

| Test | Descripción |
|------|-------------|
| `test_table_processor.py` | Tests unitarios del Table Processor (20 tests) |
| `test_table_integration.py` | Tests de integración end-to-end (7 tests) |

**Ejecutar:**
```bash
# Todos los tests de retrieval
pytest tests/retrieval/ -v

# Solo tests de tablas
pytest tests/retrieval/test_table_processor.py tests/retrieval/test_table_integration.py -v
```

**Ver documentación completa:** [`tests/retrieval/README.md`](retrieval/README.md)

---

## 🔧 Fixtures Compartidas (`conftest.py`)

Fixtures disponibles para todos los tests:

### Configuración:
- `setup_project_path`: Agrega PROJECT_ROOT al sys.path (autouse)

### Datos de Prueba:
- `sample_legal_question`: Pregunta legal de ejemplo
- `sample_pdf_path`: Ruta a PDFs de ejemplo
- `temp_upload_dir`: Directorio temporal para uploads

### Mocking:
- `mock_env_credentials`: Mock de credenciales AWS

### Tablas (TASK-015):
- `sample_markdown_table`: Tabla Markdown básica
- `sample_table_with_alignment`: Tabla con alineación
- `sample_fragment_with_table`: Fragmento legal con tabla
- `sample_multiple_tables`: Fragmento con múltiples tablas

**Uso:**
```python
def test_example(sample_legal_question, temp_upload_dir):
    # Usar fixtures directamente
    assert "artículo" in sample_legal_question.lower()
    assert temp_upload_dir.exists()
```

---

## 🚀 Ejecución de Tests

### Opción 1: Test Center (Recomendado)
```bash
python tests/run_tests.py
```

### Opción 2: pytest Directo

**Todos los tests:**
```bash
pytest tests/ -v
```

**Por categoría:**
```bash
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/api/ -v
pytest tests/evaluation/ -v
pytest tests/retrieval/ -v
```

**Un test específico:**
```bash
pytest tests/unit/test_table_processor.py::TestTableDetector::test_detect_valid_table -v
```

**Con cobertura:**
```bash
pytest tests/ -v --cov=src --cov-report=html
```

**Con logging visible:**
```bash
pytest tests/ -v -s --log-cli-level=INFO
```

**Solo tests marcados:**
```bash
pytest -m unit -v
pytest -m integration -v
pytest -m api -v
```

---

## 📊 Métricas de Éxito

### Tests Unitarios:
- ✅ **Cobertura:** > 80% de código cubierto
- ✅ **Velocidad:** < 1s por test
- ✅ **Tasa de éxito:** 100% de tests pasando

### Tests de Integración:
- ✅ **Cobertura:** Todos los flujos críticos cubiertos
- ✅ **Velocidad:** < 30s por test
- ✅ **Tasa de éxito:** > 95% de tests pasando

### Tests de API:
- ✅ **Cobertura:** Todos los endpoints cubiertos
- ✅ **Velocidad:** < 10s por test
- ✅ **Tasa de éxito:** 100% de tests pasando

### Tests de Evaluación (RAGAS):
- ✅ **Overall Score:** > 0.80 (Excelente)
- ✅ **Faithfulness:** > 0.85
- ✅ **Answer Relevancy:** > 0.80
- ✅ **Context Precision:** > 0.75
- ✅ **Context Recall:** > 0.75

### Tests de Retrieval (TASK-015):
- ✅ **Integridad de tablas:** < 5% tablas con filas/columnas faltantes
- ✅ **Performance detección:** < 50ms para fragmentos de 5KB
- ✅ **Overhead total:** < 15% en pipeline completo
- ✅ **Round-trip preservation:** 100% preservación estructura

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'src'"

**Causa:** Tests ejecutados desde directorio incorrecto.

**Solución:**
```bash
cd /path/to/Rag_Analista_Legal
pytest tests/ -v
```

### Error: "AWS credentials not found"

**Causa:** Tests de integración requieren credenciales AWS.

**Solución 1 (Mock):**
```python
# Usar fixture mock_env_credentials
def test_example(mock_env_credentials):
    # Test con credenciales mockeadas
    pass
```

**Solución 2 (Real):**
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-2
```

### Error: "No se pudo conectar al servidor" (API tests)

**Causa:** Servidor FastAPI no está corriendo.

**Solución:**
```bash
# Terminal 1: Iniciar servidor
uvicorn api.main:app --reload

# Terminal 2: Ejecutar tests
pytest tests/api/ -v
```

### Error: "Python 3.14.4 Could not find platform independent libraries"

**Causa:** Entorno virtual corrupto.

**Solución:**
```bash
# Recrear entorno virtual
rm -rf venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Tests muy lentos

**Causa:** Tests de integración usan LLM real y AWS.

**Solución:**
```bash
# Ejecutar solo tests unitarios (rápidos)
pytest tests/unit/ -v

# O usar evaluación rápida
python tests/evaluation/run_evaluation.py --quick
```

---

## 📚 Convenciones y Mejores Prácticas

### Estructura de Tests:

```python
import logging
import pytest

logger = logging.getLogger(__name__)

class TestComponentName:
    """Tests para ComponentName."""
    
    def test_feature_description(self, fixture_name):
        """Test: Verificar que feature hace X."""
        logger.info("\n" + "="*80)
        logger.info("TEST: Feature Description")
        logger.info("="*80)
        
        # 1. Setup (Arrange)
        component = ComponentName()
        input_data = "test data"
        
        # 2. Execute (Act)
        result = component.method(input_data)
        
        # 3. Verify (Assert)
        logger.info(f"  Input: {input_data}")
        logger.info(f"  Result: {result}")
        assert result == expected_value, "Mensaje descriptivo"
        
        logger.info("✅ TEST PASADO\n")
```

### Naming Conventions:

- **Archivos:** `test_<component_name>.py`
- **Clases:** `TestComponentName`
- **Métodos:** `test_<feature_description>`
- **Fixtures:** `<resource_name>` (sin prefijo test_)

### Markers:

```python
@pytest.mark.unit
def test_unit_example():
    pass

@pytest.mark.integration
def test_integration_example():
    pass

@pytest.mark.slow
def test_slow_example():
    pass

@pytest.mark.skip(reason="Temporalmente deshabilitado")
def test_skip_example():
    pass
```

### Logging:

```python
import logging
logger = logging.getLogger(__name__)

# Usar logging en lugar de print
logger.info("Información general")
logger.debug("Detalles de debugging")
logger.warning("Advertencia")
logger.error("Error")
```

### Assertions:

```python
# ✅ BUENO: Mensaje descriptivo
assert result == expected, f"Expected {expected}, got {result}"

# ❌ MALO: Sin mensaje
assert result == expected
```

---

## 🔄 Integración Continua (CI/CD)

### GitHub Actions (Ejemplo):

```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run Unit Tests
        run: pytest tests/unit/ -v --cov=src --cov-report=xml
      
      - name: Run Integration Tests
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-east-2
        run: pytest tests/integration/ -v
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./coverage.xml
      
      - name: Run RAGAS Evaluation (Quick)
        run: python tests/evaluation/run_evaluation.py --quick
```

---

## 📈 Roadmap de Tests

### ✅ Completado:
- [x] Tests unitarios de componentes core
- [x] Tests de integración AWS Bedrock
- [x] Tests de API endpoints
- [x] Sistema de evaluación RAGAS
- [x] Tests de tablas (TASK-015)
- [x] Test Center interactivo

### 🚧 En Progreso:
- [ ] Tests de performance (benchmarking)
- [ ] Tests de carga (stress testing)
- [ ] Tests de seguridad (penetration testing)

### 📋 Pendiente:
- [ ] Tests de regresión visual
- [ ] Tests de accesibilidad
- [ ] Tests de compatibilidad multi-navegador
- [ ] Tests de internacionalización (i18n)

---

## 🤝 Contribuir

### Agregar Nuevos Tests:

1. **Identificar categoría:** unit, integration, api, evaluation, retrieval
2. **Crear archivo:** `test_<component_name>.py` en carpeta correspondiente
3. **Usar fixtures:** Reutilizar fixtures de `conftest.py`
4. **Seguir convenciones:** Naming, estructura, logging
5. **Documentar:** Agregar docstrings y comentarios
6. **Actualizar README:** Si es necesario

### Agregar Nuevas Fixtures:

1. **Editar `conftest.py`:**
```python
@pytest.fixture
def new_fixture_name():
    """Descripción de la fixture."""
    # Setup
    resource = create_resource()
    
    yield resource
    
    # Teardown (opcional)
    cleanup_resource(resource)
```

2. **Documentar en este README** en sección "Fixtures Compartidas"

### Agregar Nueva Categoría:

1. **Crear carpeta:** `tests/new_category/`
2. **Crear README:** `tests/new_category/README.md`
3. **Agregar tests:** `tests/new_category/test_*.py`
4. **Actualizar Test Center:** Agregar opción en `run_tests.py`
5. **Actualizar este README:** Agregar sección en "Categorías de Tests"

---

## 📚 Referencias

- **pytest Documentation**: https://docs.pytest.org/
- **RAGAS Framework**: https://github.com/explodinggradients/ragas
- **LangChain Testing**: https://python.langchain.com/docs/guides/evaluation
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/
- **Coverage.py**: https://coverage.readthedocs.io/

---

## 📝 Changelog

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 2.5.0 | 2026-04-28 | README centralizado con arquitectura completa |
| 2.4.0 | 2026-04-28 | Tests de API migrados desde `api/test_api.py` |
| 2.3.0 | 2026-04-27 | Sistema de evaluación RAGAS implementado |
| 2.2.0 | 2026-04-26 | Tests de tablas TASK-015 completados (27 tests) |
| 2.1.0 | 2026-04-25 | Test Center interactivo con Rich UI |
| 2.0.0 | 2026-04-20 | Refactorización completa de arquitectura de tests |

---

## 👥 Mantenimiento

**Autor**: Ronny Vallejos  
**Última Actualización**: 28 de Abril de 2026  
**Versión**: 2.5.0  
**Proyecto**: RAG Analista Legal Colombiano

---

## 🎯 Resumen Ejecutivo

| Categoría | Tests | Cobertura | Estado |
|-----------|-------|-----------|--------|
| **Unit** | 20+ | Core components | ✅ Completo |
| **Integration** | 10+ | AWS + Grafo | ✅ Completo |
| **API** | 6 | Todos los endpoints | ✅ Completo |
| **Evaluation** | 22 preguntas | RAGAS completo | ✅ Completo |
| **Retrieval** | 27 | TASK-015 completo | ✅ Completo |
| **TOTAL** | **63+** | **Sistema completo** | **✅ Production-Ready** |

---

**¡Sistema de testing robusto y production-ready! 🚀**
