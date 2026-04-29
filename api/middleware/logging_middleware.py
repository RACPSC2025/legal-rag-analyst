"""
Logging Middleware — Request/Response Logging
──────────────────────────────────────────────
Middleware para logging automático de requests y responses.

Características:
  • Logging de cada request (método, path, IP)
  • Logging de cada response (status, latencia)
  • Métricas de rendimiento
  • Filtrado de rutas sensibles

Autor: Fenix Tech Líder
Fecha: 2026-04-27
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


# ── Configuración ────────────────────────────────────────────────────────────

# Rutas que no se loggean (para evitar spam)
_SKIP_LOGGING_PATHS = {
    "/health",
    "/health/live",
    "/health/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Umbral de latencia para warning (segundos)
_SLOW_REQUEST_THRESHOLD = 5.0


# ── Logging Middleware ───────────────────────────────────────────────────────

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging automático de requests y responses.
    
    Registra:
      - Método HTTP y path
      - IP del cliente
      - Status code de respuesta
      - Latencia de procesamiento
      - Request ID (si existe)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Procesa el request y registra información relevante.
        
        Args:
            request: Request de FastAPI
            call_next: Siguiente middleware/handler
            
        Returns:
            Response procesada
        """
        # Extraer información del request
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        # Obtener request_id si existe
        request_id = getattr(request.state, "request_id", "no-id")
        
        # Skip logging para rutas específicas
        if path in _SKIP_LOGGING_PATHS:
            return await call_next(request)
        
        # Timestamp de inicio
        start_time = time.time()
        
        # Log del request entrante
        logger.info(
            f"[{request_id}] → {method} {path} | IP: {client_ip}"
        )
        
        # Procesar request
        try:
            response = await call_next(request)
        except Exception as e:
            # Si hay error, loggear y re-raise
            latency = time.time() - start_time
            logger.error(
                f"[{request_id}] ✗ {method} {path} | Error: {str(e)} | "
                f"Latencia: {latency:.3f}s"
            )
            raise
        
        # Calcular latencia
        latency = time.time() - start_time
        
        # Determinar nivel de log según status y latencia
        status_code = response.status_code
        
        if status_code >= 500:
            log_level = logging.ERROR
            status_emoji = "✗"
        elif status_code >= 400:
            log_level = logging.WARNING
            status_emoji = "⚠"
        elif latency > _SLOW_REQUEST_THRESHOLD:
            log_level = logging.WARNING
            status_emoji = "⏱"
        else:
            log_level = logging.INFO
            status_emoji = "✓"
        
        # Log del response
        logger.log(
            log_level,
            f"[{request_id}] {status_emoji} {method} {path} | "
            f"Status: {status_code} | Latencia: {latency:.3f}s"
        )
        
        # Añadir header de latencia
        response.headers["X-Response-Time"] = f"{latency:.3f}s"
        
        return response


# ── Helper Functions ─────────────────────────────────────────────────────────

def configure_logging():
    """
    Configura el sistema de logging para la aplicación.
    
    Establece:
      - Formato de logs
      - Nivel de logging
      - Handlers (console, file)
    """
    import sys
    
    # Formato de logs
    log_format = (
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    )
    
    # Configurar logging básico
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Reducir verbosidad de librerías externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logger.info("✅ Sistema de logging configurado")


# ── Request Metrics (Opcional) ───────────────────────────────────────────────

class RequestMetrics:
    """
    Colector de métricas de requests (opcional).
    
    Útil para monitoreo y análisis de rendimiento.
    """
    
    def __init__(self):
        self.total_requests = 0
        self.total_errors = 0
        self.total_latency = 0.0
        self.requests_by_path = {}
    
    def record_request(
        self,
        path: str,
        status_code: int,
        latency: float,
    ):
        """Registra una request en las métricas."""
        self.total_requests += 1
        self.total_latency += latency
        
        if status_code >= 400:
            self.total_errors += 1
        
        # Contar por path
        if path not in self.requests_by_path:
            self.requests_by_path[path] = {
                "count": 0,
                "total_latency": 0.0,
                "errors": 0,
            }
        
        self.requests_by_path[path]["count"] += 1
        self.requests_by_path[path]["total_latency"] += latency
        
        if status_code >= 400:
            self.requests_by_path[path]["errors"] += 1
    
    def get_summary(self) -> dict:
        """Retorna resumen de métricas."""
        avg_latency = (
            self.total_latency / self.total_requests
            if self.total_requests > 0
            else 0.0
        )
        
        error_rate = (
            (self.total_errors / self.total_requests) * 100
            if self.total_requests > 0
            else 0.0
        )
        
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": f"{error_rate:.2f}%",
            "avg_latency_seconds": round(avg_latency, 3),
            "requests_by_path": self.requests_by_path,
        }


# Instancia global de métricas (opcional)
request_metrics = RequestMetrics()
