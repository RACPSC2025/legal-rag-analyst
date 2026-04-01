"""
Estado tipado del grafo RAG Legal.
Cada nodo del StateGraph lee/escribe sobre este objeto.
"""

from __future__ import annotations
from typing import Annotated, List, Literal
from pydantic import BaseModel, Field
from langchain_core.documents import Document
import operator


class RagState(BaseModel):
    """
    Estado centralizado que fluye por todos los nodos del grafo.

    Diseño defensivo:
    - question: nunca mutable durante el flow
    - documents: se acumula con el operador +
    - generation: producción final del LLM
    - grade: veredicto del nodo evaluador
    - attempts: evitar loops infinitos
    """

    question: str = Field(default="", description="Pregunta del usuario")

    documents: List[Document] = Field(
        default_factory=list, description="Documentos recuperados de ChromaDB"
    )

    generation: str = Field(default="", description="Respuesta generada por el LLM")

    grade: Literal["útil", "no_útil", "alucinación", "pendiente"] = Field(
        default="pendiente", description="Veredicto del nodo grader"
    )

    hallucination_score: float = Field(
        default=0.0,
        description="Score de alucinación 0.0 (limpio) → 1.0 (máximo riesgo)",
    )

    attempts: int = Field(
        default=0, description="Intentos realizados — límite máximo 2"
    )

    source_docs: List[str] = Field(
        default_factory=list,
        description="Fragmentos textuales usados como evidencia para la respuesta",
    )

    class Config:
        arbitrary_types_allowed = True
