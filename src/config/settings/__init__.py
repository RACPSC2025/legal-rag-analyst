"""
Settings Loader — Carga Configuración según ENVIRONMENT
───────────────────────────────────────────────────────
Punto de entrada para obtener la configuración apropiada.

Uso:
    from src.config.settings import get_settings, settings
    
    config = get_settings()
    print(config.API_HOST)

Autor: Fenix Tech Líder
Fecha: 2026-04-28
"""

import os
from functools import lru_cache
from typing import Union

from .base import BaseConfig
from .development import DevelopmentConfig
from .production import ProductionConfig


@lru_cache()
def get_settings() -> Union[DevelopmentConfig, ProductionConfig, BaseConfig]:
    """
    Retorna la configuración apropiada según ENVIRONMENT.
    
    La función está decorada con @lru_cache() para que la configuración
    se cargue solo una vez y se reutilice en toda la aplicación.
    
    Returns:
        DevelopmentConfig: Si ENVIRONMENT=development
        ProductionConfig: Si ENVIRONMENT=production
        BaseConfig: Si ENVIRONMENT no está definido (fallback a development)
    
    Ejemplos:
        >>> config = get_settings()
        >>> print(config.ENVIRONMENT)
        'development'
        
        >>> print(config.API_HOST)
        '127.0.0.1'
    """
    environment = os.getenv("ENVIRONMENT", "development").lower().strip()
    
    if environment == "production":
        return ProductionConfig()
    elif environment == "development":
        return DevelopmentConfig()
    else:
        # Default a development para seguridad
        # (mejor tener debug habilitado que deshabilitado por error)
        return DevelopmentConfig()


# ── Instancia Global de Settings ─────────────────────────────────────────────
# Esta instancia se carga una vez y se reutiliza en toda la aplicación
settings = get_settings()


# ── Exportar para Uso Externo ───────────────────────────────────────────────
__all__ = [
    "get_settings",
    "settings",
    "BaseConfig",
    "DevelopmentConfig",
    "ProductionConfig",
]
