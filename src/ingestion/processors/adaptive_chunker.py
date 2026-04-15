"""
Adaptive Chunker — Segmentación Legal Jerárquica
────────────────────────────────────────────────
Fragmenta el texto respetando la estructura normativa (Artículos, Capítulos).
Implementa lógica Parent-Child y protección de tablas.
"""

import logging
import re
from typing import List, Dict, Any
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter
)
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class AdaptiveLegalChunker:
    """
    Segmentador inteligente que adapta su estrategia según la estructura del texto.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        add_parent_metadata: bool = True
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.add_parent_metadata = add_parent_metadata

        # 1. Configuramos el segmentador por encabezados Markdown
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False
        )

        # 2. Configuramos el segmentador recursivo para fragmentos que excedan el tamaño
        # Usamos los separadores legales definidos en la Sección 8 de la documentación
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=[
                "\n## RESUELVE", 
                "\n## CONSIDERANDO", 
                "\n### ARTÍCULO", 
                "\n#### PARÁGRAFO",
                "\n\n\n", 
                "\n\n", 
                "\n", 
                " "
            ]
        )

    def split_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Segmenta el texto siguiendo un flujo jerárquico:
        Markdown Headers -> Recursive Splitter -> Metadata Enrichment.
        """
        if not text:
            return []

        # Paso 1: Segmentación por estructura (Headers)
        # Esto agrupa el texto por Capítulos/Artículos
        structural_chunks = self.header_splitter.split_text(text)
        
        final_chunks = []
        
        # Paso 2: Refinar fragmentos que sigan siendo muy grandes
        for chunk in structural_chunks:
            # Combinamos la metadata base con la metadata extraída del header
            base_meta = metadata.copy() if metadata else {}
            base_meta.update(chunk.metadata)
            
            if len(chunk.page_content) > self.chunk_size:
                # Si el artículo es muy largo, lo subdividimos recursivamente
                sub_chunks = self.recursive_splitter.split_text(chunk.page_content)
                for i, sub_content in enumerate(sub_chunks):
                    # Marcamos como fragmento refinado
                    meta = base_meta.copy()
                    meta["chunk_index"] = i
                    meta["is_refined"] = True
                    final_chunks.append(Document(page_content=sub_content, metadata=meta))
            else:
                # Si cabe perfecto, lo mantenemos íntegro (ideal para preservar tablas)
                final_chunks.append(Document(page_content=chunk.page_content, metadata=base_meta))

        logger.info(f"[CHUNKER] Generados {len(final_chunks)} chunks para el documento.")
        return final_chunks

def get_adaptive_chunker(chunk_size: int = 800, overlap: int = 150) -> AdaptiveLegalChunker:
    """Factory para obtener el segmentador configurado."""
    return AdaptiveLegalChunker(chunk_size=chunk_size, chunk_overlap=overlap)
