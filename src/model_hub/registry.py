"""
Bedrock Model Registry — Gestión Dinámica de Capacidades LLM
──────────────────────────────────────────────────────────────
Consulta y persiste el catálogo de modelos disponibles en AWS Bedrock
para enrutamiento inteligente por tarea (light vs heavy).

v2 fixes:
  • initialize_model_catalog() añadido (requerido por __init__.py).
  • Catálogo manual de fallback: funciona aunque AWS falle o no haya red.
  • PREFERRED_PROVIDER movido aquí como constante (no requiere settings).
  • Clasificación ampliada para modelos Amazon Nova y Meta Llama.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from src.config import settings
from src.config.logging import get_logger

log = get_logger(__name__)

# ── Persistencia ──────────────────────────────────────────────────────────────
CATALOG_DIR = Path(settings.ROOT_DIR) / "storage" / "model_catalog"
CATALOG_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_PATH = CATALOG_DIR / "available_models.json"

# ── Catálogo manual de fallback ───────────────────────────────────────────────
# Se usa cuando AWS no es accesible o el catálogo aún no se ha generado.
# Refleja los modelos configurados en settings.
_FALLBACK_CATALOG: Dict[str, Any] = {
    "last_updated": "static_fallback",
    "region": "us-east-2",
    "source": "fallback",
    "models": [
        {
            "model_id": "arn:aws:bedrock:us-east-2:762233737662:inference-profile/us.amazon.nova-lite-v1:0",
            "provider": "amazon",
            "context_length": 300000,
            "cost_profile": "light",
            "capabilities": ["TEXT"],
            "alias": "nova-lite",
        },
        {
            "model_id": "arn:aws:bedrock:us-east-2:762233737662:inference-profile/us.meta.llama3-3-70b-instruct-v1:0",
            "provider": "meta",
            "context_length": 128000,
            "cost_profile": "heavy",
            "capabilities": ["TEXT"],
            "alias": "llama3-3-70b",
        },
        {
            "model_id": "arn:aws:bedrock:us-east-2:762233737662:inference-profile/us.amazon.nova-2-lite-v1:0",
            "provider": "amazon",
            "context_length": 256000,
            "cost_profile": "heavy",
            "capabilities": ["TEXT"],
            "alias": "nova-2-lite",
        },
    ],
}


# ── API pública ────────────────────────────────────────────────────────────────


def build_model_catalog(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Consulta AWS Bedrock Control Plane y genera el catálogo de modelos.

    Args:
        force_refresh: Si True, ignora el caché local y consulta AWS de nuevo.

    Returns:
        Catálogo completo con lista de modelos clasificados.
    """
    if not force_refresh and CATALOG_PATH.exists():
        log.info(f"[REGISTRY] 📚 Cargando catálogo desde caché: {CATALOG_PATH}")
        return load_catalog()

    log.info("[REGISTRY] 📡 Sincronizando con AWS Bedrock...")

    try:
        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            aws_session_token=settings.AWS_SESSION_TOKEN or None,
            region_name=settings.AWS_REGION,
        )
        bedrock = session.client("bedrock")
        response = bedrock.list_foundation_models()
        summaries = response.get("modelSummaries", [])

        catalog: Dict[str, Any] = {
            "last_updated": datetime.now().isoformat(),
            "region": settings.AWS_REGION,
            "source": "aws_api",
            "models": [],
        }

        for model in summaries:
            if "TEXT" not in model.get("outputModalities", []):
                continue
            model_id = model.get("modelId", "")
            provider = model.get("providerName", "").lower()
            catalog["models"].append(
                {
                    "model_id": model_id,
                    "provider": provider,
                    "context_length": model.get("contextLength", 0),
                    "cost_profile": _classify_model(model_id),
                    "capabilities": model.get("inputModalities", []),
                }
            )

        CATALOG_PATH.write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log.info(f"[REGISTRY] ✅ Catálogo generado: {len(catalog['models'])} modelos.")
        return catalog

    except ClientError as e:
        log.error(f"[REGISTRY] ❌ Error AWS: {e}. Usando catálogo de fallback.")
        return _FALLBACK_CATALOG
    except Exception as e:
        log.error(f"[REGISTRY] ❌ Error inesperado: {e}. Usando catálogo de fallback.")
        return _FALLBACK_CATALOG


def load_catalog() -> Dict[str, Any]:
    """
    Carga el catálogo desde disco. Si no existe, intenta generarlo.
    Si AWS falla, retorna el catálogo de fallback estático.
    """
    if CATALOG_PATH.exists():
        try:
            data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
            if data.get("models"):
                return data
        except Exception as e:
            log.warning(f"[REGISTRY] Error leyendo catálogo: {e}")

    log.warning("[REGISTRY] Catálogo no disponible en disco. Usando fallback estático.")
    return _FALLBACK_CATALOG


def initialize_model_catalog(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Punto de entrada para inicialización al arrancar la app.
    Intenta construir el catálogo desde AWS; si falla, usa el fallback.
    Alias de build_model_catalog() con logging de arranque.

    Args:
        force_refresh: Forzar recarga desde AWS aunque exista caché.

    Returns:
        Catálogo de modelos disponible.
    """
    log.info("[REGISTRY] 🚀 Inicializando catálogo de modelos...")
    catalog = build_model_catalog(force_refresh=force_refresh)
    source = catalog.get("source", "unknown")
    n = len(catalog.get("models", []))
    log.info(f"[REGISTRY] ✅ Catálogo listo: {n} modelos | fuente={source}")
    return catalog


def get_models_by_profile(profile: str) -> List[Dict[str, Any]]:
    """Retorna todos los modelos con un cost_profile específico."""
    catalog = load_catalog()
    return [m for m in catalog.get("models", []) if m.get("cost_profile") == profile]


def _classify_model(model_id: str) -> str:
    """
    Clasifica un modelo en 'light', 'heavy' o 'standard' según su ID.

    Light  → Rápidos y económicos: Nova Lite, Haiku, Micro, 8B.
    Heavy  → Alta calidad: Nova Pro, Llama 70B+, Sonnet, Opus.
    Standard → Todo lo demás.
    """
    mid = model_id.lower()
    if any(
        x in mid for x in ["haiku", "lite", "micro", "8b", "nova-lite", "nova_lite"]
    ):
        return "light"
    if any(
        x in mid
        for x in [
            "opus",
            "pro",
            "premier",
            "70b",
            "405b",
            "sonnet",
            "nova-pro",
            "nova_pro",
        ]
    ):
        return "heavy"
    return "standard"
