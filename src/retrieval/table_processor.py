"""
Table Processor — Sistema de Procesamiento Especializado para Tablas Markdown

Este módulo implementa un sistema de 3 capas para garantizar la preservación de
integridad estructural de tablas Markdown durante la compresión contextual en el
pipeline RAG legal.

Arquitectura:
    Capa 1 - Detección: TableDetector identifica tablas Markdown
    Capa 2 - Preservación: TablePreserver protege tablas durante compresión
    Capa 3 - Integración: Modificación de ContextualCompressor existente

Componentes:
    - TableDetector: Detecta tablas con regex + heurísticas
    - MarkdownTableParser: Parser con propiedad round-trip
    - MarkdownTablePrinter: Pretty printer para formateo consistente
    - TablePreserver: Lógica de preservación inteligente
    - TableMetrics: Métricas de observabilidad

Autor: Fenix Tech Líder
Fecha: 28/04/2026
Versión: 1.0.0
"""

from __future__ import annotations

import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from langchain_core.language_models import BaseLLM
from langchain_core.prompts import ChatPromptTemplate

from src.config.logging import get_logger

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# MODELOS DE DATOS
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class TableCell:
    """Representa una celda individual en una tabla Markdown.
    
    Attributes:
        content: Contenido de texto de la celda
        alignment: Alineación ('left', 'center', 'right', 'default')
    """
    content: str
    alignment: str = "default"
    
    def __str__(self) -> str:
        return self.content.strip()


@dataclass
class TableRow:
    """Representa una fila en una tabla Markdown.
    
    Attributes:
        cells: Lista de celdas en la fila
        is_header: True si es la fila de encabezado
    """
    cells: List[TableCell]
    is_header: bool = False
    
    def __len__(self) -> int:
        return len(self.cells)
    
    def __getitem__(self, index: int) -> TableCell:
        return self.cells[index]


@dataclass
class TableStructure:
    """Representa la estructura completa de una tabla Markdown.
    
    Attributes:
        header: Fila de encabezado
        rows: Lista de filas de datos
        alignments: Lista de alineaciones por columna
        column_count: Número de columnas
    """
    header: TableRow
    rows: List[TableRow]
    alignments: List[str] = field(default_factory=list)
    
    @property
    def column_count(self) -> int:
        """Retorna el número de columnas basado en el header."""
        return len(self.header.cells)
    
    @property
    def row_count(self) -> int:
        """Retorna el número de filas de datos (sin contar header)."""
        return len(self.rows)
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Valida la consistencia de la estructura de la tabla.
        
        Returns:
            Tuple[bool, Optional[str]]: (es_válida, mensaje_error)
        """
        expected_cols = self.column_count
        
        # Validar que todas las filas tengan el mismo número de columnas
        for i, row in enumerate(self.rows):
            if len(row.cells) != expected_cols:
                return False, f"Fila {i} tiene {len(row.cells)} columnas, esperadas {expected_cols}"
        
        # Validar que alignments tenga el tamaño correcto si está presente
        if self.alignments and len(self.alignments) != expected_cols:
            return False, f"Alignments tiene {len(self.alignments)} elementos, esperados {expected_cols}"
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa la estructura a un diccionario.
        
        Returns:
            Dict con la estructura serializada
        """
        return {
            "header": [cell.content for cell in self.header.cells],
            "rows": [[cell.content for cell in row.cells] for row in self.rows],
            "alignments": self.alignments,
            "column_count": self.column_count,
            "row_count": self.row_count,
        }


@dataclass
class TableDetectionResult:
    """Resultado de la detección de tablas en un fragmento.
    
    Attributes:
        contains_table: True si se detectó al menos una tabla
        table_count: Número de tablas detectadas
        table_ranges: Lista de rangos (start_line, end_line) de cada tabla
        confidence: Score de confianza (0.0-1.0)
        detection_time_ms: Tiempo de detección en milisegundos
    """
    contains_table: bool
    table_count: int = 0
    table_ranges: List[Tuple[int, int]] = field(default_factory=list)
    confidence: float = 0.0
    detection_time_ms: float = 0.0


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPCIONES
# ══════════════════════════════════════════════════════════════════════════════


class TableProcessingError(Exception):
    """Excepción base para errores de procesamiento de tablas."""
    pass


class TableParseError(TableProcessingError):
    """Excepción lanzada cuando falla el parsing de una tabla.
    
    Attributes:
        line: Número de línea donde ocurrió el error
        column: Número de columna donde ocurrió el error
        message: Mensaje descriptivo del error
    """
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        self.line = line
        self.column = column
        self.message = message
        location = ""
        if line is not None:
            location = f" en línea {line}"
        if column is not None:
            location += f", columna {column}"
        super().__init__(f"{message}{location}")


class TableValidationError(TableProcessingError):
    """Excepción lanzada cuando falla la validación de una tabla."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENTE 1: TABLE DETECTOR (Capa 1 - Detección)
# ══════════════════════════════════════════════════════════════════════════════


class TableDetector:
    """Detector de tablas Markdown en fragmentos de texto.
    
    Utiliza regex compilado y heurísticas para identificar tablas Markdown
    con alta precisión y bajo overhead (<50ms para fragmentos de 5KB).
    
    Heurísticas:
        - Mínimo 3 líneas consecutivas con pipes (|)
        - Presencia de línea separadora (|:?-+:?|)
        - Número consistente de columnas (±1 pipe de diferencia)
    
    Confidence Scores:
        - 1.0: Tabla con separador válido
        - 0.8: Tabla sin separador pero estructura consistente
        - 0.5: Estructura irregular pero probable tabla
    """
    
    # Patrones regex compilados para performance
    _PIPE_LINE_PATTERN = re.compile(r'\|')
    _SEPARATOR_PATTERN = re.compile(r'^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$')
    
    # Tamaño máximo de caché LRU
    _CACHE_MAX_SIZE = 100
    
    def __init__(self):
        """Inicializa el detector de tablas."""
        self._detection_count = 0
        self._table_cache: Dict[str, TableDetectionResult] = {}
        self._cache_order: List[str] = []  # Para implementar LRU
        logger.info("[TABLE_DETECTOR] Inicializado con patrones regex compilados y caché LRU")
    
    def detect(self, content: str) -> TableDetectionResult:
        """Detecta tablas Markdown en el contenido.
        
        Args:
            content: Texto a analizar
            
        Returns:
            TableDetectionResult con información de detección
            
        Example:
            >>> detector = TableDetector()
            >>> result = detector.detect("| Col1 | Col2 |\\n|------|------|\\n| A | B |")
            >>> result.contains_table
            True
            >>> result.confidence
            1.0
        """
        # Calcular hash del contenido para caché
        import hashlib
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # Verificar caché
        if content_hash in self._table_cache:
            logger.debug(f"[TABLE_DETECTOR] Cache hit para hash {content_hash[:8]}")
            # Actualizar orden LRU
            self._cache_order.remove(content_hash)
            self._cache_order.append(content_hash)
            return self._table_cache[content_hash]
        
        start_time = time.perf_counter()
        
        lines = content.split('\n')
        table_ranges: List[Tuple[int, int]] = []
        
        # Detectar bloques de líneas con pipes
        i = 0
        while i < len(lines):
            # Buscar inicio de posible tabla (línea con pipes)
            if not self._has_pipes(lines[i]):
                i += 1
                continue
            
            # Encontramos una línea con pipes, buscar el bloque completo
            start_line = i
            pipe_lines = []
            separator_index = None
            
            # Recolectar líneas consecutivas con pipes
            while i < len(lines) and self._has_pipes(lines[i]):
                pipe_lines.append(lines[i])
                
                # Detectar línea separadora
                if self._is_separator_line(lines[i]):
                    separator_index = len(pipe_lines) - 1
                
                i += 1
            
            end_line = i - 1
            
            # Aplicar heurísticas de validación
            is_valid_table, confidence = self._validate_table_block(
                pipe_lines, separator_index
            )
            
            if is_valid_table:
                table_ranges.append((start_line, end_line))
                logger.debug(
                    f"[TABLE_DETECTOR] Tabla detectada en líneas {start_line}-{end_line}, "
                    f"confidence={confidence:.2f}"
                )
        
        detection_time_ms = (time.perf_counter() - start_time) * 1000
        self._detection_count += 1
        
        result = TableDetectionResult(
            contains_table=len(table_ranges) > 0,
            table_count=len(table_ranges),
            table_ranges=table_ranges,
            confidence=self._calculate_overall_confidence(table_ranges, lines),
            detection_time_ms=detection_time_ms
        )
        
        # Guardar en caché
        self._table_cache[content_hash] = result
        self._cache_order.append(content_hash)
        
        # Implementar LRU: eliminar entrada más antigua si excede tamaño máximo
        if len(self._cache_order) > self._CACHE_MAX_SIZE:
            oldest_hash = self._cache_order.pop(0)
            del self._table_cache[oldest_hash]
            logger.debug(f"[TABLE_DETECTOR] Cache LRU: eliminada entrada {oldest_hash[:8]}")
        
        logger.debug(
            f"[TABLE_DETECTOR] Detección completada en {detection_time_ms:.2f}ms: "
            f"tables={result.table_count}, confidence={result.confidence:.2f}"
        )
        
        return result
    
    def _has_pipes(self, line: str) -> bool:
        """Verifica si una línea contiene pipes (|).
        
        Args:
            line: Línea a verificar
            
        Returns:
            True si la línea contiene al menos 2 pipes
        """
        # Contar pipes (mínimo 2 para ser tabla)
        pipe_count = len(self._PIPE_LINE_PATTERN.findall(line))
        return pipe_count >= 2
    
    def _is_separator_line(self, line: str) -> bool:
        """Verifica si una línea es un separador de tabla Markdown.
        
        Args:
            line: Línea a verificar
            
        Returns:
            True si la línea es un separador válido (ej: |---|---|)
        """
        return bool(self._SEPARATOR_PATTERN.match(line))
    
    def _validate_table_block(
        self, 
        pipe_lines: List[str], 
        separator_index: Optional[int]
    ) -> Tuple[bool, float]:
        """Valida si un bloque de líneas con pipes es una tabla válida.
        
        Heurísticas:
        - Mínimo 3 líneas consecutivas con pipes
        - Número consistente de columnas (±1 pipe de diferencia)
        - Presencia de separador aumenta confidence
        
        Args:
            pipe_lines: Lista de líneas con pipes
            separator_index: Índice de la línea separadora (None si no hay)
            
        Returns:
            Tuple[bool, float]: (es_válida, confidence_score)
        """
        # Heurística 1: Mínimo 3 líneas
        if len(pipe_lines) < 3:
            return False, 0.0
        
        # Heurística 2: Número consistente de columnas
        pipe_counts = [len(self._PIPE_LINE_PATTERN.findall(line)) for line in pipe_lines]
        
        # Calcular varianza de pipes (debe ser baja para tabla válida)
        avg_pipes = sum(pipe_counts) / len(pipe_counts)
        max_deviation = max(abs(count - avg_pipes) for count in pipe_counts)
        
        # Si la desviación es >1, probablemente no es una tabla
        if max_deviation > 1:
            return False, 0.0
        
        # Calcular confidence score
        if separator_index is not None:
            # Tabla con separador válido → confidence 1.0
            confidence = 1.0
        elif max_deviation == 0:
            # Tabla sin separador pero columnas perfectamente consistentes → 0.8
            confidence = 0.8
        else:
            # Tabla con ligera inconsistencia → 0.5
            confidence = 0.5
        
        return True, confidence
    
    def _calculate_overall_confidence(
        self, 
        table_ranges: List[Tuple[int, int]], 
        lines: List[str]
    ) -> float:
        """Calcula el confidence score general para todas las tablas detectadas.
        
        Args:
            table_ranges: Rangos de líneas de tablas detectadas
            lines: Todas las líneas del contenido
            
        Returns:
            Confidence score promedio (0.0-1.0)
        """
        if not table_ranges:
            return 0.0
        
        confidences = []
        for start, end in table_ranges:
            table_lines = lines[start:end + 1]
            separator_index = None
            
            for i, line in enumerate(table_lines):
                if self._is_separator_line(line):
                    separator_index = i
                    break
            
            _, confidence = self._validate_table_block(table_lines, separator_index)
            confidences.append(confidence)
        
        return sum(confidences) / len(confidences)
    
    def extract_tables(self, content: str) -> List[str]:
        """Extrae las tablas detectadas como strings individuales.
        
        Args:
            content: Texto que contiene tablas
            
        Returns:
            Lista de strings, cada uno conteniendo una tabla completa
        """
        detection = self.detect(content)
        if not detection.contains_table:
            return []
        
        lines = content.split('\n')
        tables = []
        
        for start_line, end_line in detection.table_ranges:
            table_lines = lines[start_line:end_line + 1]
            tables.append('\n'.join(table_lines))
        
        return tables


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENTE 2: MARKDOWN TABLE PARSER (Capa 2 - Parsing)
# ══════════════════════════════════════════════════════════════════════════════


class MarkdownTableParser:
    """Parser de tablas Markdown con propiedad round-trip.
    
    Parsea tablas Markdown a estructuras de datos y garantiza que
    parse(markdown) → format(table) → parse(markdown2) produce estructuras
    equivalentes (round-trip preservation).
    
    Soporta:
        - Tablas con y sin separador
        - Alineación de columnas (left, center, right)
        - Celdas vacías
        - Pipes escapados (\\|)
        - Recuperación de columnas inconsistentes
    """
    
    def __init__(self):
        """Inicializa el parser de tablas."""
        logger.info("[TABLE_PARSER] Inicializado")
    
    def parse(self, markdown: str) -> TableStructure:
        """Parsea una tabla Markdown a TableStructure.
        
        Args:
            markdown: String con tabla Markdown
            
        Returns:
            TableStructure con la tabla parseada
            
        Raises:
            TableParseError: Si la tabla está malformada
            
        Example:
            >>> parser = MarkdownTableParser()
            >>> table = parser.parse("| A | B |\\n|---|---|\\n| 1 | 2 |")
            >>> table.column_count
            2
        """
        if not markdown or not markdown.strip():
            raise TableParseError("Tabla vacía o contenido inválido")
        
        # Split de líneas y eliminación de líneas vacías
        lines = [line.strip() for line in markdown.split('\n') if line.strip()]
        
        if len(lines) < 2:
            raise TableParseError(
                f"Tabla debe tener al menos 2 líneas (header + datos), encontradas {len(lines)}"
            )
        
        # Identificar línea separadora
        separator_index = None
        for i, line in enumerate(lines):
            if self._is_separator_line(line):
                separator_index = i
                break
        
        # Parsear header y data rows
        if separator_index is not None:
            # Tabla con separador: línea antes del separador es header
            if separator_index == 0:
                raise TableParseError("Separador no puede estar en la primera línea", line=1)
            
            header_line = lines[separator_index - 1]
            separator_line = lines[separator_index]
            data_lines = lines[separator_index + 1:]
            
            # Detectar alineación
            alignments = self.detect_alignment(separator_line)
        else:
            # Tabla sin separador: primera línea es header, resto son datos
            header_line = lines[0]
            data_lines = lines[1:]
            alignments = []
            
            logger.debug("[TABLE_PARSER] Tabla sin separador detectada, usando primera línea como header")
        
        # Parsear header
        header_cells_content = self.parse_row(header_line)
        header_cells = [TableCell(content=c, alignment="default") for c in header_cells_content]
        header = TableRow(cells=header_cells, is_header=True)
        
        expected_columns = len(header_cells)
        
        # Parsear data rows
        rows = []
        for i, data_line in enumerate(data_lines):
            try:
                row_cells_content = self.parse_row(data_line)
                
                # Validar número de columnas
                if len(row_cells_content) != expected_columns:
                    # Intentar recuperación: padding con celdas vacías
                    if len(row_cells_content) < expected_columns:
                        logger.warning(
                            f"[TABLE_PARSER] Fila {i + 1} tiene {len(row_cells_content)} columnas, "
                            f"esperadas {expected_columns}. Aplicando padding."
                        )
                        row_cells_content.extend([""] * (expected_columns - len(row_cells_content)))
                    else:
                        raise TableParseError(
                            f"Fila tiene {len(row_cells_content)} columnas, esperadas {expected_columns}",
                            line=i + 2,  # +2 porque header es línea 1
                            column=len(row_cells_content)
                        )
                
                # Aplicar alineación si está disponible
                row_cells = []
                for j, content in enumerate(row_cells_content):
                    alignment = alignments[j] if j < len(alignments) else "default"
                    row_cells.append(TableCell(content=content, alignment=alignment))
                
                rows.append(TableRow(cells=row_cells, is_header=False))
                
            except Exception as e:
                if isinstance(e, TableParseError):
                    raise
                raise TableParseError(f"Error parseando fila {i + 1}: {str(e)}", line=i + 2)
        
        # Crear estructura de tabla
        table = TableStructure(header=header, rows=rows, alignments=alignments)
        
        # Validar estructura
        is_valid, error = table.validate()
        if not is_valid:
            raise TableValidationError(f"Tabla inválida: {error}")
        
        logger.debug(
            f"[TABLE_PARSER] Tabla parseada exitosamente: {table.column_count} columnas, "
            f"{table.row_count} filas"
        )
        
        return table
    
    def parse_row(self, line: str) -> List[str]:
        """Parsea una línea de tabla y extrae las celdas.
        
        Args:
            line: Línea de tabla (ej: "| A | B | C |")
            
        Returns:
            Lista de strings con contenido de cada celda
        """
        # Eliminar pipes iniciales y finales
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]
        
        # Split por pipes, pero ignorando pipes escapados (\|)
        # Usamos regex con negative lookbehind para no romper en \|
        import re
        cells = re.split(r'(?<!\\)\|', line)
        
        # Trim de espacios y manejo de pipes escapados
        processed_cells = []
        for cell in cells:
            # Trim espacios
            cell = cell.strip()
            
            # Manejar pipes escapados: \| → |
            cell = cell.replace('\\|', '|')
            
            processed_cells.append(cell)
        
        return processed_cells
    
    def _is_separator_line(self, line: str) -> bool:
        """Verifica si una línea es un separador de tabla Markdown.
        
        Args:
            line: Línea a verificar
            
        Returns:
            True si la línea es un separador válido
        """
        # Patrón para separador: |:?-+:?|
        pattern = re.compile(r'^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$')
        return bool(pattern.match(line))
    
    def detect_alignment(self, separator_line: str) -> List[str]:
        """Detecta la alineación de columnas desde la línea separadora.
        
        Args:
            separator_line: Línea separadora (ej: "|:---|:---:|---:|")
            
        Returns:
            Lista de alineaciones: 'left', 'center', 'right', 'default'
            
        Example:
            >>> parser = MarkdownTableParser()
            >>> parser.detect_alignment("|:---|:---:|---:|")
            ['left', 'center', 'right']
        """
        # Eliminar pipes iniciales y finales
        line = separator_line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]
        
        # Split por pipes
        segments = line.split('|')
        
        alignments = []
        for segment in segments:
            segment = segment.strip()
            
            # Detectar alineación basada en posición de dos puntos (:)
            starts_with_colon = segment.startswith(':')
            ends_with_colon = segment.endswith(':')
            
            if starts_with_colon and ends_with_colon:
                # :---: → center
                alignments.append('center')
            elif starts_with_colon:
                # :--- → left
                alignments.append('left')
            elif ends_with_colon:
                # ---: → right
                alignments.append('right')
            else:
                # --- → default (left)
                alignments.append('default')
        
        return alignments


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENTE 3: MARKDOWN TABLE PRINTER (Capa 2 - Pretty Printing)
# ══════════════════════════════════════════════════════════════════════════════


class MarkdownTablePrinter:
    """Pretty printer de tablas Markdown con alineación correcta.
    
    Formatea TableStructure a Markdown con:
        - Pipes alineados verticalmente
        - Anchos de columna calculados automáticamente
        - Alineación de contenido respetada
        - Padding consistente
    """
    
    def __init__(self):
        """Inicializa el printer de tablas."""
        logger.info("[TABLE_PRINTER] Inicializado")
    
    def format(self, table: TableStructure) -> str:
        """Formatea una TableStructure a Markdown bien formateado.
        
        Args:
            table: Estructura de tabla a formatear
            
        Returns:
            String con tabla Markdown formateada
            
        Example:
            >>> printer = MarkdownTablePrinter()
            >>> markdown = printer.format(table)
            >>> print(markdown)
            | Column A | Column B |
            |----------|----------|
            | Value 1  | Value 2  |
        """
        # Calcular anchos de columna
        widths = self.calculate_column_widths(table)
        
        # Usar alignments de la tabla o default
        alignments = table.alignments if table.alignments else ['default'] * table.column_count
        
        # Formatear header
        header_line = self.format_row(table.header, widths, alignments)
        
        # Formatear separador
        separator_line = self.format_separator(widths, alignments)
        
        # Formatear data rows
        data_lines = [self.format_row(row, widths, alignments) for row in table.rows]
        
        # Unir todas las líneas
        all_lines = [header_line, separator_line] + data_lines
        
        return '\n'.join(all_lines)
    
    def calculate_column_widths(self, table: TableStructure) -> List[int]:
        """Calcula el ancho óptimo para cada columna.
        
        Args:
            table: Estructura de tabla
            
        Returns:
            Lista de anchos (en caracteres) por columna
        """
        widths = []
        
        for col_idx in range(table.column_count):
            # Calcular ancho máximo para esta columna
            max_width = len(table.header.cells[col_idx].content)
            
            for row in table.rows:
                cell_width = len(row.cells[col_idx].content)
                max_width = max(max_width, cell_width)
            
            # Añadir padding mínimo de 1 espacio a cada lado
            widths.append(max_width + 2)
        
        return widths
    
    def format_row(
        self, 
        row: TableRow, 
        widths: List[int], 
        alignments: List[str]
    ) -> str:
        """Formatea una fila con alineación y padding.
        
        Args:
            row: Fila a formatear
            widths: Anchos de columna
            alignments: Alineaciones de columna
            
        Returns:
            String con fila formateada
        """
        formatted_cells = []
        
        for i, cell in enumerate(row.cells):
            width = widths[i]
            content = cell.content
            alignment = alignments[i] if i < len(alignments) else 'default'
            
            # Aplicar alineación
            if alignment == 'center':
                # Center: distribuir espacios equitativamente
                total_padding = width - len(content)
                left_padding = total_padding // 2
                right_padding = total_padding - left_padding
                formatted = ' ' * left_padding + content + ' ' * right_padding
            elif alignment == 'right':
                # Right: espacios a la izquierda
                formatted = content.rjust(width)
            else:
                # Left o default: espacios a la derecha
                formatted = content.ljust(width)
            
            formatted_cells.append(formatted)
        
        # Unir celdas con pipes
        return '|' + '|'.join(formatted_cells) + '|'
    
    def format_separator(self, widths: List[int], alignments: List[str]) -> str:
        """Formatea la línea separadora con alineación.
        
        Args:
            widths: Anchos de columna
            alignments: Alineaciones de columna
            
        Returns:
            String con separador formateado (ej: "|:---|:---:|---:|")
        """
        separators = []
        
        for i, width in enumerate(widths):
            alignment = alignments[i] if i < len(alignments) else 'default'
            
            # Generar separador basado en alineación
            if alignment == 'center':
                # :---: para center
                sep = ':' + '-' * (width - 2) + ':'
            elif alignment == 'right':
                # ---: para right
                sep = '-' * (width - 1) + ':'
            elif alignment == 'left':
                # :--- para left
                sep = ':' + '-' * (width - 1)
            else:
                # --- para default
                sep = '-' * width
            
            separators.append(sep)
        
        # Unir separadores con pipes
        return '|' + '|'.join(separators) + '|'


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENTE 4: TABLE PRESERVER (Capa 2 - Preservación)
# ══════════════════════════════════════════════════════════════════════════════


class TablePreserver:
    """Preservador de tablas durante compresión LLM.
    
    Garantiza que las tablas se preserven completas durante la compresión
    contextual, aplicando compresión solo al texto circundante y validando
    la integridad post-compresión.
    """
    
    def __init__(self, llm: BaseLLM, parser: MarkdownTableParser):
        """Inicializa el preservador de tablas.
        
        Args:
            llm: Modelo de lenguaje para compresión
            parser: Parser de tablas para validación
        """
        self.llm = llm
        self.parser = parser
        self._tables_preserved = 0
        self._integrity_violations = 0
        logger.info("[TABLE_PRESERVER] Inicializado")
    
    def preserve_with_llm(
        self, 
        fragment: str, 
        query: str, 
        table_ranges: List[Tuple[int, int]]
    ) -> str:
        """Preserva tablas durante compresión LLM del fragmento.
        
        Args:
            fragment: Fragmento de texto con tablas
            query: Query del usuario para contexto
            table_ranges: Rangos de líneas de cada tabla
            
        Returns:
            Fragmento comprimido con tablas preservadas
        """
        start_time = time.perf_counter()
        
        try:
            # Split del fragmento en líneas
            lines = fragment.split('\n')
            
            # Extraer tablas y texto circundante
            tables = []
            text_segments = []
            last_end = 0
            
            for start_line, end_line in table_ranges:
                # Texto antes de la tabla
                if start_line > last_end:
                    text_before = '\n'.join(lines[last_end:start_line])
                    if text_before.strip():
                        text_segments.append((last_end, start_line, text_before))
                
                # Tabla
                table_text = '\n'.join(lines[start_line:end_line + 1])
                tables.append((start_line, end_line, table_text))
                
                last_end = end_line + 1
            
            # Texto después de la última tabla
            if last_end < len(lines):
                text_after = '\n'.join(lines[last_end:])
                if text_after.strip():
                    text_segments.append((last_end, len(lines), text_after))
            
            # Si no hay texto circundante, retornar fragmento original
            if not text_segments:
                logger.debug("[TABLE_PRESERVER] Fragmento contiene solo tablas, sin compresión")
                self._tables_preserved += len(tables)
                return fragment
            
            # Importar prompt (lazy import para evitar dependencias circulares)
            from src.retrieval.table_prompts import TABLE_COMPRESS_PROMPT
            
            # Comprimir cada segmento de texto
            compressed_segments = []
            for start, end, text in text_segments:
                try:
                    # Crear chain de compresión
                    chain = TABLE_COMPRESS_PROMPT | self.llm
                    
                    # Invocar LLM para comprimir texto
                    response = chain.invoke({
                        "question": query,
                        "context": text
                    })
                    
                    # Extraer contenido comprimido
                    compressed_text = response.content if hasattr(response, 'content') else str(response)
                    compressed_segments.append((start, end, compressed_text.strip()))
                    
                except Exception as e:
                    logger.warning(
                        f"[TABLE_PRESERVER] Error comprimiendo segmento {start}-{end}: {str(e)}. "
                        f"Usando texto original."
                    )
                    compressed_segments.append((start, end, text))
            
            # Reconstruir fragmento: intercalar texto comprimido y tablas preservadas
            result_parts = []
            all_parts = sorted(compressed_segments + tables, key=lambda x: x[0])
            
            for start, end, content in all_parts:
                if content.strip():
                    result_parts.append(content)
            
            result = '\n\n'.join(result_parts)
            
            # Registrar métricas
            preservation_time_ms = (time.perf_counter() - start_time) * 1000
            self._tables_preserved += len(tables)
            
            logger.debug(
                f"[TABLE_PRESERVER] Preservación completada en {preservation_time_ms:.2f}ms: "
                f"{len(tables)} tablas preservadas, {len(text_segments)} segmentos comprimidos"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"[TABLE_PRESERVER] Error en preserve_with_llm: {str(e)}. "
                f"Retornando fragmento original."
            )
            return fragment
    
    def validate_preservation(
        self, 
        original_table: str, 
        compressed_table: str
    ) -> Tuple[bool, Optional[str]]:
        """Valida que la tabla se preservó correctamente.
        
        Args:
            original_table: Tabla original
            compressed_table: Tabla después de compresión
            
        Returns:
            Tuple[bool, Optional[str]]: (es_válida, mensaje_error)
        """
        try:
            # Parsear ambas tablas
            original_structure = self.parser.parse(original_table)
            compressed_structure = self.parser.parse(compressed_table)
            
            # Validación 1: Mismo número de columnas
            if original_structure.column_count != compressed_structure.column_count:
                error_msg = (
                    f"Número de columnas diferente: original={original_structure.column_count}, "
                    f"comprimida={compressed_structure.column_count}"
                )
                logger.warning(f"[TABLE_PRESERVER] Validación fallida: {error_msg}")
                self._integrity_violations += 1
                return False, error_msg
            
            # Validación 2: Mismo número de filas
            if original_structure.row_count != compressed_structure.row_count:
                error_msg = (
                    f"Número de filas diferente: original={original_structure.row_count}, "
                    f"comprimida={compressed_structure.row_count}"
                )
                logger.warning(f"[TABLE_PRESERVER] Validación fallida: {error_msg}")
                self._integrity_violations += 1
                return False, error_msg
            
            # Validación 3: Contenido del header es igual
            original_header = [cell.content.strip() for cell in original_structure.header.cells]
            compressed_header = [cell.content.strip() for cell in compressed_structure.header.cells]
            
            if original_header != compressed_header:
                error_msg = (
                    f"Header diferente: original={original_header}, "
                    f"comprimida={compressed_header}"
                )
                logger.warning(f"[TABLE_PRESERVER] Validación fallida: {error_msg}")
                self._integrity_violations += 1
                return False, error_msg
            
            # Validación 4: Contenido de celdas es igual (permitir diferencias de espacios)
            for i, (orig_row, comp_row) in enumerate(zip(original_structure.rows, compressed_structure.rows)):
                orig_cells = [cell.content.strip() for cell in orig_row.cells]
                comp_cells = [cell.content.strip() for cell in comp_row.cells]
                
                if orig_cells != comp_cells:
                    error_msg = (
                        f"Contenido diferente en fila {i}: original={orig_cells}, "
                        f"comprimida={comp_cells}"
                    )
                    logger.warning(f"[TABLE_PRESERVER] Validación fallida: {error_msg}")
                    self._integrity_violations += 1
                    return False, error_msg
            
            # Todas las validaciones pasaron
            logger.debug(
                f"[TABLE_PRESERVER] Validación exitosa: {original_structure.column_count} columnas, "
                f"{original_structure.row_count} filas"
            )
            return True, None
            
        except TableParseError as e:
            error_msg = f"Error parseando tabla: {str(e)}"
            logger.warning(f"[TABLE_PRESERVER] Validación fallida: {error_msg}")
            self._integrity_violations += 1
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Error inesperado en validación: {str(e)}"
            logger.error(f"[TABLE_PRESERVER] {error_msg}")
            self._integrity_violations += 1
            return False, error_msg
    
    @property
    def tables_preserved(self) -> int:
        """Retorna el contador de tablas preservadas."""
        return self._tables_preserved
    
    @property
    def integrity_violations(self) -> int:
        """Retorna el contador de violaciones de integridad."""
        return self._integrity_violations


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENTE 5: TABLE METRICS (Observabilidad)
# ══════════════════════════════════════════════════════════════════════════════


class TableMetrics:
    """Métricas de observabilidad para el procesamiento de tablas.
    
    Recolecta métricas de:
        - Tablas detectadas
        - Tablas preservadas
        - Violaciones de integridad
        - Tiempos de detección y preservación
    """
    
    def __init__(self):
        """Inicializa el sistema de métricas."""
        self.tables_detected = 0
        self.tables_preserved = 0
        self.table_integrity_violations = 0
        self.detection_times_ms: List[float] = []
        self.preservation_times_ms: List[float] = []
        logger.info("[TABLE_METRICS] Sistema de métricas inicializado")
    
    def record_detection(self, detection_time_ms: float, table_count: int):
        """Registra una detección de tablas.
        
        Args:
            detection_time_ms: Tiempo de detección en ms
            table_count: Número de tablas detectadas
        """
        self.tables_detected += table_count
        self.detection_times_ms.append(detection_time_ms)
    
    def record_preservation(self, preservation_time_ms: float, success: bool):
        """Registra una preservación de tabla.
        
        Args:
            preservation_time_ms: Tiempo de preservación en ms
            success: True si la preservación fue exitosa
        """
        self.preservation_times_ms.append(preservation_time_ms)
        if success:
            self.tables_preserved += 1
        else:
            self.table_integrity_violations += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna un resumen de las métricas.
        
        Returns:
            Dict con estadísticas agregadas
        """
        avg_detection_time = (
            sum(self.detection_times_ms) / len(self.detection_times_ms)
            if self.detection_times_ms else 0.0
        )
        avg_preservation_time = (
            sum(self.preservation_times_ms) / len(self.preservation_times_ms)
            if self.preservation_times_ms else 0.0
        )
        
        return {
            "tables_detected": self.tables_detected,
            "tables_preserved": self.tables_preserved,
            "integrity_violations": self.table_integrity_violations,
            "avg_detection_time_ms": round(avg_detection_time, 2),
            "avg_preservation_time_ms": round(avg_preservation_time, 2),
            "success_rate": (
                self.tables_preserved / (self.tables_preserved + self.table_integrity_violations)
                if (self.tables_preserved + self.table_integrity_violations) > 0
                else 0.0
            )
        }


# ══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Modelos de datos
    "TableCell",
    "TableRow",
    "TableStructure",
    "TableDetectionResult",
    # Excepciones
    "TableProcessingError",
    "TableParseError",
    "TableValidationError",
    # Componentes
    "TableDetector",
    "MarkdownTableParser",
    "MarkdownTablePrinter",
    "TablePreserver",
    "TableMetrics",
]
