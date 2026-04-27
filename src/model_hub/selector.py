"""
Model Selector — Enrutamiento dinámico de modelos por tarea
────────────────────────────────────────────────────────────
Selecciona el modelo óptimo para cada nodo del grafo RAG:
  • light  → grade_documents, check_hallucination, summarize (velocidad)
  • heavy  → generate, analyze (máxima calidad)

v2 fixes:
  • get_model_selector() añadido (requerido por __init__.py).
  • PREFERRED_PROVIDER definido aquí, no en settings (es decisión del hub).
  • get_llm_for_task() devuelve instancia ChatBedrock lista para usar.
  • Funciona sin cambiar get_llm() en config/__init__.py (backward compat).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from src.config import settings
from src.config.logging import get_logger
from .registry import load_catalog, _classify_model

log = get_logger(__name__)

# ── Proveedor preferido (Amazon Nova por defecto, cambiable) ──────────────────
# El selector busca primero modelos de este proveedor antes de hacer fallback.
PREFERRED_PROVIDER: str = "amazon"

# ── Mapeo tarea → perfil de costo ─────────────────────────────────────────────
TASK_MAP: Dict[str, str] = {
    # Nodos ligeros — velocidad y bajo costo
    "grade": "light",  # grade_documents()
    "verify": "light",  # check_hallucination()
    "summarize": "light",  # build_summary_index() en hierarchical_retriever
    "compress": "light",  # contextual_compression (sentence-level)
    "rewrite": "light",  # conversation_memory.rewrite_if_followup()
    # Nodos pesados — máxima calidad
    "generate": "heavy",  # generate() — respuesta legal final
    "analyze": "heavy",  # specialized_analysis
    "hyde": "heavy",  # HyDE document generation en query_expansion
}


class ModelSelector:
    """
    Selector de modelos basado en el catálogo dinámico del registry.

    Prioridades de selección:
    1. Proveedor preferido + perfil correcto + mayor contexto.
    2. Cualquier proveedor + perfil correcto + mayor contexto.
    3. Fallback a settings.AWS_MODEL_SIMPLE_TEXT (light) o AWS_MODEL_DEEP_ANALYSIS (heavy).
    """

    def __init__(self):
        catalog = load_catalog()
        self.models: List[Dict] = catalog.get("models", [])
        self._llm_cache: Dict[str, Any] = {}  # Cache de instancias ChatBedrock
        self._boto3_client = None             # Singleton client
        log.info(f"[SELECTOR] 🧠 Inicializado con {len(self.models)} modelos.")

    def _get_boto3_client(self):
        """Retorna el cliente de Bedrock Runtime (Singleton)."""
        if self._boto3_client is None:
            import boto3
            session = boto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                aws_session_token=settings.AWS_SESSION_TOKEN or None,
                region_name=settings.AWS_REGION,
            )
            self._boto3_client = session.client("bedrock-runtime")
        return self._boto3_client

    def select_model_id(self, task: str = "generate") -> str:
        """
        Retorna el model_id óptimo para la tarea indicada.

        Args:
            task: Nombre de la tarea (ver TASK_MAP).

        Returns:
            model_id string (ARN o ID corto) listo para ChatBedrock.
        """
        target_profile = TASK_MAP.get(task.lower(), "heavy")
        log.info(f"[SELECTOR] Tarea='{task}' → perfil='{target_profile}'")

        # 0. Prioridad absoluta: Si settings tiene un ARN de perfil de inferencia, usarlo.
        if target_profile == "light" and "inference-profile" in settings.AWS_MODEL_SIMPLE_TEXT:
            log.info(f"[SELECTOR] 🎯 Usando Perfil de Inferencia (Light): {settings.AWS_MODEL_SIMPLE_TEXT}")
            return settings.AWS_MODEL_SIMPLE_TEXT
        
        if target_profile == "heavy" and "inference-profile" in settings.AWS_MODEL_DEEP_ANALYSIS:
            log.info(f"[SELECTOR] 🎯 Usando Perfil de Inferencia (Heavy): {settings.AWS_MODEL_DEEP_ANALYSIS}")
            return settings.AWS_MODEL_DEEP_ANALYSIS

        # Modelos que sabemos que dan problemas 'on-demand'
        BLACKLIST = ["amazon.nova-pro-v1:0"]

        # 1. Proveedor preferido + perfil exacto
        candidates = [
            m
            for m in self.models
            if m.get("cost_profile") == target_profile
            and m.get("provider", "").lower() == PREFERRED_PROVIDER.lower()
            and m.get("model_id") not in BLACKLIST
        ]

        # 2. Fallback: cualquier proveedor con el perfil correcto
        if not candidates:
            log.warning(
                f"[SELECTOR] No hay modelos '{target_profile}' de '{PREFERRED_PROVIDER}'. "
                "Buscando en todos los proveedores..."
            )
            candidates = [
                m for m in self.models 
                if m.get("cost_profile") == target_profile
                and m.get("model_id") not in BLACKLIST
            ]

        # 3. Fallback final: usar defaults de settings
        if not candidates:
            fallback = (
                settings.AWS_MODEL_SIMPLE_TEXT
                if target_profile == "light"
                else settings.AWS_MODEL_DEEP_ANALYSIS
            )
            log.error(
                f"[SELECTOR] ❌ Sin candidatos para '{target_profile}'. "
                f"Usando fallback de settings: {fallback}"
            )
            return fallback

        # Ordenar por context_length descendente (mayor contexto = más capaz)
        candidates.sort(key=lambda m: m.get("context_length", 0), reverse=True)
        selected = candidates[0]["model_id"]
        log.info(f"[SELECTOR] ✅ '{task}' → {selected}")
        return selected

    def get_llm_for_task(self, task: str = "generate"):
        """
        Retorna una instancia ChatBedrock configurada para la tarea.
        Implementa caching de instancias para evitar re-instanciación costosa.

        Args:
            task: Nombre de la tarea.

        Returns:
            ChatBedrock instance lista para invocar.
        """
        model_id = self.select_model_id(task)
        
        # ── Intento recuperar del caché ──────────────────────────────────────
        if model_id in self._llm_cache:
            log.debug(f"[SELECTOR] Recuperando {model_id} desde caché de modelos.")
            return self._llm_cache[model_id]

        # ── Instanciación (solo si no está en caché) ────────────────────────
        from langchain_aws import ChatBedrock

        provider = _infer_provider(model_id)
        temperature = 0.0
        client = self._get_boto3_client()

        llm = ChatBedrock(
            client=client,
            model_id=model_id,
            provider=provider,
            temperature=temperature,
            region_name=settings.AWS_REGION,
            max_tokens=settings.MAX_TOKENS,
        )

        # Guardar en caché antes de retornar
        self._llm_cache[model_id] = llm
        log.info(f"[SELECTOR] ✅ {model_id} instanciado y cacheado.")
        return llm


def _infer_provider(model_id: str) -> str:
    """Infiere el parámetro 'provider' de ChatBedrock desde el model_id."""
    mid = model_id.lower()
    if "anthropic" in mid or "claude" in mid:
        return "anthropic"
    if "meta" in mid or "llama" in mid:
        return "meta"
    if "mistral" in mid:
        return "mistral"
    if "cohere" in mid:
        return "cohere"
    # Amazon Nova y Titan → "amazon"
    return "amazon"


# ── Singleton ──────────────────────────────────────────────────────────────────

_selector_instance: Optional[ModelSelector] = None


def get_model_selector() -> ModelSelector:
    """
    Retorna la instancia singleton del ModelSelector.
    Requerido por __init__.py y por cualquier módulo que quiera routing.
    """
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = ModelSelector()
    return _selector_instance


def get_recommended_model(task: str = "generate") -> str:
    """Shortcut funcional — retorna el model_id recomendado para la tarea."""
    return get_model_selector().select_model_id(task)


def get_llm_for_task(task: str = "generate"):
    """
    Shortcut funcional — retorna ChatBedrock listo para la tarea.

    Uso en nodes.py:
        from src.model_hub.selector import get_llm_for_task
        llm = get_llm_for_task("grade")      # Nova Lite (rápido)
        llm = get_llm_for_task("generate")   # Llama 70B (calidad)
    """
    return get_model_selector().get_llm_for_task(task)
