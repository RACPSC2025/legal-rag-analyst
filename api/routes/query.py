"""
Query Routes — Endpoints de Consulta RAG
────────────────────────────────────────
Endpoints para realizar consultas al sistema RAG.

Endpoints:
  • POST /query          - Consulta individual
  • POST /query/batch    - Consultas en batch
  • POST /query/stream   - Consulta con streaming (SSE)

Autor: Fenix Tech Líder
Fecha: 2026-04-27
"""

from __future__ import annotations

import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from api.schemas.request_models import QueryRequest, BatchQueryRequest
from api.schemas.response_models import (
    QueryResponse,
    BatchQueryResponse,
    CitationResponse,
    RequirementResponse,
    ErrorResponse,
)
from src.core.graph import query as rag_query
from src.cache import legal_cache

router = APIRouter()


# ── Helper Functions ─────────────────────────────────────────────────────────

def _generate_query_id() -> str:
    """Genera un ID único para la consulta."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"q_{timestamp}_{unique_id}"


def _build_query_response(
    query_id: str,
    question: str,
    result: dict,
    is_cached: bool = False,
    cache_layer: str | None = None,
) -> QueryResponse:
    """Construye una QueryResponse estandarizada."""
    # Mapear citas
    citations = [
        CitationResponse(
            article_id=cit.get("article_id", "N/A"),
            source=cit.get("source", "Contexto"),
            page=int(cit.get("page")) if str(cit.get("page", "")).isdigit() else None,
            verified=cit.get("verified", False),
            confidence=cit.get("confidence", 1.0),
        )
        for cit in result.get("verified_citations", [])
    ]
    
    # Mapear requerimientos
    requirements = [
        RequirementResponse(
            description=req.get("description", ""),
            deadline=req.get("deadline"),
            responsible=req.get("responsible")
        )
        for req in result.get("legal_requirements", [])
    ]
    
    metadata = {
        "attempts": result.get("attempts", 1),
        "grade": result.get("grade", "útil"),
        "hallucination_score": result.get("hallucination_score", 0.0),
    }
    
    return QueryResponse(
        query_id=query_id,
        question=question,
        answer=result.get("generation", ""),
        sources=result.get("source_docs", []),
        citations=citations,
        requirements=requirements,
        confidence_score=result.get("confidence_score", 0.5),
        metadata=metadata,
        is_cached=is_cached,
        cache_layer=cache_layer,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Consulta RAG Individual",
    description=(
        "Realiza una consulta al sistema RAG Legal. "
        "Retorna una respuesta fundamentada con citas verificadas."
    ),
    responses={
        200: {"description": "Consulta procesada exitosamente"},
        400: {"model": ErrorResponse, "description": "Request inválido"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
    },
)
async def query_rag(request: QueryRequest) -> QueryResponse:
    """
    Endpoint principal de consulta RAG.
    
    Flujo:
      1. Genera ID único para la consulta
      2. Verifica caché si use_cache=True
      3. Ejecuta el grafo RAG si no hay cache hit
      4. Retorna respuesta estandarizada
    
    Args:
        request: QueryRequest con la pregunta y parámetros.
        
    Returns:
        QueryResponse con la respuesta generada.
        
    Raises:
        HTTPException: Si ocurre un error durante el procesamiento.
    """
    query_id = _generate_query_id()
    
    try:
        # Verificar caché si está habilitado
        if request.use_cache:
            cached_response, cache_layer = legal_cache.get(request.question)
            if cached_response:
                # Cache hit - retornar respuesta cacheada
                return _build_query_response(
                    query_id=query_id,
                    question=request.question,
                    result=cached_response,
                    is_cached=True,
                    cache_layer=cache_layer,
                )
        
        # Cache miss o caché deshabilitado - ejecutar RAG
        result = rag_query(request.question)
        
        # Construir respuesta
        response = _build_query_response(
            query_id=query_id,
            question=request.question,
            result=result,
            is_cached=False,
            cache_layer=None,
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando consulta: {str(e)}",
        )


@router.post(
    "/batch",
    response_model=BatchQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultas en Batch",
    description=(
        "Procesa múltiples consultas en un solo request. "
        "Útil para evaluación o procesamiento masivo."
    ),
)
async def query_batch(request: BatchQueryRequest) -> BatchQueryResponse:
    """
    Procesa múltiples consultas en batch.
    
    Args:
        request: BatchQueryRequest con lista de preguntas.
        
    Returns:
        BatchQueryResponse con resultados de todas las consultas.
    """
    batch_id = f"batch_{time.strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    start_time = time.time()
    
    results = []
    successful = 0
    failed = 0
    
    for question in request.questions:
        query_id = _generate_query_id()
        
        try:
            # Verificar caché
            if request.use_cache:
                cached_response, cache_layer = legal_cache.get(question)
                if cached_response:
                    response = _build_query_response(
                        query_id=query_id,
                        question=question,
                        result=cached_response,
                        is_cached=True,
                        cache_layer=cache_layer,
                    )
                    results.append(response)
                    successful += 1
                    continue
            
            # Ejecutar RAG
            result = rag_query(question)
            response = _build_query_response(
                query_id=query_id,
                question=question,
                result=result,
            )
            results.append(response)
            successful += 1
        
        except Exception as e:
            # Registrar error pero continuar con las demás preguntas
            failed += 1
            # Crear respuesta de error
            error_response = QueryResponse(
                query_id=query_id,
                question=question,
                answer=f"Error: {str(e)}",
                sources=[],
                citations=[],
                metadata={"error": str(e)},
            )
            results.append(error_response)
    
    total_latency = time.time() - start_time
    
    return BatchQueryResponse(
        batch_id=batch_id,
        total_questions=len(request.questions),
        successful=successful,
        failed=failed,
        results=results,
        total_latency_seconds=round(total_latency, 2),
    )


@router.post(
    "/stream",
    summary="Consulta con Streaming (SSE)",
    description=(
        "Realiza una consulta con respuesta en streaming usando Server-Sent Events. "
        "Útil para UX en tiempo real en el frontend."
    ),
)
async def query_stream(request: QueryRequest):
    """
    Endpoint de consulta con streaming SSE.
    
    Retorna eventos en formato SSE:
      - event: start
      - event: chunk (múltiples)
      - event: sources
      - event: citations
      - event: end
    
    Args:
        request: QueryRequest con la pregunta.
        
    Returns:
        EventSourceResponse con eventos SSE.
    """
    
    async def event_generator() -> AsyncGenerator[dict, None]:
        """Generador de eventos SSE."""
        query_id = _generate_query_id()
        
        try:
            # Evento de inicio
            yield {
                "event": "start",
                "data": {
                    "query_id": query_id,
                    "question": request.question,
                }
            }
            
            # Verificar caché
            if request.use_cache:
                cached_response, cache_layer = legal_cache.get(request.question)
                if cached_response:
                    # Enviar respuesta cacheada completa
                    yield {
                        "event": "answer",
                        "data": {
                            "text": cached_response.get("answer", ""),
                            "is_cached": True,
                            "cache_layer": cache_layer,
                        }
                    }
                    
                    yield {
                        "event": "sources",
                        "data": {"sources": cached_response.get("sources", [])}
                    }
                    
                    yield {
                        "event": "end",
                        "data": {"query_id": query_id, "status": "completed"}
                    }
                    return
            
            # Ejecutar RAG (sin streaming real por ahora - mejora futura)
            result = rag_query(request.question)
            
            # Simular streaming dividiendo la respuesta en chunks
            answer = result.get("answer", "")
            chunk_size = 50  # Caracteres por chunk
            
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i + chunk_size]
                yield {
                    "event": "chunk",
                    "data": {"text": chunk}
                }
            
            # Enviar fuentes
            yield {
                "event": "sources",
                "data": {"sources": result.get("source_docs", [])}
            }
            
            # Enviar citas
            citations = result.get("verified_citations", [])
            if citations:
                yield {
                    "event": "citations",
                    "data": {"citations": citations}
                }
            
            # Evento de finalización
            yield {
                "event": "end",
                "data": {
                    "query_id": query_id,
                    "status": "completed",
                    "metadata": {
                        "attempts": result.get("attempts", 1),
                        "grade": result.get("grade", "útil"),
                    }
                }
            }
        
        except Exception as e:
            # Evento de error
            yield {
                "event": "error",
                "data": {
                    "query_id": query_id,
                    "error": str(e),
                }
            }
    
    return EventSourceResponse(event_generator())


@router.get(
    "/history",
    summary="Historial de Consultas",
    description="Retorna el historial de consultas recientes (próximamente)",
)
async def query_history():
    """
    Endpoint para historial de consultas.
    
    TODO: Implementar almacenamiento de historial en base de datos.
    """
    return {
        "message": "Historial de consultas - Próximamente",
        "status": "not_implemented",
    }
