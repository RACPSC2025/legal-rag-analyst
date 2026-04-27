"""
Query Cache — L1 (Exact) y L2 (Normalized) Cache Key Generation
────────────────────────────────────────────────────────────
Gestiona la normalización de consultas y la generación de hashes SHA256.
"""

import hashlib
import re
import logging
from typing import Optional

log = logging.getLogger(__name__)

class QueryHasher:
    """
    Clase especializada en transformar consultas de lenguaje natural
    en llaves de caché persistentes y normalizadas.
    """

    @staticmethod
    def create_exact_key(query: str) -> str:
        """
        L1: Genera un hash SHA256 de la consulta exacta.
        Útil para capturar repeticiones literales (copy-paste).
        """
        return hashlib.sha256(query.encode("utf-8")).hexdigest()

    @staticmethod
    def create_normalized_key(query: str) -> str:
        """
        L2: Normaliza la consulta antes de generar el hash.
        - Convierte a minúsculas.
        - Elimina signos de puntuación y caracteres especiales.
        - Colapsa espacios en blanco redundantes.
        - Elimina tildes (opcional, pero recomendado para búsqueda en español).
        """
        # 1. Lowercase y strip
        q = query.lower().strip()
        
        # 2. Quitar signos de puntuación comunes en consultas legales
        # Mantenemos números de artículos (ej: 2.2.1) pero quitamos puntuación de frase
        q = re.sub(r'[¿?¡!.,:;()\[\]\'\"«»—–]', ' ', q)
        
        # 3. Quitar acentos (normalización para español)
        import unicodedata
        q = ''.join(
            c for c in unicodedata.normalize('NFD', q)
            if unicodedata.category(c) != 'Mn'
        )
        
        # 4. Colapsar espacios
        q = re.sub(r'\s+', ' ', q).strip()
        
        return hashlib.sha256(q.encode("utf-8")).hexdigest()

    @classmethod
    def get_cache_id(cls, query: str, mode: str = "normalized") -> str:
        """Punto de entrada unificado para obtener el ID de caché."""
        if mode == "exact":
            return cls.create_exact_key(query)
        return cls.create_normalized_key(query)
