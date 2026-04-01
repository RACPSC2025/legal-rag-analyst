"""
Base loader interface para PDFs.
Define el contrato que deben implementar todos los loaders.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from langchain_core.documents import Document


class BasePDFLoader(ABC):
    """Interfaz base para loaders de PDF."""

    @abstractmethod
    def load(self, pdf_path: str | Path) -> List[Document]:
        """Carga un PDF y retorna lista de Documents."""
        pass

    @abstractmethod
    def load_multiple(self, pdf_paths: List[str | Path]) -> List[Document]:
        """Carga múltiples PDFs."""
        pass

    @property
    @abstractmethod
    def loader_type(self) -> str:
        """Retorna el tipo de loader (ej: 'pymupdf', 'llamaparse')."""
        pass
