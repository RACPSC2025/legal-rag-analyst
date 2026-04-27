"""
Citation Verifier Service — Analista Legal v2
────────────────────────────────────────────────────────────
Verifica la fidelidad de las citas textuales contra los originales.
"""

import re
import logging
from typing import List, Tuple, Any
from src.schemas.legal_output import Citation

logger = logging.getLogger(__name__)

class CitationVerifier:
    """
    Servicio premium para garantizar que las citas extraídas por el LLM
    existan realmente en los documentos fuente.
    """
    
    @staticmethod
    def verify_citation(citation: Citation, source_text: str) -> Tuple[bool, float]:
        """
        Verifica la existencia de una cita en el texto fuente.
        """
        clean_citation = CitationVerifier._clean_text(citation.text)
        clean_source = CitationVerifier._clean_text(source_text)
        
        if clean_citation in clean_source:
            logger.info(f"[VERIFIER] ✅ Cita verificada: {citation.article_id}")
            return True, 1.0
        
        # Búsqueda parcial (si el 80% de las palabras coinciden)
        # TODO: Implementar Levenshtein o Fuzzy en fase avanzada
        logger.warning(f"[VERIFIER] ❌ Cita no encontrada exactamente: {citation.article_id}")
        return False, 0.0

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normaliza el texto para comparación."""
        text = text.lower()
        # Eliminar caracteres no alfanuméricos básicos para comparación robusta
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def verify_response_citations(self, citations: List[Citation], documents: List[Any]) -> List[Citation]:
        """Verifica todas las citas de una respuesta contra el contexto."""
        combined_context = " ".join([doc.page_content for doc in documents])
        
        for citation in citations:
            is_verified, _ = self.verify_citation(citation, combined_context)
            citation.verified = is_verified
            
        return citations
