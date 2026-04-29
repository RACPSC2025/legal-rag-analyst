"""
Cache Routes — Endpoints de Gestión de Caché
─────────────────────────────────────────────
Endpoints para consultar estadísticas y gestionar el sistema de caché.

Endpoints:
  • GET /cache/stats   - Estadísticas del caché
  • POST /cache/clear  - Limpiar caché (requiere confirmación)

Autor: Fenix Tech Líder
Fecha: 2026-04-27
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from api.schemas.request_models import CacheClearRequest
from api.schemas.response_models import (
    CacheStatsResponse,
    CacheClearResponse,
    ErrorResponse,
)
from src.cache import legal_cache

router = APIRouter()


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    response_model=CacheStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Estadísticas del Caché",
    description=(
        "Retorna estadísticas detalladas del sistema de caché: "
        "hits, misses, hit rate, ahorro estimado, etc."
    ),
    responses={
        200: {"description": "Estadísticas recuperadas exitosamente"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
    },
)
async def get_cache_stats() -> CacheStatsResponse:
    """
    Endpoint para obtener estadísticas del caché.
    
    Retorna:
      - Total de requests procesados
      - Total de hits y misses
      - Hit rate (porcentaje)
      - Hits por capa (L1, L2, L3)
      - Ahorro estimado en USD
    
    Returns:
        CacheStatsResponse con estadísticas completas.
        
    Raises:
        HTTPException: Si ocurre un error obteniendo las estadísticas.
    """
    try:
        # Obtener estadísticas del caché
        stats = legal_cache.get_stats()
        
        # Calcular hit rate
        total_requests = stats.get("total_requests", 0)
        total_hits = stats.get("total_hits", 0)
        
        if total_requests > 0:
            hit_rate_value = (total_hits / total_requests) * 100
            hit_rate = f"{hit_rate_value:.1f}%"
        else:
            hit_rate = "0.0%"
        
        # Obtener hits por capa
        hits_by_layer = stats.get("hits_by_layer", {})
        
        # Calcular ahorro estimado
        # Asumiendo $0.015 por query sin caché
        cost_per_query = 0.015
        estimated_savings = total_hits * cost_per_query
        
        return CacheStatsResponse(
            total_requests=total_requests,
            total_hits=total_hits,
            total_misses=stats.get("total_misses", 0),
            hit_rate=hit_rate,
            hits_by_layer=hits_by_layer,
            estimated_savings_usd=round(estimated_savings, 2),
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas de caché: {str(e)}",
        )


@router.post(
    "/clear",
    response_model=CacheClearResponse,
    status_code=status.HTTP_200_OK,
    summary="Limpiar Caché",
    description=(
        "Limpia el sistema de caché. Requiere confirmación explícita. "
        "Puede especificar capas específicas (L1, L2, L3) o limpiar todas."
    ),
    responses={
        200: {"description": "Caché limpiado exitosamente"},
        400: {"model": ErrorResponse, "description": "Request inválido"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
    },
)
async def clear_cache(request: CacheClearRequest) -> CacheClearResponse:
    """
    Endpoint para limpiar el caché.
    
    Flujo:
      1. Valida que confirm=True (seguridad)
      2. Determina qué capas limpiar
      3. Ejecuta limpieza
      4. Retorna resultado con estadísticas
    
    Args:
        request: CacheClearRequest con confirmación y capas.
        
    Returns:
        CacheClearResponse con resultado de la operación.
        
    Raises:
        HTTPException: Si no hay confirmación o ocurre un error.
    """
    # Validar confirmación
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe confirmar la limpieza del caché (confirm=true)",
        )
    
    try:
        # Determinar capas a limpiar
        layers_to_clear = request.layers if request.layers else ["L1", "L2", "L3"]
        
        # Contador de entradas eliminadas
        entries_removed = 0
        layers_cleared = []
        
        # Limpiar cada capa
        for layer in layers_to_clear:
            try:
                if layer == "L1":
                    # Limpiar L1 (in-memory)
                    count = legal_cache._clear_layer("L1")
                    entries_removed += count
                    layers_cleared.append("L1")
                
                elif layer == "L2":
                    # Limpiar L2 (disk)
                    count = legal_cache._clear_layer("L2")
                    entries_removed += count
                    layers_cleared.append("L2")
                
                elif layer == "L3":
                    # Limpiar L3 (semantic)
                    count = legal_cache._clear_layer("L3")
                    entries_removed += count
                    layers_cleared.append("L3")
            
            except Exception as e:
                # Continuar con las demás capas si una falla
                continue
        
        # Construir mensaje
        if layers_cleared:
            message = f"Caché limpiado exitosamente: {', '.join(layers_cleared)}"
            status_result = "success"
        else:
            message = "No se pudo limpiar ninguna capa del caché"
            status_result = "failed"
        
        return CacheClearResponse(
            status=status_result,
            layers_cleared=layers_cleared,
            entries_removed=entries_removed,
            message=message,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error limpiando caché: {str(e)}",
        )


@router.get(
    "/info",
    summary="Información del Sistema de Caché",
    description="Retorna información sobre la configuración del sistema de caché.",
)
async def cache_info():
    """
    Endpoint para obtener información del sistema de caché.
    
    Returns:
        Información sobre capas, TTL, configuración, etc.
    """
    return {
        "layers": {
            "L1": {
                "name": "In-Memory Cache",
                "type": "LRU",
                "max_size": 100,
                "description": "Caché en memoria para queries exactas",
            },
            "L2": {
                "name": "Disk Cache",
                "type": "Persistent",
                "ttl_days": 7,
                "description": "Caché persistente en disco con TTL",
            },
            "L3": {
                "name": "Semantic Cache",
                "type": "Vector-based",
                "similarity_threshold": 0.95,
                "description": "Caché semántico para queries similares",
            },
        },
        "cascade_order": ["L1", "L2", "L3"],
        "analytics_enabled": True,
        "cost_per_query_usd": 0.015,
    }
