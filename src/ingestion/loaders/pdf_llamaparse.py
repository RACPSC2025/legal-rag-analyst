"""
Loader de PDF usando LlamaParse.
Para documentos complejos con tablas, imágenes y formato mixed.
Costo por página procesada.
"""

import logging
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document

from src.config import settings
from src.ingestion.base import BasePDFLoader

logger = logging.getLogger(__name__)


class LlamaParseLoader(BasePDFLoader):
    """Loader de PDF usando LlamaParse (pago, mejor calidad)."""

    def __init__(
        self,
        result_type: str = "markdown",
        language: str = "es",
        api_key: str = None,
        max_pages: int = None,
    ):
        self.result_type = result_type
        self.language = language
        self.api_key = api_key or settings.LLAMA_PARSE_API_KEY
        self.max_pages = max_pages or 350

    @property
    def loader_type(self) -> str:
        return "llamaparse"

    def _get_parser(self):
        """Obtiene instancia del parser LlamaParse."""
        try:
            from llama_parse import LlamaParse

            return LlamaParse(
                result_type=self.result_type,
                language=self.language,
                api_key=self.api_key,
                verbose=False,
            )
        except ImportError:
            raise ImportError(
                "llama-parse no instalado. Ejecuta: pip install llama-parse"
            )

    def load(self, pdf_path: str | Path) -> List[Document]:
        """Carga un PDF usando LlamaParse."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

        try:
            parser = self._get_parser()
            docs = parser.load_data(str(pdf_path))

            for doc in docs:
                doc.metadata["source"] = pdf_path.name
                doc.metadata["path"] = str(pdf_path)
                doc.metadata["loader"] = "llamaparse"

            logger.info(f"LlamaParse: {len(docs)} páginas de '{pdf_path.name}'")
            return docs

        except Exception as e:
            logger.error(f"Error con LlamaParse: {e}")
            raise

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


def get_llamaparse_loader(**kwargs) -> LlamaParseLoader:
    """Factory function para obtener loader LlamaParse."""
    return LlamaParseLoader(**kwargs)
