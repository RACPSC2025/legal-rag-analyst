"""
Schemas de salida legal estructurada — Analista Legal v2
────────────────────────────────────────────────────────────
Define la estructura de las respuestas, citas y requisitos.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class Citation(BaseModel):
    """Representa una cita textual verificada de un documento legal."""
    article_id: str = Field(description="Identificador del artículo o sección (ej: Art. 123)")
    source: str = Field(description="Nombre del documento fuente")
    page: Optional[str] = Field(None, description="Página del documento")
    text: str = Field(description="Fragmento de texto exacto extraído")
    verified: bool = Field(default=False, description="Indica si la cita fue verificada contra el original")

class LegalRequirement(BaseModel):
    """Representa una obligación o requisito identificado en la norma."""
    description: str = Field(description="Descripción clara de la obligación")
    deadline: Optional[str] = Field(None, description="Plazo o término legal para cumplimiento")
    responsible: Optional[str] = Field(None, description="Entidad o persona responsable")

class LegalResponse(BaseModel):
    """Respuesta estructurada final del Analista Legal RAG."""
    answer: str = Field(description="Respuesta detallada a la consulta jurídica")
    citations: List[Citation] = Field(default_factory=list, description="Lista de citas que sustentan la respuesta")
    requirements: List[LegalRequirement] = Field(default_factory=list, description="Requisitos detectados")
    confidence_score: float = Field(default=0.0, description="Nivel de confianza (0.0-1.0)")
    limitations: Optional[str] = Field(None, description="Advertencias o limitaciones del análisis")
