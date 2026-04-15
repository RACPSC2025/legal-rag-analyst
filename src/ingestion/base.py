"""
Base Ingestion — Contratos e Interfaces de Datos
─────────────────────────────────────────────────
Define la estructura de datos que viaja a través del pipeline.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class IngestionResult(BaseModel):
    """Objeto estandarizado de salida tras la extracción de un documento."""
    content: str = Field(..., description="Contenido textual extraído (Markdown o texto plano)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos extraídos del documento")
    source_path: str = Field(..., description="Ruta original del archivo fuente")
    tool_used: str = Field(..., description="Nombre de la herramienta que realizó la extracción")
    pages: int = Field(default=0, description="Número de páginas procesadas")
    success: bool = Field(True, description="Estado de la operación")
    error: Optional[str] = Field(None, description="Mensaje de error si falló")

class BasePDFLoader(ABC):
    """Interfaz obligatoria para todos los cargadores de la carpeta loaders/."""
    
    @abstractmethod
    def load(self, file_path: Path, **kwargs) -> IngestionResult:
        """Extrae el contenido de un archivo y devuelve un IngestionResult."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre identificativo del motor."""
        pass
