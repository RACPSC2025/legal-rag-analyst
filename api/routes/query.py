"""
Query Routes — Endpoints de Consulta RAG v2.5
─────────────────────────────────────────────
Endpoints para realizar consultas al sistema RAG con Generación Verificable.

Endpoints:
  • POST /query          - Consulta individual con LegalResponse
  • POST /query/batch    - Consultas en batch con LegalResponse
  • POST /query/stream   - Consulta con streaming (SSE) - Fase 3.2

Autor: Fenix Tech Líder
Fecha: 2026-04-30
"""

from __future__ import annotations

import time
import uuid
import logging
from typing import AsyncGenerator, Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from api.schemas.request_models import QueryRequest, BatchQueryRequest
from api.schemas.response_models import (
    QueryResponse,
    BatchQueryResponse,
    LegalAnswerResponse,
    CitationOut,
    NumericDiscrepancyOut,
    VerificationMetaOut,
    ErrorResponse,
)
from src.core.graph import query as rag_query
from src.cache import legal_cache
from src.schemas.legal_output import LegalAnswer, LegalCitation, NumericDiscrepancy
from src.services.citation_verifier import CitationVerifier
from src.services.numeric_grader import NumericGrader

# Configuración de logging
logger = logging.getLogger(__name__)

router = APIRouter()


# ── Helper Functions ─────────────────────────────────────────────────────────

def _generate_query_id() -> str:
    """Genera un ID único para la consulta."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"q_{timestamp}_{unique_id}"


def _build_legal_answer_response(
    query_id: str,
    question: str,
    result: dict,
    is_cached: bool = False,
    cache_layer: str | None = None,
) -> LegalAnswerResponse:
    """
    Construye una LegalAnswerResponse estandarizada desde el resultado del grafo RAG.
    
 Esta función convierte el resultado del grafo RAG al nuevo formato LegalAnswerResponse
    con soporte completo para verificación de citas y discrepancias numéricas.
    """
    try:
        # Extraer LegalAnswer del resultado si existe, sino construirlo
        legal_answer = result.get("legal_answer")
        if not legal_answer:
            # Fallback para compatibilidad con versiones anteriores
            logger.warning(f"[API] No se encontró LegalAnswer en resultado, construyendo fallback para {query_id}")
            legal_answer = LegalAnswer(
                answer=result.get("generation", ""),
                citations=[],
                confidence_score=result.get("confidence_score", 0.0),
                requires_human_review=result.get("requires_human_review", False),
                metadata=result.get("metadata", {})
            )
        
        # Convertir LegalCitation a CitationOut
        citations = []
        for citation in legal_answer.citations:
            citation_out = CitationOut(
                article_id=citation.article_id,
                source_doc=citation.source_doc,
                quote=citation.quote,
                relevance_score=citation.relevance_score,
                is_verified=citation.is_verified,
                verification_note=citation.verification_note or ""
            )
            citations.append(citation_out)
        
        # Convertir NumericDiscrepancy a NumericDiscrepancyOut
        numeric_discrepancies = []
        for discrepancy in legal_answer.numeric_discrepancies:
            discrepancy_out = NumericDiscrepancyOut(
                field_name=discrepancy.field_name,
                expected_value=str(discrepancy.expected_value),
                found_value=str(discrepancy.found_value),
                source_table=getattr(discrepancy, 'source_table', 'Tabla desconocida'),
                data_type=discrepancy.data_type
            )
            numeric_discrepancies.append(discrepancy_out)
        
        # Construir metadata de verificación
        verification_meta = None
        if "verification_passed" in result or "attempts" in result:
            verification_meta = VerificationMetaOut(
                verified_count=sum(1 for c in citations if c.is_verified),
                failed_count=len(citations) - sum(1 for c in citations if c.is_verified),
                duration_ms=result.get("verification_time_ms", 0.0),
                attempt=result.get("attempts", 1)
            )
        
        return LegalAnswerResponse(
            request_id=query_id,
            answer=legal_answer.answer,
            citations=citations,
            confidence_score=legal_answer.confidence_score,
            requires_human_review=legal_answer.requires_human_review,
            numeric_discrepancies=numeric_discrepancies,
            verification_meta=verification_meta
        )
        
    except Exception as e:
        logger.error(f"[API] Error construyendo LegalAnswerResponse: {e}")
        # Fallback a formato básico
        return LegalAnswerResponse(
            request_id=query_id,
            answer=result.get("generation", "Error procesando la respuesta"),
            citations=[],
            confidence_score=0.0,
            requires_human_review=True,
            numeric_discrepancies=[],
            verification_meta=None
        )


def _build_legacy_query_response(
    query_id: str,
    question: str,
    result: dict,
    is_cached: bool = False,
    cache_layer: str | None = None,
) -> QueryResponse:
    """Construye una QueryResponse estandarizada (formato legacy)."""
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
    response_model=LegalAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Consulta RAG Legal v2.5 - Generación Verificable",
    description=(
        "Realiza una consulta al sistema RAG Legal con auditoría post-generación. "
        "Retorna una LegalAnswerResponse con citas verificadas, "
        "discrepancias numéricas y métricas de confianza."
    ),
    responses={
        200: {"description": "Consulta procesada con verificación legal"},
        400: {"model": ErrorResponse, "description": "Request inválido"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
    },
)
async def query_rag_v2(request: QueryRequest) -> LegalAnswerResponse:
    """
    Endpoint principal de consulta RAG v2.5 con Generación Verificable.
    
    Flujo:
      1. Genera ID único para la consulta
      2. Verifica caché si use_cache=True
      3. Ejecuta el grafo RAG si no hay cache hit
      4. Procesa respuesta con LegalAnswer y verificación dual
      5. Retorna LegalAnswerResponse con métricas de auditoría
    
    Args:
        request: QueryRequest con la pregunta y parámetros.
        
    Returns:
        LegalAnswerResponse con respuesta verificada y auditoría integrada.
        
    Raises:
        HTTPException: Si ocurre un error durante el procesamiento.
    """
    query_id = _generate_query_id()
    start_time = time.time()
    
    try:
        # Verificar caché si está habilitado
        if request.use_cache:
            cached_response, cache_layer = legal_cache.get(request.question)
            if cached_response:
                logger.info(f"[API] Cache hit para consulta {query_id}")
                # Cache hit - retornar respuesta cacheada en formato v2
                return _build_legal_answer_response(
                    query_id=query_id,
                    question=request.question,
                    result=cached_response,
                    is_cached=True,
                    cache_layer=cache_layer,
                )
        
        # Cache miss o caché deshabilitado - ejecutar RAG
        logger.info(f"[API] Ejecutando RAG para consulta {query_id}")
        result = rag_query(request.question)
        
        # Procesar respuesta con verificación legal mejorada
        processed_result = _process_legal_verification(query_id, request.question, result)
        
        # Construir respuesta v2
        response = _build_legal_answer_response(
            query_id=query_id,
            question=request.question,
            result=processed_result,
            is_cached=False,
            cache_layer=None,
        )
        
        # Registrar métricas
        duration = time.time() - start_time
        logger.info(f"[API] Consulta {query_id} procesada en {duration:.2f}s")
        
        return response
    
    except Exception as e:
        logger.error(f"[API] Error en consulta {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando consulta: {str(e)}",
        )


def _process_legal_verification(query_id: str, question: str, result: dict) -> dict:
    """
    Procesa el resultado del grafo RAG con verificación legal mejorada.
    
    Args:
        query_id: ID de la consulta
        question: Pregunta original
        result: Resultado del grafo RAG
        
    Returns:
        Dict con respuesta procesada y métricas de verificación
    """
    try:
        # Inicializar servicios de verificación
        verifier = CitationVerifier(threshold=0.85)
        grader = NumericGrader()
        
        # Extraer documentos del contexto
        context_docs = result.get("source_docs", [])
        
        # Procesar LegalAnswer si existe
        legal_answer = result.get("legal_answer")
        if legal_answer:
            # Ejecutar verificación dual: citas + números
            verified_citations, numeric_discrepancies = verifier.audit_response(
                llm_answer=legal_answer.answer,
                citations=legal_answer.citations,
                context=context_docs
            )
            
            # Actualizar LegalAnswer con resultados
            legal_answer.citations = verified_citations
            legal_answer.numeric_discrepancies = numeric_discrepancies
            
            # Recalcular métricas
            legal_answer = _recompute_legal_answer_metrics(legal_answer)
            
            # Actualizar resultado
            result["legal_answer"] = legal_answer
            result["verification_passed"] = len(numeric_discrepancies) == 0 and all(c.is_verified for c in verified_citations)
            result["verification_time_ms"] = result.get("verification_time_ms", 0.0)
            
            logger.info(f"[API] Verificación dual completada para {query_id}: "
                       f"{sum(1 for c in verified_citations if c.is_verified)}/{len(verified_citations)} citas verificadas, "
                       f"{len(numeric_discrepancies)} discrepancias numéricas")
        
        return result
        
    except Exception as e:
        logger.error(f"[API] Error en verificación legal para {query_id}: {e}")
        # Retornar resultado original sin verificación
        return result


def _recompute_legal_answer_metrics(legal_answer: LegalAnswer) -> LegalAnswer:
    """
    Recalcula las métricas de LegalAnswer después de la verificación.
    
    Args:
        legal_answer: LegalAnswer original
        
    Returns:
        LegalAnswer con métricas actualizadas
    """
    # Recalcular confidence_score basado en citas verificadas
    if legal_answer.citations:
        verified_citations = [c for c in legal_answer.citations if c.is_verified]
        if verified_citations:
            legal_answer.confidence_score = sum(c.relevance_score for c in verified_citations) / len(verified_citations)
        else:
            legal_answer.confidence_score = 0.0
    else:
        legal_answer.confidence_score = 0.0
    
    # Actualizar requires_human_review
    if legal_answer.numeric_discrepancies or any(not c.is_verified for c in legal_answer.citations):
        legal_answer.requires_human_review = True
    else:
        legal_answer.requires_human_review = False
    
    return legal_answer


@router.post(
    "/batch",
    response_model=BatchQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultas en Batch v2.5",
    description=(
        "Procesa múltiples consultas en un solo request con verificación legal. "
        "Útil para evaluación, procesamiento masivo y benchmarking."
    ),
)
async def query_batch_v2(request: BatchQueryRequest) -> BatchQueryResponse:
    """
    Procesa múltiples consultas en batch con verificación legal mejorada.
    
    Args:
        request: BatchQueryRequest con lista de preguntas.
        
    Returns:
        BatchQueryResponse con resultados de todas las consultas en formato v2.5.
    """
    batch_id = f"batch_{time.strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    start_time = time.time()
    
    results = []
    successful = 0
    failed = 0
    
    for question in request.questions:
        query_id = _generate_query_id()
        try:
            # Verificar caché si está habilitado
            if request.use_cache:
                cached_response, cache_layer = legal_cache.get(question)
                if cached_response:
                    # Cache hit - procesar en formato v2
                    response = _build_legal_answer_response(
                        query_id=query_id,
                        question=question,
                        result=cached_response,
                        is_cached=True,
                        cache_layer=cache_layer,
                    )
                    results.append(response)
                    successful += 1
                    continue
            
            # Cache miss - ejecutar RAG
            result = rag_query(question)
            
            # Procesar con verificación legal
            processed_result = _process_legal_verification(query_id, question, result)
            
            # Construir respuesta v2
            response = _build_legal_answer_response(
                query_id=query_id,
                question=question,
                result=processed_result,
                is_cached=False,
                cache_layer=None,
            )
            
            results.append(response)
            successful += 1
            
        except Exception as e:
            logger.error(f"[API] Error en batch query {query_id}: {e}")
            # Agregar respuesta de error
            error_response = LegalAnswerResponse(
                request_id=query_id,
                answer=f"Error procesando consulta: {str(e)}",
                citations=[],
                confidence_score=0.0,
                requires_human_review=True,
                numeric_discrepancies=[],
                verification_meta=None
            )
            results.append(error_response)
            failed += 1
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
    summary="Consulta con Streaming Real (SSE) - v2.5",
    description=(
        "Realiza una consulta con respuesta en streaming real usando astream_events. "
        "Emite tokens de generación, estados de verificación y la respuesta final estructurada."
    ),
)
async def query_stream(request: QueryRequest):
    """
    Endpoint de consulta con streaming real nativo de LangGraph.
    
    Eventos SSE emitidos:
      - event: phase_change (generation, verification, delivery)
      - event: token (tokens del LLM en tiempo real)
      - event: verification_complete (resultado de la auditoría)
      - event: final_response (LegalAnswerResponse completo)
      - event: error
    """
    
    async def event_generator() -> AsyncGenerator[dict, None]:
        query_id = _generate_query_id()
        graph = get_graph()
        
        try:
            # 1. Verificar Caché (Síncrono para velocidad)
            if request.use_cache:
                cached_response, cache_layer = legal_cache.get(request.question)
                if cached_response:
                    yield {"event": "start", "data": {"query_id": query_id, "is_cached": True}}
                    yield {"event": "token", "data": {"content": cached_response.get("answer", "")}}
                    yield {
                        "event": "final_response", 
                        "data": _build_legal_answer_response(query_id, request.question, cached_response).model_dump()
                    }
                    yield {"event": "end", "data": {"status": "completed"}}
                    return

            # 2. Ejecución con Streaming Real
            config = {"configurable": {"thread_id": query_id}}
            initial_state = {"question": request.question}
            
            yield {"event": "start", "data": {"query_id": query_id}}
            yield {
                "event": "phase_change", 
                "data": {"phase": "generation", "message": "Generando respuesta jurídica..."}
            }

            async for event in graph.astream_events(initial_state, config, version="v2"):
                kind = event["event"]
                
                # A. Streaming de Tokens (on_chat_model_stream)
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield {"event": "token", "data": {"content": content}}

                # B. Transiciones de Fase (on_chain_start para nodos específicos)
                elif kind == "on_chain_start" and event["name"] == "verify_citations":
                    yield {
                        "event": "phase_change", 
                        "data": {"phase": "verification", "message": "Iniciando auditoría técnica de citas y cifras..."}
                    }

                # C. Captura de Resultados de Nodos (on_chain_end)
                elif kind == "on_chain_end" and event["name"] == "verify_citations":
                    output = event["data"].get("output", {})
                    if isinstance(output, dict) and "legal_answer" in output:
                        ans = output["legal_answer"]
                        yield {
                            "event": "verification_complete",
                            "data": {
                                "verified": sum(1 for c in ans.citations if c.is_verified),
                                "failed": len(ans.citations) - sum(1 for c in ans.citations if c.is_verified),
                                "verification_passed": output.get("verification_passed", False)
                            }
                        }

            # 3. Respuesta Final (Obtenida del estado final)
            final_state = await graph.aget_state(config)
            result = final_state.values
            
            yield {
                "event": "phase_change", 
                "data": {"phase": "delivery", "message": "Procesamiento completado"}
            }
            
            yield {
                "event": "final_response",
                "data": _build_legal_answer_response(query_id, request.question, result).model_dump()
            }
            
            yield {"event": "end", "data": {"status": "completed"}}

        except Exception as e:
            logger.error(f"[API] Error crítico en stream {query_id}: {str(e)}")
            yield {"event": "error", "data": {"message": "Error interno en el motor de streaming", "details": str(e)}}

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
