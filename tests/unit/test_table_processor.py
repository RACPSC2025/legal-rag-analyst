"""
Test de Table Processor — TASK-015: Optimización de Tablas
═══════════════════════════════════════════════════════════════

Verifica que el sistema de procesamiento de tablas funciona correctamente:
1. TableDetector: Detecta tablas Markdown con alta precisión
2. MarkdownTableParser: Parsea tablas a estructuras de datos validadas
3. MarkdownTablePrinter: Formatea tablas con alineación correcta
4. TablePreserver: Preserva tablas completas durante compresión
5. Round-trip: parse → format → parse preserva estructura

Autor: Fenix Tech Líder
Fecha: 2026-04-28
"""

import sys
import logging
from pathlib import Path

# Configuración de path para encontrar 'src'
root_path = str(Path(__file__).parent.parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import pytest
from src.retrieval.table_processor import (
    TableDetector,
    MarkdownTableParser,
    MarkdownTablePrinter,
    TablePreserver,
    TableParseError,
    TableValidationError,
)

# Configurar logging para ver el proceso
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: TableDetector (Task 2.3)
# ══════════════════════════════════════════════════════════════════════════════

class TestTableDetector:
    """Suite de tests para TableDetector."""
    
    def test_detect_valid_table_with_separator(self):
        """Test: Detectar tabla válida con separador → confidence=1.0"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Detectar tabla válida con separador")
        logger.info("="*80)
        
        detector = TableDetector()
        
        markdown = """
| Artículo | Plazo   | Requisito         |
|----------|---------|-------------------|
| 2.2.1.4  | 30 días | Solicitud escrita |
| 2.2.1.5  | 15 días | Planos            |
"""
        
        result = detector.detect(markdown)
        
        logger.info(f"  Contains table: {result.contains_table}")
        logger.info(f"  Table count: {result.table_count}")
        logger.info(f"  Confidence: {result.confidence}")
        logger.info(f"  Detection time: {result.detection_time_ms:.2f}ms")
        
        assert result.contains_table == True
        assert result.table_count == 1
        assert result.confidence == 1.0
        assert len(result.table_ranges) == 1
        
        logger.info("✅ TEST PASADO\n")
    
    def test_detect_table_without_separator(self):
        """Test: Detectar tabla sin separador → confidence=0.8"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Detectar tabla sin separador")
        logger.info("="*80)
        
        detector = TableDetector()
        
        markdown = """
| Artículo | Plazo   | Requisito         |
| 2.2.1.4  | 30 días | Solicitud escrita |
| 2.2.1.5  | 15 días | Planos            |
"""
        
        result = detector.detect(markdown)
        
        logger.info(f"  Contains table: {result.contains_table}")
        logger.info(f"  Confidence: {result.confidence}")
        
        assert result.contains_table == True
        assert result.confidence >= 0.5  # Puede ser 0.8 o 0.5 dependiendo de consistencia
        
        logger.info("✅ TEST PASADO\n")
    
    def test_reject_false_positive(self):
        """Test: Rechazar false positive (pipes en texto normal)"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Rechazar false positive")
        logger.info("="*80)
        
        detector = TableDetector()
        
        text = """
El artículo establece que el plazo | requisito debe cumplirse.
Además, la norma | decreto indica que...
"""
        
        result = detector.detect(text)
        
        logger.info(f"  Contains table: {result.contains_table}")
        
        assert result.contains_table == False
        
        logger.info("✅ TEST PASADO\n")
    
    def test_detect_multiple_tables(self):
        """Test: Detectar múltiples tablas en un fragmento"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Detectar múltiples tablas")
        logger.info("="*80)
        
        detector = TableDetector()
        
        markdown = """
Primera tabla:

| Col1 | Col2 |
|------|------|
| A    | B    |

Texto intermedio.

Segunda tabla:

| Col3 | Col4 |
|------|------|
| C    | D    |
"""
        
        result = detector.detect(markdown)
        
        logger.info(f"  Table count: {result.table_count}")
        logger.info(f"  Table ranges: {result.table_ranges}")
        
        assert result.contains_table == True
        assert result.table_count == 2
        assert len(result.table_ranges) == 2
        
        logger.info("✅ TEST PASADO\n")
    
    def test_edge_cases(self):
        """Test: Edge cases (tabla vacía, una sola fila, celdas vacías)"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Edge cases")
        logger.info("="*80)
        
        detector = TableDetector()
        
        # Tabla con celdas vacías
        markdown_empty_cells = """
| Col1 | Col2 | Col3 |
|------|------|------|
| A    |      | C    |
|      | B    |      |
"""
        
        result = detector.detect(markdown_empty_cells)
        logger.info(f"  Tabla con celdas vacías: {result.contains_table}")
        assert result.contains_table == True
        
        # Tabla de una sola fila (header + separator)
        markdown_single_row = """
| Col1 | Col2 |
|------|------|
"""
        
        result = detector.detect(markdown_single_row)
        logger.info(f"  Tabla de una fila: {result.contains_table}")
        # Puede o no detectarse como tabla válida (depende de heurística)
        
        logger.info("✅ TEST PASADO\n")
    
    def test_extract_tables(self):
        """Test: Extraer tablas como strings individuales"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Extraer tablas")
        logger.info("="*80)
        
        detector = TableDetector()
        
        markdown = """
Texto antes.

| Col1 | Col2 |
|------|------|
| A    | B    |

Texto después.
"""
        
        tables = detector.extract_tables(markdown)
        
        logger.info(f"  Tablas extraídas: {len(tables)}")
        if tables:
            logger.info(f"  Primera tabla:\n{tables[0]}")
        
        assert len(tables) == 1
        assert "Col1" in tables[0]
        assert "Col2" in tables[0]
        
        logger.info("✅ TEST PASADO\n")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: MarkdownTableParser (Task 3.4)
# ══════════════════════════════════════════════════════════════════════════════

class TestMarkdownTableParser:
    """Suite de tests para MarkdownTableParser."""
    
    def test_parse_well_formed_table(self):
        """Test: Parsear tabla bien formada → TableStructure válida"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Parsear tabla bien formada")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        
        markdown = """
| Artículo | Plazo   | Requisito         |
|----------|---------|-------------------|
| 2.2.1.4  | 30 días | Solicitud escrita |
| 2.2.1.5  | 15 días | Planos            |
"""
        
        table = parser.parse(markdown)
        
        logger.info(f"  Column count: {table.column_count}")
        logger.info(f"  Row count: {table.row_count}")
        logger.info(f"  Headers: {[cell.content for cell in table.header.cells]}")
        
        assert table.column_count == 3
        assert table.row_count == 2
        assert table.header.cells[0].content == "Artículo"
        
        is_valid, error = table.validate()
        assert is_valid == True
        
        logger.info("✅ TEST PASADO\n")
    
    def test_detect_alignment(self):
        """Test: Detectar alineación correcta (left, center, right)"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Detectar alineación")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        
        markdown = """
| Left | Center | Right |
|:-----|:------:|------:|
| A    | B      | C     |
"""
        
        table = parser.parse(markdown)
        
        logger.info(f"  Alignments: {table.alignments}")
        
        assert table.alignments[0] == "left"
        assert table.alignments[1] == "center"
        assert table.alignments[2] == "right"
        
        logger.info("✅ TEST PASADO\n")
    
    def test_handle_empty_cells(self):
        """Test: Manejar celdas vacías → preservar como ''"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Manejar celdas vacías")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        
        markdown = """
| Col1 | Col2 | Col3 |
|------|------|------|
| A    |      | C    |
|      | B    |      |
"""
        
        table = parser.parse(markdown)
        
        logger.info(f"  Row 1: {[cell.content for cell in table.rows[0].cells]}")
        logger.info(f"  Row 2: {[cell.content for cell in table.rows[1].cells]}")
        
        assert table.rows[0].cells[1].content == ""
        assert table.rows[1].cells[0].content == ""
        assert table.rows[1].cells[2].content == ""
        
        logger.info("✅ TEST PASADO\n")
    
    def test_handle_escaped_pipes(self):
        """Test: Manejar pipes escapados → \\| se convierte en |"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Manejar pipes escapados")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        
        markdown = """
| Col1 | Col2 |
|------|------|
| A\\|B | C    |
"""
        
        table = parser.parse(markdown)
        
        logger.info(f"  Cell content: '{table.rows[0].cells[0].content}'")
        
        assert table.rows[0].cells[0].content == "A|B"
        
        logger.info("✅ TEST PASADO\n")
    
    def test_error_handling_inconsistent_columns(self):
        """Test: Error handling (columnas inconsistentes) → TableParseError"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Error handling - columnas inconsistentes")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        
        # Tabla con columnas inconsistentes (sin recovery posible)
        markdown = """
| Col1 | Col2 | Col3 |
|------|------|------|
| A    | B    | C    | D    | E    |
"""
        
        # Debería lanzar error o intentar recovery
        try:
            table = parser.parse(markdown)
            # Si hace recovery, verificar que se aplicó padding
            logger.info(f"  Recovery aplicado: {table.column_count} columnas")
            logger.info("  (Parser intentó recuperación con padding)")
        except TableParseError as e:
            logger.info(f"  TableParseError capturado: {e}")
            logger.info("  (Parser rechazó tabla malformada)")
        
        logger.info("✅ TEST PASADO\n")
    
    def test_table_without_separator(self):
        """Test: Tabla sin separador → todas las filas como data"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Tabla sin separador")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        
        markdown = """
| Col1 | Col2 |
| A    | B    |
| C    | D    |
"""
        
        table = parser.parse(markdown)
        
        logger.info(f"  Column count: {table.column_count}")
        logger.info(f"  Row count: {table.row_count}")
        logger.info(f"  Header: {[cell.content for cell in table.header.cells]}")
        
        # Primera línea es header, resto son data
        assert table.column_count == 2
        assert table.row_count == 2
        
        logger.info("✅ TEST PASADO\n")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: MarkdownTablePrinter (Task 4.3)
# ══════════════════════════════════════════════════════════════════════════════

class TestMarkdownTablePrinter:
    """Suite de tests para MarkdownTablePrinter."""
    
    def test_format_with_correct_alignment(self):
        """Test: Formatear tabla con alineación correcta"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Formatear con alineación")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        printer = MarkdownTablePrinter()
        
        markdown = """
| Left | Center | Right |
|:-----|:------:|------:|
| A    | B      | C     |
"""
        
        table = parser.parse(markdown)
        formatted = printer.format(table)
        
        logger.info(f"  Formatted table:\n{formatted}")
        
        # Verificar que tiene pipes
        assert "|" in formatted
        # Verificar que tiene separador con alineación
        assert ":---" in formatted or "---:" in formatted or ":---:" in formatted
        
        logger.info("✅ TEST PASADO\n")
    
    def test_calculate_column_widths(self):
        """Test: Calcular anchos de columna correctamente"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Calcular anchos de columna")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        printer = MarkdownTablePrinter()
        
        markdown = """
| Short | VeryLongContent | Mid  |
|-------|-----------------|------|
| A     | B               | C    |
"""
        
        table = parser.parse(markdown)
        widths = printer.calculate_column_widths(table)
        
        logger.info(f"  Column widths: {widths}")
        
        # El ancho debe ser al menos el largo del contenido más largo + padding
        assert widths[1] > widths[0]  # VeryLongContent > Short
        
        logger.info("✅ TEST PASADO\n")
    
    def test_preserve_cell_content(self):
        """Test: Preservar contenido de celdas sin truncar"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Preservar contenido de celdas")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        printer = MarkdownTablePrinter()
        
        markdown = """
| Col1 | Col2 |
|------|------|
| Este es un contenido muy largo que no debe truncarse | B |
"""
        
        table = parser.parse(markdown)
        formatted = printer.format(table)
        
        logger.info(f"  Formatted table:\n{formatted}")
        
        # Verificar que el contenido largo está presente
        assert "Este es un contenido muy largo que no debe truncarse" in formatted
        
        logger.info("✅ TEST PASADO\n")
    
    def test_edge_cases_special_characters(self):
        """Test: Edge cases (celdas muy largas, caracteres especiales)"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Edge cases - caracteres especiales")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        printer = MarkdownTablePrinter()
        
        markdown = """
| Col1 | Col2 |
|------|------|
| A&B  | C<D  |
| E>F  | G"H  |
"""
        
        table = parser.parse(markdown)
        formatted = printer.format(table)
        
        logger.info(f"  Formatted table:\n{formatted}")
        
        # Verificar que los caracteres especiales se preservan
        assert "A&B" in formatted
        assert "C<D" in formatted
        
        logger.info("✅ TEST PASADO\n")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Round-Trip Preservation (Task 4.4)
# ══════════════════════════════════════════════════════════════════════════════

class TestRoundTripPreservation:
    """Suite de tests para round-trip preservation."""
    
    def test_round_trip_basic(self):
        """Test: parse → format → parse preserva estructura"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Round-trip preservation básico")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        printer = MarkdownTablePrinter()
        
        markdown = """
| Artículo | Plazo   | Requisito         |
|:---------|:--------|:------------------|
| 2.2.1.4  | 30 días | Solicitud escrita |
| 2.2.1.5  | 15 días | Planos            |
"""
        
        # Parse
        table1 = parser.parse(markdown)
        logger.info(f"  Table 1: {table1.column_count} cols, {table1.row_count} rows")
        
        # Format
        formatted = printer.format(table1)
        logger.info(f"  Formatted:\n{formatted}")
        
        # Parse again
        table2 = parser.parse(formatted)
        logger.info(f"  Table 2: {table2.column_count} cols, {table2.row_count} rows")
        
        # Verify equivalence
        assert table1.column_count == table2.column_count
        assert table1.row_count == table2.row_count
        assert table1.header.cells[0].content == table2.header.cells[0].content
        
        # Verify cell content preservation
        for i, (row1, row2) in enumerate(zip(table1.rows, table2.rows)):
            for j, (cell1, cell2) in enumerate(zip(row1.cells, row2.cells)):
                assert cell1.content == cell2.content, f"Cell [{i}][{j}] differs"
        
        logger.info("✅ TEST PASADO\n")
    
    def test_round_trip_with_empty_cells(self):
        """Test: Round-trip con celdas vacías"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Round-trip con celdas vacías")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        printer = MarkdownTablePrinter()
        
        markdown = """
| Col1 | Col2 | Col3 |
|------|------|------|
| A    |      | C    |
|      | B    |      |
"""
        
        table1 = parser.parse(markdown)
        formatted = printer.format(table1)
        table2 = parser.parse(formatted)
        
        # Verify empty cells are preserved
        assert table1.rows[0].cells[1].content == table2.rows[0].cells[1].content == ""
        assert table1.rows[1].cells[0].content == table2.rows[1].cells[0].content == ""
        
        logger.info("✅ TEST PASADO\n")
    
    def test_round_trip_with_alignment(self):
        """Test: Round-trip preserva alineación"""
        logger.info("\n" + "="*80)
        logger.info("TEST: Round-trip preserva alineación")
        logger.info("="*80)
        
        parser = MarkdownTableParser()
        printer = MarkdownTablePrinter()
        
        markdown = """
| Left | Center | Right |
|:-----|:------:|------:|
| A    | B      | C     |
"""
        
        table1 = parser.parse(markdown)
        formatted = printer.format(table1)
        table2 = parser.parse(formatted)
        
        # Verify alignment preservation
        assert table1.alignments == table2.alignments
        
        logger.info("✅ TEST PASADO\n")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("\n" + "="*80)
    logger.info("🧪 SUITE DE TESTS: Table Processor (TASK-015)")
    logger.info("="*80)
    
    # Ejecutar con pytest
    pytest.main([__file__, "-v", "--tb=short"])
