"""
DoclingLoader — Loader de PDFs Legales vía Docling (IBM Research, open source).

Cuándo usar Docling en lugar de PyMuPDF:
─────────────────────────────────────────
  • PDFs con TABLAS complejas (ej: tablas de artículos del Decreto 1072)
  • PDFs con múltiples COLUMNAS (boletines, gacetas)
  • PDFs escaneados con OCR (Docling integra EasyOCR / Tesseract)
  • Cualquier documento donde la ESTRUCTURA semántica sea crítica

Ventaja clave: Docling convierte el PDF a Markdown estructurado ANTES de chunkear,
lo que permite al splitter respetar encabezados, listas y celdas de tabla.

Instalación:
    pip install docling

Nota: El primer uso descarga modelos (~1GB). Usa artifacts_path para no repetirlo.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from src.ingestion.base import BasePDFLoader
from src.config import settings

logger = logging.getLogger(__name__)

# Separadores para el fallback RecursiveCharacterTextSplitter (post-Markdown)
MARKDOWN_FALLBACK_SEPARATORS = [
    "\n## ",   # Encabezados H2 (ARTÍCULO, CAPÍTULO en Markdown)
    "\n### ",  # Encabezados H3 (secciones internas)
    "\n\n",    # Párrafos
    "\n",
    " ",
]

# Headers que Docling suele generar para normativa colombiana
MARKDOWN_HEADERS_TO_SPLIT = [
    ("#", "titulo"),
    ("##", "capitulo"),
    ("###", "articulo"),
    ("####", "paragrafo"),
]


class DoclingLoader(BasePDFLoader):
    """
    Loader que usa Docling para convertir PDFs a Markdown estructurado
    antes de hacer chunking. Ideal para documentos legales con tablas.
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        max_pages: int = None,
        use_ocr: bool = False,
        artifacts_path: Optional[str] = None,
    ) -> None:
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.max_pages = max_pages  # None = sin límite en Docling
        self.use_ocr = use_ocr

        # Directorio de caché de modelos Docling (evita redownloads)
        self.artifacts_path = artifacts_path or str(
            Path(settings.ROOT_DIR) / "storage" / "docling_models"
        )

    @property
    def loader_type(self) -> str:
        return "docling_legal"

    def _convert_to_markdown(self, pdf_path: Path) -> str:
        """
        Convierte el PDF a Markdown usando Docling.

        Preserva tablas como markdown tables (| col | col |).
        Si Docling no está instalado o falla, hace fallback a PyMuPDF.

        Args:
            pdf_path: Ruta al archivo PDF.

        Returns:
            Texto Markdown estructurado.
        """
        try:
            from docling.document_converter import DocumentConverter
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import PdfFormatOption

            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = self.use_ocr
            pipeline_options.do_table_structure = True  # CRÍTICO para tablas legales
            pipeline_options.table_structure_options.do_cell_matching = True

            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options,
                        artifacts_path=self.artifacts_path,
                    )
                }
            )

            result = converter.convert(str(pdf_path))
            markdown_text = result.document.export_to_markdown()

            logger.info(
                f"[DOCLING] ✅ '{pdf_path.name}' convertido a Markdown "
                f"({len(markdown_text)} chars)"
            )
            return markdown_text

        except ImportError:
            logger.warning(
                "[DOCLING] Docling no está instalado. Ejecuta: pip install docling\n"
                "Fallback a extracción de texto básico con PyMuPDF."
            )
            return self._fallback_text_extract(pdf_path)

        except Exception as e:
            logger.error(f"[DOCLING] Error convirtiendo '{pdf_path.name}': {e}. Usando fallback.")
            return self._fallback_text_extract(pdf_path)

    def _fallback_text_extract(self, pdf_path: Path) -> str:
        """
        Extracción básica con PyMuPDF si Docling falla.

        Args:
            pdf_path: Ruta al archivo PDF.

        Returns:
            Texto extraído con encabezados Markdown básicos.
        """
        try:
            import fitz

            doc = fitz.open(str(pdf_path))
            pages: List[str] = []

            max_page = self.max_pages or doc.page_count
            for page_num, page in enumerate(doc, start=1):
                if page_num > max_page:
                    logger.warning(
                        f"[DOCLING FALLBACK] Límite de páginas ({max_page}) en '{pdf_path.name}'"
                    )
                    break
                text = page.get_text("text")
                if text.strip():
                    pages.append(f"## Página {page_num}\n\n{text}")

            doc.close()
            return "\n\n".join(pages)

        except Exception as e:
            logger.error(f"[DOCLING FALLBACK] Error con fitz: {e}")
            return ""

    def _clean_markdown(self, text: str) -> str:
        """
        Limpia ruidos específicos de normativa colombiana en el Markdown generado.

        Args:
            text: Texto Markdown crudo.

        Returns:
            Texto Markdown limpio.
        """
        if not text:
            return ""

        # Ruidos típicos del Decreto 1072
        text = re.sub(
            r"Departamento Administrativo de la Función Pública",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"Decreto 1072 de 2015 Sector Trabajo\s*\d+\s*EVA - Gestor Normativo",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"_{4,}|-{4,}", "", text)

        # Normalizar saltos excesivos sin romper estructura Markdown
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()

    def _split_markdown(self, markdown: str, source: str) -> List[Document]:
        """
        Chunking en dos pasos:
        1. MarkdownHeaderTextSplitter: respeta la jerarquía de encabezados.
        2. RecursiveCharacterTextSplitter: subdivide chunks demasiado grandes.

        Esto garantiza que:
        - Las tablas no se corten en la mitad.
        - Los artículos largos se subdividen con overlap.
        - Cada chunk sabe a qué artículo/capítulo pertenece (via metadata).

        Args:
            markdown: Texto Markdown estructurado.
            source: Ruta o nombre del archivo fuente.

        Returns:
            Lista de Documents con metadata enriquecida.
        """
        clean_md = self._clean_markdown(markdown)
        source_name = Path(source).name

        # Paso 1: Split por encabezados Markdown
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=MARKDOWN_HEADERS_TO_SPLIT,
            strip_headers=False,  # Conservar el encabezado en el contenido
        )
        header_chunks = header_splitter.split_text(clean_md)

        # Paso 2: Subdividir chunks grandes respetando párrafos
        char_splitter = RecursiveCharacterTextSplitter(
            separators=MARKDOWN_FALLBACK_SEPARATORS,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )

        documents: List[Document] = []
        chunk_idx = 0

        for header_chunk in header_chunks:
            # Si el chunk cabe en un solo trozo, usarlo directamente
            if len(header_chunk.page_content) <= self.chunk_size:
                sub_chunks: List[str] = [header_chunk.page_content]
            else:
                sub_chunks = char_splitter.split_text(header_chunk.page_content)

            for sub_chunk in sub_chunks:
                if len(sub_chunk.strip()) < 50:
                    continue

                # Extraer número de artículo del contenido o del metadata del header
                article_num = self._extract_article_num(
                    sub_chunk, header_chunk.metadata
                )

                # Inyección de Contextual Header (mismo patrón que PyMuPDFLoader)
                article_info = f"Art. {article_num}" if article_num else "Contexto general"
                # Extraer capítulo/sección del metadata del header si existe
                section_info = (
                    header_chunk.metadata.get("capitulo")
                    or header_chunk.metadata.get("titulo")
                    or ""
                )
                header_str = (
                    f"[Documento: {source_name} | "
                    f"{article_info}{' | ' + section_info if section_info else ''} | "
                    f"Formato: Markdown]\n"
                )

                content_with_context = header_str + sub_chunk.strip()

                metadata = {
                    "source": source_name,
                    "path": str(source),
                    "loader": "docling_legal",
                    "article": article_num,
                    "chunk_index": chunk_idx,
                    "chunk_size": len(content_with_context),
                    "format": "markdown",
                    # Propagamos metadata de sección del MarkdownHeaderSplitter
                    **{
                        k: v
                        for k, v in header_chunk.metadata.items()
                        if v  # Solo metadata no vacío
                    },
                }

                documents.append(
                    Document(page_content=content_with_context, metadata=metadata)
                )
                chunk_idx += 1

        logger.info(
            f"✅ [DOCLING] '{source_name}' → {len(documents)} chunks "
            f"(Markdown estructurado, tablas preservadas)."
        )
        return documents

    def _extract_article_num(self, text: str, header_metadata: dict) -> Optional[str]:
        """
        Extrae número de artículo del contenido o del metadata del encabezado.

        Args:
            text: Contenido del chunk.
            header_metadata: Metadata del MarkdownHeaderTextSplitter.

        Returns:
            Número de artículo o None si no se encuentra.
        """
        # Primero buscar en el metadata del MarkdownHeaderSplitter
        articulo_meta = header_metadata.get("articulo", "")
        if articulo_meta:
            match = re.search(r"(\d[\d\.]*)", articulo_meta)
            if match:
                return match.group(1)

        # Buscar en el texto del chunk
        match = re.search(r"ARTÍCULO\s*([\d\.]+)", text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def load(self, pdf_path: str | Path) -> List[Document]:
        """
        Carga un PDF convirtiéndolo a Markdown con Docling.

        Args:
            pdf_path: Ruta al archivo PDF.

        Returns:
            Lista de Documents con chunks Markdown.

        Raises:
            FileNotFoundError: Si el PDF no existe.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

        markdown = self._convert_to_markdown(pdf_path)
        return self._split_markdown(markdown, str(pdf_path))

    def load_multiple(self, pdf_paths: List[str | Path]) -> List[Document]:
        """
        Carga múltiples PDFs.

        Args:
            pdf_paths: Lista de rutas a PDFs.

        Returns:
            Lista combinada de Documents de todos los PDFs procesados.
        """
        documents: List[Document] = []
        for pdf_path in pdf_paths:
            try:
                docs = self.load(pdf_path)
                documents.extend(docs)
            except Exception as e:
                logger.error(f"[DOCLING] Error cargando '{pdf_path}': {e}")
        return documents


def get_docling_loader(**kwargs) -> DoclingLoader:
    """
    Factory function para obtener el loader Docling.

    Args:
        **kwargs: Parámetros para DoclingLoader (chunk_size, use_ocr, etc.)

    Returns:
        Instancia de DoclingLoader.
    """
    return DoclingLoader(**kwargs)
