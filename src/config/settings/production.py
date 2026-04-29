"""
Configuración de Producción
───────────────────────────
Optimizada para producción con seguridad y performance.

Autor: Fenix Tech Líder
Fecha: 2026-04-28
"""

import os
from .base import BaseConfig


class ProductionConfig(BaseConfig):
    """
    Configuración para ambiente de producción.
    
    Características:
    - Debug deshabilitado
    - Logging estructurado (JSON)
    - Cache habilitado
    - Rate limiting estricto
    - CORS restrictivo
    - Múltiples workers
    - Seguridad reforzada
    """
    
    # ── Environment ──────────────────────────────────────────────────────────
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # ── API Configuration ────────────────────────────────────────────────────
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "4"))  # Múltiples workers
    API_RELOAD: bool = False  # No hot reload en producción
    
    # ── CORS (Restrictivo en Producción) ─────────────────────────────────────
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "https://rag-legal.example.com"
    ).split(",")
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["GET", "POST", "PUT", "DELETE"]
    CORS_ALLOW_HEADERS: list = ["Content-Type", "Authorization"]
    
    # ── Logging (Estructurado en Producción) ─────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # JSON para CloudWatch/ELK
    LOG_TO_FILE: bool = True
    LOG_TO_CLOUDWATCH: bool = True
    
    # ── Cache (Habilitado en Producción) ─────────────────────────────────────
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL_DAYS: int = int(os.getenv("CACHE_TTL_DAYS", "7"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))
    
    # ── Rate Limiting (Estricto en Producción) ───────────────────────────────
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # Override de rate limiting para producción (más estricto)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100"))
    RATE_LIMIT_BURST_LIMIT: int = int(os.getenv("RATE_LIMIT_BURST_LIMIT", "20"))
    
    # ── Ingestion (Batch Grande para Eficiencia) ─────────────────────────────
    INGESTION_BATCH_SIZE: int = int(os.getenv("INGESTION_BATCH_SIZE", "40"))
    
    # ── Security ─────────────────────────────────────────────────────────────
    ENABLE_HTTPS_REDIRECT: bool = True
    ENABLE_HSTS: bool = True
    ENABLE_CSP: bool = True
    
    # ── Secrets (Desde AWS Secrets Manager en Producción) ────────────────────
    # En producción, considerar cargar secretos desde AWS Secrets Manager
    # en lugar de variables de entorno
    
    @classmethod
    def load_secrets_from_aws(cls) -> dict:
        """
        Carga secretos desde AWS Secrets Manager.
        
        Uso futuro para producción:
            secrets = ProductionConfig.load_secrets_from_aws()
            config.AWS_ACCESS_KEY_ID = secrets.get("AWS_ACCESS_KEY_ID")
        """
        try:
            import boto3
            import json
            
            client = boto3.client("secretsmanager", region_name=cls.AWS_REGION)
            response = client.get_secret_value(SecretId="rag-legal/prod")
            return json.loads(response["SecretString"])
        except Exception as e:
            # Fallback a variables de entorno
            print(f"Warning: No se pudieron cargar secretos de AWS: {e}")
            return {}
