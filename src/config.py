"""
Configuración centralizada - RAG Legal - Analista Juridico.
Lee valores del .env del proyecto raíz.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde la raíz del proyecto
_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env", override=True)


class Settings:
    """Configuración inmutable para el sistema RAG Legal."""

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

    # ── Rutas ───────────────────────────────────────────────────────
    ROOT_DIR: Path = _ROOT
    STORAGE_PATH: str = os.getenv("DATA_STORAGE_PATH", str(_ROOT / "storage"))
    DATA_INPUT_PATH: str = os.getenv("DATA_INPUT_PATH", str(_ROOT / "data" / "input"))

    DATA_PROCESSED_PATH: str = str(_ROOT / "data" / "processed")
    LOGS_PATH: str = str(_ROOT / "logs")

    # ── ChromaDB ────────────────────────────────────────────────────────────
    COLLECTION_NAME: str = os.getenv("VECTOR_DB_COLLECTION_NAME", "my_collection")

    # ── LlamaParse (para PDFs complejos) ──────────────────────────────────
    LLAMA_PARSE_API_KEY: str = os.getenv("LLAMA_PARSE_API_KEY", "")


settings = Settings()


def get_llm():
    """LLM Nova Lite vía AWS Bedrock — temperatura cero para dominio legal."""
    from langchain_aws import ChatBedrock
    import boto3

    session = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN if settings.AWS_SESSION_TOKEN else None,
        region_name=settings.AWS_REGION,
    )
    client = session.client("bedrock-runtime")

    return ChatBedrock(
        client=client,
        model_id=settings.AWS_MODEL_SIMPLE_TEXT,
        provider="amazon",  # Requerido cuando model_id es un ARN
        temperature=float(settings.TEMPERATURE),
        region_name=settings.AWS_REGION,
        max_tokens=settings.MAX_TOKENS,
    )


def get_embeddings():
    """Embeddings Amazon Titan v2 vía AWS Bedrock — 1024 dims, multilingüe."""
    from langchain_aws import BedrockEmbeddings
    import boto3

    session = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN if settings.AWS_SESSION_TOKEN else None,
        region_name=settings.AWS_REGION,
    )
    client = session.client("bedrock-runtime")

    return BedrockEmbeddings(
        client=client,
        model_id="amazon.titan-embed-text-v2:0",
        region_name=settings.AWS_REGION,
        normalize=True,  # Vectores unitarios — mejora cosine similarity
    )
