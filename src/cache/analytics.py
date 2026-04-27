"""
Cache Analytics — Monitoreo de performance y ahorro de costos
────────────────────────────────────────────────────────────
Rastrea métricas de hit-rate y estima el ahorro económico.
"""

import logging
from typing import Dict, Any

log = logging.getLogger(__name__)

class CacheAnalytics:
    """
    Gestiona las estadísticas de uso del sistema de caché.
    """

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.hits_by_layer = {
            "L1_exact": 0,
            "L2_normalized": 0,
            "L3_semantic": 0
        }
        # Ahorro estimado en USD (promedio conservador por llamada Bedrock)
        self.estimated_savings_per_hit = 0.015 

    def record_hit(self, layer: str):
        """Registra un acierto en una capa específica."""
        self.hits += 1
        if layer in self.hits_by_layer:
            self.hits_by_layer[layer] += 1
        log.debug(f"[ANALYTICS] Cache Hit registrado en capa: {layer}")

    def record_miss(self):
        """Registra un fallo de caché."""
        self.misses += 1
        log.debug("[ANALYTICS] Cache Miss registrado.")

    def get_summary(self) -> Dict[str, Any]:
        """Retorna un resumen de métricas para el dashboard."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "total_hits": self.hits,
            "total_misses": self.misses,
            "hit_rate": f"{hit_rate:.1%}",
            "hits_by_layer": self.hits_by_layer,
            "estimated_savings_usd": round(self.hits * self.estimated_savings_per_hit, 4)
        }

    def reset(self):
        """Reinicia las estadísticas de la sesión."""
        self.hits = 0
        self.misses = 0
        for layer in self.hits_by_layer:
            self.hits_by_layer[layer] = 0
