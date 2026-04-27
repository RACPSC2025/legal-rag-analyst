"""
MetadataExtractor v2.0 — Extracción de Inteligencia Legal Colombiana
───────────────────────────────────────────────────────────────────
Módulo especializado en la identificación de entidades, resoluciones,
NITs y jurisdicción dentro de documentos jurídicos colombianos.

Incorpora patrones Pro de GrokAI y lógica de validación estructurada.
"""

from __future__ import annotations
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """
    Motor de extracción de metadata para el ecosistema legal colombiano.
    """

    def __init__(self):
        # Patrones regex optimizados y expandidos
        self.patterns = {
            "resolution_number": [
                r"(?:Resolución|Circular|Decreto|Ley|Acuerdo)\s+(?:No\.?|Nro\.?|Número)\s*(\d+[\d\-\s]*)",
                r"RESOLUCIÓN\s+(?:No\.|NRO\.)\s*(\d+)",
            ],
            "entity": [
                # Autoridades Ambientales
                r"Secretaría Distrital de Ambiente",
                r"Corporación Autónoma Regional [A-Za-zÁÉÍÓÚáéíóú\s]+",
                r"ANLA", r"SDA", r"CAR",
                # Ministerios y Entidades Nacionales
                r"Ministerio de [A-Za-zÁÉÍÓÚáéíóú\s]+",
                r"Departamento Administrativo de [A-Za-zÁÉÍÓÚáéíóú\s]+",
                r"Superintendencia de [A-Za-zÁÉÍÓÚáéíóú\s]+",
                r"DIAN", r"ICBF", r"SENA",
            ],
            "date": [
                r"(\d{1,2})\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})",
                r"(\d{2}/\d{2}/\d{4})",
                r"(\d{4}-\d{2}-\d{2})",
            ],
            "nit": [
                r"NIT\s*[:=]?\s*(\d{6,12}[-\s]?\d?)",
                r"N\.?I\.?T\.?\s*(\d{6,12})",
            ],
            "location": [
                r"(?:municipio|ciudad) de ([A-Za-zÁÉÍÓÚáéíóú\s]+)",
                r"localidad de ([A-Za-zÁÉÍÓÚáéíóú\s]+)",
                r"departamento de ([A-Za-zÁÉÍÓÚáéíóú\s]+)",
                r"vereda\s+([A-Za-zÁÉÍÓÚáéíóú\s]+)",
            ],
        }

    def extract_from_text(self, text: str, source_path: str | Path) -> Dict[str, Any]:
        """
        Analiza el texto para extraer metadata estructurada.
        """
        text_sample = text[:10000] # Analizar principalmente los primeros 10k chars (donde está el encabezado)
        
        metadata: Dict[str, Any] = {
            "source": Path(source_path).name,
            "processed_at": datetime.now().isoformat(),
            "document_type": self._detect_document_type(text_sample),
            "jurisdiction": self._detect_jurisdiction(text_sample),
            "extraction_method": "metadata_extractor_v2_pro",
        }

        # Ejecutar extracciones regex
        metadata["resolution_number"] = self._extract_field(text_sample, "resolution_number", group=1)
        metadata["entity"] = self._extract_field(text_sample, "entity")
        metadata["issue_date"] = self._extract_field(text_sample, "date")
        metadata["nit"] = self._extract_field(text_sample, "nit", group=1)
        metadata["location"] = self._extract_field(text_sample, "location", group=1)

        # Enriquecimiento adicional
        metadata["is_permanent_knowledge"] = self._is_permanent(metadata["document_type"])
        
        logger.debug(f"[METADATA v2] Extracción exitosa para: {metadata['source']}")
        return metadata

    def enrich_documents(self, documents: List[Document]) -> List[Document]:
        """Aplica la metadata global a cada fragmento del documento."""
        if not documents: return []

        full_text = "\n\n".join([doc.page_content[:2000] for doc in documents[:5]]) # Muestra para metadata
        path = documents[0].metadata.get("path", "unknown")
        global_meta = self.extract_from_text(full_text, path)

        for doc in documents:
            doc.metadata.update(global_meta)
            # Agregar sección específica del chunk
            doc.metadata["section"] = self._detect_chunk_section(doc.page_content)

        return documents

    # --- MÉTODOS PRIVADOS DE EXTRACCIÓN ---

    def _extract_field(self, text: str, field: str, group: int = 0) -> Optional[str]:
        for pattern in self.patterns.get(field, []):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(group).strip()
                return val if val else None
        return None

    def _detect_document_type(self, text: str) -> str:
        text_lower = text.lower()
        if "resolución no." in text_lower or "resuelve" in text_lower: return "resolucion"
        if "decreto único reglamentario" in text_lower or "dur" in text_lower: return "decreto_dur"
        if "decreto no." in text_lower or "decreto número" in text_lower: return "decreto"
        if "ley" in text_lower and re.search(r"ley\s+\d+", text_lower): return "ley"
        if "circular" in text_lower: return "circular"
        if "concepto" in text_lower: return "concepto_juridico"
        return "otros_legales"

    def _detect_jurisdiction(self, text: str) -> str:
        text_lower = text.lower()
        if "república de colombia" in text_lower or "nacional" in text_lower: return "nacional"
        if "alcaldía" in text_lower or "municipio" in text_lower: return "municipal"
        if "gobernación" in text_lower or "departamento de" in text_lower: return "departamental"
        return "no_especificada"

    def _is_permanent(self, doc_type: str) -> bool:
        """Determina si el documento debe ser parte del RAG permanente."""
        return doc_type in ["ley", "decreto", "decreto_dur", "circular"]

    def _detect_chunk_section(self, text: str) -> str:
        """Identifica la sección a nivel de fragmento."""
        upper = text.upper()
        if "RESUELVE" in upper: return "PARTE_RESOLUTIVA"
        if "CONSIDERANDO" in upper: return "CONSIDERACIONES"
        if "ARTÍCULO" in upper: return "ARTICULADO"
        if "PARÁGRAFO" in upper: return "PARAGRAFO"
        if "|" in text and "-|-" in text: return "TABLA_DATOS"
        return "CUERPO_TEXTO"

# Factory / Singleton
_instance = MetadataExtractor()
def get_metadata_extractor() -> MetadataExtractor:
    return _instance

