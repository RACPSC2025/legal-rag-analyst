"""
Citation Verifier Service — Fénix Legal v2.5
────────────────────────────────────────────────────────────
Servicio de auditoría de precisión jurídica que valida la existencia,
integridad y literalidad de las citaciones generadas por el modelo.
"""

import re
import logging
from typing import List, Tuple, Any, Dict, Optional
from difflib import SequenceMatcher
from unidecode import unidecode
from src.schemas.legal_output import LegalCitation

logger = logging.getLogger(__name__)

class CitationVerifier:
    """
    Motor de auditoría avanzada para el Analista Jurídico. 
    Cruza metadatos de artículos con el texto recuperado para detectar alucinaciones.
    """
    
    def __init__(self, threshold: float = 0.85):
        """
        Inicializa el verificador con un umbral de similitud ajustable.
        """
        self.threshold = threshold
        logger.info(f"[VERIFICADOR] Inicializado con umbral de fidelidad: {self.threshold:.0%}")

    def _normalize_text(self, text: str) -> str:
        """
        Normaliza el texto para una comparación robusta.
        """
        if not text:
            return ""
        text = unidecode(text)
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def fuzzy_match(self, query: str, context: str) -> Tuple[bool, float, str]:
        """
        Busca una coincidencia difusa de una cita dentro de un bloque de texto.
        """
        import time
        t0 = time.perf_counter()
        
        norm_query = self._normalize_text(query)
        norm_context = self._normalize_text(context)
        
        if not norm_query:
            return False, 0.0, "Cita vacía o inválida"

        # 1. Coincidencia exacta
        if norm_query in norm_context:
            dt = (time.perf_counter() - t0) * 1000
            logger.debug(f"[VERIFICADOR] Coincidencia exacta encontrada en {dt:.2f}ms")
            return True, 1.0, "Coincidencia exacta (100%)"

        # 2. Búsqueda de ventana más cercana (SequenceMatcher)
        matcher = SequenceMatcher(None, norm_query, norm_context, autojunk=False)
        similarity = matcher.ratio()
        
        dt = (time.perf_counter() - t0) * 1000
        
        if similarity >= self.threshold:
            logger.debug(f"[VERIFICADOR] Coincidencia difusa aceptada: {similarity:.2%} en {dt:.2f}ms")
            return True, similarity, f"Coincidencia difusa ({similarity:.2%})"
        
        logger.warning(f"[VERIFICADOR] Fidelidad insuficiente: {similarity:.2%} (Umbral: {self.threshold:.2%})")
        return False, similarity, f"Fidelidad insuficiente ({similarity:.2%})"

    def verify_legal_citation(self, citation: LegalCitation, retrieved_documents: List[Dict[str, Any]]) -> LegalCitation:
        """
        Verifica una cita legal cruzando el article_id con el contexto recuperado.
        
        Args:
            citation: El objeto LegalCitation generado por el LLM.
            retrieved_documents: Lista de diccionarios con content y metadata.
            
        Returns:
            LegalCitation: Objeto actualizado con is_verified y verification_note.
        """
        target_article = self._normalize_text(citation.article_id)
        best_match_score = 0.0
        best_match_note = "Artículo no encontrado en contexto recuperado"
        found_article = False
        
        logger.info(f"[VERIFICADOR] Auditando cita: {citation.article_id}")

        for doc in retrieved_documents:
            metadata = doc.get("metadata", {})
            doc_article = self._normalize_text(str(metadata.get("article", "")))
            
            # 1. ¿El ID del artículo coincide?
            if target_article and doc_article and (target_article in doc_article or doc_article in target_article):
                found_article = True
                # 2. Verificar el texto (quote)
                is_valid, score, note = self.fuzzy_match(citation.quote, doc.get("page_content", ""))
                
                if score > best_match_score:
                    best_match_score = score
                    best_match_note = note

        # Actualizar objeto de cita
        citation.is_verified = found_article and (best_match_score >= self.threshold)
        
        dt = (time.perf_counter() - t0) * 1000
        
        if not found_article:
            citation.verification_note = f"ERROR: El artículo {citation.article_id} no está presente en los fragmentos recuperados."
            logger.error(f"[VERIFICADOR] ❌ FALLO CRÍTICO: {citation.article_id} NO ENCONTRADO en el contexto ({dt:.2f}ms)")
        elif not citation.is_verified:
            citation.verification_note = f"ADVERTENCIA: Se encontró el artículo pero el texto citado no es fiel (Similitud: {best_match_score:.2%})."
            logger.warning(f"[VERIFICADOR] ⚠️ ALUCINACIÓN DETECTADA: {citation.article_id} con fidelidad baja ({best_match_score:.2%}) en {dt:.2f}ms")
        else:
            citation.verification_note = best_match_note
            logger.info(f"[VERIFICADOR] ✅ CITA VERIFICADA: {citation.article_id} ({best_match_score:.2%}) en {dt:.2f}ms")
            
        citation.relevance_score = best_match_score
        return citation

    def audit_response(self, llm_answer: str, citations: List[LegalCitation], context: List[Dict[str, Any]]) -> Tuple[List[LegalCitation], List[Any]]:
        """
        Audita una respuesta completa: Citas textuales + Integridad numérica.
        """
        import time
        t0 = time.perf_counter()
        
        logger.info("\n" + "─" * 40)
        logger.info(f"🔍 [AUDITORÍA] Iniciando validación de {len(citations)} citas...")
        
        # 1. Verificar Citas Textuales
        verified_list = []
        for cit in citations:
            verified_list.append(self.verify_legal_citation(cit, context))
        
        # 2. Verificar Integridad Numérica (Grader)
        # Nota: Se asume que self.numeric_grader ya está inicializado en __init__ o inyectado
        # Para este ejemplo, mantenemos la lógica pero aseguramos el logging
        from src.services.numeric_grader import NumericGrader
        grader = NumericGrader()
        numeric_discrepancies = grader.audit_numbers(llm_answer, context)
        
        dt = (time.perf_counter() - t0) * 1000
        total_verified = sum(1 for c in verified_list if c.is_verified)
        
        logger.info(f"📊 [AUDITORÍA] RESULTADO FINAL:")
        logger.info(f"   ➤ Citas OK: {total_verified}/{len(citations)}")
        logger.info(f"   ➤ Discrepancias Numéricas: {len(numeric_discrepancies)}")
        logger.info(f"   ➤ Tiempo de Auditoría: {dt:.2f}ms")
        logger.info("─" * 40 + "\n")
        
        return verified_list, numeric_discrepancies

