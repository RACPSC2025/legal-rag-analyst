"""
OCRPreprocessor — Pipeline avanzado de preprocesamiento para PDFs escaneados.
Optimizado para resoluciones administrativas colombianas.
"""

import cv2
import numpy as np
from pathlib import Path
from PIL import Image
import tempfile
from typing import List
import fitz
import logging

logger = logging.getLogger(__name__)

class OCRPreprocessor:
    """Preprocesador robusto para OCR en documentos legales escaneados."""

    def __init__(self, target_dpi: int = 300, debug: bool = False):
        self.target_dpi = target_dpi
        self.debug = debug

    def preprocess_page(self, image: np.ndarray | Image.Image) -> np.ndarray:
        """Pipeline completo para una página."""
        if isinstance(image, Image.Image):
            img = np.array(image.convert("RGB"))
        else:
            img = image.copy()

        # 1. Convertir a grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # 2. Deskew fuerte (corrección de inclinación)
        deskewed = self._deskew(gray)

        # 3. Denoise (eliminar ruido de sal y pimienta / granulosidad)
        denoised = cv2.fastNlMeansDenoising(deskewed, None, h=10, searchWindowSize=21)

        # 4. Binarización adaptativa (clave para fotocopias con fondos oscuros/grisáceos)
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, blockSize=11, C=2
        )

        # 5. Mejora de contraste + sharpening
        enhanced = self._enhance_contrast_and_sharpen(binary)

        # 6. Upscale si el DPI es bajo (interpolación para mejorar bordes de letras)
        if self._estimate_dpi(img) < 220:
            scale = 1.5 if self._estimate_dpi(img) < 150 else 1.2
            enhanced = cv2.resize(enhanced, None, fx=scale, fy=scale, 
                                interpolation=cv2.INTER_CUBIC)

        return enhanced

    def _deskew(self, gray: np.ndarray) -> np.ndarray:
        """Corrige la rotación del documento detectando líneas de texto."""
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, 
                               minLineLength=100, maxLineGap=10)
        
        if lines is None:
            return gray

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Filtrar ángulos locos, solo queremos pequeñas inclinaciones (típicas de escáner)
            if abs(angle) < 10:
                angles.append(angle)

        if not angles:
            return gray

        median_angle = np.median(angles)
        if abs(median_angle) < 0.5:
            return gray

        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, 
                               borderMode=cv2.BORDER_REPLICATE)
        return rotated

    def _enhance_contrast_and_sharpen(self, img: np.ndarray) -> np.ndarray:
        """Mejora la legibilidad del texto aumentando el contraste local."""
        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(img)

        # Sharpening suave (5-point kernel)
        kernel = np.array([
            [0, -1, 0], 
            [-1, 5, -1], 
            [0, -1, 0]
        ])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        return sharpened

    def _estimate_dpi(self, img: np.ndarray) -> int:
        """Estimación heurística de DPI para decidir si hacer upscale."""
        # Asumiendo tamaño carta (8.5 pulgadas de ancho)
        width_pixels = img.shape[1]
        return int(width_pixels / 8.5)

    def process_pdf(self, pdf_path: Path, output_dir: Path | None = None) -> List[Path]:
        """Convierte PDF a lista de imágenes preprocesadas listas para OCR."""
        doc = fitz.open(str(pdf_path))
        temp_paths = []
        
        # Usar directorio proporcionado o uno temporal por defecto
        save_dir = output_dir or (Path(tempfile.gettempdir()) / "rag_ocr")
        save_dir.mkdir(parents=True, exist_ok=True)

        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=self.target_dpi)
            img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Preprocesar
            processed_img = self.preprocess_page(img_pil)
            
            # Guardar (Solución robusta para acentos en Windows)
            import re
            safe_stem = re.sub(r'[^\w\s-]', '', pdf_path.stem).strip().replace(' ', '_')
            img_path = save_dir / f"{safe_stem}_page_{i:03d}.png"
            
            is_success, buffer = cv2.imencode(".png", processed_img)
            if is_success:
                buffer.tofile(str(img_path))
                temp_paths.append(img_path)
            else:
                logger.error(f"[OCR_PRE] No se pudo codificar la imagen de la pagina {i}")
            
        doc.close()
        return temp_paths

_ocr_preprocessor = OCRPreprocessor()

def get_ocr_preprocessor() -> OCRPreprocessor:
    return _ocr_preprocessor
