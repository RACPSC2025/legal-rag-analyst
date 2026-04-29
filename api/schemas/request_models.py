"""
Request Models — Pydantic Schemas para Validación
────────────────────────────────────────────────
Modelos de entrada para validación automática de requests.

Principios:
  • Validación estricta con Pydantic v2
  • Documentación inline para OpenAPI
  • Valores por defecto sensatos
  • Constraints de negocio aplicados

Autor: Fenix Tech Líder
Fecha: 2026-04-27
"""

from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ── Query Requests ───────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """
    Request para consulta RAG.
    
    Example:
        ```json
        {
            "question": "¿Cuáles son los requisitos para concesión de aguas?",
            "top_k": 10,
            "use_cache": true,
            "stream": false
        }
        ```
    """
    
    question: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Pregunta legal en lenguaje natural",
        examples=["¿Cuáles son los requisitos para obtener una concesión de aguas?"]
    )
    
    top_k: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Número de documentos a recuperar (1-20)"
    )
    
    use_cache: bool = Field(
        default=True,
        description="Si True, intenta recuperar respuesta del caché"
    )
    
    stream: bool = Field(
        default=False,
        description="Si True, retorna respuesta en streaming (SSE)"
    )
    
    metadata_filter: Optional[dict] = Field(
        default=None,
        description="Filtros de metadata para ChromaDB (ej: {'document_type': 'decreto'})"
    )
    
    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Valida que la pregunta no esté vacía después de strip."""
        v = v.strip()
        if not v:
            raise ValueError("La pregunta no puede estar vacía")
        return v


class BatchQueryRequest(BaseModel):
    """
    Request para múltiples consultas en batch.
    
    Example:
        ```json
        {
            "questions": [
                "¿Qué es una licencia ambiental?",
                "¿Cuál es el plazo para resolver un recurso?"
            ],
            "top_k": 10
        }
        ```
    """
    
    questions: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Lista de preguntas (máximo 10)"
    )
    
    top_k: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Número de documentos a recuperar por pregunta"
    )
    
    use_cache: bool = Field(
        default=True,
        description="Si True, intenta recuperar respuestas del caché"
    )


# ── Ingestion Requests ───────────────────────────────────────────────────────

class IngestionRequest(BaseModel):
    """
    Request para ingesta de documentos.
    
    Example:
        ```json
        {
            "file_paths": [
                "data/input/decreto_1076.pdf",
                "data/input/ley_99.pdf"
            ],
            "force_reconvert": false,
            "collection_name": "legal_docs"
        }
        ```
    """
    
    file_paths: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Rutas a archivos PDF o Markdown (máximo 50)"
    )
    
    force_reconvert: bool = Field(
        default=False,
        description="Si True, fuerza reconversión de PDFs aunque exista Golden MD"
    )
    
    collection_name: Optional[str] = Field(
        default=None,
        description="Nombre de la colección ChromaDB (default: settings.COLLECTION_NAME)"
    )
    
    @field_validator("file_paths")
    @classmethod
    def validate_paths(cls, v: List[str]) -> List[str]:
        """Valida que las rutas no estén vacías."""
        if not v:
            raise ValueError("Debe proporcionar al menos un archivo")
        
        # Validar extensiones
        valid_extensions = {".pdf", ".md"}
        for path in v:
            ext = path.lower().split(".")[-1]
            if f".{ext}" not in valid_extensions:
                raise ValueError(f"Extensión no soportada: {ext}. Use .pdf o .md")
        
        return v


class IngestionStatusRequest(BaseModel):
    """
    Request para consultar estado de ingesta.
    
    Example:
        ```json
        {
            "job_id": "ing_20260427_143022"
        }
        ```
    """
    
    job_id: str = Field(
        ...,
        min_length=1,
        description="ID del job de ingesta"
    )


# ── Cache Requests ───────────────────────────────────────────────────────────

class CacheClearRequest(BaseModel):
    """
    Request para limpiar caché.
    
    Example:
        ```json
        {
            "layers": ["L1", "L2"],
            "confirm": true
        }
        ```
    """
    
    layers: Optional[List[str]] = Field(
        default=None,
        description="Capas a limpiar: ['L1', 'L2', 'L3']. Si None, limpia todas"
    )
    
    confirm: bool = Field(
        ...,
        description="Confirmación explícita requerida para limpiar caché"
    )
    
    @field_validator("layers")
    @classmethod
    def validate_layers(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Valida que las capas sean válidas."""
        if v is None:
            return v
        
        valid_layers = {"L1", "L2", "L3"}
        for layer in v:
            if layer not in valid_layers:
                raise ValueError(f"Capa inválida: {layer}. Use L1, L2 o L3")
        
        return v


# ── Feedback Requests ────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    """
    Request para enviar feedback sobre una respuesta.
    
    Example:
        ```json
        {
            "query_id": "q_20260427_143022",
            "rating": 5,
            "comment": "Respuesta muy precisa y bien citada",
            "is_correct": true
        }
        ```
    """
    
    query_id: str = Field(
        ...,
        description="ID de la consulta evaluada"
    )
    
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Calificación de 1 a 5 estrellas"
    )
    
    comment: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Comentario opcional del usuario"
    )
    
    is_correct: Optional[bool] = Field(
        default=None,
        description="Si la respuesta fue correcta (validación binaria)"
    )
