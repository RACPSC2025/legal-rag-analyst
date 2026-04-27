"""
DoclingLoader Avanzado — Estrategia Ganadora (v3.0)
Abril 2026 - Optimizado para Imágenes Preprocesadas y OCR Legal
"""

from __future__ import annotations

import time
import re
import logging
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document

from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions, RapidOcrOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc.document import DoclingDocument

from src.ingestion.base import BasePDFLoader
from src.ingestion.detectors.quality_detector import PDFQualityDetector
from src.ingestion.processors.ocr_preprocessor import OCRPreprocessor
from src.ingestion.processors.text_cleaner import get_text_cleaner
from src.ingestion.processors.adaptive_chunker import AdaptiveChunker
from src.ingestion.processors.metadata_extractor import get_metadata_extractor

from src.config.logging import get_logger

log = get_logger(__name__)


class DoclingLoader(BasePDFLoader):
    """DoclingLoader optimizado con escala 3.0 y soporte dual PDF/IMAGE."""

    def __init__(
        self,
        chunk_size: int = 750,
        chunk_overlap: int = 180,
        table_mode: str = "accurate",
        force_full_page_ocr: bool = True,
        images_scale: float = 3.0,      # Aumentado a 3.0 según estrategia Ronny
        use_ocr: bool = True,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.table_mode = table_mode
        self.force_full_page_ocr = force_full_page_ocr
        self.images_scale = images_scale
        self.use_ocr = use_ocr

        # Componentes
        self.quality_detector = PDFQualityDetector()
        # Nota: OCRPreprocessor ahora usará modo suave internamente
        self.ocr_preprocessor = OCRPreprocessor(target_dpi=300)
        self.text_cleaner = get_text_cleaner("legal_colombia")
        self.chunker = AdaptiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.metadata_extractor = get_metadata_extractor()

        # Configuración Maestro de Pipeline (Aplicable a PDF e Imágenes)
        self.pipeline_options = PdfPipelineOptions(
            do_ocr=True,
            do_table_structure=True,
            table_structure_options=TableStructureOptions(
                do_cell_matching=True,
                mode=table_mode,
            ),
            ocr_options=RapidOcrOptions(
                force_full_page_ocr=True,
                lang=["es", "en"],
            ),
            images_scale=self.images_scale,
            generate_parsed_pages=True,
        )

        # CRÍTICO: Definir opciones para AMBOS formatos para que convert_all respete la config
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=self.pipeline_options),
                InputFormat.IMAGE: ImageFormatOption(pipeline_options=self.pipeline_options)
            }
        )

    @property
    def loader_type(self) -> str:
        return "docling_advanced_v3"

    @property
    def name(self) -> str:
        return "Docling High-Res Engine"

    def load(self, pdf_path: str | Path, **kwargs) -> List[Document]:
        pdf_path = Path(pdf_path)
        start_time = time.time()
        log.info(f"[DOCLING] 🎯 Iniciando Ingestión de Alta Resolución: {pdf_path.name}")

        try:
            quality = self.quality_detector.analyze(pdf_path)
            # Activamos visión industrial si la calidad es baja
            use_preprocessed = (quality.recommendation in ("ocr_heavy", "docling") or quality.quality_score < 0.4)

            if use_preprocessed:
                log.info("[DOCLING] → Aplicando Visión Industrial (OpenCV) + Docling Scale 3.0")
                output_dir = Path("debug_ocr") / pdf_path.stem
                image_paths = self.ocr_preprocessor.process_pdf(pdf_path, output_dir=output_dir)

                # Docling ahora usará ImageFormatOption con Scale 3.0
                results = list(self.converter.convert_all([str(p) for p in image_paths]))
                docling_doc = results[0].document if results else None
                markdown = "\n\n".join([r.document.export_to_markdown() for r in results])
            else:
                log.info("[DOCLING] → Conversión Nativa de Alta Resolución")
                result = self.converter.convert(str(pdf_path))
                docling_doc = result.document
                markdown = docling_doc.export_to_markdown()

            # Post-procesamiento
            if docling_doc:
                markdown = self._post_process_tables(markdown, docling_doc)

            cleaned = self.text_cleaner.clean(markdown)
            base_doc = Document(page_content=cleaned, metadata={"source": pdf_path.name})
            
            chunks = self.chunker.chunk([base_doc], document_type="resolucion")
            enriched = self.metadata_extractor.enrich_documents(chunks)

            log.info(f"[DOCLING] ✓ Éxito: {len(enriched)} chunks generados en {time.time()-start_time:.1f}s")
            return enriched

        except Exception as e:
            log.error(f"[DOCLING] Error Crítico: {e}")
            return self._fallback_load(pdf_path)

    def _post_process_tables(self, markdown: str, docling_doc: DoclingDocument) -> str:
        if not hasattr(docling_doc, "tables") or not docling_doc.tables:
            return markdown

        processed = markdown
        for idx, table in enumerate(docling_doc.tables):
            try:
                df = table.export_to_dataframe()
                if df is None or df.empty: continue
                df.columns = [str(c).strip().replace('\n', ' ') for c in df.columns]
                df = df.map(lambda x: str(x).strip() if isinstance(x, str) else x)
                # Normalización legal colombiana
                df = df.replace(r'(?i)^\s*Si\s*$', 'Cumple', regex=True)
                df = df.replace(r'(?i)^\s*No\s*$', 'No Cumple', regex=True)
                
                clean_md = df.to_markdown(index=False, tablefmt="pipe")
                processed = re.sub(rf'(?i)(?:Tabla\s*{idx+1}|\[Tabla\])', f"\n\n### Tabla {idx+1}\n\n{clean_md}\n\n", processed, count=1)
            except Exception: continue
        return processed

    def _fallback_load(self, pdf_path: Path) -> List[Document]:
        import fitz
        doc = fitz.open(str(pdf_path))
        text = "\n\n".join(page.get_text("text") for page in doc)
        doc.close()
        base_doc = Document(page_content=text, metadata={"source": pdf_path.name})
        chunks = self.chunker.chunk([base_doc], document_type="resolucion")
        return self.metadata_extractor.enrich_documents(chunks)

    def load_multiple(self, pdf_paths: List[str | Path]) -> List[Document]:
        all_docs = []
        for p in pdf_paths:
            try: all_docs.extend(self.load(p))
            except Exception as e: log.error(f"Error en {p}: {e}")
        return all_docs

def get_docling_loader(**kwargs) -> DoclingLoader:
    return DoclingLoader(**kwargs)