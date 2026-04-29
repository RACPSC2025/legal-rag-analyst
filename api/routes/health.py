"""
Health Routes — Endpoints de Health Check
──────────────────────────────────────────
Endpoints para monitoreo de salud del sistema.

Endpoints:
  • GET /health       - Health check general
  • GET /health/ready - Readiness probe (K8s)
  • GET /health/live  - Liveness probe (K8s)

Autor: Fenix Tech Líder
Fecha: 2026-04-27
"""

from __future__ import annotations

import time
from datetime import datetime

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from api.schemas.response_models import HealthResponse

router = APIRouter()

# Timestamp de inicio de la aplicación
_START_TIME = time.time()


# ── Helper Functions ─────────────────────────────────────────────────────────

def _check_chromadb() -> str:
    """
    Verifica conectividad con ChromaDB.
    
    Returns:
        "healthy", "degraded" o "unhealthy"
    """
    try:
        from src.retrieval import get_document_count
        doc_count = get_document_count()
        
        if doc_count > 0:
            return "healthy"
        else:
            return "degraded"  # Conectado pero sin documentos
    
    except Exception:
        return "unhealthy"


def _check_model_hub() -> str:
    """
    Verifica que el Model Hub esté inicializado.
    
    Returns:
        "healthy", "degraded" o "unhealthy"
    """
    try:
        from src.model_hub import get_model_selector
        selector = get_model_selector()
        
        # Intentar seleccionar un modelo
        model_id = selector.select_model("generate")
        
        if model_id:
            return "healthy"
        else:
            return "degraded"
    
    except Exception:
        return "unhealthy"


def _check_cache() -> str:
    """
    Verifica que el sistema de caché esté operativo.
    
    Returns:
        "healthy", "degraded" o "unhealthy"
    """
    try:
        from src.cache import legal_cache
        
        # Intentar obtener estadísticas
        stats = legal_cache.get_stats()
        
        if stats:
            return "healthy"
        else:
            return "degraded"
    
    except Exception:
        return "unhealthy"


def _calculate_overall_status(components: dict) -> str:
    """
    Calcula el estado general del sistema.
    
    Args:
        components: Dict con estado de cada componente.
        
    Returns:
        "healthy", "degraded" o "unhealthy"
    """
    unhealthy_count = sum(1 for status in components.values() if status == "unhealthy")
    degraded_count = sum(1 for status in components.values() if status == "degraded")
    
    if unhealthy_count > 0:
        return "unhealthy"
    elif degraded_count > 0:
        return "degraded"
    else:
        return "healthy"


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check General",
    description=(
        "Verifica el estado de salud del sistema completo. "
        "Incluye verificación de componentes críticos: ChromaDB, Model Hub, Cache."
    ),
)
async def health_check() -> HealthResponse:
    """
    Endpoint de health check general.
    
    Verifica:
      - ChromaDB: Conectividad y documentos indexados
      - Model Hub: Disponibilidad de modelos
      - Cache: Sistema de caché operativo
    
    Returns:
        HealthResponse con estado general y componentes.
    """
    # Verificar componentes
    components = {
        "chromadb": _check_chromadb(),
        "model_hub": _check_model_hub(),
        "cache": _check_cache(),
    }
    
    # Calcular estado general
    overall_status = _calculate_overall_status(components)
    
    # Calcular uptime
    uptime_seconds = time.time() - _START_TIME
    
    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        components=components,
        uptime_seconds=round(uptime_seconds, 2),
    )


@router.get(
    "/ready",
    summary="Readiness Probe",
    description=(
        "Readiness probe para Kubernetes. "
        "Retorna 200 si el sistema está listo para recibir tráfico."
    ),
)
async def readiness_probe():
    """
    Readiness probe para K8s.
    
    Verifica que todos los componentes críticos estén operativos.
    Si algún componente está unhealthy, retorna 503.
    
    Returns:
        200 OK si ready, 503 Service Unavailable si no ready.
    """
    components = {
        "chromadb": _check_chromadb(),
        "model_hub": _check_model_hub(),
    }
    
    # Si algún componente crítico está unhealthy, no está ready
    if any(status == "unhealthy" for status in components.values()):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "ready": False,
                "components": components,
                "message": "Sistema no está listo para recibir tráfico",
            },
        )
    
    return {
        "ready": True,
        "components": components,
        "message": "Sistema listo para recibir tráfico",
    }


@router.get(
    "/live",
    summary="Liveness Probe",
    description=(
        "Liveness probe para Kubernetes. "
        "Retorna 200 si la aplicación está viva (no colgada)."
    ),
)
async def liveness_probe():
    """
    Liveness probe para K8s.
    
    Verifica que la aplicación esté respondiendo.
    Este endpoint siempre retorna 200 a menos que la app esté completamente colgada.
    
    Returns:
        200 OK siempre (si responde).
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(time.time() - _START_TIME, 2),
    }


@router.get(
    "/metrics",
    summary="Métricas del Sistema",
    description="Retorna métricas detalladas del sistema (próximamente).",
)
async def system_metrics():
    """
    Endpoint para métricas del sistema.
    
    TODO: Implementar métricas Prometheus-compatible.
    """
    try:
        from src.retrieval import get_document_count
        from src.cache import legal_cache
        
        doc_count = get_document_count()
        cache_stats = legal_cache.get_stats()
        
        return {
            "documents_indexed": doc_count,
            "cache_hit_rate": cache_stats.get("hit_rate", "0%"),
            "cache_total_hits": cache_stats.get("total_hits", 0),
            "cache_total_requests": cache_stats.get("total_requests", 0),
            "uptime_seconds": round(time.time() - _START_TIME, 2),
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "message": "Error obteniendo métricas",
        }
