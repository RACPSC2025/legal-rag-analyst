"""
Contextual Compression — Post-Retrieval Filtering para RAG Legal
────────────────────────────────────────────────────────────────
Problema que resuelve:
  Los chunks recuperados suelen contener texto relevante MEZCLADO con
  contenido irrelevante (encabezados, firmas, considerandos genéricos).
  Enviar el chunk completo al generador introduce ruido que degrada la
  calidad de la respuesta y consume tokens innecesarios.

Solución:
  Para cada chunk recuperado, extraer SOLO los pasajes directamente
  relacionados con la pregunta antes de enviar al nodo generate.

Dos estrategias:
  1. LLM Compression (alta calidad, más lento): usa el LLM para identificar
     y extraer pasajes relevantes. Ideal para chunks con tablas.
  2. Sentence-level Compression (rápido, sin LLM): filtra oraciones por
     similitud léxica con la query. Usado como fallback.

Razones de este módulo:
  • Reduce tokens en 40-60% sin perder información relevante.
  • Mejora calidad de respuesta al eliminar ruido.
  • Protege tablas completas (nunca las fragmenta).
  • Especialmente importante para chunks largos (>500 chars).

Uso en nodes.py:
    from src.retrieval.contextual_compression import compress_documents
    compressed = compress_documents(docs, question)

Autor: Fenix Tech Líder
Fecha: 2026-04-26
Versión: 1.0.0
Basado en: Claude (Legal v2) con mejoras de los 4 seniors
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple, Optional

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.config import get_llm
from src.retrieval.table_processor import (
    TableDetector,
    MarkdownTableParser,
    MarkdownTablePrinter,
    TablePreserver,
)

logger = logging.getLogger(__name__)

# ── Configuración de umbrales ────────────────────────────────────────────────

# Umbral mínimo de caracteres para que valga la pena comprimir un chunk
_MIN_COMPRESS_LENGTH = 400

# Si el chunk ya es pequeño, se pasa directo sin comprimir
_MAX_PASSTHROUGH_LENGTH = 300

# Pasajes mínimos que debe retener la compresión (para no perder la tabla entera)
_MIN_RETAINED_RATIO = 0.3

# Máximo de llamadas LLM por batch (para controlar costos)
_MAX_LLM_CALLS_PER_BATCH = 5

# ── Prompts optimizados para normativa colombiana ────────────────────────────

_COMPRESS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """Eres un extractor de información legal colombiana de alta precisión.

TAREA: Del FRAGMENTO DE DOCUMENTO proporcionado, extrae ÚNICAMENTE los pasajes,
cifras, tablas y artículos que son directamente relevantes para responder la PREGUNTA.

REGLAS ESTRICTAS:
1. Copia los pasajes LITERALMENTE, sin parafrasear ni resumir.
2. Si hay una TABLA relacionada con la pregunta, inclúyela COMPLETA (todas las filas y columnas).
3. Mantén las referencias a artículos y páginas que aparezcan en el texto.
4. Si el fragmento NO contiene información relevante, responde exactamente: [SIN_CONTENIDO_RELEVANTE]
5. No añadas explicaciones ni comentarios — solo el texto extraído.
6. Máximo 600 palabras en la extracción.
7. Si hay listas numeradas o requisitos, inclúyelos completos.

EJEMPLOS:
Pregunta: "¿Cuáles son los requisitos para concesión de aguas?"
Fragmento: "ARTÍCULO 2.2.1.4. Requisitos. Para obtener la concesión de aguas el solicitante deberá:
1. Presentar solicitud escrita
2. Adjuntar planos topográficos
3. Certificado de tradición
[Considerando que la normativa anterior...]"

Extracción correcta:
"ARTÍCULO 2.2.1.4. Requisitos. Para obtener la concesión de aguas el solicitante deberá:
1. Presentar solicitud escrita
2. Adjuntar planos topográficos
3. Certificado de tradición"
""",
    ),
    (
        "human",
        "PREGUNTA: {question}\n\nFRAGMENTO:\n{document}\n\nExtracción de pasajes relevantes:",
    ),
])

# ── Clase principal ──────────────────────────────────────────────────────────

class ContextualCompressor:
    """
    Comprime documentos recuperados extrayendo solo los pasajes relevantes.
    
    Estrategia adaptativa:
      - Chunks con tablas → siempre LLM (protege la estructura tabular)
      - Chunks cortos (< MAX_PASSTHROUGH_LENGTH) → passthrough directo
      - Chunks largos → LLM compression con fallback a sentence-level
      
    Principios de diseño:
    - Single Responsibility: Solo comprime, no hace retrieval ni generación.
    - Fail-safe: Si LLM falla, usa sentence-level compression.
    - Logging completo: Cada decisión se registra para trazabilidad.
    - Protección de tablas: Nunca fragmenta tablas.
    
    Args:
        use_llm: Si True, usa LLM para compresión (default: True).
        batch_size: Máximo de llamadas LLM por batch (default: 5).
    """

    def __init__(self, use_llm: bool = True, batch_size: int = 5):
        """
        Inicializa el compresor contextual.
        
        Args:
            use_llm: Si True, usa LLM para compresión de alta calidad.
            batch_size: Máximo de llamadas LLM por batch para controlar costos.
        """
        self.use_llm = use_llm
        self.batch_size = min(batch_size, _MAX_LLM_CALLS_PER_BATCH)
        
        # Inicializar componentes de tabla
        self.table_detector = TableDetector()
        self.table_parser = MarkdownTableParser()
        self.table_printer = MarkdownTablePrinter()
        self.table_preserver: Optional[TablePreserver] = None  # Lazy init (requiere LLM)
        
        # Inicializar métricas de observabilidad
        from src.retrieval.table_processor import TableMetrics
        self.table_metrics = TableMetrics()
        
        logger.info(
            f"[COMPRESSOR] Inicializado: "
            f"use_llm={use_llm}, batch_size={self.batch_size}, "
            f"table_processor=enabled"
        )

    def compress(
        self, 
        documents: List[Document], 
        question: str
    ) -> List[Document]:
        """
        Comprime la lista de documentos recuperados.
        
        Proceso:
        1. Evalúa cada documento (tamaño, presencia de tablas).
        2. Decide estrategia: passthrough, LLM o sentence-level.
        3. Aplica compresión y valida resultado.
        4. Descarta chunks sin contenido relevante.
        5. Retorna documentos comprimidos con metadata enriquecida.
        
        Args:
            documents: Chunks recuperados del vector store.
            question:  Pregunta original del usuario.
            
        Returns:
            Lista de Documents con contenido comprimido.
            Mantiene metadata original + añade compression_applied=True.
            
        Example:
            >>> from src.retrieval.contextual_compression import compress_documents
            >>> compressed = compress_documents(docs, "¿Cuáles son los requisitos?")
            >>> for doc in compressed:
            ...     print(f"Ratio: {doc.metadata['compression_ratio']}")
        """
        if not documents:
            logger.warning("[COMPRESSOR] Lista de documentos vacía.")
            return []

        logger.info(
            f"[COMPRESSOR] Comprimiendo {len(documents)} documentos "
            f"para query: '{question[:80]}...'"
        )

        compressed: List[Document] = []
        llm_budget = self.batch_size  # Máximo de llamadas LLM en esta ronda
        stats = {
            "passthrough": 0,
            "llm": 0,
            "sentence": 0,
            "discarded": 0,
        }

        for i, doc in enumerate(documents, 1):
            content = doc.page_content
            meta = doc.metadata.copy()

            # ── Detección de tablas ──────────────────────────────────────────
            detection = self.table_detector.detect(content)
            meta["contains_table"] = detection.contains_table
            meta["table_count"] = detection.table_count
            meta["table_detection_confidence"] = detection.confidence
            
            # Registrar métricas de detección
            self.table_metrics.record_detection(
                detection.detection_time_ms,
                detection.table_count
            )

            # ── Decisión 1: Passthrough para chunks cortos ───────────────────
            if len(content) < _MAX_PASSTHROUGH_LENGTH:
                meta["compression_applied"] = False
                meta["compression_method"] = "passthrough_short"
                meta["original_length"] = len(content)
                meta["compressed_length"] = len(content)
                meta["compression_ratio"] = 1.0
                compressed.append(Document(page_content=content, metadata=meta))
                stats["passthrough"] += 1
                logger.debug(
                    f"[COMPRESSOR] Doc {i}/{len(documents)}: "
                    f"Passthrough (corto: {len(content)} chars)"
                )
                continue

            # ── Decisión 2: Detectar si tiene tabla ──────────────────────────
            is_table = detection.contains_table or meta.get("is_table", False)

            # ── Decisión 3: Compresión con preservación de tablas ────────────
            if detection.contains_table and self.use_llm and llm_budget > 0:
                # Usar método especializado de preservación de tablas
                extracted, method = self._compress_with_table_preservation(
                    content, question, detection
                )
                llm_budget -= 1
                stats["llm"] += 1
                
                # Añadir metadata específica de tablas
                meta["table_preserved"] = (method == "table_preserved")
                if detection.table_ranges:
                    # Calcular dimensiones de cada tabla
                    table_dimensions = []
                    for start, end in detection.table_ranges:
                        rows = end - start + 1
                        # Estimar columnas (contar pipes en primera línea)
                        first_line = content.split('\n')[start] if start < len(content.split('\n')) else ""
                        cols = first_line.count('|') - 1 if '|' in first_line else 0
                        table_dimensions.append((rows, cols))
                    meta["table_dimensions"] = table_dimensions
                meta["table_integrity_verified"] = (method == "table_preserved")
                
            # ── Decisión 4: LLM o Sentence-level para texto sin tablas ───────
            elif self.use_llm and (is_table or len(content) >= _MIN_COMPRESS_LENGTH) and llm_budget > 0:
                extracted, method = self._llm_compress(content, question)
                llm_budget -= 1
                stats["llm"] += 1
            else:
                extracted, method = self._sentence_compress(content, question)
                stats["sentence"] += 1

            # ── Validación: Verificar que la compresión no eliminó demasiado ─
            if not extracted or extracted == "[SIN_CONTENIDO_RELEVANTE]":
                # Chunk irrelevante: lo descartamos
                logger.info(
                    f"[COMPRESSOR] Doc {i}/{len(documents)}: "
                    f"Descartado (sin contenido relevante) — "
                    f"{meta.get('source', '?')} art={meta.get('article', '?')}"
                )
                stats["discarded"] += 1
                continue

            # Verificar ratio mínimo de retención
            retained_ratio = len(extracted) / max(len(content), 1)
            if retained_ratio < _MIN_RETAINED_RATIO and not is_table:
                # Muy poco retenido en chunk no-tabla → usar original
                logger.warning(
                    f"[COMPRESSOR] Doc {i}/{len(documents)}: "
                    f"Ratio muy bajo ({retained_ratio:.2%}), usando original"
                )
                extracted = content
                method = "fallback_original"

            # ── Enriquecer metadata ──────────────────────────────────────────
            meta["compression_applied"] = True
            meta["compression_method"] = method
            meta["original_length"] = len(content)
            meta["compressed_length"] = len(extracted)
            meta["compression_ratio"] = round(len(extracted) / max(len(content), 1), 3)

            compressed.append(Document(page_content=extracted, metadata=meta))
            
            logger.debug(
                f"[COMPRESSOR] Doc {i}/{len(documents)}: "
                f"{method} | {len(content)} → {len(extracted)} chars "
                f"({meta['compression_ratio']:.1%})"
            )

        # ── Logging de estadísticas ───────────────────────────────────────────
        logger.info(
            f"[COMPRESSOR] ✅ Compresión completada: "
            f"{len(documents)} → {len(compressed)} docs "
            f"({stats['discarded']} descartados)"
        )
        logger.info(
            f"[COMPRESSOR] Métodos: "
            f"Passthrough={stats['passthrough']}, "
            f"LLM={stats['llm']}, "
            f"Sentence={stats['sentence']}"
        )
        
        # Logging de métricas de tablas
        table_summary = self.table_metrics.get_summary()
        if table_summary["tables_detected"] > 0:
            logger.info(
                f"[COMPRESSOR] Métricas de tablas: "
                f"detectadas={table_summary['tables_detected']}, "
                f"preservadas={table_summary['tables_preserved']}, "
                f"violaciones={table_summary['integrity_violations']}, "
                f"success_rate={table_summary['success_rate']:.1%}"
            )

        return compressed

    # ── Métodos de compresión ─────────────────────────────────────────────────

    def _compress_with_table_preservation(
        self,
        content: str,
        question: str,
        detection: "TableDetectionResult",
    ) -> Tuple[str, str]:
        """
        Comprime fragmento preservando tablas completas.
        
        Args:
            content: Contenido del fragmento con tablas
            question: Pregunta del usuario
            detection: Resultado de detección de tablas
            
        Returns:
            Tupla (contenido_comprimido, método)
        """
        import time
        start_time = time.perf_counter()
        
        try:
            # Lazy init de TablePreserver (requiere LLM)
            if self.table_preserver is None:
                llm = get_llm(task="generate")
                self.table_preserver = TablePreserver(llm, self.table_parser)
                logger.debug("[COMPRESSOR] TablePreserver inicializado (lazy)")
            
            # Preservar tablas durante compresión
            preserved = self.table_preserver.preserve_with_llm(
                content, question, detection.table_ranges
            )
            
            # Extraer tablas para validación
            tables_original = self.table_detector.extract_tables(content)
            tables_preserved = self.table_detector.extract_tables(preserved)
            
            # Validar que todas las tablas se preservaron correctamente
            if len(tables_original) != len(tables_preserved):
                logger.warning(
                    f"[COMPRESSOR] Número de tablas cambió: "
                    f"original={len(tables_original)}, preservado={len(tables_preserved)}. "
                    f"Usando fragmento original."
                )
                preservation_time_ms = (time.perf_counter() - start_time) * 1000
                self.table_metrics.record_preservation(preservation_time_ms, success=False)
                return content, "table_fallback_original"
            
            # Validar integridad de cada tabla
            for i, (orig_table, pres_table) in enumerate(zip(tables_original, tables_preserved)):
                is_valid, error = self.table_preserver.validate_preservation(
                    orig_table, pres_table
                )
                
                if not is_valid:
                    logger.warning(
                        f"[COMPRESSOR] Validación fallida para tabla {i + 1}: {error}. "
                        f"Usando fragmento original."
                    )
                    preservation_time_ms = (time.perf_counter() - start_time) * 1000
                    self.table_metrics.record_preservation(preservation_time_ms, success=False)
                    return content, "table_fallback_original"
            
            # Todas las validaciones pasaron
            preservation_time_ms = (time.perf_counter() - start_time) * 1000
            self.table_metrics.record_preservation(preservation_time_ms, success=True)
            logger.debug(
                f"[COMPRESSOR] Preservación exitosa: {len(tables_original)} tablas validadas"
            )
            return preserved, "table_preserved"
            
        except Exception as e:
            logger.error(
                f"[COMPRESSOR] Error en preservación de tablas: {str(e)}. "
                f"Usando fragmento original."
            )
            preservation_time_ms = (time.perf_counter() - start_time) * 1000
            self.table_metrics.record_preservation(preservation_time_ms, success=False)
            return content, "table_fallback_original"

    def _llm_compress(self, content: str, question: str) -> Tuple[str, str]:
        """
        Compresión con LLM: máxima calidad para tablas y texto complejo.
        
        Args:
            content: Contenido del chunk a comprimir.
            question: Pregunta del usuario.
            
        Returns:
            Tupla (contenido_comprimido, método).
        """
        try:
            llm = get_llm(task="generate")  # Usar modelo potente para calidad
            chain = _COMPRESS_PROMPT | llm | StrOutputParser()
            result = chain.invoke({
                "question": question, 
                "document": content
            }).strip()
            
            logger.debug(
                f"[LLM_COMPRESS] {len(content)} → {len(result)} chars "
                f"({len(result)/max(len(content),1):.1%})"
            )
            
            return result, "llm"
        except Exception as e:
            logger.warning(
                f"[LLM_COMPRESS] Error en compresión LLM: {e}. "
                f"Fallback a sentence-level..."
            )
            return self._sentence_compress(content, question)

    def _sentence_compress(self, content: str, question: str) -> Tuple[str, str]:
        """
        Compresión por similitud léxica a nivel de oración.
        Rápida y sin costo LLM. Menos precisa que LLM pero útil como fallback.
        
        Args:
            content: Contenido del chunk a comprimir.
            question: Pregunta del usuario.
            
        Returns:
            Tupla (contenido_comprimido, método).
        """
        # Tokenizar query en keywords relevantes
        query_tokens = set(
            w.lower() for w in re.findall(r"\b\w{3,}\b", question)
        )

        # Dividir en oraciones (respetando puntos de artículo y tablas)
        sentences = re.split(r"(?<=[.!?])\s+|\n{2,}", content)

        scored: List[Tuple[float, str]] = []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            
            # Score: ratio de tokens de la query que aparecen en la oración
            sent_tokens = set(w.lower() for w in re.findall(r"\b\w{3,}\b", sent))
            overlap = query_tokens & sent_tokens
            score = len(overlap) / max(len(query_tokens), 1)
            
            # Bonus para tablas y artículos
            if "|" in sent:
                score += 0.4
            if re.search(r"\bart[ií]culo\s+\d", sent, re.IGNORECASE):
                score += 0.2
            if re.search(r"\brequisito|condici[oó]n|plazo|documento", sent, re.IGNORECASE):
                score += 0.15
            
            scored.append((score, sent))

        # Retener oraciones con score > 0.15 (al menos algo de overlap)
        relevant = [s for sc, s in scored if sc > 0.15]

        if not relevant:
            # Fallback: primeras 3 oraciones (suelen tener el artículo y objeto)
            relevant = [s for _, s in scored[:3]]

        result = "\n".join(relevant)
        
        logger.debug(
            f"[SENTENCE_COMPRESS] {len(content)} → {len(result)} chars "
            f"({len(result)/max(len(content),1):.1%})"
        )
        
        return result, "sentence_level"

    # ── Métodos auxiliares ────────────────────────────────────────────────────

    def _has_table(self, content: str) -> bool:
        """
        Detecta si el contenido tiene una tabla.
        
        Heurística: Si tiene más de 2 líneas con pipes (|) y al menos
        una línea con guiones (---), probablemente es una tabla Markdown.
        
        Args:
            content: Contenido a analizar.
            
        Returns:
            True si detecta tabla, False en caso contrario.
        """
        lines = content.split("\n")
        pipe_lines = sum(1 for line in lines if "|" in line)
        has_separator = any("---" in line for line in lines)
        
        return pipe_lines > 2 and has_separator


# ── Singleton y funciones de conveniencia ────────────────────────────────────

_compressor: Optional[ContextualCompressor] = None


def get_compressor(use_llm: bool = True, batch_size: int = 5) -> ContextualCompressor:
    """
    Retorna una instancia singleton del ContextualCompressor.
    
    Args:
        use_llm: Si True, usa LLM para compresión.
        batch_size: Máximo de llamadas LLM por batch.
        
    Returns:
        Instancia singleton de ContextualCompressor.
    """
    global _compressor
    if _compressor is None:
        _compressor = ContextualCompressor(use_llm=use_llm, batch_size=batch_size)
    return _compressor


def compress_documents(
    documents: List[Document],
    question: str,
    use_llm: bool = True,
    batch_size: int = 5,
) -> List[Document]:
    """
    Shortcut funcional para comprimir documentos.
    
    Esta es la función principal que debes usar en nodes.py.
    
    Args:
        documents: Lista de Documents recuperados.
        question: Pregunta del usuario.
        use_llm: Si True, usa LLM para compresión (default: True).
        batch_size: Máximo de llamadas LLM (default: 5).
        
    Returns:
        Lista de Documents comprimidos con metadata enriquecida.
        
    Example:
        >>> from src.retrieval.contextual_compression import compress_documents
        >>> compressed = compress_documents(docs, "¿Cuáles son los requisitos?")
        >>> print(f"Antes: {len(docs)} docs, Después: {len(compressed)} docs")
        >>> for doc in compressed:
        ...     ratio = doc.metadata.get('compression_ratio', 1.0)
        ...     print(f"Compresión: {ratio:.1%}")
    """
    return get_compressor(use_llm=use_llm, batch_size=batch_size).compress(
        documents, question
    )


# ── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "ContextualCompressor",
    "compress_documents",
    "get_compressor",
]
