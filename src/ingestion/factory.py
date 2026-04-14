"""
Factory para seleccionar el loader de PDF apropiado.

Permite cambiar entre:
- PyMuPDF (gratis, rápido, texto nativo)
- Docling IBM (gratis, preserva tablas → Markdown)
- LlamaParse (pago, máxima fidelidad en PDFs escaneados)
"""

import logging
from typing import List

from langchain_core.documents import Document

from src.ingestion.base import BasePDFLoader
from src.ingestion.pdf_simple import PyMuPDFLoader, get_pymupdf_loader
from src.ingestion.pdf_llamaparse import (
    LlamaParseLoader,
    get_llamaparse_loader,
)

# DoclingLoader — import condicional (depende de `pip install docling`)
try:
    from src.ingestion.pdf_docling import DoclingLoader, get_docling_loader
    _DOCLING_AVAILABLE = True
except ImportError:
    DoclingLoader = None  # type: ignore[misc, assignment]
    get_docling_loader = None  # type: ignore[misc, assignment]
    _DOCLING_AVAILABLE = False

logger = logging.getLogger(__name__)


class LoaderType:
    """Constantes para tipos de loader."""

    PYMUPDF = "pymupdf"
    DOCLING = "docling"
    LLAMAPARSE = "llamaparse"


def get_loader(loader_type: str = LoaderType.PYMUPDF, **kwargs) -> BasePDFLoader:
    """
    Obtiene el loader según el tipo.

    Args:
        loader_type: 'pymupdf', 'docling' o 'llamaparse'
        **kwargs: Parámetros adicionales para el loader

    Returns:
        Instancia de BasePDFLoader

    Raises:
        ValueError: Si el loader_type no es reconocido.
        ImportError: Si Docling no está instalado y se solicita.
    """
    if loader_type == LoaderType.PYMUPDF:
        logger.info("Usando loader PyMuPDF (gratis, rápido)")
        return get_pymupdf_loader(**kwargs)
    elif loader_type == LoaderType.DOCLING:
        if not _DOCLING_AVAILABLE:
            raise ImportError(
                "Docling no está instalado. "
                "Ejecuta: pip install docling\n"
                "Docling es ideal para PDFs con tablas complejas y columnas múltiples."
            )
        logger.info("Usando loader Docling (gratis, tablas → Markdown)")
        return get_docling_loader(**kwargs)
    elif loader_type == LoaderType.LLAMAPARSE:
        logger.info("Usando loader LlamaParse (pago, máxima fidelidad)")
        return get_llamaparse_loader(**kwargs)
    else:
        raise ValueError(
            f"Loader desconocido: {loader_type}. Usa 'pymupdf', 'docling' o 'llamaparse'"
        )


def load_pdf(
    pdf_path: str, loader_type: str = LoaderType.PYMUPDF, **kwargs
) -> List[Document]:
    """Carga un PDF con el loader especificado."""
    loader = get_loader(loader_type, **kwargs)
    return loader.load(pdf_path)


def load_pdfs(
    pdf_paths: List[str], loader_type: str = LoaderType.PYMUPDF, **kwargs
) -> List[Document]:
    """Carga múltiples PDFs con el loader especificado."""
    loader = get_loader(loader_type, **kwargs)
    return loader.load_multiple(pdf_paths)

