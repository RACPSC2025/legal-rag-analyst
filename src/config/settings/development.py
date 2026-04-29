"""
Configuración de Desarrollo
───────────────────────────
Optimizada para desarrollo local con debugging habilitado.

Autor: Fenix Tech Líder
Fecha: 2026-04-28
"""

import os
from .base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """
    Configuración para ambiente de desarrollo.
    
    Características:
    - Debug habilitado
    - Logging verbose
    - Cache deshabilitado (para ver cambios inmediatos)
    - Rate limiting permisivo
    - CORS permisivo
    """
    
    # ── Environment ──────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # ── API Configuration ────────────────────────────────────────────────────
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "1"))
    API_RELOAD: bool = True  # Hot reload en desarrollo
    
    # ── CORS (Permisivo en Desarrollo) ───────────────────────────────────────
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8501"
    ).split(",")
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # ── Logging (Verbose en Desarrollo) ──────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "text")  # Más legible en consola
    LOG_TO_FILE: bool = True
    
    # ── Cache (Deshabilitado en Desarrollo) ──────────────────────────────────
    # Deshabilitado por defecto para ver cambios inmediatos
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "false").lower() == "true"
    CACHE_TTL_DAYS: int = int(os.getenv("CACHE_TTL_DAYS", "1"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "50"))
    
    # ── Rate Limiting (Permisivo en Desarrollo) ──────────────────────────────
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "1000"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # Override de rate limiting para desarrollo (más permisivo)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100"))
    RATE_LIMIT_BURST_LIMIT: int = int(os.getenv("RATE_LIMIT_BURST_LIMIT", "20"))
    
    # ── Ingestion (Batch Pequeño para Testing Rápido) ────────────────────────
    INGESTION_BATCH_SIZE: int = int(os.getenv("INGESTION_BATCH_SIZE", "5"))
    
    # ── Secrets (Desde .env en Desarrollo) ───────────────────────────────────
    # En desarrollo, las credenciales se cargan desde .env local
    # No se usa AWS Secrets Manager
