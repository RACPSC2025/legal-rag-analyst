"""
Ingestion Routes — Endpoints de Ingesta de Documentos
──────────────────────────────────────────────────────
Endpoints para gestionar la ingesta de documentos PDF/MD al sistema.

Endpoints:
  • POST /ingestion        - Iniciar ingesta de documentos
  • GET /ingestion/status  - Consultar estado de un job

Autor: Fenix Tech Líder
Fecha: 2026-04-27
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from api.schemas.request_models import IngestionRequest, IngestionStatusRequest
from api.schemas.response_models import IngestionResponse, ErrorResponse
from src.ingestion.pipeline import run_ingestion_pipeline

router = APIRouter()

# Almacenamiento en memoria de jobs (en producción usar Redis/DB)
_ingestion_jobs: Dict[str, Dict[str, Any]] = {}


# ── Helper Functions ─────────────────────────────────────────────────────────

def _generate_job_id() -> str:
    """Genera un ID único para el job de ingesta."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"ing_{timestamp}_{unique_id}"


def _run_ingestion_background(job_id: str, request: IngestionRequest):
    """
    Ejecuta la ingesta en background.
    
    Actualiza el estado del job en _ingestion_jobs durante el proceso.
    """
    try:
        # Actualizar estado a processing
        _ingestion_jobs[job_id]["status"] = "processing"
        _ingestion_jobs[job_id]["started_at"] = time.time()
        
        # Ejecutar pipeline de ingesta
        result = run_ingestion_pipeline(
            paths=request.file_paths,
            force_reconvert=request.force_reconvert,
            collection_name=request.collection_name,
        )
        
        # Actualizar estado según resultado
        if result.get("status") == "success":
            _ingestion_jobs[job_id]["status"] = "completed"
            _ingestion_jobs[job_id]["processed_files"] = result.get("processed_files", [])
            _ingestion_jobs[job_id]["total_chunks"] = result.get("total_chunks", 0)
            _ingestion_jobs[job_id]["indexed_chunks"] = result.get("indexed_chunks", 0)
            _ingestion_jobs[job_id]["errors"] = result.get("errors", [])
        else:
            _ingestion_jobs[job_id]["status"] = "failed"
            _ingestion_jobs[job_id]["errors"] = result.get("errors", ["Error desconocido"])
        
        # Calcular duración
        completed_at = time.time()
        started_at = _ingestion_jobs[job_id]["started_at"]
        _ingestion_jobs[job_id]["completed_at"] = completed_at
        _ingestion_jobs[job_id]["duration_seconds"] = round(completed_at - started_at, 2)
    
    except Exception as e:
        # Manejar errores inesperados
        _ingestion_jobs[job_id]["status"] = "failed"
        _ingestion_jobs[job_id]["errors"] = [f"Error crítico: {str(e)}"]
        _ingestion_jobs[job_id]["completed_at"] = time.time()


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar Ingesta de Documentos",
    description=(
        "Inicia un job de ingesta de documentos PDF o Markdown. "
        "El proceso se ejecuta en background y retorna un job_id para consultar el estado."
    ),
    responses={
        202: {"description": "Job de ingesta iniciado exitosamente"},
        400: {"model": ErrorResponse, "description": "Request inválido"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
    },
)
async def ingest_documents(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
) -> IngestionResponse:
    """
    Endpoint para iniciar ingesta de documentos.
    
    Flujo:
      1. Genera job_id único
      2. Valida que los archivos existan (opcional)
      3. Registra el job en estado 'queued'
      4. Ejecuta la ingesta en background
      5. Retorna job_id para consultar estado
    
    Args:
        request: IngestionRequest con rutas de archivos.
        background_tasks: FastAPI background tasks manager.
        
    Returns:
        IngestionResponse con job_id y estado inicial.
        
    Raises:
        HTTPException: Si ocurre un error durante la validación.
    """
    job_id = _generate_job_id()
    
    try:
        # Registrar job en estado queued
        _ingestion_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "file_paths": request.file_paths,
            "force_reconvert": request.force_reconvert,
            "collection_name": request.collection_name,
            "processed_files": [],
            "failed_files": [],
            "total_chunks": 0,
            "indexed_chunks": 0,
            "errors": [],
            "started_at": None,
            "completed_at": None,
            "duration_seconds": None,
        }
        
        # Ejecutar ingesta en background
        background_tasks.add_task(
            _run_ingestion_background,
            job_id,
            request,
        )
        
        return IngestionResponse(
            job_id=job_id,
            status="queued",
            processed_files=[],
            failed_files=[],
            total_chunks=0,
            indexed_chunks=0,
            errors=[],
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando ingesta: {str(e)}",
        )


@router.get(
    "/status/{job_id}",
    response_model=IngestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar Estado de Ingesta",
    description=(
        "Consulta el estado de un job de ingesta usando su job_id. "
        "Retorna información detallada del progreso y resultados."
    ),
    responses={
        200: {"description": "Estado del job recuperado exitosamente"},
        404: {"model": ErrorResponse, "description": "Job no encontrado"},
    },
)
async def get_ingestion_status(job_id: str) -> IngestionResponse:
    """
    Endpoint para consultar estado de ingesta.
    
    Args:
        job_id: ID del job de ingesta.
        
    Returns:
        IngestionResponse con estado actual del job.
        
    Raises:
        HTTPException: Si el job_id no existe.
    """
    if job_id not in _ingestion_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job no encontrado: {job_id}",
        )
    
    job_data = _ingestion_jobs[job_id]
    
    # Convertir timestamps a datetime si existen
    from datetime import datetime
    
    started_at = None
    completed_at = None
    
    if job_data["started_at"]:
        started_at = datetime.fromtimestamp(job_data["started_at"])
    
    if job_data["completed_at"]:
        completed_at = datetime.fromtimestamp(job_data["completed_at"])
    
    return IngestionResponse(
        job_id=job_data["job_id"],
        status=job_data["status"],
        processed_files=job_data["processed_files"],
        failed_files=job_data["failed_files"],
        total_chunks=job_data["total_chunks"],
        indexed_chunks=job_data["indexed_chunks"],
        errors=job_data["errors"],
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=job_data["duration_seconds"],
    )


@router.get(
    "/jobs",
    summary="Listar Jobs de Ingesta",
    description="Lista todos los jobs de ingesta registrados (últimos 50).",
)
async def list_ingestion_jobs():
    """
    Endpoint para listar jobs de ingesta.
    
    Returns:
        Lista de jobs con información resumida.
    """
    # Ordenar por timestamp descendente (más recientes primero)
    sorted_jobs = sorted(
        _ingestion_jobs.values(),
        key=lambda x: x["job_id"],
        reverse=True,
    )
    
    # Limitar a últimos 50
    recent_jobs = sorted_jobs[:50]
    
    # Resumir información
    summary = []
    for job in recent_jobs:
        summary.append({
            "job_id": job["job_id"],
            "status": job["status"],
            "file_count": len(job["file_paths"]),
            "processed_files": len(job["processed_files"]),
            "total_chunks": job["total_chunks"],
            "indexed_chunks": job["indexed_chunks"],
            "errors_count": len(job["errors"]),
            "duration_seconds": job["duration_seconds"],
        })
    
    return {
        "total_jobs": len(_ingestion_jobs),
        "recent_jobs": summary,
    }
