# 📋 Schemas Module

## Descripción General

El módulo **Schemas** define los modelos de datos estructurados utilizados en todo el sistema RAG Legal. Utiliza Pydantic para validación automática de tipos y generación de documentación.

## 📦 Componentes

### 1. **graph_outputs.py**
**Propósito**: Outputs estructurados de los nodos del grafo

#### **A. GradeOutput**
```python
class GradeOutput(BaseModel):
    """Output del nodo grade_documents"""
    score: Literal["si", "no"]
    razon: str
    
    # Ejemplo
    {
        "score": "si",
        "razon": "El fragmento contiene la tabla de negociadores solicitada"
    }
```

**Uso en nodos**:
```python
structured_llm = llm.with_structured_output(GradeOutput)
result = structured_llm.invoke({"question": q, "document": doc})
if result.score == "si":
    relevant_docs.append(doc)
```

#### **B. HallucinationOutput**
```python
class HallucinationOutput(BaseModel):
    """Output del nodo check_hallucination"""
    score: Literal["limpio", "alucinacion"]
    razon: str
    
    # Ejemplo
    {
        "score": "limpio",
        "razon": "Todas las afirmaciones están respaldadas por los documentos"
    }
```

**Ventajas**:
- ✅ **Validación automática**: Pydantic valida tipos
- 📝 **Documentación**: Schemas auto-documentados
- 🎯 **Type safety**: Autocompletado en IDE
- 🔒 **Consistencia**: Formato uniforme

---

### 2. **legal_output.py**
**Propósito**: Modelos específicos del dominio legal

#### **A. Citation**
```python
class Citation(BaseModel):
    """Cita legal verificable"""
    article_id: str              # "Art. 2.2.2.4.11"
    source: str                  # "Decreto 1082 de 2015"
    page: Optional[str]          # "45"
    text: str                    # Texto citado
    verified: bool = False       # ¿Verificada?
    confidence: float = 0.0      # Score de confianza
    
    # Ejemplo
    {
        "article_id": "Art. 2.2.2.4.11",
        "source": "Decreto 1082 de 2015",
        "page": "45",
        "text": "Los negociadores son...",
        "verified": True,
        "confidence": 0.95
    }
```

#### **B. LegalDocument**
```python
class LegalDocument(BaseModel):
    """Documento legal estructurado"""
    title: str
    document_type: str           # "decreto", "ley", "resolución"
    number: str                  # "1082"
    year: int                    # 2015
    issuing_entity: str          # "Ministerio de Comercio"
    summary: Optional[str]
    articles: List[Article]
    
    # Ejemplo
    {
        "title": "Decreto Único Reglamentario",
        "document_type": "decreto",
        "number": "1082",
        "year": 2015,
        "issuing_entity": "Presidencia de la República",
        "articles": [...]
    }
```

#### **C. Article**
```python
class Article(BaseModel):
    """Artículo de normativa"""
    article_id: str              # "2.2.2.4.11"
    title: str                   # "Negociadores"
    content: str                 # Texto completo
    chapter: Optional[str]       # "Capítulo 2"
    section: Optional[str]       # "Sección 4"
    page: Optional[int]          # 45
    
    # Ejemplo
    {
        "article_id": "2.2.2.4.11",
        "title": "Negociadores",
        "content": "Los negociadores son...",
        "chapter": "Capítulo 2",
        "section": "Sección 4",
        "page": 45
    }
```

#### **D. LegalQuery**
```python
class LegalQuery(BaseModel):
    """Query legal estructurada"""
    question: str
    query_type: str              # "article", "procedure", "requirement"
    entities: List[str]          # Entidades mencionadas
    article_refs: List[str]      # Referencias a artículos
    
    # Ejemplo
    {
        "question": "¿Cuáles son los requisitos del Art. 2.2.2.4.11?",
        "query_type": "requirement",
        "entities": ["negociadores"],
        "article_refs": ["2.2.2.4.11"]
    }
```

#### **E. LegalResponse**
```python
class LegalResponse(BaseModel):
    """Respuesta legal completa"""
    answer: str
    citations: List[Citation]
    sources: List[str]
    confidence: float
    hallucination_score: float
    attempts: int
    
    # Ejemplo
    {
        "answer": "Los requisitos son...",
        "citations": [...],
        "sources": ["Decreto 1082 de 2015"],
        "confidence": 0.92,
        "hallucination_score": 0.0,
        "attempts": 1
    }
```

**Ventajas**:
- 📊 **Estructura clara**: Datos organizados
- ✅ **Validación**: Tipos y valores validados
- 🔍 **Trazabilidad**: Metadata completa
- 🎯 **Dominio específico**: Optimizado para legal

---

## 🎯 Ventajas del Módulo

### Type Safety
- ✅ **Validación automática**: Pydantic valida en runtime
- 🎯 **Autocompletado**: IDE sugiere campos
- 🔒 **Prevención de errores**: Tipos incorrectos fallan temprano

### Documentación
- 📝 **Auto-documentada**: Schemas generan docs
- 💡 **Ejemplos claros**: Fácil entender estructura
- 📚 **Contratos explícitos**: Interfaces claras

### Mantenibilidad
- 🔄 **Evolución controlada**: Cambios rastreables
- 🧪 **Testeable**: Fácil crear fixtures
- 🔌 **Reutilizable**: Schemas compartidos

---

## 🔧 Uso

### Validación de Datos

```python
from src.schemas.legal_output import Citation

# Crear cita con validación
citation = Citation(
    article_id="Art. 2.2.2.4.11",
    source="Decreto 1082",
    page="45",
    text="Los negociadores son...",
    verified=True,
    confidence=0.95
)

# Validación automática
try:
    invalid = Citation(
        article_id=123,  # ❌ Debe ser string
        source="Decreto"
    )
except ValidationError as e:
    print(e)
```

### Serialización

```python
# A dict
citation_dict = citation.dict()

# A JSON
citation_json = citation.json()

# Desde dict
citation = Citation(**data)

# Desde JSON
citation = Citation.parse_raw(json_string)
```

### Uso en Nodos

```python
from src.schemas.graph_outputs import GradeOutput

# Structured output con LLM
structured_llm = llm.with_structured_output(GradeOutput)
result: GradeOutput = structured_llm.invoke(prompt)

# Type safety garantizado
if result.score == "si":  # ✅ IDE sabe que es Literal["si", "no"]
    print(result.razon)   # ✅ IDE sabe que es str
```

---

## 📚 Mejores Prácticas

1. **Siempre usar Pydantic**: Para cualquier estructura de datos
2. **Documentar campos**: Usar `Field(description="...")`
3. **Validadores custom**: Para lógica de negocio
4. **Ejemplos en docstrings**: Facilita comprensión
5. **Versionado**: Mantener compatibilidad hacia atrás

---

**Última actualización**: 2026-04-28
**Versión**: 2.0.0
**Mantenedor**: Equipo de Schemas
