"""
Schemas de salida para nodos del grafo — Analista Legal v2
────────────────────────────────────────────────────────────
Estructuras para clasificación binaria y evaluación factual.
"""

from pydantic import BaseModel, Field

class GradeOutput(BaseModel):
    """Output del nodo grade_documents."""
    score: str = Field(description="'si' si el documento es relevante, 'no' en caso contrario.")
    razon: str = Field(description="Explicación breve del veredicto.")

class HallucinationOutput(BaseModel):
    """Output del nodo check_hallucination."""
    score: str = Field(description="'limpio' o 'alucinacion'")
    razon: str = Field(description="Explicación de la evaluación.")
