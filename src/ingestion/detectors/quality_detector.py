"""
Quality Detector — Triage de Documentos Legales
─────────────────────────────────────────────
Analiza la calidad del PDF para decidir la ruta de extracción.
"""

import logging
from pathlib import Path
import pdfplumber

logger = logging.getLogger(__name__)

class QualityReport:
    """Informe de calidad de un documento."""
    def __init__(self, is_scanned: bool, text_density: float, pages: int):
        self.is_scanned = is_scanned
        self.text_density = text_density  # Caracteres por página (promedio)
        self.pages = pages

    def needs_ocr(self) -> bool:
        """Decide si el documento requiere OCR pesado."""
        return self.is_scanned or self.text_density < 100

    def __repr__(self):
        return f"<QualityReport scanned={self.is_scanned}, density={self.text_density:.2f} chars/pg>"

def analyze_pdf_quality(file_path: Path) -> QualityReport:
    """
    Analiza las primeras páginas para determinar si es un escaneo.
    """
    total_text = 0
    pages_with_text = 0
    total_pages = 0

    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            # Analizamos máximo 5 páginas para rapidez
            pages_to_check = pdf.pages[:5]
            
            for page in pages_to_check:
                text = page.extract_text() or ""
                total_text += len(text.strip())
                if len(text.strip()) > 50:
                    pages_with_text += 1

        avg_density = total_text / len(pages_to_check) if pages_to_check else 0
        # Si menos del 20% de las páginas revisadas tienen texto, es un escaneo
        is_scanned = (pages_with_text / len(pages_to_check)) < 0.2 if pages_to_check else True

        report = QualityReport(is_scanned, avg_density, total_pages)
        logger.info(f"[QUALITY] {file_path.name}: {report}")
        return report

    except Exception as e:
        logger.error(f"[QUALITY] Error analizando {file_path.name}: {e}")
        return QualityReport(is_scanned=True, text_density=0, pages=0)
