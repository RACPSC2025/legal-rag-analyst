"""
Error Handler Middleware — Manejo Global de Errores
────────────────────────────────────────────────────
Middleware para capturar y formatear errores de forma consistente.

Características:
  • Captura excepciones no manejadas
  • Formatea errores con estructura estándar
  • Logging automático de errores
  • Request ID para trazabilidad

Autor: Fenix Tech Líder
Fecha: 2026-04-27
"""

from __future__ import annotations

import logging
import traceback
import uuid
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# ── Error Response Builder ───────────────────────────────────────────────────

def _build_error_response(
    error_type: str,
    message: str,
    detail: str | None = None,
    request_id: str | None = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> JSONResponse:
    """
    Construye una respuesta de error estandarizada.
    
    Args:
        error_type: Tipo de error (ValidationError, HTTPException, etc.)
        message: Mensaje descriptivo del error
        detail: Detalles adicionales (opcional)
        request_id: ID de la request para trazabilidad
        status_code: Código HTTP del error
        
    Returns:
        JSONResponse con formato estándar de error
    """
    from datetime import datetime
    
    error_response = {
        "error": error_type,
        "message": message,
        "detail": detail,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    return JSONResponse(
        status_code=status_code,
        content=error_response,
    )


# ── Exception Handlers ───────────────────────────────────────────────────────

async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handler para errores de validación de Pydantic.
    
    Captura errores cuando los datos de entrada no cumplen con el schema.
    """
    request_id = request.state.request_id if hasattr(request.state, "request_id") else None
    
    # Extraer detalles de validación
    errors = exc.errors()
    error_details = []
    
    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append(f"{field}: {error['msg']}")
    
    detail = "; ".join(error_details)
    
    logger.warning(
        f"[{request_id}] Validation error en {request.method} {request.url.path}: {detail}"
    )
    
    return _build_error_response(
        error_type="ValidationError",
        message="Los datos de entrada no son válidos",
        detail=detail,
        request_id=request_id,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    Handler para excepciones HTTP (404, 403, etc.).
    """
    request_id = request.state.request_id if hasattr(request.state, "request_id") else None
    
    logger.warning(
        f"[{request_id}] HTTP {exc.status_code} en {request.method} {request.url.path}: {exc.detail}"
    )
    
    return _build_error_response(
        error_type="HTTPException",
        message=exc.detail,
        detail=None,
        request_id=request_id,
        status_code=exc.status_code,
    )


async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handler para excepciones no capturadas.
    
    Captura cualquier error inesperado y lo formatea de forma segura.
    """
    request_id = request.state.request_id if hasattr(request.state, "request_id") else None
    
    # Logging detallado del error
    logger.error(
        f"[{request_id}] Error no manejado en {request.method} {request.url.path}",
        exc_info=True,
    )
    
    # En producción, no exponer detalles internos
    # En desarrollo, incluir traceback
    import os
    is_development = os.getenv("ENVIRONMENT", "production") == "development"
    
    if is_development:
        detail = traceback.format_exc()
    else:
        detail = "Error interno del servidor. Contacte al administrador."
    
    return _build_error_response(
        error_type="InternalServerError",
        message="Ha ocurrido un error inesperado",
        detail=detail,
        request_id=request_id,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ── Request ID Middleware ────────────────────────────────────────────────────

async def add_request_id_middleware(request: Request, call_next: Callable):
    """
    Middleware para añadir request_id a cada request.
    
    Útil para trazabilidad y debugging.
    """
    # Generar request_id único
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Procesar request
    response = await call_next(request)
    
    # Añadir request_id al header de respuesta
    response.headers["X-Request-ID"] = request_id
    
    return response


# ── Setup Function ───────────────────────────────────────────────────────────

def add_error_handlers(app: FastAPI):
    """
    Registra todos los error handlers en la aplicación FastAPI.
    
    Args:
        app: Instancia de FastAPI
    """
    # Registrar exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # Registrar middleware de request_id
    app.middleware("http")(add_request_id_middleware)
    
    logger.info("✅ Error handlers registrados correctamente")
