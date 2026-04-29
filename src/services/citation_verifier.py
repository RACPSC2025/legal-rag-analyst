"""
Citation Verifier Service — Analista Legal v2
────────────────────────────────────────────────────────────
Verifica la fidelidad de las citas textuales contra los originales.
"""

import re
import logging
from typing import List, Tuple, Any
from difflib import SequenceMatcher
from src.schemas.legal_output import Citation

logger = logging.getLogger(__name__)

class CitationVerifier:
    """
    Servicio premium para garantizar que las citas extraídas por el LLM
    existan realmente en los documentos fuente mediante comparación difusa.
    """
    
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def verify_citation(self, citation: Citation, source_text: str) -> Tuple[bool, float]:
        """
        Verifica la existencia de una cita en el texto fuente usando fuzzy matching.
        
        Retorna:
            (bool, float): (Es válida, Score de similitud)
        """
        if not citation.text or len(citation.text) < 10:
            return False, 0.0

        clean_citation = self._clean_text(citation.text)
        clean_source = self._clean_text(source_text)
        
        # 1. Intento de coincidencia exacta (rápido)
        if clean_citation in clean_source:
            logger.info(f"[VERIFIER] ✅ Coincidencia exacta: {citation.article_id}")
            return True, 1.0
        
        # 2. Intento de coincidencia difusa si la exacta falla
        # Buscamos en ventanas de texto similares en el source para optimizar
        # Para esta fase, usamos una aproximación de similitud global simplificada
        # En una fase avanzada, se buscaría el fragmento más similar (best match)
        similarity = SequenceMatcher(None, clean_citation, clean_source).ratio()
        
        if similarity >= self.threshold:
            logger.info(f"[VERIFIER] 🟡 Coincidencia difusa ({similarity:.2f}): {citation.article_id}")
            return True, similarity
            
        logger.warning(f"[VERIFIER] ❌ Cita no verificada (Score: {similarity:.2f}): {citation.article_id}")
        return False, similarity

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normaliza el texto para comparación eliminando ruido legal común."""
        text = text.lower()
        # Eliminar puntuación y espacios extra
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def verify_response_citations(self, citations: List[Citation], documents: List[Any]) -> List[Citation]:
        """Verifica todas las citas de una respuesta contra el contexto consolidado."""
        if not citations:
            return []
            
        combined_context = " ".join([doc.page_content for d in documents for doc in (d if isinstance(d, list) else [d])])
        
        for citation in citations:
            is_verified, score = self.verify_citation(citation, combined_context)
            citation.verified = is_verified
            # Podríamos guardar el score en metadatos si fuera necesario
            
        return citations
