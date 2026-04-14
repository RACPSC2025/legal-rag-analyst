"""
Módulo de ingestion — punto de entrada unificado para carga de PDFs.

Exporta:
- load_pdfs(paths, loader_type)  → List[Document]  (usado en app.py)
- load_pdf(path, loader_type)    → List[Document]
- LoaderType                     → constantes de tipo de loader
- get_loader(loader_type)        → instancia de BasePDFLoader

Loaders disponibles:
    LoaderType.PYMUPDF    → PyMuPDF (gratis, rápido, texto nativo)
    LoaderType.DOCLING    → Docling IBM (gratis, preserva tablas → Markdown)
    LoaderType.LLAMAPARSE → LlamaParse (pago, máxima fidelidad en PDFs escaneados)
"""

from src.ingestion.factory import (
    get_loader,
    load_pdf,
    load_pdfs,
    LoaderType,
)
from src.ingestion.base import BasePDFLoader
from src.ingestion.pdf_simple import PyMuPDFLoader, get_pymupdf_loader
from src.ingestion.pdf_llamaparse import LlamaParseLoader, get_llamaparse_loader

# DoclingLoader — se importa condicionalmente porque depende de `docling` (pip install docling).
# Si no está instalado, el import falla silenciosamente y el loader no está disponible.
try:
    from src.ingestion.pdf_docling import DoclingLoader, get_docling_loader
except ImportError:
    DoclingLoader = None  # type: ignore[misc, assignment]
    get_docling_loader = None  # type: ignore[misc, assignment]

__all__ = [
    # Factory principal
    "get_loader",
    "load_pdf",
    "load_pdfs",
    "LoaderType",
    # Base
    "BasePDFLoader",
    # Loaders concretos
    "PyMuPDFLoader",
    "get_pymupdf_loader",
    "LlamaParseLoader",
    "get_llamaparse_loader",
    "DoclingLoader",
    "get_docling_loader",
]

