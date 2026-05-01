"""
Schemas de salida legal estructurada — Fénix Legal v2.5
────────────────────────────────────────────────────────────
Define el contrato de datos para respuestas con auditoría,
citaciones verificables y metadatos de rendimiento.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import re

class LegalCitation(BaseModel):
    """
    Representa una cita textual verificada extraída de la normativa colombiana.
    
    Este modelo es el pilar de la 'Generación Verificable', permitiendo 
    trazar cada afirmación del modelo a un artículo específico.
    """
    article_id: str = Field(
        ..., 
        description="Identificador jerárquico del artículo (ej: 2.2.3.2.9.1)",
        examples=["Art. 1", "2.2.3.2.9.1", "Parágrafo 1"]
    )
    source_doc: str = Field(
        ..., 
        description="Nombre oficial del documento fuente",
        examples=["Decreto 1072 de 2015", "Ley 99 de 1993"]
    )
    quote: str = Field(
        ..., 
        description="Fragmento de texto literal extraído del documento",
        min_length=10
    )
    relevance_score: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Puntuación de relevancia del fragmento para la respuesta"
    )
    is_verified: bool = Field(
        default=False, 
        description="Indica si el motor de auditoría validó la existencia y exactitud de la cita"
    )
    verification_note: Optional[str] = Field(
        default=None, 
        description="Detalle técnico del proceso de verificación (ej: match 95%)"
    )
    page_number: Optional[int] = Field(
        default=None, 
        description="Número de página en el PDF original si está disponible"
    )

    @field_validator("article_id")
    @classmethod
    def validate_article_format(cls, v: str) -> str:
        """
        Valida y normaliza formatos de artículos en la normativa colombiana.
        """
        if not v or len(v.strip()) == 0:
            raise ValueError("El identificador del artículo no puede estar vacío")
        
        v_clean = v.strip()
        
        patterns = [
            # Formato DUR (Decimal profundo: 2.2.1...)
            r'^\d+(\.\d+)+$',
            # Formato Artículo estándar (Art. 1, Art 1, Artículo 1)
            r'^(?i:Art[íi]culo|Art\.?)\s+\d+[a-zA-Z-]*$',
            # Parágrafos
            r'^(?i:Par[áa]grafo)\s+\d*$',
            # Secciones generales
            r'^(?i:T[íi]tulo|Cap[íi]tulo|Secci[óo]n)\s+[A-Z0-9VIXLC]*$'
        ]
        
        if not any(re.match(p, v_clean) for p in patterns):
            raise ValueError(f"El identificador del artículo '{v_clean}' no coincide con ningún formato legal reconocido.")
                
        return v_clean

    @field_validator("source_doc")
    @classmethod
    def validate_source_not_placeholder(cls, v: str) -> str:
        """Evita que el modelo use placeholders genéricos como 'documento'."""
        placeholders = ["documento", "fuente", "archivo", "pdf", "unknown"]
        if v.lower().strip() in placeholders:
            raise ValueError(f"El nombre del documento fuente no puede ser un placeholder: {v}")
        return v.strip()

    @field_validator("quote")
    @classmethod
    def validate_quote_integrity(cls, v: str) -> str:
        """Asegura que la cita no esté truncada de forma inválida."""
        if "[...]" in v and len(v) < 50:
            raise ValueError("La cita parece estar truncada de forma inválida o es demasiado corta.")
        return v

class LegalRequirement(BaseModel):
    """Representa una obligación o requisito identificado en la norma."""
    description: str = Field(..., description="Descripción clara de la obligación")
    deadline: Optional[str] = Field(None, description="Plazo o término legal para cumplimiento")
    responsible: Optional[str] = Field(None, description="Entidad o persona responsable (ej: ANLA, Empleador)")

class NumericDiscrepancy(BaseModel):
    """Representa una discrepancia detectada entre la respuesta y la fuente original."""
    field_name: str = Field(..., description="Nombre del campo (ej: tarifa, plazo)")
    expected_value: Union[str, float, int] = Field(..., description="Valor encontrado en la fuente")
    found_value: Union[str, float, int] = Field(..., description="Valor generado por el LLM")
    data_type: str = Field(..., description="Tipo de dato (currency, percentage, date, etc.)")
    severity: str = Field(default="high", description="Severidad de la discrepancia")

class LegalAnswer(BaseModel):
    """
    Respuesta estructurada final del Analista Legal RAG con auditoría integrada.
    """
    answer: str = Field(
        ..., 
        description="Respuesta jurídica detallada en formato Markdown"
    )
    citations: List[LegalCitation] = Field(
        default_factory=list, 
        description="Lista de evidencias textuales que sustentan la respuesta"
    )
    requirements: List[LegalRequirement] = Field(
        default_factory=list, 
        description="Lista de obligaciones detectadas en el análisis"
    )
    numeric_discrepancies: List[NumericDiscrepancy] = Field(
        default_factory=list,
        description="Discrepancias numéricas detectadas por el Numeric Grader"
    )
    confidence_score: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Confianza media ponderada"
    )
    requires_human_review: bool = Field(
        default=False, 
        description="Bandera de seguridad"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Metadatos técnicos: tokens, latencia, modelos usados"
    )

    @model_validator(mode='after')
    def compute_metrics(self) -> 'LegalAnswer':
        """
        Calcula automáticamente el confidence_score y el flag de revisión humana.
        """
        # Si hay discrepancias numéricas, se requiere revisión humana sí o sí
        if self.numeric_discrepancies:
            self.requires_human_review = True
            
        # Calcular confianza basada en citas verificadas
        if not self.citations:
            self.confidence_score = 0.0
        else:
            verified_citations = [c for c in self.citations if c.is_verified]
            
            if verified_citations:
                # Promedio de relevancia de ONLY verified citations
                self.confidence_score = sum(c.relevance_score for c in verified_citations) / len(verified_citations)
            else:
                self.confidence_score = 0.0
                
            # Si hay alguna cita no verificada, marcamos para revisión
            if any(not c.is_verified for c in self.citations):
                self.requires_human_review = True
                
        return self

    def verification_summary(self) -> Dict[str, Any]:
        """Genera un resumen estructurado del estado de verificación."""
        failed = [
            {"article_id": c.article_id, "reason": c.verification_note or "No coincidente"}
            for c in self.citations if not c.is_verified
        ]
        return {
            "verification_passed": len(failed) == 0 and not self.numeric_discrepancies,
            "verified_count": sum(1 for c in self.citations if c.is_verified),
            "failed_citations": failed,
            "numeric_discrepancies_count": len(self.numeric_discrepancies)
        }

# Aliases para compatibilidad
class Citation(LegalCitation): pass
class LegalResponse(LegalAnswer): pass
