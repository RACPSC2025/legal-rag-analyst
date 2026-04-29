"""
Configuración Base — Común a Todos los Ambientes
────────────────────────────────────────────────
Valores por defecto y configuración compartida.

Autor: Fenix Tech Líder
Fecha: 2026-04-28
"""

import os
from pathlib import Path
from typing import Optional

# ── Raíz del Proyecto ────────────────────────────────────────────────────────
# __file__ está en src/config/settings/base.py
# parents[0] = src/config/settings
# parents[1] = src/config
# parents[2] = src
# parents[3] = raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parents[3]


class BaseConfig:
    """
    Configuración base común a todos los ambientes.
    
    Esta clase contiene la configuración que es compartida entre
    desarrollo, producción y testing.
    """
    
    # ── Metadata del Proyecto ────────────────────────────────────────────────
    PROJECT_NAME: str = "RAG Legal Colombiano"
    VERSION: str = "2.5.0"
    DESCRIPTION: str = "Sistema RAG especializado en normativa legal colombiana"
    
    # ── AWS Bedrock ──────────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "").strip("\"'")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip("\"'")
    AWS_SESSION_TOKEN: Optional[str] = os.getenv("AWS_SESSION_TOKEN", "").strip("\"'") or None
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-2").strip("\"'")
    
    # ── Modelos de AWS Bedrock ───────────────────────────────────────────────
    AWS_MODEL_SIMPLE_TEXT: str = os.getenv(
        "AWS_MODEL_SIMPLE_TEXT",
        "us.amazon.nova-lite-v1:0"
    ).strip("\"'")
    
    AWS_MODEL_DEEP_ANALYSIS: str = os.getenv(
        "AWS_MODEL_DEEP_ANALYSIS",
        "us.meta.llama3-3-70b-instruct-v1:0"
    ).strip("\"'")
    
    AWS_IMAGE_ANALYSIS: str = os.getenv(
        "AWS_IMAGE_ANALYSIS",
        "us.amazon.nova-pro-v1:0"
    ).strip("\"'")
    
    AWS_MODEL_LARGE_CONTEXT: str = os.getenv(
        "AWS_MODEL_LARGE_CONTEXT",
        "us.amazon.nova-2-lite-v1:0"
    ).strip("\"'")
    
    # ── Parámetros del LLM ───────────────────────────────────────────────────
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    
    # ── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "10"))
    RATE_LIMIT_BURST_LIMIT: int = int(os.getenv("RATE_LIMIT_BURST_LIMIT", "3"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    
    # ── Parámetros RAG ───────────────────────────────────────────────────────
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "300"))
    TOP_K_DOCS: int = int(os.getenv("TOP_K_DOCS", "6"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
    INGESTION_BATCH_SIZE: int = int(os.getenv("INGESTION_BATCH_SIZE", "5"))
    
    # ── Vector DB (ChromaDB) ─────────────────────────────────────────────────
    VECTOR_DB: str = os.getenv("VECTOR_DB", "chromadb").strip("\"'")
    VECTOR_DB_COLLECTION_NAME: str = os.getenv("VECTOR_DB_COLLECTION_NAME", "my_collection").strip("\"'")
    VECTOR_DB_DIMENSION: int = int(os.getenv("VECTOR_DB_DIMENSION", "1024"))
    
    # ── Rutas del Sistema ────────────────────────────────────────────────────
    ROOT_DIR: Path = ROOT_DIR
    DATA_INPUT_PATH: str = os.getenv("DATA_INPUT_PATH", str(ROOT_DIR / "data" / "input"))
    DATA_PROCESSED_PATH: str = os.getenv("DATA_PROCESSED_PATH", str(ROOT_DIR / "data" / "processed"))
    DATA_STORAGE_PATH: str = os.getenv("DATA_STORAGE_PATH", str(ROOT_DIR / "storage"))
    LOGS_PATH: str = os.getenv("LOGS_PATH", str(ROOT_DIR / "logs"))
    
    # Convertir a Path objects para facilitar uso
    STORAGE_PATH: str = DATA_STORAGE_PATH  # Alias para compatibilidad
    COLLECTION_NAME: str = VECTOR_DB_COLLECTION_NAME  # Alias para compatibilidad
    
    # ── Model Hub (Fase 0) ───────────────────────────────────────────────────
    PREFERRED_PROVIDER: str = os.getenv("PREFERRED_PROVIDER", "anthropic").lower().strip("\"'")
    MODEL_SELECTION_MODE: str = os.getenv("MODEL_SELECTION_MODE", "performance").lower().strip("\"'")
    ENABLE_DYNAMIC_MODEL_SELECTION: bool = os.getenv("ENABLE_DYNAMIC_MODEL_SELECTION", "true").lower() == "true"
    
    # ── LlamaParse (Opcional) ────────────────────────────────────────────────
    LLAMA_PARSE_API_KEY: str = os.getenv("LLAMA_PARSE_API_KEY", "").strip("\"'")
    
    # ── Aliases para Compatibilidad con Código Existente ─────────────────────
    # Estos aliases aseguran que el código existente siga funcionando
    RPM: int = RATE_LIMIT_REQUESTS_PER_MINUTE
    BURST: int = RATE_LIMIT_BURST_LIMIT
    TOP_K: int = TOP_K_DOCS
    BATCH_SIZE: int = INGESTION_BATCH_SIZE
    TEMPERATURE: float = LLM_TEMPERATURE
    MAX_TOKENS: int = LLM_MAX_TOKENS
    
    def __repr__(self) -> str:
        """Representación string de la configuración (sin secretos)."""
        return (
            f"<{self.__class__.__name__} "
            f"environment={getattr(self, 'ENVIRONMENT', 'base')} "
            f"region={self.AWS_REGION}>"
        )
