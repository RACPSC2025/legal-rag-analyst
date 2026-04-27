"""
Model Hub — Sistema de registro y selección dinámica de modelos LLM.
──────────────────────────────────────────────────────────────────────
Proporciona:
  • Registro automático de modelos disponibles en AWS Bedrock.
  • Selección inteligente por tarea (light / heavy).
  • Caché de catálogo para evitar llamadas repetidas a la API.
  • Fallback estático cuando AWS no es accesible.

Uso rápido en cualquier módulo:
    from src.model_hub import get_llm_for_task, get_recommended_model

    llm_grade    = get_llm_for_task("grade")     # Nova Lite — rápido
    llm_generate = get_llm_for_task("generate")  # Llama 70B — calidad
"""

from .registry import (
    build_model_catalog,
    load_catalog,
    initialize_model_catalog,
)
from .selector import (
    ModelSelector,
    get_model_selector,
    get_recommended_model,
    get_llm_for_task,
    TASK_MAP,
    PREFERRED_PROVIDER,
)

__all__ = [
    # Registry
    "build_model_catalog",
    "load_catalog",
    "initialize_model_catalog",
    # Selector
    "ModelSelector",
    "get_model_selector",
    "get_recommended_model",
    "get_llm_for_task",
    "TASK_MAP",
    "PREFERRED_PROVIDER",
]
