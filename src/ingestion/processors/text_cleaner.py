"""
Text Cleaner — Refinería de Texto Legal Multimodal
──────────────────────────────────────────────────
Versión Upgrade (Senior Logic):
Implementa limpieza especializada por perfiles (Legal Colombia, Contratos, OCR).
Normaliza unidades técnicas (m³, L/s) y preserva la jerarquía para el chunker.
"""

import re
import logging
from typing import Dict, Callable, Optional
from unidecode import unidecode

logger = logging.getLogger(__name__)

class LegalTextCleaner:
    """
    Gestor de perfiles de limpieza de alto rendimiento.
    Cada perfil aplica reglas específicas según la naturaleza del documento.
    """

    def __init__(self, remove_accents: bool = False):
        self.remove_accents = remove_accents
        self.profiles: Dict[str, Callable[[str], str]] = {
            "general": self._clean_general,
            "legal_colombia": self._clean_legal_colombia,
            "contract": self._clean_contract,
            "ocr_output": self._clean_ocr_output,
        }

    def clean(self, text: str, profile: str = "legal_colombia") -> str:
        """
        Aplica el pipeline de limpieza según el perfil solicitado.
        """
        if not text:
            return ""

        cleaner_func = self.profiles.get(profile, self.profiles["legal_colombia"])
        cleaned = cleaner_func(text)

        # Opcional: Remover acentos para búsqueda insensible profunda
        if self.remove_accents:
            cleaned = unidecode(cleaned)

        logger.debug(f"[CLEANER] Perfil '{profile}': {len(text)} -> {len(cleaned)} chars")
        return cleaned.strip()

    def _clean_general(self, text: str) -> str:
        """Limpieza básica universal de espacios y normalización."""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _clean_ocr_output(self, text: str) -> str:
        """Limpieza agresiva de artefactos típicos de motores de OCR."""
        # Correcciones de confusión de caracteres (l/I/1, O/0)
        text = re.sub(r'\b[lI1]\b', '1', text)
        text = re.sub(r'\b[Oo]\b', '0', text)
        # Normalizar separador decimal (coma por punto para cálculos técnicos)
        text = re.sub(r'(\d+)\s*,\s*(\d+)', r'\1.\2', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _clean_legal_colombia(self, text: str) -> str:
        """
        Perfil Maestro para Resoluciones Administrativas (SDA, CAR, ANLA).
        Prepara el texto para que el Adaptive Chunker detecte perfectamente las secciones.
        """
        # Paso previo: Limpieza de OCR
        text = self._clean_ocr_output(text)

        # 1. Normalizar encabezados de Resoluciones
        text = re.sub(r'Resolución\s+No\.\s*0*', 'Resolución No. ', text, flags=re.IGNORECASE)
        text = re.sub(r'POR LA CUAL', 'POR LA CUAL', text)

        # 2. Inyectar Jerarquía Markdown para el Chunker (Normalización de Secciones)
        section_map = {
            r'ANTECEDENTES': '## ANTECEDENTES',
            r'CONSIDERANDO': '## CONSIDERANDO',
            r'CONSIDERACIONES TÉCNICAS': '## CONSIDERACIONES TÉCNICAS',
            r'ANÁLISIS AMBIENTAL': '## ANÁLISIS AMBIENTAL',
            r'RESUELVE': '## RESUELVE',
            r'ARTÍCULO': '### ARTÍCULO',
        }
        for pattern, replacement in section_map.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # 3. Eliminación de Ruido Específico (Filtro de Impurezas)
        noise_patterns = [
            r"Departamento Administrativo de la Función Pública",
            r"Decreto 1072 de 2015.*EVA.*Gestor Normativo",
            r"Diario Oficial No\.\s*\d+",
            r"_{4,}|-{4,}",
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # 4. Normalizar Unidades Técnicas (Vital para extracción de volúmenes)
        text = re.sub(r'(\d+)\.?(\d*)\s*m³', r'\1.\2 m³', text)
        text = re.sub(r'(\d+)\.?(\d*)\s*L/s', r'\1.\2 L/s', text)

        # 5. Normalización de saltos de línea (Preservar estructura Markdown)
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        text = re.sub(r' +', ' ', text)

        return text.strip()

    def _clean_contract(self, text: str) -> str:
        """Perfil especializado para contratos y cláusulas civiles."""
        text = self._clean_legal_colombia(text)
        text = re.sub(r'CLÁUSULA', '### CLÁUSULA', text, flags=re.IGNORECASE)
        text = re.sub(r'LAS PARTES', '### LAS PARTES', text, flags=re.IGNORECASE)
        return text

# Factory singleton
_text_cleaner = LegalTextCleaner()

def get_text_cleaner(remove_accents: bool = False) -> LegalTextCleaner:
    return _text_cleaner
