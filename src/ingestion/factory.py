"""
Factory para seleccionar el loader de PDF apropiado.
Permite cambiar entre PyMuPDF (gratis) y LlamaParse (pago).
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

logger = logging.getLogger(__name__)


class LoaderType:
    """Constantes para tipos de loader."""

    PYMUPDF = "pymupdf"
    LLAMAPARSE = "llamaparse"


def get_loader(loader_type: str = LoaderType.PYMUPDF, **kwargs) -> BasePDFLoader:
    """
    Obtiene el loader según el tipo.

    Args:
        loader_type: 'pymupdf' (gratis) o 'llamaparse' (pago)
        **kwargs: Parámetros adicionales para el loader

    Returns:
        Instancia de BasePDFLoader
    """
    if loader_type == LoaderType.PYMUPDF:
        logger.info("Usando loader PyMuPDF (gratis)")
        return get_pymupdf_loader(**kwargs)
    elif loader_type == LoaderType.LLAMAPARSE:
        logger.info("Usando loader LlamaParse (pago)")
        return get_llamaparse_loader(**kwargs)
    else:
        raise ValueError(
            f"Loader desconocido: {loader_type}. Usa 'pymupdf' o 'llamaparse'"
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
