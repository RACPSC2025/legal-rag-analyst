"""
MetadataExtractor — Extracción inteligente y robusta de metadata para documentos legales colombianos.
"""

from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """
    Extrae metadata estructurada de documentos legales colombianos.
    """

    def __init__(self):
        # Patrones regex optimizados para resoluciones colombianas
        self.patterns = {
            "resolution_number": [
                r"Resolución\s+No\.?\s*(\d{3,6})",
                r"Resolución\s+Nro\.?\s*(\d{3,6})",
                r"RESOLUCIÓN\s+No\.\s*(\d+)",
            ],
            "entity": [
                r"Secretaría Distrital de Ambiente",
                r"Corporación Autónoma Regional de Cundinamarca",
                r"CAR.*Alto Magdalena",
                r"SDA",
                r"CAR",
            ],
            "date": [
                r"(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})",
                r"(\d{2}/\d{2}/\d{4})",
                r"(\d{4}-\d{2}-\d{2})",
            ],
            "nit": [
                r"NIT\s*[:=]?\s*(\d{6,12}[-\s]?\d?)",
                r"N\.?I\.?T\.?\s*(\d{6,12})",
            ],
            "concession_type": [
                r"concesión\s+de\s+aguas\s+(subterráneas|superficiales)",
                r"concesion\s+de\s+aguas",
                r"pozo\s+\d+",
            ],
            "location": [
                r"municipio de ([A-Za-zÁÉÍÓÚáéíóú\s]+)",
                r"localidad de ([A-Za-zÁÉÍÓÚáéíóú\s]+)",
                r"vereda\s+([A-Za-zÁÉÍÓÚáéíóú\s]+)",
            ],
        }

    def extract_from_text(self, text: str, source_path: str | Path) -> Dict[str, Any]:
        """Extrae metadata completa a partir del texto completo del documento."""
        metadata: Dict[str, Any] = {
            "source": Path(source_path).name,
            "path": str(source_path),
            "processed_at": datetime.now().isoformat(),
            "document_type": self._detect_document_type(text),
            "extraction_method": "metadata_extractor_v1",
        }

        # Extracciones principales
        metadata["resolution_number"] = self._extract_resolution_number(text)
        metadata["entity"] = self._extract_entity(text)
        metadata["issue_date"] = self._extract_date(text)
        metadata["nit"] = self._extract_nit(text)
        metadata["location"] = self._extract_location(text)
        metadata["concession_type"] = self._extract_concession_type(text)

        # Información derivada
        metadata["is_resolucion"] = metadata["document_type"] == "resolucion"
        metadata["has_resolution_number"] = bool(metadata["resolution_number"])

        logger.debug(f"[METADATA] Extracción completa para {Path(source_path).name}")
        return metadata

    def enrich_documents(self, documents: List[Document]) -> List[Document]:
        """Enriquecer una lista de Documents (chunks) con metadata común + específica."""
        if not documents:
            return []

        # Extraer metadata global del documento completo
        full_text = "\n\n".join([doc.page_content for doc in documents])
        base_metadata = self.extract_from_text(full_text, documents[0].metadata.get("path", ""))

        enriched = []
        for i, doc in enumerate(documents):
            chunk_metadata = {
                **base_metadata,
                **doc.metadata,
                "chunk_index": i,
                "section": self._detect_section(doc.page_content),
            }

            enriched.append(Document(
                page_content=doc.page_content,
                metadata=chunk_metadata
            ))

        logger.info(f"[METADATA] {len(enriched)} fragmentos enriquecidos para {base_metadata.get('source')}")
        return enriched

    def _extract_resolution_number(self, text: str) -> Optional[str]:
        for pattern in self.patterns["resolution_number"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_entity(self, text: str) -> Optional[str]:
        for pattern in self.patterns["entity"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        for pattern in self.patterns["date"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    def _extract_nit(self, text: str) -> Optional[str]:
        for pattern in self.patterns["nit"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).replace(" ", "").replace("-", "").strip()
        return None

    def _extract_location(self, text: str) -> Optional[str]:
        for pattern in self.patterns["location"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_concession_type(self, text: str) -> Optional[str]:
        for pattern in self.patterns["concession_type"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    def _detect_document_type(self, text: str) -> str:
        text_lower = text.lower()
        if "resolución no." in text_lower or "resuelve" in text_lower:
            return "resolucion"
        if "concesión de aguas" in text_lower or ("pozo" in text_lower and "m³" in text_lower):
            return "concesion_aguas"
        if "cláusula" in text_lower:
            return "contrato"
        return "legal_document"

    def _detect_section(self, text: str) -> str:
        text_upper = text.upper()
        if "RESUELVE" in text_upper:
            return "RESUELVE"
        if "CONSIDERANDO" in text_upper:
            return "CONSIDERANDO"
        if "ANTECEDENTES" in text_upper:
            return "ANTECEDENTES"
        if "ARTÍCULO" in text_upper:
            return "ARTICULO"
        if "TABLA" in text_upper[:400] or "|" in text[:300]:
            return "TABLA"
        return "GENERAL"

_metadata_extractor = MetadataExtractor()

def get_metadata_extractor() -> MetadataExtractor:
    return _metadata_extractor
