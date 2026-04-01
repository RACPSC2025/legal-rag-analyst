"""
PyMuPDFLoader Profesional para Documentos Legales Colombianos
Versión optimizada - Respeta artículos completos y reduce cortes
"""

import logging
import re
from pathlib import Path
from typing import List

import fitz
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import settings
from src.ingestion.base import BasePDFLoader

logger = logging.getLogger(__name__)

# Separadores jerárquicos (orden de mayor a menor prioridad)
LEGAL_SEPARATORS = [
    "\nARTÍCULO ",           # Prioridad #1
    "\nArtículo ",
    "\nCAPÍTULO ",
    "\nSECCIÓN ",
    "\nPARÁGRAFO ",
    "\n\n\n",                # Bloques grandes
    "\n\n",
    "\n",
    " ",
]


class PyMuPDFLoader(BasePDFLoader):
    """Loader optimizado para normativa legal colombiana (Decreto 1072, etc.)."""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        max_pages: int = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.max_pages = max_pages or 400

    @property
    def loader_type(self) -> str:
        return "pymupdf_legal"

    def _extract_text(self, pdf_path: Path) -> str:
        """Extrae texto completo preservando orden secuencial de páginas."""
        doc = fitz.open(str(pdf_path))
        pages: List[str] = []

        for page_num, page in enumerate(doc, start=1):
            if page_num > self.max_pages:
                logger.warning(f"Límite de páginas alcanzado en {pdf_path.name}")
                break
            text = page.get_text("text")
            if text.strip():
                pages.append(f"[Página {page_num}]\n{text}")

        doc.close()
        return "\n\n".join(pages)

    def _clean_text(self, text: str) -> str:
        """Limpieza agresiva de ruido típico del Decreto 1072."""
        if not text:
            return ""
        
        # Eliminar franjas repetitivas
        text = re.sub(r"Departamento Administrativo de la Función Pública", "", text, flags=re.IGNORECASE)
        text = re.sub(r"Decreto 1072 de 2015 Sector Trabajo\s*\d+\s*EVA - Gestor Normativo", "", text, flags=re.IGNORECASE)
        text = re.sub(r"_{4,}|-{4,}", "", text)
        
        # Limpieza general sin alterar estructura legal
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        # text = re.sub(r"(\w)\n(\w)", r"\1 \2", text)  # COMENTADO: Rompe tablas legales
        text = re.sub(r" +", " ", text)
        
        return text.strip()

    def _get_article_metadata(self, chunk_text: str) -> dict:
        """Extrae metadata útil del chunk."""
        page_match = re.search(r"\[Página\s*(\d+)\]", chunk_text)
        page = page_match.group(1) if page_match else "?"

        article_match = re.search(r"ARTÍCULO\s*([\d\.]+)", chunk_text, re.IGNORECASE)
        article_num = article_match.group(1) if article_match else None

        return {
            "source": Path(chunk_text).name if hasattr(chunk_text, 'name') else "document.pdf",  # fallback
            "page": page,
            "article": article_num,
            "loader": "pymupdf_legal",
        }

    def _split_text(self, text: str, source: str) -> List[Document]:
        """Chunking inteligente con Contextual Headers (Módulo 11)."""
        clean_text = self._clean_text(text)

        splitter = RecursiveCharacterTextSplitter(
            separators=LEGAL_SEPARATORS,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

        # Primera pasada: dividir el texto
        raw_chunks = splitter.split_text(clean_text)

        documents = []
        source_name = Path(source).name
        
        for i, chunk in enumerate(raw_chunks):
            if len(chunk.strip()) < 50:
                continue

            metadata = self._get_article_metadata(chunk)
            
            # --- CONTEXTUAL HEADER INJECTION ---
            # Inyectamos el contexto literal al principio del contenido del chunk
            # Esto ayuda al embedding y al LLM a saber dónde están parados.
            article_info = f"Art. {metadata['article']}" if metadata['article'] else "Contexto general"
            header = f"[Documento: {source_name} | {article_info} | Página: {metadata['page']}]\n"
            
            content_with_context = header + chunk.strip()

            metadata.update({
                "source": source_name,
                "path": str(source),
                "chunk_index": i,
                "chunk_size": len(content_with_context),
            })

            documents.append(Document(
                page_content=content_with_context,
                metadata=metadata
            ))

        logger.info(
            f"✅ {source_name} → {len(documents)} chunks con Contextual Headers."
        )
        return documents

    def load(self, pdf_path: str | Path) -> List[Document]:
        """Carga y procesa un PDF."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

        text = self._extract_text(pdf_path)
        return self._split_text(text, str(pdf_path))

    def load_multiple(self, pdf_paths: List[str | Path]) -> List[Document]:
        """Carga múltiples PDFs."""
        documents = []
        for pdf_path in pdf_paths:
            try:
                docs = self.load(pdf_path)
                documents.extend(docs)
            except Exception as e:
                logger.error(f"Error cargando {pdf_path}: {e}")
        return documents


def get_pymupdf_loader(**kwargs) -> PyMuPDFLoader:
    """Factory function para obtener el loader."""
    return PyMuPDFLoader(**kwargs)
