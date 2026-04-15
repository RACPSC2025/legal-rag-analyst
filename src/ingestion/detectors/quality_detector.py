"""
PDFQualityDetector — Detector inteligente de calidad para PDFs legales.
───────────────────────────────────────────────────────────────────────
Versión Upgrade (Senior Logic):
Decide la mejor ruta de procesamiento según:
- Calidad del texto nativo
- Presencia de tablas (caracteres de dibujo │)
- Cobertura de palabras y DPI estimado
"""

from __future__ import annotations
import fitz  # PyMuPDF
import pdfplumber
import numpy as np
from pathlib import Path
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class QualityResult:
    """Informe detallado de calidad y recomendación de motor."""
    is_native: bool
    is_scanned: bool
    quality_score: float          # 0.0 (muy malo) → 1.0 (excelente)
    avg_chars_per_page: float
    text_coverage: float
    dpi_estimate: float
    has_tables: bool
    has_images: bool
    recommendation: str           # "pymupdf", "docling", "ocr_heavy"
    reasoning: str

    def needs_ocr(self) -> bool:
        """Helper para compatibilidad con el pipeline anterior."""
        return self.recommendation == "ocr_heavy"

class PDFQualityDetector:
    """Detector de calidad optimizado para resoluciones administrativas colombianas."""

    def __init__(self):
        self.min_chars_good = 650
        self.min_chars_scanned = 280
        self.low_quality_threshold = 0.58

    def analyze(self, pdf_path: str | Path) -> QualityResult:
        """
        Analiza el PDF y retorna un score de calidad ponderado.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {path}")

        try:
            doc = fitz.open(str(path))
            total_chars = 0
            page_count = len(doc)
            text_coverages = []
            has_tables = False
            has_images = False

            # Analizar una muestra representativa (primeras 10 páginas)
            sample_pages = doc[:10]
            for page in sample_pages:
                text = page.get_text("text").strip()
                total_chars += len(text)

                # Cobertura: palabras / 350 (densidad estándar de página legal)
                words = len(text.split())
                coverage = min(1.0, words / 350)
                text_coverages.append(coverage)

                # Detección de tablas por caracteres de dibujo o palabras clave
                try:
                    tabs = page.find_tables()
                    if tabs.tables or "│" in text or ("Tabla" in text and "Si" in text):
                        has_tables = True
                except:
                    if "│" in text or ("Tabla" in text and "Si" in text):
                        has_tables = True
                if page.get_images():
                    has_images = True

            doc.close()

            avg_chars = total_chars / max(len(sample_pages), 1)
            avg_coverage = np.mean(text_coverages) if text_coverages else 0.0

            # Estimación DPI vía pdfplumber (más preciso para metadatos de imagen)
            dpi_estimate = 72.0
            try:
                with pdfplumber.open(str(path)) as pdf:
                    dpi_estimate = getattr(pdf.pages[0], 'dpi', 72) or 72
            except:
                pass

            is_native = avg_chars > self.min_chars_good and avg_coverage > 0.65
            is_scanned = avg_chars < self.min_chars_scanned or avg_coverage < 0.45

            # Ponderación del Score de Calidad
            quality_score = min(1.0, 
                (avg_chars / 1400) * 0.55 + 
                avg_coverage * 0.35 + 
                (0.1 if dpi_estimate > 200 else 0)
            )

            # Lógica de Recomendación Inteligente (El Corazón del Router)
            if has_tables and quality_score < 0.75:
                # Si hay tablas y la calidad no es perfecta, Docling es la mejor opción
                recommendation = "docling"
            elif is_scanned or quality_score < self.low_quality_threshold:
                # Si es un escaneo sucio o score bajo, requiere OCR con preprocesamiento
                recommendation = "ocr_heavy"
            else:
                # Para documentos nativos limpios, PyMuPDF es instantáneo y barato
                recommendation = "pymupdf" if is_native else "docling"

            reasoning = (
                f"Chars/page: {avg_chars:.0f}, Coverage: {avg_coverage:.2f}, "
                f"Tables: {has_tables}, DPI: {dpi_estimate:.0f} → {recommendation}"
            )

            result = QualityResult(
                is_native=is_native,
                is_scanned=is_scanned,
                quality_score=round(quality_score, 3),
                avg_chars_per_page=round(avg_chars, 1),
                text_coverage=round(avg_coverage, 3),
                dpi_estimate=round(dpi_estimate, 1),
                has_tables=has_tables,
                has_images=has_images,
                recommendation=recommendation,
                reasoning=reasoning,
            )
            logger.info(f"[QUALITY_UPGRADE] {path.name}: {result.reasoning}")
            return result

        except Exception as e:
            logger.error(f"[QUALITY_UPGRADE] Error crítico en {path.name}: {e}")
            return QualityResult(
                is_native=False, is_scanned=True, quality_score=0.35,
                avg_chars_per_page=0, text_coverage=0.0, dpi_estimate=72,
                has_tables=False, has_images=False, recommendation="ocr_heavy",
                reasoning=f"Error: {str(e)} → Fallback OCR Safe",
            )

def analyze_pdf_quality(file_path: Path) -> QualityResult:
    """Entry point funcional para el pipeline."""
    detector = PDFQualityDetector()
    return detector.analyze(file_path)
