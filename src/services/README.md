# 🛠️ Services Module

## Descripción General

El módulo **Services** proporciona servicios especializados de alto nivel para el sistema RAG Legal. Incluye verificación de citas, conversión de documentos a Markdown (Golden MD Library), análisis especializado y servicios de procesamiento de PDFs.

## 📦 Componentes

### 1. **citation_verifier.py**
**Propósito**: Verificación automática de citas legales

**Características**:
- Extrae citas del texto generado estructurado
- **Fuzzy Matching**: Verifica contra documentos fuente usando `SequenceMatcher`
- **Similitud Adaptativa**: Threshold configurable (default 0.85)
- Detecta citas inventadas o incorrectas incluso con variaciones tipográficas

**Uso**:
```python
from src.services.citation_verifier import CitationVerifier

verifier = CitationVerifier()
citation = Citation(
    article_id="Art. 2.2.2.4.11",
    source="Decreto 1082",
    page="45",
    text="Los negociadores son..."
)

is_verified, score = verifier.verify_citation(citation, context)
print(f"Verificada: {is_verified}, Score: {score:.2f}")
```

**Ventajas**:
- ✅ **Robustez**: Valida citas con errores menores de puntuación/transcripción
- ✅ **Confiabilidad**: Evita alucinaciones en referencias legales
- ✅ **Transparencia**: Proporciona scores de similitud realistas

---

### 2. **markdown_service.py**
**Propósito**: Golden Markdown Library - Conversión y cache de documentos

**Arquitectura**:
```
PDF → Quality Detection → Loader Selection → Markdown Conversion → Cache Storage
```

**Componentes**:

#### **A. MarkdownLibrary**
Gestiona el almacenamiento persistente de conversiones:
```python
class MarkdownLibrary:
    """
    Biblioteca de documentos Markdown con metadata.
    
    Estructura:
    data/markdown_library/
    ├── decreto_1082_2015.md
    ├── decreto_1082_2015.json  # Metadata
    └── ...
    """
```

#### **B. MarkdownConversionService**
Servicio de conversión con cache inteligente:
```python
result = MarkdownConversionService.convert_and_save(
    pdf_path="decreto_1082.pdf",
    use_ocr=False,
    force_reconvert=False
)
# Returns: {"md_path": Path, "tool": "docling", "cached": True}
```

**Ventajas**:
- 💾 **Cache permanente**: No reprocesa documentos
- 🎯 **Selección automática**: Elige mejor loader
- 📊 **Metadata rica**: Tracking completo
- 💰 **Ahorro 70% tokens**: Markdown optimizado

---

### 3. **pdf_direct_service.py**
**Propósito**: Servicio directo de procesamiento de PDFs

**Características**:
- Extracción rápida de texto
- Metadata básica
- Sin conversión a Markdown
- Útil para análisis rápido

**Uso**:
```python
from src.services.pdf_direct_service import extract_text

text, metadata = extract_text("documento.pdf")
```

---

### 4. **specialized_analysis.py**
**Propósito**: Análisis especializado de documentos legales

**Funcionalidades**:
- **Extracción de entidades**: Artículos, leyes, decretos
- **Análisis de referencias**: Referencias cruzadas
- **Detección de tablas**: Identificación y extracción
- **Clasificación**: Tipo de documento normativo

**Uso**:
```python
from src.services.specialized_analysis import analyze_legal_document

analysis = analyze_legal_document(text)
print(analysis["entities"])      # Entidades extraídas
print(analysis["references"])    # Referencias cruzadas
print(analysis["tables"])        # Tablas detectadas
```

**Ventajas**:
- 🎯 **Especializado**: Optimizado para normativa colombiana
- 📊 **Metadata rica**: Información estructurada
- 🔍 **Análisis profundo**: Más allá de texto plano

---

## 🎯 Ventajas del Módulo

### Calidad
- ✅ **Verificación automática**: Citas validadas
- 📝 **Conversión precisa**: Golden MD Library
- 🎯 **Análisis especializado**: Dominio legal

### Eficiencia
- 💾 **Cache inteligente**: No reprocesa
- ⚡ **Servicios rápidos**: Optimizados
- 💰 **Ahorro de costos**: Menos llamadas a API

### Mantenibilidad
- 🔌 **Modular**: Servicios independientes
- 📚 **Reutilizable**: Fácil integración
- 🧪 **Testeable**: Interfaces claras

---

## 🔧 Uso

### Conversión con Golden MD Library

```python
from src.services.markdown_service import MarkdownConversionService

# Conversión automática con cache
result = MarkdownConversionService.convert_and_save(
    pdf_path="decreto_1082.pdf",
    use_ocr=False,
    force_reconvert=False
)

if result["cached"]:
    print("Usando versión cacheada")
else:
    print(f"Convertido con {result['tool']}")

# Leer Markdown
md_content = result["md_path"].read_text()
```

### Verificación de Citas

```python
from src.services.citation_verifier import CitationVerifier
from src.schemas.legal_output import Citation

verifier = CitationVerifier()

# Extraer y verificar citas
citations = extract_citations(generated_text)
for cit in citations:
    is_valid, score = verifier.verify_citation(cit, source_docs)
    if not is_valid:
        print(f"⚠️ Cita no verificada: {cit.article_id}")
```

---

**Última actualización**: 2026-04-28
**Versión**: 2.0.0
**Mantenedor**: Equipo de Services
