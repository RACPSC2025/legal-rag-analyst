"""
Response Models — Pydantic Schemas para Respuestas
────────────────────────────────────────────────────
Modelos de salida estandarizados para la API.

Principios:
  • Respuestas consistentes y predecibles
  • Metadata enriquecida para debugging
  • Timestamps para trazabilidad
  • Status codes semánticos

Autor: Fenix Tech Líder
Fecha: 2026-04-27
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ── Query Responses ──────────────────────────────────────────────────────────

class RequirementResponse(BaseModel):
    """Representa un requisito o plazo legal identificado."""
    description: str = Field(..., description="Descripción de la obligación")
    deadline: Optional[str] = Field(None, description="Plazo legal asociado")
    responsible: Optional[str] = Field(None, description="Sujeto responsable")


class CitationResponse(BaseModel):
    """Cita verificada en la respuesta."""
    
    article_id: str = Field(
        ...,
        description="Identificador del artículo citado (ej: 'Art. 2.2.1.4')"
    )
    
    source: str = Field(
        ...,
        description="Fuente del documento (ej: 'Decreto 1076 de 2015')"
    )
    
    page: Optional[int] = Field(
        default=None,
        description="Número de página en el documento original"
    )
    
    verified: bool = Field(
        ...,
        description="Si la cita fue verificada contra el documento fuente"
    )
    
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nivel de confianza de la verificación (0.0-1.0)"
    )


class QueryResponse(BaseModel):
    """
    Respuesta estándar para consultas RAG.
    
    Example:
        ```json
        {
            "query_id": "q_20260427_143022",
            "question": "¿Cuáles son los requisitos?",
            "answer": "Los requisitos son...",
            "sources": ["Decreto 1076", "Ley 99"],
            "citations": [...],
            "metadata": {...},
            "timestamp": "2026-04-27T14:30:22Z"
        }
        ```
    """
    
    query_id: str = Field(
        ...,
        description="ID único de la consulta para trazabilidad"
    )
    
    question: str = Field(
        ...,
        description="Pregunta original del usuario"
    )
    
    answer: str = Field(
        ...,
        description="Respuesta generada por el RAG"
    )
    
    sources: List[str] = Field(
        default_factory=list,
        description="Lista de fuentes documentales citadas"
    )
    
    citations: List[CitationResponse] = Field(
        default_factory=list,
        description="Citas verificadas en la respuesta"
    )
    
    requirements: List[RequirementResponse] = Field(
        default_factory=list,
        description="Requisitos y obligaciones legales detectados"
    )
    
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Nivel de confianza global (0.0-1.0)"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata adicional (latencia, tokens, scores, etc.)"
    )
    
    is_cached: bool = Field(
        default=False,
        description="Si la respuesta proviene del caché"
    )
    
    cache_layer: Optional[str] = Field(
        default=None,
        description="Capa de caché de donde se recuperó (L1/L2/L3)"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp UTC de la respuesta"
    )


class BatchQueryResponse(BaseModel):
    """Respuesta para consultas en batch."""
    
    batch_id: str = Field(
        ...,
        description="ID único del batch"
    )
    
    total_questions: int = Field(
        ...,
        description="Total de preguntas procesadas"
    )
    
    successful: int = Field(
        ...,
        description="Número de consultas exitosas"
    )
    
    failed: int = Field(
        ...,
        description="Número de consultas fallidas"
    )
    
    results: List[QueryResponse] = Field(
        default_factory=list,
        description="Lista de respuestas individuales"
    )
    
    total_latency_seconds: float = Field(
        ...,
        description="Latencia total del batch en segundos"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp UTC del batch"
    )


# ── Ingestion Responses ──────────────────────────────────────────────────────

class IngestionResponse(BaseModel):
    """Respuesta para operaciones de ingesta."""
    
    job_id: str = Field(
        ...,
        description="ID único del job de ingesta"
    )
    
    status: str = Field(
        ...,
        description="Estado: 'queued', 'processing', 'completed', 'failed'"
    )
    
    processed_files: List[str] = Field(
        default_factory=list,
        description="Archivos procesados exitosamente"
    )
    
    failed_files: List[str] = Field(
        default_factory=list,
        description="Archivos que fallaron"
    )
    
    total_chunks: int = Field(
        default=0,
        description="Total de chunks generados"
    )
    
    indexed_chunks: int = Field(
        default=0,
        description="Chunks indexados en ChromaDB"
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="Lista de errores encontrados"
    )
    
    started_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp de inicio del job"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp de finalización del job"
    )
    
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Duración total del job en segundos"
    )


# ── Cache Responses ──────────────────────────────────────────────────────────

class CacheStatsResponse(BaseModel):
    """Estadísticas del sistema de caché."""
    
    total_requests: int = Field(
        ...,
        description="Total de requests procesados"
    )
    
    total_hits: int = Field(
        ...,
        description="Total de cache hits"
    )
    
    total_misses: int = Field(
        ...,
        description="Total de cache misses"
    )
    
    hit_rate: str = Field(
        ...,
        description="Tasa de aciertos (ej: '75.5%')"
    )
    
    hits_by_layer: Dict[str, int] = Field(
        default_factory=dict,
        description="Hits por capa (L1, L2, L3)"
    )
    
    estimated_savings_usd: float = Field(
        ...,
        description="Ahorro estimado en USD por cache hits"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp de las estadísticas"
    )


class CacheClearResponse(BaseModel):
    """Respuesta para operación de limpieza de caché."""
    
    status: str = Field(
        ...,
        description="Estado de la operación: 'success' o 'failed'"
    )
    
    layers_cleared: List[str] = Field(
        default_factory=list,
        description="Capas que fueron limpiadas"
    )
    
    entries_removed: int = Field(
        default=0,
        description="Número de entradas eliminadas"
    )
    
    message: str = Field(
        ...,
        description="Mensaje descriptivo de la operación"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp de la operación"
    )


# ── Health Responses ─────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Respuesta para health check."""
    
    status: str = Field(
        ...,
        description="Estado general: 'healthy', 'degraded', 'unhealthy'"
    )
    
    version: str = Field(
        ...,
        description="Versión de la API"
    )
    
    components: Dict[str, str] = Field(
        default_factory=dict,
        description="Estado de componentes individuales"
    )
    
    uptime_seconds: float = Field(
        ...,
        description="Tiempo de actividad en segundos"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp del health check"
    )


# ── Error Responses ──────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Respuesta estándar para errores."""
    
    error: str = Field(
        ...,
        description="Tipo de error"
    )
    
    message: str = Field(
        ...,
        description="Mensaje descriptivo del error"
    )
    
    detail: Optional[str] = Field(
        default=None,
        description="Detalles adicionales del error"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="ID de la request para debugging"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp del error"
    )


# ── Feedback Responses ───────────────────────────────────────────────────────

class FeedbackResponse(BaseModel):
    """Respuesta para envío de feedback."""
    
    feedback_id: str = Field(
        ...,
        description="ID único del feedback registrado"
    )
    
    status: str = Field(
        ...,
        description="Estado: 'received', 'processed'"
    )
    
    message: str = Field(
        default="Feedback recibido correctamente",
        description="Mensaje de confirmación"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp del feedback"
    )
