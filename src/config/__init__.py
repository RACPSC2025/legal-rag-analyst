"""
Configuración Centralizada — RAG Legal v2.5
──────────────────────────────────────────
Punto de entrada principal para configuración del sistema.

IMPORTANTE: Este archivo mantiene backward compatibility total.
El código existente que usa `from src.config import settings` seguirá funcionando.

Nueva estructura (recomendada):
    from src.config.settings import get_settings
    config = get_settings()

Estructura antigua (sigue funcionando):
    from src.config import settings
    print(settings.AWS_REGION)

Autor: Fenix Tech Líder
Fecha: 2026-04-28
Migrado a: Estructura multi-ambiente (Django-style)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Cargar Variables de Entorno ──────────────────────────────────────────────
# __file__ está en src/config/__init__.py
# parents[0] = src/config
# parents[1] = src
# parents[2] = raíz del proyecto
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env", override=True)


# ── Importar Nueva Estructura de Settings ────────────────────────────────────
from .settings import get_settings, settings as new_settings


# ── Clase Settings Antigua (DEPRECATED - Mantener para Backward Compatibility) ──
class Settings:
    """
    Configuración inmutable para el sistema RAG Legal.
    
    DEPRECATED: Esta clase se mantiene solo para backward compatibility.
    Usa `from src.config.settings import get_settings` en código nuevo.
    
    El código existente que usa esta clase seguirá funcionando sin cambios.
    """

    # ── Modelo de Lenguaje ──────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "").strip("\"'")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip("\"'")
    AWS_SESSION_TOKEN: str = os.getenv("AWS_SESSION_TOKEN", "").strip("\"'")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-2").strip("\"'")
    AWS_MODEL_SIMPLE_TEXT: str = os.getenv(
        "AWS_MODEL_SIMPLE_TEXT",
        "arn:aws:bedrock:us-east-2:762233737662:inference-profile/us.amazon.nova-lite-v1:0",
    )
    TEMPERATURE: float = os.getenv(
        "LLM_TEMPERATURE", "0.0"
    )  # Cero para dominio legal — NUNCA improvisar
    MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    # ── Embeddings ──────────────────────────────────────────────────────────
    AWS_MODEL_DEEP_ANALYSIS: str = os.getenv(
        "AWS_MODEL_DEEP_ANALYSIS",
        "arn:aws:bedrock:us-east-2:762233737662:inference-profile/us.meta.llama3-3-70b-instruct-v1:0",
    )
    AWS_MODEL_LARGE_CONTEXT: str = os.getenv(
        "AWS_MODEL_LARGE_CONTEXT",
        "arn:aws:bedrock:us-east-2:762233737662:inference-profile/us.amazon.nova-2-lite-v1:0",
    )  # Para PDF directo (256k tokens)

    # ── Rate Limiting (Free API Key) ────────────────────────────────────────
    RPM: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "10"))
    BURST: int = int(os.getenv("RATE_LIMIT_BURST_LIMIT", "3"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # ── Retrieval ───────────────────────────────────────────────────────────
    TOP_K: int = int(os.getenv("TOP_K_DOCS", "10"))

    # ── Chunking (para ingesta de nuevos PDFs) ──────────────────────────────
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "2500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "400"))
    BATCH_SIZE: int = int(os.getenv("INGESTION_BATCH_SIZE", "5"))

    # ── Rutas ───────────────────────────────────────────────────────────────
    ROOT_DIR: Path = _ROOT
    STORAGE_PATH: str = os.getenv("DATA_STORAGE_PATH", str(_ROOT / "storage"))
    DATA_INPUT_PATH: str = os.getenv("DATA_INPUT_PATH", str(_ROOT / "data" / "input"))

    DATA_PROCESSED_PATH: str = str(_ROOT / "data" / "processed")
    LOGS_PATH: str = str(_ROOT / "logs")

    # ── ChromaDB ────────────────────────────────────────────────────────────
    COLLECTION_NAME: str = os.getenv("VECTOR_DB_COLLECTION_NAME", "my_collection")

    # ── LlamaParse (para PDFs complejos) ────────────────────────────────────
    LLAMA_PARSE_API_KEY: str = os.getenv("LLAMA_PARSE_API_KEY", "")

    # ── Model Hub (Fase 0) ──────────────────────────────────────────────────
    PREFERRED_PROVIDER: str = os.getenv("PREFERRED_PROVIDER", "anthropic").lower().strip()
    MODEL_SELECTION_MODE: str = os.getenv("MODEL_SELECTION_MODE", "performance").lower().strip()
    ENABLE_DYNAMIC_MODEL_SELECTION: bool = os.getenv("ENABLE_DYNAMIC_MODEL_SELECTION", "true").lower() == "true"


# ── Instancia Global de Settings (Backward Compatibility) ────────────────────
# Esta instancia se mantiene para que el código existente siga funcionando
settings = Settings()


# ── Funciones de Utilidad ───────────────────────────────────────────────────

def get_llm(task: str = "generate"):
    """
    Retorna un LLM configurado dinámicamente según la tarea.
    Punto de entrada principal para obtener modelos Bedrock.
    
    Args:
        task: Tipo de tarea ("generate", "analyze", "extract", etc.)
    
    Returns:
        ChatBedrock: Instancia configurada del LLM
    """
    from langchain_aws import ChatBedrock
    import boto3
    from src.model_hub.selector import get_recommended_model

    # Usar la nueva configuración si está disponible, sino usar la antigua
    config = new_settings if new_settings else settings

    # Seleccionar modelo dinámicamente si está habilitado, si no, usar el default
    if config.ENABLE_DYNAMIC_MODEL_SELECTION:
        model_id = get_recommended_model(task)
    else:
        model_id = config.AWS_MODEL_SIMPLE_TEXT

    session = boto3.Session(
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        aws_session_token=config.AWS_SESSION_TOKEN if config.AWS_SESSION_TOKEN else None,
        region_name=config.AWS_REGION,
    )
    client = session.client("bedrock-runtime")

    # Intentar detectar el provider (fallback a amazon para ARNs)
    provider = "anthropic" if "anthropic" in model_id.lower() else "amazon"

    return ChatBedrock(
        client=client,
        model_id=model_id,
        provider=provider,
        temperature=float(config.TEMPERATURE if hasattr(config, 'TEMPERATURE') else config.LLM_TEMPERATURE),
        region_name=config.AWS_REGION,
        max_tokens=config.MAX_TOKENS if hasattr(config, 'MAX_TOKENS') else config.LLM_MAX_TOKENS,
    )


def get_dynamic_llm(task: str = "generate"):
    """Alias para get_llm con propósitos de legibilidad."""
    return get_llm(task=task)


def get_embeddings():
    """Embeddings Amazon Titan v2 vía AWS Bedrock — 1024 dims, multilingüe."""
    from langchain_aws import BedrockEmbeddings
    import boto3

    # Usar la nueva configuración si está disponible, sino usar la antigua
    config = new_settings if new_settings else settings

    session = boto3.Session(
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        aws_session_token=config.AWS_SESSION_TOKEN if config.AWS_SESSION_TOKEN else None,
        region_name=config.AWS_REGION,
    )
    client = session.client("bedrock-runtime")

    return BedrockEmbeddings(
        client=client,
        model_id="amazon.titan-embed-text-v2:0",
        region_name=config.AWS_REGION,
        normalize=True,  # Vectores unitarios — mejora cosine similarity
    )


# ── Exportar para Uso Externo ───────────────────────────────────────────────
__all__ = [
    "settings",           # Backward compatibility
    "get_settings",       # Nueva forma recomendada
    "get_llm",
    "get_dynamic_llm",
    "get_embeddings",
]
