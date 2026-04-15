"""
OCRPreprocessor — Pipeline avanzado de preprocesamiento para PDFs escaneados.
─────────────────────────────────────────────────────────────────────────────
Versión Upgrade (Senior Logic):
Optimizado para resoluciones administrativas colombianas:
- Deskew fuerte (corrección de inclinación usando Transformada de Hough)
- Denoise + binarización adaptativa
- Mejora de contraste CLAHE + Unsharp masking para texto fino
- Upscale inteligente según DPI estimado
"""

import cv2
import numpy as np
from pathlib import Path
from PIL import Image
import tempfile
from typing import List
import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)

class OCRPreprocessor:
    """Preprocesador robusto para OCR en documentos legales escaneados."""

    def __init__(self, target_dpi: int = 300, debug: bool = False):
        self.target_dpi = target_dpi
        self.debug = debug

    def preprocess_page(self, image: np.ndarray | Image.Image) -> np.ndarray:
        """Pipeline completo de mejora para una página."""
        if isinstance(image, Image.Image):
            img = np.array(image.convert("RGB"))
        else:
            img = image.copy()

        # 1. Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # 2. Deskew fuerte (crítico para resoluciones mal escaneadas)
        deskewed = self._deskew(gray)

        # 3. Denoise (eliminación de ruido JPEG y suciedad de escaneo)
        denoised = cv2.fastNlMeansDenoising(deskewed, None, h=12, searchWindowSize=21)

        # 4. Binarización adaptativa (superior para fondos irregulares o sombras)
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, blockSize=11, C=2
        )

        # 5. Mejora de contraste CLAHE + Sharpening (clave para números de artículos)
        enhanced = self._enhance_contrast_and_sharpen(binary)

        # 6. Upscale inteligente si la resolución original es pobre
        estimated_dpi = self._estimate_dpi(img)
        if estimated_dpi < 220:
            scale = 1.6 if estimated_dpi < 150 else 1.3
            logger.info(f"[OCR_PRE] Upscaling página (scale={scale}x) debido a bajo DPI ({estimated_dpi})")
            enhanced = cv2.resize(enhanced, None, fx=scale, fy=scale, 
                                interpolation=cv2.INTER_CUBIC)

        return enhanced

    def _deskew(self, gray: np.ndarray) -> np.ndarray:
        """Endereza la imagen detectando líneas dominantes."""
        edges = cv2.Canny(gray, 30, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80, 
                              minLineLength=80, maxLineGap=15)
        
        if lines is None or len(lines) == 0:
            return gray

        angles = []
        for [[x1, y1, x2, y2]] in lines:
            if x2 - x1 != 0:
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                angles.append(angle)

        if not angles:
            return gray

        median_angle = np.median(angles)
        if abs(median_angle) < 0.7:  # No rotar si la inclinación es mínima
            return gray

        # Rotación compensatoria
        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(gray, M, (w, h), 
                               flags=cv2.INTER_CUBIC, 
                               borderMode=cv2.BORDER_REPLICATE)
        return rotated

    def _enhance_contrast_and_sharpen(self, img: np.ndarray) -> np.ndarray:
        """Resalta los bordes de las letras y normaliza la iluminación."""
        # CLAHE: Ecualización de histograma adaptativa limitada por contraste
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(img)

        # Unsharp masking para resaltar trazos finos
        blurred = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=2.5)
        sharpened = cv2.addWeighted(enhanced, 1.8, blurred, -0.8, 0)

        return sharpened

    def _estimate_dpi(self, img: np.ndarray) -> int:
        """Estimación heurística de DPI basada en dimensiones."""
        height_inches = img.shape[0] / 72.0
        return int(img.shape[0] / height_inches) if height_inches > 0 else 72

    def process_pdf(self, pdf_path: Path, output_dir: Path | None = None) -> List[Path]:
        """Convierte PDF a set de imágenes PNG mejoradas para el motor de OCR."""
        doc = fitz.open(str(pdf_path))
        processed_paths: List[Path] = []
        out_dir = output_dir or Path(tempfile.gettempdir()) / "ocr_refinery"
        out_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"[OCR_PRE] Refinando '{pdf_path.name}' ({len(doc)} páginas)...")

        for i, page in enumerate(doc):
            # Renderizar página a imagen de alta resolución
            pix = page.get_pixmap(dpi=self.target_dpi)
            img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Aplicar pipeline de mejora
            processed = self.preprocess_page(img_pil)

            # Guardar imagen optimizada
            out_path = out_dir / f"{pdf_path.stem}_p{i:03d}_refined.png"
            Image.fromarray(processed).save(out_path, "PNG", dpi=(self.target_dpi, self.target_dpi))
            processed_paths.append(out_path)

        doc.close()
        return processed_paths

def get_preprocessor(target_dpi: int = 300) -> OCRPreprocessor:
    """Factory para obtener el preprocesador configurado."""
    return OCRPreprocessor(target_dpi=target_dpi)
