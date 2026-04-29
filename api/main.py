"""
FastAPI Main Application — RAG Legal Colombiano
────────────────────────────────────────────────
API REST profesional para el sistema RAG Analista Legal.

Características:
  • Endpoints RESTful para consultas y gestión
  • Streaming de respuestas con SSE
  • Validación automática con Pydantic
  • Documentación OpenAPI automática
  • CORS configurado para frontend React
  • Health checks y métricas

Autor: Fenix Tech Líder
Fecha: 2026-04-27
Versión: 1.0.0
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Añadir src al path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.routes import query, ingestion, health, cache
from api.middleware.error_handler import add_error_handlers
from api.middleware.logging_middleware import LoggingMiddleware
from src.config import settings

logger = logging.getLogger(__name__)

# ── Lifespan Events ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    
    Startup:
      - Inicializa conexiones a ChromaDB
      - Carga el catálogo de modelos
      - Valida credenciales AWS
    
    Shutdown:
      - Cierra conexiones abiertas
      - Limpia recursos temporales
    """
    # Startup
    logger.info("🚀 Iniciando API RAG Legal...")
    
    # Validar que ChromaDB esté accesible
    try:
        from src.retrieval import get_document_count
        doc_count = get_document_count()
        logger.info(f"✅ ChromaDB conectado: {doc_count} documentos indexados")
    except Exception as e:
        logger.warning(f"⚠️ ChromaDB no accesible: {e}")
    
    # Inicializar Model Hub
    try:
        from src.model_hub import initialize_model_catalog
        initialize_model_catalog()
        logger.info("✅ Model Hub inicializado")
    except Exception as e:
        logger.warning(f"⚠️ Model Hub no inicializado: {e}")
    
    logger.info("✅ API lista para recibir peticiones")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando API RAG Legal...")
    logger.info("✅ Recursos liberados correctamente")


# ── Aplicación FastAPI ───────────────────────────────────────────────────────

app = FastAPI(
    title="RAG Legal Colombiano API",
    description=(
        "API REST profesional para consultas legales usando RAG "
        "(Retrieval-Augmented Generation) especializado en normativa colombiana."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────────────────

# CORS para frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React dev server
        "http://localhost:5173",      # Vite dev server
        "http://localhost:8501",      # Streamlit
        "https://rag-legal.app",      # Producción (ajustar según dominio)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware personalizado
app.add_middleware(LoggingMiddleware)

# ── Error Handlers ───────────────────────────────────────────────────────────

add_error_handlers(app)

# ── Routes ───────────────────────────────────────────────────────────────────

# Health checks y métricas
app.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

# Consultas RAG
app.include_router(
    query.router,
    prefix="/api/v1/query",
    tags=["Query"],
)

# Ingesta de documentos
app.include_router(
    ingestion.router,
    prefix="/api/v1/ingestion",
    tags=["Ingestion"],
)

# Gestión de caché
app.include_router(
    cache.router,
    prefix="/api/v1/cache",
    tags=["Cache"],
)

# ── Root Endpoint ────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    """
    Endpoint raíz con información de la API.
    """
    return {
        "name": "RAG Legal Colombiano API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "query": "/api/v1/query",
            "ingestion": "/api/v1/ingestion",
            "cache": "/api/v1/cache",
        }
    }


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Hot reload en desarrollo
        log_level="info",
    )
