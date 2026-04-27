"""
AdaptiveChunker v2.0 — Segmentación Legal Jerárquica Profesional
────────────────────────────────────────────────────────────────
Fragmenta el texto respetando la estructura normativa (Artículos, Capítulos, Parágrafos).
Implementa lógica de contexto jerárquico y protección de tablas.

Basado en: Fenix Pro 2026 & GrokAI Legal Patterns.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# ── Patrones Regex Legales (Estructura Colombiana) ──────────────────────────

class LegalPatterns:
    """Colección de patrones regex para estructura legal colombiana."""

    CHAPTER = re.compile(
        r"^(?:CAP[ÍI]TULO\s+(?:[IVXLCDM]+|\d+|[A-ZÁÉÍÓÚ]+))",
        re.IGNORECASE | re.MULTILINE,
    )

    SECTION = re.compile(
        r"^(?:SECCI[ÓO]N\s+(?:[IVXLCDM]+|\d+))",
        re.IGNORECASE | re.MULTILINE,
    )

    ARTICLE = re.compile(
        r"^(?:ART[ÍI]CULO\s+(?:\d+[°º]?|[IVXLCDM]+)|Art(?:ículo|iculo|\.)\s+(?:\d+[°º]?|[IVXLCDM]+))",
        re.IGNORECASE | re.MULTILINE,
    )

    PARAGRAPH = re.compile(
        r"^(?:PAR[ÁA]GRAFO\s+(?:\d+|[A-Z]+|ÚNICO))",
        re.IGNORECASE | re.MULTILINE,
    )

    RESOLVE = re.compile(r"^(?:RESUELVE|CONSIDERANDO|ANTECEDENTES):?", re.IGNORECASE | re.MULTILINE)

    @classmethod
    def detect_level(cls, text: str) -> str:
        """Detecta el nivel jerárquico de un bloque de texto."""
        line = text.strip().split("\n")[0][:150]
        if cls.CHAPTER.match(line): return "chapter"
        if cls.SECTION.match(line): return "section"
        if cls.ARTICLE.match(line): return "article"
        if cls.PARAGRAPH.match(line): return "paragraph_legal"
        if cls.RESOLVE.match(line): return "header_block"
        return "text_block"

@dataclass
class HierarchyContext:
    """Mantiene el contexto de dónde estamos en la norma."""
    chapter: str = ""
    section: str = ""
    article: str = ""
    
    def update(self, level: str, text: str):
        identifier = text.strip().split("\n")[0][:100]
        if level == "chapter":
            self.chapter = identifier
            self.section = ""; self.article = ""
        elif level == "section":
            self.section = identifier
            self.article = ""
        elif level == "article":
            self.article = identifier

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v}

# ── AdaptiveChunker v2.0 ─────────────────────────────────────────────────────

class AdaptiveChunker:
    """
    Segmentador inteligente optimizado para normativa legal colombiana.
    Preserva la integridad de artículos y enriquece con metadata jerárquica.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Separadores jerárquicos (orden de prioridad)
        self.separators = [
            "\n## RESUELVE", 
            "\n## CONSIDERANDO", 
            "\n## ANTECEDENTES",
            "\n### CAPÍTULO",
            "\n### ARTÍCULO",
            "\n#### PARÁGRAFO",
            "\n\n\n", 
            "\n\n", 
            "\n", 
            ". "
        ]
        
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            is_separator_regex=False,
            keep_separator=True
        )

    def split_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Segmenta el texto inyectando contexto jerárquico."""
        if not text:
            return []

        # 1. Primera pasada: Dividir por bloques estructurales mayores (Artículos/Capítulos)
        # Usamos un lookahead para no perder el separador
        structure_pattern = re.compile(r"(?=\n(?:ART[ÍI]CULO|CAP[ÍI]TULO|SECCI[ÓO]N|RESUELVE|CONSIDERANDO))", re.IGNORECASE)
        blocks = structure_pattern.split(text)
        
        final_chunks = []
        hierarchy = HierarchyContext()
        chunk_idx = 0

        for block in blocks:
            if not block.strip(): continue
            
            # Detectar nivel y actualizar jerarquía
            level = LegalPatterns.detect_level(block)
            hierarchy.update(level, block)
            
            # 2. Segunda pasada: Sub-dividir bloques que superen el chunk_size
            sub_chunks = self.recursive_splitter.split_text(block)
            
            for sub_content in sub_chunks:
                meta = (metadata or {}).copy()
                meta.update({
                    "chunk_index": chunk_idx,
                    "legal_level": level,
                    "hierarchy": hierarchy.to_dict(),
                    "chunk_size": len(sub_content)
                })
                # Inyectar el artículo actual directamente en la metadata para filtros rápidos
                if hierarchy.article:
                    meta["article"] = hierarchy.article
                
                final_chunks.append(Document(page_content=sub_content.strip(), metadata=meta))
                chunk_idx += 1

        return final_chunks

    def chunk(self, documents: List[Document]) -> List[Document]:
        """Interfaz de procesamiento por lotes."""
        all_chunks = []
        for doc in documents:
            all_chunks.extend(self.split_text(doc.page_content, metadata=doc.metadata))
        
        logger.info(f"[ADAPTIVE_CHUNKER v2] Generados {len(all_chunks)} chunks jerárquicos.")
        return all_chunks

def get_adaptive_chunker(chunk_size: int = 1000, overlap: int = 200) -> AdaptiveChunker:
    """Factory para obtener el segmentador Pro."""
    return AdaptiveChunker(chunk_size=chunk_size, chunk_overlap=overlap)

