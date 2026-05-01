"""
Response models v2 — Fénix Legal v2.5 Fase 3
Con anotaciones OpenAPI completas para generación de cliente TypeScript.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ejemplos de dominio — reutilizados en múltiples schemas
# ---------------------------------------------------------------------------

_EXAMPLE_CITATION = {
    "article_id": "2.2.1.4",
    "source_doc": "Decreto 1072 de 2015",
    "quote": (
        "Las corporaciones autónomas regionales tendrán a su cargo "
        "la ejecución de las políticas, planes, programas y proyectos "
        "sobre medio ambiente y recursos naturales renovables."
    ),
    "relevance_score": 0.934,
    "is_verified": True,
    "verification_note": "Cita verificada por coincidencia exacta.",
}

_EXAMPLE_DISCREPANCY = {
    "field_name": "tarifa_inscripcion",
    "expected_value": "$1,000,000 COP",
    "found_value": "$1,500,000 COP",
    "source_table": "Tabla 3.2 - Tarifas vigentes",
    "data_type": "currency",
}

_EXAMPLE_VERIFY_META = {
    "verified_count": 3,
    "failed_count": 0,
    "duration_ms": 187.4,
    "attempt": 1,
}


# ---------------------------------------------------------------------------
# CitationOut
# ---------------------------------------------------------------------------

class CitationOut(BaseModel):
    """Representación pública de una cita legal verificada."""

    article_id: str = Field(
        description=(
            "Identificador del artículo. Formato DUR numérico (`2.2.1.4`) "
            "o abreviado (`Art. 15`). Coincide con los metadatos del chunk recuperado."
        ),
        examples=["2.2.1.4", "2.2.3.2.9.1", "Art. 15"],
    )
    source_doc: str = Field(
        description="Nombre completo del decreto o norma fuente.",
        examples=["Decreto 1072 de 2015", "Ley 99 de 1993"],
    )
    quote: str = Field(
        description=(
            "Fragmento textual extraído literalmente del documento. "
            "El Citation Verifier confirma que este texto existe en el corpus."
        ),
        examples=[_EXAMPLE_CITATION["quote"]],
    )
    relevance_score: float = Field(
        description=(
            "Score de relevancia semántica asignado por el retriever. "
            "Rango: 0.0 (irrelevante) – 1.0 (máxima relevancia)."
        ),
        ge=0.0, le=1.0,
        examples=[0.934, 0.812],
    )
    is_verified: bool = Field(
        description=(
            "**True** si el Citation Verifier confirmó que:\n"
            "1. El `article_id` existe en los documentos recuperados.\n"
            "2. El `quote` coincide con el texto fuente (fuzzy ≥ 85%).\n\n"
            "**False** si la verificación falló y la respuesta fue marcada "
            "para revisión humana (`requires_human_review: true`)."
        ),
        examples=[True],
    )
    verification_note: str = Field(
        description=(
            "Detalle del resultado de verificación. Si `is_verified: false`, "
            "contiene el motivo del fallo y la similitud obtenida."
        ),
        examples=[
            "Cita verificada por coincidencia exacta.",
            "Texto no coincide con la fuente (similitud: 72%, umbral: 85%).",
        ],
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# NumericDiscrepancyOut
# ---------------------------------------------------------------------------

class NumericDiscrepancyOut(BaseModel):
    """
    Discrepancia detectada entre un valor numérico en la respuesta
    y el valor original en las tablas del corpus.

    Presencia de este objeto implica `requires_human_review: true`.
    """

    field_name: str = Field(
        description="Nombre del campo o concepto donde se detectó la discrepancia.",
        examples=["tarifa_inscripcion", "plazo_dias", "multa_maxima"],
    )
    expected_value: str = Field(
        description="Valor que aparece en la tabla fuente original.",
        examples=["$1,000,000 COP", "30 días hábiles", "500 SMMLV"],
    )
    found_value: str = Field(
        description="Valor que el LLM incluyó en su respuesta.",
        examples=["$1,500,000 COP", "30 días", "300 SMMLV"],
    )
    source_table: str = Field(
        description="Título o identificador de la tabla donde se encontró el valor correcto.",
        examples=["Tabla 3.2 - Tarifas vigentes", "Tabla 1.1 - Plazos legales"],
    )
    data_type: str = Field(
        description=(
            "Tipo de dato numérico detectado. Determina la tolerancia aplicada:\n"
            "- `currency`: tolerancia $0.01 (redondeo)\n"
            "- `percentages`: tolerancia 0.1%\n"
            "- `days` / `months` / `years` / `smmlv`: tolerancia 0 (exacto)"
        ),
        examples=["currency", "days", "percentages", "smmlv"],
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# VerificationMetaOut
# ---------------------------------------------------------------------------

class VerificationMetaOut(BaseModel):
    """
    Métricas internas del proceso de verificación.
    Útil para monitoreo, debugging y observabilidad en el frontend.
    """

    verified_count: int = Field(
        description="Número de citas que pasaron la verificación automática.",
        examples=[3],
    )
    failed_count: int = Field(
        description=(
            "Número de citas que fallaron la verificación. "
            "Si > 0 y `requires_human_review: false`, "
            "la respuesta fue corregida automáticamente en un reintento."
        ),
        examples=[0],
    )
    duration_ms: float = Field(
        description=(
            "Tiempo de ejecución del proceso de verificación en milisegundos. "
            "NFR-01: debe ser < 500ms. Si supera 400ms se registra una alerta."
        ),
        examples=[187.4],
    )
    attempt: int = Field(
        description=(
            "Número de intento en el que se obtuvo la respuesta final. "
            "`1` = sin reintentos. `2` o `3` = self-correction activado."
        ),
        examples=[1, 2],
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# LegalAnswerResponse — response model raíz
# ---------------------------------------------------------------------------

class LegalAnswerResponse(BaseModel):
    """
    Respuesta verificada del agente Fénix Legal.

    ## Campos clave

    - `answer`: texto en Markdown listo para renderizar.
    - `citations`: citas auditadas con score de confianza individual.
    - `confidence_score`: media ponderada de las citas verificadas (0.0–1.0).
    - `requires_human_review`: **siempre verificar este flag** antes de
      mostrar la respuesta al usuario final.
    - `numeric_discrepancies`: lista vacía en respuestas correctas.

    ## Interpretación de `requires_human_review`

    | `requires_human_review` | `confidence_score` | Acción recomendada |
    |-------------------------|--------------------|--------------------|
    | `false` | > 0.85 | Mostrar directamente |
    | `false` | 0.60–0.85 | Mostrar con disclaimer de confianza media |
    | `true`  | cualquiera | Mostrar con banner de revisión pendiente |

    ## Generación del cliente TypeScript

```bash
    npx openapi-typescript /api/openapi.json -o src/api/types.ts
    # Genera: LegalAnswerResponse, CitationOut, NumericDiscrepancyOut...
```
    """

    request_id: str = Field(
        description=(
            "ID único del request para correlación de logs. "
            "Propagado desde el header `X-Request-ID` si lo envía el cliente, "
            "o generado automáticamente con UUID v4."
        ),
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )
    answer: str = Field(
        description=(
            "Respuesta jurídica en formato **Markdown**. "
            "Contiene encabezados, listas y referencias a los artículos citados. "
            "Renderizar con un parser Markdown en el frontend."
        ),
        examples=[(
            "## Respuesta\n\n"
            "Según el **artículo 2.2.1.4** del Decreto 1072 de 2015, "
            "las Corporaciones Autónomas Regionales (CAR) tienen a su cargo "
            "la ejecución de políticas ambientales en su jurisdicción.\n\n"
            "### Fuentes verificadas\n"
            "- Decreto 1072 de 2015, Art. 2.2.1.4"
        )],
    )
    citations: List[CitationOut] = Field(
        description=(
            "Lista de citas legales referenciadas en la respuesta. "
            "Todas las citas con `is_verified: true` han sido auditadas "
            "automáticamente contra el corpus documental."
        ),
        examples=[[_EXAMPLE_CITATION]],
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Media ponderada de `relevance_score` de las citas verificadas. "
            "`0.0` si no hay citas verificadas o la respuesta está en fallback."
        ),
        examples=[0.934, 0.0],
    )
    requires_human_review: bool = Field(
        description=(
            "**Flag crítico.** `true` cuando:\n"
            "- Una o más citas no superaron la verificación automática.\n"
            "- El Numeric Grader detectó discrepancias no resueltas.\n"
            "- El sistema entró en fallback tras 2 reintentos fallidos.\n\n"
            "Mostrar siempre un aviso visible al usuario cuando sea `true`."
        ),
        examples=[False, True],
    )
    numeric_discrepancies: List[NumericDiscrepancyOut] = Field(
        default_factory=list,
        description=(
            "Discrepancias detectadas entre valores en la respuesta "
            "y las tablas del corpus. Lista vacía en respuestas correctas."
        ),
        examples=[[], [_EXAMPLE_DISCREPANCY]],
    )
    verification_meta: Optional[VerificationMetaOut] = Field(
        default=None,
        description=(
            "Métricas del proceso de verificación. "
            "`null` si la respuesta no pasó por verificación "
            "(no debería ocurrir en v2)."
        ),
        examples=[_EXAMPLE_VERIFY_META],
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Respuesta verificada — happy path",
                    "description": (
                        "Respuesta con 3 citas verificadas, "
                        "sin discrepancias y confidence alto."
                    ),
                    "value": {
                        "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "answer": (
                            "## Respuesta\n\nSegún el **artículo 2.2.1.4** "
                            "del Decreto 1072 de 2015..."
                        ),
                        "citations": [_EXAMPLE_CITATION],
                        "confidence_score": 0.934,
                        "requires_human_review": False,
                        "numeric_discrepancies": [],
                        "verification_meta": _EXAMPLE_VERIFY_META,
                    },
                },
                {
                    "summary": "Fallback — revisión humana requerida",
                    "description": (
                        "Verificación fallida tras 2 reintentos. "
                        "La respuesta se entrega degradada con flag de revisión."
                    ),
                    "value": {
                        "request_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                        "answer": (
                            "## Respuesta\n\n⚠️ *Esta respuesta requiere "
                            "revisión humana antes de ser utilizada.*\n\n..."
                        ),
                        "citations": [{
                            **_EXAMPLE_CITATION,
                            "is_verified": False,
                            "verification_note": (
                                "Texto no coincide con la fuente "
                                "(similitud: 72%, umbral: 85%)."
                            ),
                        }],
                        "confidence_score": 0.0,
                        "requires_human_review": True,
                        "numeric_discrepancies": [_EXAMPLE_DISCREPANCY],
                        "verification_meta": {
                            **_EXAMPLE_VERIFY_META,
                            "verified_count": 0,
                            "failed_count": 1,
                            "attempt": 3,
                        },
                    },
                },
            ]
        },
    }

    @classmethod
    def from_legal_answer(
        cls,
        answer,
        request_id: str,
    ) -> "LegalAnswerResponse":
        verification = answer.metadata.get("verification", {})
        return cls(
            request_id=request_id,
            answer=answer.answer,
            citations=[
                CitationOut(
                    article_id=c.article_id,
                    source_doc=c.source_doc,
                    quote=c.quote,
                    relevance_score=c.relevance_score,
                    is_verified=c.is_verified,
                    verification_note=c.verification_note,
                )
                for c in answer.citations
            ],
            confidence_score=answer.confidence_score,
            requires_human_review=answer.requires_human_review,
            numeric_discrepancies=[
                NumericDiscrepancyOut(
                    field_name=d.field_name,
                    expected_value=d.expected_value,
                    found_value=d.found_value,
                    source_table=d.source_table,
                    data_type=d.data_type,
                )
                for d in answer.numeric_discrepancies
            ],
            verification_meta=VerificationMetaOut(
                verified_count=verification.get("verified_count", 0),
                failed_count=verification.get("failed_count", 0),
                duration_ms=verification.get("duration_ms", 0.0),
                attempt=answer.metadata.get("attempt", 1),
            ) if verification else None,
        )


# ---------------------------------------------------------------------------
# Legacy Models (Backward Compatibility)
# ---------------------------------------------------------------------------

class CitationResponse(BaseModel):
    """Modelo legacy para citaciones."""
    article_id: str
    source: str
    page: Optional[int] = None
    verified: bool = False
    confidence: float = 1.0

class RequirementResponse(BaseModel):
    """Modelo legacy para requerimientos legales."""
    description: str
    deadline: Optional[str] = None
    responsible: Optional[str] = None

class QueryResponse(BaseModel):
    """Modelo legacy para respuestas de consulta individual."""
    query_id: str
    question: str
    answer: str
    sources: List[str] = []
    citations: List[CitationResponse] = []
    requirements: List[RequirementResponse] = []
    confidence_score: float = 0.5
    metadata: Dict[str, Any] = {}
    is_cached: bool = False
    cache_layer: Optional[str] = None

class BatchQueryResponse(BaseModel):
    """Respuesta para consultas en batch."""
    batch_id: str
    total_questions: int
    successful: int
    failed: int
    results: List[LegalAnswerResponse]
    total_latency_seconds: float

class ErrorResponse(BaseModel):
    """Modelo para respuestas de error."""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None

class IngestionResponse(BaseModel):
    """Respuesta para un job de ingesta."""
    job_id: str
    status: str
    processed_files: List[str] = []
    failed_files: List[str] = []
    total_chunks: int = 0
    indexed_chunks: int = 0
    errors: List[str] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

class CacheStatsResponse(BaseModel):
    """Estadísticas del sistema de caché."""
    total_requests: int
    total_hits: int
    total_misses: int
    hit_rate: str
    hits_by_layer: Dict[str, int]
    estimated_savings_usd: float

class CacheClearResponse(BaseModel):
    """Respuesta tras limpiar el caché."""
    status: str
    layers_cleared: List[str]
    entries_removed: int
    message: str

class HealthResponse(BaseModel):
    """Respuesta de salud del sistema."""
    status: str
    version: str
    components: Dict[str, str]
    uptime_seconds: float
