"""
API Routes Package
──────────────────
Exporta todos los routers de la API.

Autor: Fenix Tech Líder
Fecha: 2026-04-27
"""

from . import query, ingestion, health, cache

__all__ = ["query", "ingestion", "health", "cache"]
