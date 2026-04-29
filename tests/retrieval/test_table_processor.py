"""
Tests Unitarios para Table Processor

Suite de tests para validar el funcionamiento de cada componente del
sistema de procesamiento de tablas Markdown.

Autor: Fenix Tech Líder
Fecha: 28/04/2026
"""

import pytest
from typing import List

from src.retrieval.table_processor import (
    # Modelos de datos
    TableCell,
    TableRow,
    TableStructure,
    TableDetectionResult,
    # Excepciones
    TableProcessingError,
    TableParseError,
    TableValidationError,
    # Componentes
    TableDetector,
    MarkdownTableParser,
    MarkdownTablePrinter,
    TablePreserver,
    TableMetrics,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def simple_table_markdown() -> str:
    """Tabla Markdown simple bien formada."""
    return """| Columna A | Columna B | Columna C |
|-----------|-----------|-----------|
| Valor 1   | Valor 2   | Valor 3   |
| Valor 4   | Valor 5   | Valor 6   |"""


@pytest.fixture
def table_with_alignment() -> str:
    """Tabla con alineación de columnas."""
    return """| Left | Center | Right |
|:-----|:------:|------:|
| A    | B      | C     |
| D    | E      | F     |"""


@pytest.fixture
def table_with_empty_cells() -> str:
    """Tabla con celdas vacías."""
    return """| Col1 | Col2 | Col3 |
|------|------|------|
| A    |      | C    |
|      | B    |      |"""


@pytest.fixture
def table_detector() -> TableDetector:
    """Instancia de TableDetector."""
    return TableDetector()


@pytest.fixture
def table_parser() -> MarkdownTableParser:
    """Instancia de MarkdownTableParser."""
    return MarkdownTableParser()


@pytest.fixture
def table_printer() -> MarkdownTablePrinter:
    """Instancia de MarkdownTablePrinter."""
    return MarkdownTablePrinter()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: MODELOS DE DATOS
# ══════════════════════════════════════════════════════════════════════════════


class TestTableCell:
    """Tests para TableCell."""
    
    def test_create_cell(self):
        """Test: Crear celda con contenido."""
        cell = TableCell(content="Test", alignment="left")
        assert cell.content == "Test"
        assert cell.alignment == "left"
    
    def test_cell_str(self):
        """Test: Conversión a string elimina espacios."""
        cell = TableCell(content="  Test  ")
        assert str(cell) == "Test"


class TestTableRow:
    """Tests para TableRow."""
    
    def test_create_row(self):
        """Test: Crear fila con celdas."""
        cells = [TableCell("A"), TableCell("B"), TableCell("C")]
        row = TableRow(cells=cells, is_header=True)
        assert len(row) == 3
        assert row.is_header is True
    
    def test_row_indexing(self):
        """Test: Acceso a celdas por índice."""
        cells = [TableCell("A"), TableCell("B")]
        row = TableRow(cells=cells)
        assert row[0].content == "A"
        assert row[1].content == "B"


class TestTableStructure:
    """Tests para TableStructure."""
    
    def test_create_structure(self):
        """Test: Crear estructura de tabla."""
        header = TableRow([TableCell("H1"), TableCell("H2")])
        rows = [
            TableRow([TableCell("A"), TableCell("B")]),
            TableRow([TableCell("C"), TableCell("D")]),
        ]
        table = TableStructure(header=header, rows=rows)
        
        assert table.column_count == 2
        assert table.row_count == 2
    
    def test_validate_consistent_columns(self):
        """Test: Validación detecta columnas consistentes."""
        header = TableRow([TableCell("H1"), TableCell("H2")])
        rows = [TableRow([TableCell("A"), TableCell("B")])]
        table = TableStructure(header=header, rows=rows)
        
        is_valid, error = table.validate()
        assert is_valid is True
        assert error is None
    
    def test_validate_inconsistent_columns(self):
        """Test: Validación detecta columnas inconsistentes."""
        header = TableRow([TableCell("H1"), TableCell("H2")])
        rows = [TableRow([TableCell("A")])]  # Solo 1 columna
        table = TableStructure(header=header, rows=rows)
        
        is_valid, error = table.validate()
        assert is_valid is False
        assert "columnas" in error.lower()
    
    def test_to_dict(self):
        """Test: Serialización a diccionario."""
        header = TableRow([TableCell("H1"), TableCell("H2")])
        rows = [TableRow([TableCell("A"), TableCell("B")])]
        table = TableStructure(header=header, rows=rows)
        
        data = table.to_dict()
        assert data["header"] == ["H1", "H2"]
        assert data["rows"] == [["A", "B"]]
        assert data["column_count"] == 2
        assert data["row_count"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: TABLE DETECTOR (Tarea 2.3)
# ══════════════════════════════════════════════════════════════════════════════


class TestTableDetector:
    """Tests para TableDetector."""
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 2.1")
    def test_detect_valid_table_with_separator(self, table_detector, simple_table_markdown):
        """Test: Detectar tabla válida con separador → confidence=1.0."""
        result = table_detector.detect(simple_table_markdown)
        
        assert result.contains_table is True
        assert result.table_count == 1
        assert result.confidence == 1.0
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 2.1")
    def test_detect_table_without_separator(self, table_detector):
        """Test: Detectar tabla sin separador → confidence=0.8."""
        markdown = """| A | B |
| C | D |
| E | F |"""
        result = table_detector.detect(markdown)
        
        assert result.contains_table is True
        assert result.confidence == 0.8
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 2.1")
    def test_reject_false_positive(self, table_detector):
        """Test: Rechazar false positive (pipes en texto normal)."""
        text = "El artículo dice: A | B | C son opciones válidas."
        result = table_detector.detect(text)
        
        assert result.contains_table is False
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 2.2")
    def test_detect_multiple_tables(self, table_detector):
        """Test: Detectar múltiples tablas en un fragmento."""
        markdown = """Primera tabla:
| A | B |
|---|---|
| 1 | 2 |

Segunda tabla:
| X | Y |
|---|---|
| 3 | 4 |"""
        result = table_detector.detect(markdown)
        
        assert result.table_count == 2
        assert len(result.table_ranges) == 2
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 2.1")
    def test_edge_case_empty_table(self, table_detector):
        """Test: Edge case - tabla vacía."""
        markdown = """| A | B |
|---|---|"""
        result = table_detector.detect(markdown)
        
        # Debe detectarse como tabla válida aunque no tenga filas de datos
        assert result.contains_table is True
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 2.1")
    def test_edge_case_single_row(self, table_detector):
        """Test: Edge case - una sola fila."""
        markdown = "| A | B | C |"
        result = table_detector.detect(markdown)
        
        # Una sola fila no es suficiente para ser tabla
        assert result.contains_table is False


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: MARKDOWN TABLE PARSER (Tarea 3.4)
# ══════════════════════════════════════════════════════════════════════════════


class TestMarkdownTableParser:
    """Tests para MarkdownTableParser."""
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 3.1")
    def test_parse_well_formed_table(self, table_parser, simple_table_markdown):
        """Test: Parsear tabla bien formada → TableStructure válida."""
        table = table_parser.parse(simple_table_markdown)
        
        assert table.column_count == 3
        assert table.row_count == 2
        assert table.header.cells[0].content == "Columna A"
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 3.2")
    def test_detect_alignment(self, table_parser, table_with_alignment):
        """Test: Detectar alineación correcta (left, center, right)."""
        table = table_parser.parse(table_with_alignment)
        
        assert table.alignments == ["left", "center", "right"]
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 3.3")
    def test_handle_empty_cells(self, table_parser, table_with_empty_cells):
        """Test: Manejar celdas vacías → preservar como ''."""
        table = table_parser.parse(table_with_empty_cells)
        
        # Primera fila de datos: "A", "", "C"
        assert table.rows[0].cells[1].content == ""
        # Segunda fila de datos: "", "B", ""
        assert table.rows[1].cells[0].content == ""
        assert table.rows[1].cells[2].content == ""
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 3.3")
    def test_handle_escaped_pipes(self, table_parser):
        """Test: Manejar pipes escapados → \\| se convierte en |."""
        markdown = """| Col1 | Col2 |
|------|------|
| A\\|B | C    |"""
        table = table_parser.parse(markdown)
        
        assert table.rows[0].cells[0].content == "A|B"
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 3.3")
    def test_error_handling_inconsistent_columns(self, table_parser):
        """Test: Error handling (columnas inconsistentes) → TableParseError."""
        markdown = """| A | B | C |
|---|---|---|
| 1 | 2 |"""  # Falta una columna
        
        with pytest.raises(TableParseError) as exc_info:
            table_parser.parse(markdown)
        
        assert "columna" in str(exc_info.value).lower()
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 3.3")
    def test_table_without_separator(self, table_parser):
        """Test: Tabla sin separador → todas las filas como data."""
        markdown = """| A | B |
| C | D |
| E | F |"""
        table = table_parser.parse(markdown)
        
        # Primera fila se toma como header
        assert table.header.cells[0].content == "A"
        # Resto son filas de datos
        assert table.row_count == 2


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: MARKDOWN TABLE PRINTER (Tarea 4.3)
# ══════════════════════════════════════════════════════════════════════════════


class TestMarkdownTablePrinter:
    """Tests para MarkdownTablePrinter."""
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 4.1")
    def test_format_with_alignment(self, table_printer):
        """Test: Formatear tabla con alineación correcta."""
        header = TableRow([TableCell("A"), TableCell("B"), TableCell("C")])
        rows = [TableRow([TableCell("1"), TableCell("2"), TableCell("3")])]
        table = TableStructure(header=header, rows=rows, alignments=["left", "center", "right"])
        
        markdown = table_printer.format(table)
        
        # Verificar que contiene pipes alineados
        assert "|" in markdown
        # Verificar que contiene separador con alineación
        assert ":---" in markdown or "---:" in markdown
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 4.1")
    def test_calculate_column_widths(self, table_printer):
        """Test: Calcular anchos de columna correctamente."""
        header = TableRow([TableCell("Short"), TableCell("Very Long Header")])
        rows = [TableRow([TableCell("A"), TableCell("B")])]
        table = TableStructure(header=header, rows=rows)
        
        widths = table_printer.calculate_column_widths(table)
        
        # Ancho de columna 1 = len("Short") = 5
        # Ancho de columna 2 = len("Very Long Header") = 16
        assert widths[0] >= 5
        assert widths[1] >= 16
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 4.1")
    def test_preserve_cell_content(self, table_printer):
        """Test: Preservar contenido de celdas sin truncar."""
        header = TableRow([TableCell("Header")])
        rows = [TableRow([TableCell("Very long content that should not be truncated")])]
        table = TableStructure(header=header, rows=rows)
        
        markdown = table_printer.format(table)
        
        assert "Very long content that should not be truncated" in markdown
    
    @pytest.mark.skip(reason="Implementación pendiente en Tarea 4.1")
    def test_edge_case_special_characters(self, table_printer):
        """Test: Edge case - caracteres especiales."""
        header = TableRow([TableCell("Col")])
        rows = [TableRow([TableCell("A|B & C < D > E")])]
        table = TableStructure(header=header, rows=rows)
        
        markdown = table_printer.format(table)
        
        # Pipes internos deben escaparse
        assert "A|B & C < D > E" in markdown or "A\\|B & C < D > E" in markdown


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: TABLE PRESERVER (Tarea 5.4)
# ══════════════════════════════════════════════════════════════════════════════


class TestTablePreserver:
    """Tests para TablePreserver (Tarea 5.4)."""
    
    def test_preserve_complete_table(self):
        """Test: Preservar tabla completa durante compresión LLM."""
        from unittest.mock import Mock
        
        # Mock del LLM
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "Texto comprimido relevante."
        mock_llm.invoke = Mock(return_value=mock_response)
        
        # Parser real
        parser = MarkdownTableParser()
        
        # Crear preserver
        preserver = TablePreserver(llm=mock_llm, parser=parser)
        
        # Fragmento con tabla
        fragment = """Este es un texto largo que puede ser comprimido.
Contiene información adicional que no es relevante.

| Artículo | Plazo | Requisito |
|----------|-------|-----------|
| 2.2.1.4  | 30 días | Solicitud |
| 2.2.1.5  | 15 días | Planos |

Más texto que puede ser comprimido después de la tabla."""
        
        # Rangos de la tabla (líneas 3-6)
        table_ranges = [(3, 6)]
        
        # Preservar
        result = preserver.preserve_with_llm(fragment, "¿Cuáles son los plazos?", table_ranges)
        
        # Verificar que la tabla está completa en el resultado
        assert "| Artículo | Plazo | Requisito |" in result
        assert "| 2.2.1.4  | 30 días | Solicitud |" in result
        assert "| 2.2.1.5  | 15 días | Planos |" in result
        
        # Verificar que el LLM fue llamado para comprimir texto
        assert mock_llm.invoke.called
        
        # Verificar contador
        assert preserver.tables_preserved == 1
    
    def test_validation_detects_missing_columns(self):
        """Test: Validación detecta tabla corrupta (columnas faltantes) → fallback."""
        parser = MarkdownTableParser()
        mock_llm = Mock()
        preserver = TablePreserver(llm=mock_llm, parser=parser)
        
        # Tabla original con 3 columnas
        original_table = """| Col1 | Col2 | Col3 |
|------|------|------|
| A    | B    | C    |
| D    | E    | F    |"""
        
        # Tabla corrupta con 2 columnas
        corrupted_table = """| Col1 | Col2 |
|------|------|
| A    | B    |
| D    | E    |"""
        
        # Validar
        is_valid, error = preserver.validate_preservation(original_table, corrupted_table)
        
        # Verificar que detecta el error
        assert is_valid is False
        assert error is not None
        assert "columnas" in error.lower()
        
        # Verificar contador de violaciones
        assert preserver.integrity_violations == 1
    
    def test_validation_detects_missing_rows(self):
        """Test: Validación detecta tabla corrupta (filas faltantes) → fallback."""
        parser = MarkdownTableParser()
        mock_llm = Mock()
        preserver = TablePreserver(llm=mock_llm, parser=parser)
        
        # Tabla original con 3 filas de datos
        original_table = """| Col1 | Col2 |
|------|------|
| A    | B    |
| C    | D    |
| E    | F    |"""
        
        # Tabla corrupta con 2 filas de datos
        corrupted_table = """| Col1 | Col2 |
|------|------|
| A    | B    |
| C    | D    |"""
        
        # Validar
        is_valid, error = preserver.validate_preservation(original_table, corrupted_table)
        
        # Verificar que detecta el error
        assert is_valid is False
        assert error is not None
        assert "filas" in error.lower()
        
        # Verificar contador de violaciones
        assert preserver.integrity_violations == 1
    
    def test_compress_surrounding_text(self):
        """Test: Comprimir texto circundante sin afectar tabla."""
        from unittest.mock import Mock
        
        # Mock del LLM que retorna texto comprimido
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "Texto comprimido."
        mock_llm.invoke = Mock(return_value=mock_response)
        
        parser = MarkdownTableParser()
        preserver = TablePreserver(llm=mock_llm, parser=parser)
        
        # Fragmento con mucho texto antes y después de la tabla
        fragment = """Este es un párrafo muy largo con mucha información que no es relevante
para la consulta del usuario. Contiene detalles adicionales, contexto histórico,
y referencias que pueden ser comprimidas sin perder el sentido principal.

| Artículo | Valor |
|----------|-------|
| 2.2.1.4  | 100   |

Este es otro párrafo largo después de la tabla con información adicional
que también puede ser comprimida. Incluye explicaciones detalladas y
ejemplos que no son críticos para la respuesta."""
        
        # Rangos de la tabla (líneas 4-6)
        table_ranges = [(4, 6)]
        
        # Preservar
        result = preserver.preserve_with_llm(fragment, "¿Cuál es el valor del artículo?", table_ranges)
        
        # Verificar que la tabla está intacta
        assert "| Artículo | Valor |" in result
        assert "| 2.2.1.4  | 100   |" in result
        
        # Verificar que el LLM fue llamado 2 veces (texto antes y después)
        assert mock_llm.invoke.call_count == 2
        
        # Verificar que el resultado contiene texto comprimido
        assert "Texto comprimido." in result
    
    def test_handle_multiple_tables(self):
        """Test: Manejar múltiples tablas en un fragmento."""
        from unittest.mock import Mock
        
        # Mock del LLM
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "Comprimido."
        mock_llm.invoke = Mock(return_value=mock_response)
        
        parser = MarkdownTableParser()
        preserver = TablePreserver(llm=mock_llm, parser=parser)
        
        # Fragmento con 2 tablas
        fragment = """Texto inicial.

| Tabla1 | Col |
|--------|-----|
| A      | B   |

Texto intermedio.

| Tabla2 | Col |
|--------|-----|
| C      | D   |

Texto final."""
        
        # Rangos de ambas tablas
        table_ranges = [(2, 4), (8, 10)]
        
        # Preservar
        result = preserver.preserve_with_llm(fragment, "¿Qué tablas hay?", table_ranges)
        
        # Verificar que ambas tablas están presentes
        assert "| Tabla1 | Col |" in result
        assert "| A      | B   |" in result
        assert "| Tabla2 | Col |" in result
        assert "| C      | D   |" in result
        
        # Verificar contador
        assert preserver.tables_preserved == 2


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: TABLE PROMPTS (Tarea 6.2)
# ══════════════════════════════════════════════════════════════════════════════


class TestTablePrompts:
    """Tests para validación de prompts especializados (Tarea 6.2)."""
    
    def test_prompt_instructs_table_preservation(self):
        """Test: Prompt instruye preservación completa de tablas."""
        from src.retrieval.table_prompts import TABLE_COMPRESS_PROMPT
        
        # Obtener el prompt formateado
        messages = TABLE_COMPRESS_PROMPT.format_messages(
            question="¿Cuáles son los plazos?",
            context="Texto con tabla..."
        )
        
        # Verificar que el prompt contiene instrucciones de preservación
        prompt_text = str(messages)
        
        # Verificar instrucciones críticas
        assert "NUNCA elimines filas o columnas" in prompt_text
        assert "SIEMPRE preserva la estructura completa" in prompt_text
        assert "inclúyela COMPLETA" in prompt_text
        
        # Verificar que menciona tablas Markdown
        assert "Markdown" in prompt_text or "markdown" in prompt_text
    
    def test_prompt_includes_preservation_examples(self):
        """Test: Prompt incluye ejemplos de preservación correcta."""
        from src.retrieval.table_prompts import TABLE_COMPRESS_PROMPT
        
        # Obtener el prompt formateado
        messages = TABLE_COMPRESS_PROMPT.format_messages(
            question="Test",
            context="Test"
        )
        
        prompt_text = str(messages)
        
        # Verificar que incluye ejemplo
        assert "EJEMPLO" in prompt_text or "Ejemplo" in prompt_text
        
        # Verificar que el ejemplo muestra una tabla
        assert "|" in prompt_text  # Pipes de tabla Markdown
        assert "---" in prompt_text  # Separador de tabla
    
    def test_prompt_maintains_markdown_syntax(self):
        """Test: Prompt mantiene sintaxis Markdown correcta."""
        from src.retrieval.table_prompts import TABLE_COMPRESS_PROMPT
        
        # Obtener el prompt formateado
        messages = TABLE_COMPRESS_PROMPT.format_messages(
            question="Test",
            context="Test"
        )
        
        prompt_text = str(messages)
        
        # Verificar que menciona sintaxis Markdown
        assert "sintaxis" in prompt_text.lower()
        assert "pipes" in prompt_text.lower() or "|" in prompt_text
        
        # Verificar que muestra formato correcto
        assert "| Columna" in prompt_text or "| Col" in prompt_text


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: TABLE METRICS
# ══════════════════════════════════════════════════════════════════════════════


class TestTableMetrics:
    """Tests para TableMetrics."""
    
    def test_record_detection(self):
        """Test: Registrar detección de tablas."""
        metrics = TableMetrics()
        metrics.record_detection(detection_time_ms=10.5, table_count=2)
        
        assert metrics.tables_detected == 2
        assert len(metrics.detection_times_ms) == 1
        assert metrics.detection_times_ms[0] == 10.5
    
    def test_record_preservation_success(self):
        """Test: Registrar preservación exitosa."""
        metrics = TableMetrics()
        metrics.record_preservation(preservation_time_ms=50.0, success=True)
        
        assert metrics.tables_preserved == 1
        assert metrics.table_integrity_violations == 0
    
    def test_record_preservation_failure(self):
        """Test: Registrar fallo de preservación."""
        metrics = TableMetrics()
        metrics.record_preservation(preservation_time_ms=50.0, success=False)
        
        assert metrics.tables_preserved == 0
        assert metrics.table_integrity_violations == 1
    
    def test_get_summary(self):
        """Test: Obtener resumen de métricas."""
        metrics = TableMetrics()
        metrics.record_detection(10.0, 1)
        metrics.record_detection(20.0, 1)
        metrics.record_preservation(50.0, True)
        metrics.record_preservation(60.0, True)
        
        summary = metrics.get_summary()
        
        assert summary["tables_detected"] == 2
        assert summary["tables_preserved"] == 2
        assert summary["avg_detection_time_ms"] == 15.0
        assert summary["avg_preservation_time_ms"] == 55.0
        assert summary["success_rate"] == 1.0


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: LOGGING Y MÉTRICAS (Tarea 9.3)
# ══════════════════════════════════════════════════════════════════════════════


class TestLoggingAndMetrics:
    """Tests para logging y métricas de observabilidad (Tarea 9.3)."""
    
    def test_table_detector_logging(self, caplog):
        """Test: Verificar que TableDetector genera logs correctos."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        detector = TableDetector()
        
        # Detectar tabla
        markdown = """| A | B |
|---|---|
| 1 | 2 |"""
        
        result = detector.detect(markdown)
        
        # Verificar que se generaron logs
        assert any("[TABLE_DETECTOR]" in record.message for record in caplog.records)
        
        # Verificar que el log contiene información relevante
        log_messages = [record.message for record in caplog.records if "[TABLE_DETECTOR]" in record.message]
        assert len(log_messages) > 0
    
    def test_table_parser_logging(self, caplog):
        """Test: Verificar que MarkdownTableParser genera logs correctos."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        parser = MarkdownTableParser()
        
        # Parsear tabla
        markdown = """| Col1 | Col2 |
|------|------|
| A    | B    |"""
        
        table = parser.parse(markdown)
        
        # Verificar que se generaron logs con prefijo correcto
        assert any("[TABLE_PARSER]" in record.message for record in caplog.records)
        
        # Verificar que el log menciona dimensiones
        log_messages = [record.message for record in caplog.records if "[TABLE_PARSER]" in record.message]
        assert any("columnas" in msg.lower() or "filas" in msg.lower() for msg in log_messages)
    
    def test_table_preserver_logging(self, caplog):
        """Test: Verificar que TablePreserver genera logs correctos."""
        import logging
        from unittest.mock import Mock
        
        caplog.set_level(logging.DEBUG)
        
        # Mock del LLM
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "Comprimido."
        mock_llm.invoke = Mock(return_value=mock_response)
        
        parser = MarkdownTableParser()
        preserver = TablePreserver(llm=mock_llm, parser=parser)
        
        # Verificar log de inicialización
        assert any("[TABLE_PRESERVER]" in record.message and "Inicializado" in record.message 
                   for record in caplog.records)
    
    def test_metrics_increment_correctly(self):
        """Test: Verificar que métricas se incrementan correctamente."""
        metrics = TableMetrics()
        
        # Estado inicial
        assert metrics.tables_detected == 0
        assert metrics.tables_preserved == 0
        assert metrics.table_integrity_violations == 0
        
        # Registrar detección
        metrics.record_detection(10.0, 2)
        assert metrics.tables_detected == 2
        
        # Registrar preservación exitosa
        metrics.record_preservation(50.0, True)
        assert metrics.tables_preserved == 1
        assert metrics.table_integrity_violations == 0
        
        # Registrar fallo
        metrics.record_preservation(60.0, False)
        assert metrics.tables_preserved == 1  # No incrementa
        assert metrics.table_integrity_violations == 1  # Incrementa
    
    def test_log_format_with_prefixes(self, caplog):
        """Test: Verificar formato de logs (prefijos correctos)."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        # Crear componentes
        detector = TableDetector()
        parser = MarkdownTableParser()
        
        # Ejecutar operaciones
        markdown = """| A | B |
|---|---|
| 1 | 2 |"""
        
        detector.detect(markdown)
        parser.parse(markdown)
        
        # Verificar prefijos
        prefixes = ["[TABLE_DETECTOR]", "[TABLE_PARSER]"]
        
        for prefix in prefixes:
            assert any(prefix in record.message for record in caplog.records), \
                f"No se encontró log con prefijo {prefix}"
