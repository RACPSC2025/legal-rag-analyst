"""
Módulo de Ingestión — Arquitectura Profesional "Golden Markdown"
───────────────────────────────────────────────────────────────
Punto de entrada unificado para el procesamiento de documentos legales.

Exporta:
- run_ingestion_pipeline  → El orquestador maestro (PDF -> Golden MD -> VectorDB)
- LoaderType              → Enumeración de motores disponibles
- get_loader              → Factory para motores de extracción
"""

from src.ingestion.factory import LoaderType, get_loader
from src.ingestion.pipeline import run_ingestion_pipeline

__all__ = [
    "run_ingestion_pipeline",
    "LoaderType",
    "get_loader",
]
