"""
LegalCache Orchestrator — Sistema de caché unificado (L1, L2, L3)
────────────────────────────────────────────────────────────
Orquesta las capas de caché, analíticas y persistencia.
"""

import logging
from typing import Optional, Any, Dict, Tuple
from .query_cache import QueryHasher
from .response_cache import ResponseCache
from .analytics import CacheAnalytics
from .semantic_cache import SemanticCache

log = logging.getLogger(__name__)

class LegalCache:
    """
    Punto de entrada único para el sistema de caché.
    Orquesta la lógica multinivel: L1 (Exact) -> L2 (Normalized) -> L3 (Semantic).
    """
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LegalCache, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.hasher = QueryHasher()
        self.storage = ResponseCache()
        self.analytics = CacheAnalytics()
        self.semantic = SemanticCache()
        
        log.info("✅ LegalCache Orchestrator inicializado con L1, L2 y L3.")

    def get(self, query: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Busca en todas las capas de caché.
        Retorna (respuesta, capa_del_hit) o (None, None).
        """
        # 1. Intentar L1: Exact Match
        exact_id = self.hasher.get_cache_id(query, mode="exact")
        response = self.storage.get(exact_id)
        if response:
            self.analytics.record_hit("L1_exact")
            return response, "L1_exact"

        # 2. Intentar L2: Normalized Match
        norm_id = self.hasher.get_cache_id(query, mode="normalized")
        # Si el ID exacto y normalizado son iguales, no repetimos búsqueda
        if norm_id != exact_id:
            response = self.storage.get(norm_id)
            if response:
                self.analytics.record_hit("L2_normalized")
                return response, "L2_normalized"

        # 3. Intentar L3: Semantic Cache (Búsqueda Vectorial)
        response = self.semantic.get(query)
        if response:
            self.analytics.record_hit("L3_semantic")
            return response, "L3_semantic"

        # Si llegamos aquí, es un MISS absoluto
        self.analytics.record_miss()
        return None, None

    def set(self, query: str, response: Dict[str, Any], ttl: Optional[int] = None):
        """
        Guarda la respuesta en las capas correspondientes.
        """
        exact_id = self.hasher.get_cache_id(query, mode="exact")
        norm_id = self.hasher.get_cache_id(query, mode="normalized")
        
        # Guardamos en ambas llaves para maximizar hits futuros
        self.storage.set(exact_id, response, ttl)
        if norm_id != exact_id:
            self.storage.set(norm_id, response, ttl)
        
        # También guardamos en la capa semántica (L3) para búsquedas por similitud
        self.semantic.set(query, response)
        
        log.debug(f"[LEGAL_CACHE] Respuesta cacheada en L1, L2 y L3 para: {query[:50]}...")

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene las métricas de uso."""
        return self.analytics.get_summary()

# Singleton para uso global
legal_cache = LegalCache()
