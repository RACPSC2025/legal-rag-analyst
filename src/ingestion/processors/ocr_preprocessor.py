"""
OCR Preprocessor — Refinería de Imágenes
────────────────────────────────────────
Optimiza imágenes de documentos escaneados usando OpenCV.
"""

import logging
import cv2
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

class ImageEnhancer:
    """Aplica filtros de visión artificial para mejorar la legibilidad."""

    @staticmethod
    def process_image(image_path: Path, output_path: Path) -> bool:
        """
        Lee una imagen, aplica filtros y la guarda.
        Ideal para DPI bajo o texto borroso.
        """
        try:
            # Leer imagen en escala de grises
            img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                return False

            # 1. Binarización Adaptativa (Maneja iluminación desigual)
            binary = cv2.adaptiveThreshold(
                img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )

            # 2. Denoising (Eliminar ruido tipo sal y pimienta)
            denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)

            # 3. Deskew (Corrección de inclinación ligera)
            # (Lógica simplificada para esta versión)
            
            # Guardar resultado
            cv2.imwrite(str(output_path), denoised)
            logger.info(f"[IMAGE_PRE] Mejorada: {image_path.name}")
            return True

        except Exception as e:
            logger.error(f"[IMAGE_PRE] Fallo en {image_path.name}: {e}")
            return False

def get_preprocessor():
    return ImageEnhancer()
