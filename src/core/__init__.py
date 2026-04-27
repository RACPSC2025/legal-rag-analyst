"""
Módulo core — exporta los componentes principales del grafo RAG Legal.

Permite importar desde src.core directamente (requerido por app.py):
    from src.core import get_graph, RagState, query
    from src.core import retrieve, grade_documents, generate, check_hallucination, no_answer
"""

from src.core.graph import build_graph, get_graph, query
from src.core.state import RagState
from src.core.nodes import (
    retrieve,
    grade_documents,
    generate,
    check_hallucination,
    no_answer,
)

__all__ = [
    # Graph
    "build_graph",
    "get_graph",
    "query",
    # State
    "RagState",
    # Nodes
    "retrieve",
    "grade_documents",
    "generate",
    "check_hallucination",
    "no_answer",
]

