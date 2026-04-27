"""
Response Cache — Almacenamiento persistente de respuestas LLM
────────────────────────────────────────────────────────────
Gestiona la persistencia en disco, TTL y recuperación de respuestas.
"""

import os
import json
import time
import logging
from typing import Optional, Any, Dict
from pathlib import Path
from src.config import settings

log = logging.getLogger(__name__)

class ResponseCache:
    """
    Maneja el almacenamiento físico de las respuestas en disco.
    Implementa lógica de expiración por tiempo (TTL).
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or os.path.join(settings.STORAGE_PATH, "cache", "responses"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # TTL por defecto: 7 días (configurado en el plan)
        self.default_ttl = 3600 * 24 * 7 

    def _get_path(self, cache_id: str) -> Path:
        return self.cache_dir / f"{cache_id}.json"

    def get(self, cache_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera una respuesta del caché si existe y no ha expirado.
        """
        path = self._get_path(cache_id)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Verificar expiración
            timestamp = data.get("timestamp", 0)
            ttl = data.get("ttl", self.default_ttl)
            
            if time.time() - timestamp > ttl:
                log.info(f"[RESPONSE_CACHE] Cache ID {cache_id} expirado. Eliminando...")
                path.unlink() # Eliminar archivo expirado
                return None
            
            log.debug(f"[RESPONSE_CACHE] Hit para ID: {cache_id}")
            return data.get("response")
        
        except Exception as e:
            log.error(f"[RESPONSE_CACHE] Error al leer caché {cache_id}: {e}")
            return None

    def set(self, cache_id: str, response: Dict[str, Any], ttl: Optional[int] = None):
        """
        Guarda una respuesta en el caché con un timestamp.
        """
        path = self._get_path(cache_id)
        data = {
            "cache_id": cache_id,
            "timestamp": time.time(),
            "ttl": ttl or self.default_ttl,
            "response": response
        }
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log.debug(f"[RESPONSE_CACHE] Guardado ID: {cache_id}")
        except Exception as e:
            log.error(f"[RESPONSE_CACHE] Error al escribir caché {cache_id}: {e}")

    def clear(self):
        """Limpia todo el caché de respuestas."""
        for file in self.cache_dir.glob("*.json"):
            file.unlink()
        log.info("[RESPONSE_CACHE] Caché de respuestas vaciado.")
