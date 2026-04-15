"""
Ingestion Factory — Despachador de Cargadores
─────────────────────────────────────────────
Patrón Factory para instanciar motores de extracción.
"""

import logging
from enum import Enum
from typing import Optional
from src.ingestion.base import BasePDFLoader

logger = logging.getLogger(__name__)

class LoaderType(str, Enum):
    """Tipos de cargadores soportados."""
    DOCLING = "docling"
    PYMUPDF = "pymupdf"
    LLAMAPARSE = "llamaparse"
    OCR = "ocr"

def get_loader(loader_type: LoaderType | str) -> BasePDFLoader:
    """
    Retorna una instancia del cargador solicitado.
    
    Args:
        loader_type: Tipo de motor (docling, pymupdf, llamaparse, ocr)
        
    Returns:
        Instancia que hereda de BasePDFLoader.
    """
    # Normalización del tipo
    if isinstance(loader_type, str):
        loader_type = LoaderType(loader_type.lower())

    if loader_type == LoaderType.DOCLING:
        from src.ingestion.loaders.pdf_docling import DoclingLoader
        return DoclingLoader()
    
    elif loader_type == LoaderType.PYMUPDF:
        from src.ingestion.loaders.pdf_pymupdf import PyMuPDFLoader
        return PyMuPDFLoader()
    
    elif loader_type == LoaderType.LLAMAPARSE:
        from src.ingestion.loaders.pdf_llamaparse import LlamaParsePDFLoader
        return LlamaParsePDFLoader()
    
    # Próximamente: OCR Loader
    # elif loader_type == LoaderType.OCR:
    #     from src.ingestion.loaders.pdf_ocr import OCRPDFLoader
    #     return OCRPDFLoader()

    raise ValueError(f"Loader '{loader_type}' no reconocido o no implementado.")
