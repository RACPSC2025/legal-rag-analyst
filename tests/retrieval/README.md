# Tests de Retrieval — RAG Legal v2.5

## Descripción

Esta carpeta contiene tests específicos para los componentes de retrieval del sistema RAG Legal, incluyendo tests unitarios y de integración para el procesamiento de tablas (TASK-015).

## Estructura

```
tests/retrieval/
├── README.md                      # Este archivo
├── test_table_processor.py        # Tests unitarios del Table Processor
└── test_table_integration.py      # Tests de integración end-to-end
```

## Tests Implementados

### 1. test_table_processor.py (Tests Unitarios)

**Cobertura:**
- **TableDetector** (Task 2.3)
  - Detectar tabla válida con separador → confidence=1.0
  - Detectar tabla sin separador → confidence=0.8
  - Rechazar false positives (pipes en texto normal)
  - Detectar múltiples tablas en un fragmento
  - Edge cases (tabla vacía, una sola fila, celdas vacías)
  - Extraer tablas como strings individuales

- **MarkdownTableParser** (Task 3.4)
  - Parsear tabla bien formada → TableStructure válida
  - Detectar alineación correcta (left, center, right)
  - Manejar celdas vacías → preservar como ""
  - Manejar pipes escapados → \| se convierte en |
  - Error handling (columnas inconsistentes)
  - Tabla sin separador → todas las filas como data

- **MarkdownTablePrinter** (Task 4.3)
  - Formatear tabla con alineación correcta
  - Calcular anchos de columna correctamente
  - Preservar contenido de celdas sin truncar
  - Edge cases (celdas muy largas, caracteres especiales)

- **Round-Trip Preservation** (Task 4.4)
  - parse → format → parse preserva estructura
  - Round-trip con celdas vacías
  - Round-trip preserva alineación

**Ejecutar:**
```bash
pytest tests/retrieval/test_table_processor.py -v
```

### 2. test_table_integration.py (Tests de Integración)

**Cobertura:**
- **Integración End-to-End** (Tasks 10.1-10.5)
  - Test 10.1: Preservación end-to-end de tabla completa
  - Test 10.2: Compresión de texto circundante sin afectar tabla
  - Test 10.3: Múltiples tablas en un fragmento
  - Test 10.4: Fallback a original cuando validación falla
  - Test 10.5: Fragmentos sin tablas no sufren regresiones

- **Performance** (Task 12.3)
  - Medir tiempo de detección para diferentes tamaños (1KB, 5KB, 10KB)
  - Verificar que caché reduce tiempo en 2da llamada
  - Verificar overhead <15% en pipeline completo

**Ejecutar:**
```bash
pytest tests/retrieval/test_table_integration.py -v
```

## Ejecutar Todos los Tests de Tablas

### Opción 1: Usando pytest directamente
```bash
# Todos los tests de retrieval
pytest tests/retrieval/ -v

# Solo tests de tablas
pytest tests/retrieval/test_table_processor.py tests/retrieval/test_table_integration.py -v

# Con cobertura
pytest tests/retrieval/ -v --cov=src/retrieval/table_processor --cov-report=html
```

### Opción 2: Usando el Test Center
```bash
python tests/run_tests.py
```

Luego selecciona:
- Opción 4: "Pruebas de Tablas (TASK-015 Completo)"

O navega a:
- Opción 1 → Opción 6: "Table Processor" (tests unitarios)
- Opción 2 → Opción 4: "Table Integration" (tests de integración)

## Fixtures Disponibles

Las siguientes fixtures están disponibles en `tests/conftest.py`:

- `sample_markdown_table`: Tabla Markdown básica para tests
- `sample_table_with_alignment`: Tabla con alineación (left, center, right)
- `sample_fragment_with_table`: Fragmento legal completo con tabla
- `sample_multiple_tables`: Fragmento con múltiples tablas

**Uso:**
```python
def test_example(sample_markdown_table):
    parser = MarkdownTableParser()
    table = parser.parse(sample_markdown_table)
    assert table.column_count == 3
```

## Métricas de Éxito

Los tests verifican que el sistema cumple con los siguientes requisitos:

| Métrica | Objetivo | Verificación |
|---------|----------|--------------|
| **Integridad de tablas** | <5% tablas con filas/columnas faltantes | Tests 10.1, 10.3 |
| **Performance detección** | <50ms para fragmentos de 5KB | Test de performance |
| **Overhead total** | <15% en pipeline completo | Test de performance |
| **Round-trip preservation** | 100% preservación estructura | Tests de round-trip |
| **No regresiones** | Fragmentos sin tablas funcionan igual | Test 10.5 |

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'src'"

**Solución:** Asegúrate de ejecutar los tests desde la raíz del proyecto:
```bash
cd /path/to/Rag_Analista_Legal
pytest tests/retrieval/ -v
```

### Error: "AWS credentials not found"

**Solución:** Los tests de integración pueden requerir credenciales AWS. Usa la fixture `mock_env_credentials` o configura tus credenciales:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-2
```

### Tests muy lentos

**Solución:** Los tests de integración que usan LLM real pueden ser lentos. Para tests rápidos, ejecuta solo los unitarios:
```bash
pytest tests/retrieval/test_table_processor.py -v
```

## Contribuir

Al agregar nuevos tests:

1. **Mantén la estructura:** Tests unitarios en `test_table_processor.py`, integración en `test_table_integration.py`
2. **Usa fixtures:** Reutiliza las fixtures de `conftest.py` cuando sea posible
3. **Documenta:** Agrega docstrings explicando qué verifica cada test
4. **Logging:** Usa `logger.info()` para mostrar resultados intermedios
5. **Assertions claras:** Usa mensajes descriptivos en los asserts

**Ejemplo:**
```python
def test_new_feature(sample_markdown_table):
    """Test: Verificar nueva funcionalidad X."""
    logger.info("\n" + "="*80)
    logger.info("TEST: Nueva funcionalidad X")
    logger.info("="*80)
    
    # Setup
    detector = TableDetector()
    
    # Execute
    result = detector.new_method(sample_markdown_table)
    
    # Verify
    logger.info(f"  Result: {result}")
    assert result == expected_value, "Mensaje descriptivo del error"
    
    logger.info("✅ TEST PASADO\n")
```

## Referencias

- **Spec TASK-015:** `.kiro/specs/table-optimization/`
- **Implementación:** `src/retrieval/table_processor.py`
- **Prompts:** `src/retrieval/table_prompts.py`
- **Integración:** `src/retrieval/contextual_compression.py`

---

**Autor:** Fenix Tech Líder  
**Fecha:** 28/04/2026  
**Versión:** 1.0.0
