# Text Processors — Pipeline de Refinamiento Legal

## 📋 Descripción General

Este módulo contiene **4 procesadores especializados** que transforman el texto crudo extraído de PDFs en fragmentos estructurados, limpios y enriquecidos con metadata legal colombiana.

## 🎯 Procesadores Disponibles

### 1. **Adaptive Chunker** (`adaptive_chunker.py`)
**Segmentador inteligente que respeta la estructura jerárquica legal.**

#### Características:
- 🔥 **Jerarquía Legal**: Detecta y preserva Capítulos, Artículos, Parágrafos
- 🔥 **Contexto Inyectado**: Cada chunk conoce su ubicación en la norma
- 🔥 **Protección de Tablas**: No fragmenta tablas legales
- 🔥 **Separadores Inteligentes**: Prioriza divisiones naturales del documento
- 🔥 **Metadata Enriquecida**: Agrega información jerárquica automáticamente

#### Cuándo Usar:
- Después de extraer texto con cualquier loader
- Para normativa colombiana (Decretos, Leyes, Resoluciones)
- Cuando necesitas preservar la estructura legal
- Antes de generar embeddings

#### Configuración:
```python
from src.ingestion.processors.adaptive_chunker import get_adaptive_chunker

chunker = get_adaptive_chunker(
    chunk_size=1000,        # Tamaño objetivo de fragmentos
    chunk_overlap=200       # Solapamiento para contexto
)

# Procesar documentos
chunks = chunker.chunk(documents)
```

#### Patrones Legales Detectados:
```python
class LegalPatterns:
    CHAPTER = r"^(?:CAP[ÍI]TULO\s+(?:[IVXLCDM]+|\d+|[A-ZÁÉÍÓÚ]+))"
    SECTION = r"^(?:SECCI[ÓO]N\s+(?:[IVXLCDM]+|\d+))"
    ARTICLE = r"^(?:ART[ÍI]CULO\s+(?:\d+[°º]?|[IVXLCDM]+))"
    PARAGRAPH = r"^(?:PAR[ÁA]GRAFO\s+(?:\d+|[A-Z]+|ÚNICO))"
    RESOLVE = r"^(?:RESUELVE|CONSIDERANDO|ANTECEDENTES):?"
```

#### Niveles Jerárquicos:
- `chapter` → CAPÍTULO
- `section` → SECCIÓN
- `article` → ARTÍCULO
- `paragraph_legal` → PARÁGRAFO
- `header_block` → RESUELVE, CONSIDERANDO
- `text_block` → Texto general

#### Metadata Generada:
```python
{
    "chunk_index": 42,
    "legal_level": "article",
    "hierarchy": {
        "chapter": "CAPÍTULO 4",
        "section": "SECCIÓN 1",
        "article": "ARTÍCULO 2.2.4.1.2.3"
    },
    "article": "ARTÍCULO 2.2.4.1.2.3",  # Para filtros rápidos
    "chunk_size": 987
}
```

#### Separadores Jerárquicos (Orden de Prioridad):
```python
separators = [
    "\n## RESUELVE",
    "\n## CONSIDERANDO",
    "\n## ANTECEDENTES",
    "\n### CAPÍTULO",
    "\n### ARTÍCULO",
    "\n#### PARÁGRAFO",
    "\n\n\n",
    "\n\n",
    "\n",
    ". "
]
```

---

### 2. **Metadata Extractor** (`metadata_extractor.py`)
**Motor de extracción de inteligencia legal colombiana.**

#### Características:
- 🔍 **Entidades**: Identifica autoridades ambientales, ministerios, superintendencias
- 🔍 **Resoluciones**: Extrae números de resolución, decretos, leyes
- 🔍 **NITs**: Detecta números de identificación tributaria
- 🔍 **Fechas**: Normaliza fechas en múltiples formatos
- 🔍 **Jurisdicción**: Clasifica como nacional, departamental o municipal
- 🔍 **Tipo de Documento**: Identifica resolución, decreto, ley, circular, concepto

#### Cuándo Usar:
- Después del chunking
- Para enriquecer metadata de búsqueda
- Cuando necesitas filtros avanzados (por entidad, fecha, jurisdicción)
- Antes de indexar en vectorstore

#### Configuración:
```python
from src.ingestion.processors.metadata_extractor import get_metadata_extractor

extractor = get_metadata_extractor()

# Enriquecer documentos
enriched_docs = extractor.enrich_documents(chunks)
```

#### Patrones de Extracción:

**Resoluciones:**
```python
r"(?:Resolución|Circular|Decreto|Ley|Acuerdo)\s+(?:No\.?|Nro\.?|Número)\s*(\d+[\d\-\s]*)"
```

**Entidades:**
```python
- "Secretaría Distrital de Ambiente"
- "Corporación Autónoma Regional [...]"
- "ANLA", "SDA", "CAR"
- "Ministerio de [...]"
- "DIAN", "ICBF", "SENA"
```

**Fechas:**
```python
r"(\d{1,2})\s+de\s+(?:enero|febrero|marzo|...)\s+de\s+(\d{4})"
r"(\d{2}/\d{2}/\d{4})"
r"(\d{4}-\d{2}-\d{2})"
```

**NITs:**
```python
r"NIT\s*[:=]?\s*(\d{6,12}[-\s]?\d?)"
```

**Ubicaciones:**
```python
r"(?:municipio|ciudad) de ([A-Za-zÁÉÍÓÚáéíóú\s]+)"
r"departamento de ([A-Za-zÁÉÍÓÚáéíóú\s]+)"
```

#### Metadata Generada:
```python
{
    "source": "resolucion_001.pdf",
    "processed_at": "2026-04-28T10:30:00",
    "document_type": "resolucion",
    "jurisdiction": "nacional",
    "extraction_method": "metadata_extractor_v2_pro",
    "resolution_number": "001",
    "entity": "Secretaría Distrital de Ambiente",
    "issue_date": "15 de marzo de 2026",
    "nit": "899999034-1",
    "location": "Bogotá D.C.",
    "is_permanent_knowledge": True,
    "section": "PARTE_RESOLUTIVA"
}
```

#### Tipos de Documento:
- `resolucion` → Resoluciones administrativas
- `decreto` → Decretos generales
- `decreto_dur` → Decreto Único Reglamentario
- `ley` → Leyes de la República
- `circular` → Circulares normativas
- `concepto_juridico` → Conceptos jurídicos
- `otros_legales` → Otros documentos legales

#### Jurisdicciones:
- `nacional` → República de Colombia
- `departamental` → Gobernaciones
- `municipal` → Alcaldías
- `no_especificada` → Sin información

#### Secciones de Chunk:
- `PARTE_RESOLUTIVA` → Contiene "RESUELVE"
- `CONSIDERACIONES` → Contiene "CONSIDERANDO"
- `ARTICULADO` → Contiene "ARTÍCULO"
- `PARAGRAFO` → Contiene "PARÁGRAFO"
- `TABLA_DATOS` → Contiene tablas (detecta `|` y `-|-`)
- `CUERPO_TEXTO` → Texto general

---

### 3. **OCR Preprocessor** (`ocr_preprocessor.py`)
**Pipeline avanzado de preprocesamiento para PDFs escaneados.**

#### Características:
- 🖼️ **Deskew**: Corrección automática de inclinación
- 🖼️ **Denoise**: Eliminación de ruido (sal y pimienta)
- 🖼️ **Binarización Adaptativa**: Mejora contraste en fondos oscuros
- 🖼️ **Sharpening**: Mejora bordes de letras
- 🖼️ **Upscaling**: Aumenta resolución si DPI < 220
- 🖼️ **CLAHE**: Mejora contraste local

#### Cuándo Usar:
- PDFs escaneados o fotocopiados
- Documentos con calidad de imagen baja
- Antes de aplicar OCR (Docling, Tesseract)
- Resoluciones administrativas con sellos y firmas

#### Configuración:
```python
from src.ingestion.processors.ocr_preprocessor import get_ocr_preprocessor

preprocessor = get_ocr_preprocessor()

# Procesar PDF completo
image_paths = preprocessor.process_pdf(
    pdf_path="data/input/resolucion_escaneada.pdf",
    output_dir="debug_ocr/resolucion_001"
)

# Las imágenes preprocesadas están listas para OCR
```

#### Pipeline de Procesamiento:
1. **Conversión a Grayscale** → Elimina información de color innecesaria
2. **Deskew** → Detecta líneas de texto y corrige rotación (< 10°)
3. **Denoise** → `cv2.fastNlMeansDenoising` elimina granulosidad
4. **Binarización Adaptativa** → `cv2.adaptiveThreshold` con Gaussian
5. **CLAHE** → Mejora contraste local (clipLimit=2.0)
6. **Sharpening** → Kernel 5-point para bordes nítidos
7. **Upscaling** → Si DPI < 220, escala 1.2x-1.5x con interpolación cúbica

#### Parámetros:
```python
preprocessor = OCRPreprocessor(
    target_dpi=300,     # DPI objetivo para conversión
    debug=False         # Guardar imágenes intermedias
)
```

#### Estimación de DPI:
```python
# Asume tamaño carta (8.5 pulgadas de ancho)
estimated_dpi = width_pixels / 8.5
```

#### Corrección de Deskew:
```python
# Detecta líneas con Hough Transform
# Calcula mediana de ángulos (< 10°)
# Aplica rotación con interpolación cúbica
```

#### Salida:
```python
# Lista de rutas a imágenes PNG preprocesadas
[
    Path("debug_ocr/resolucion_001/resolucion_001_page_000.png"),
    Path("debug_ocr/resolucion_001/resolucion_001_page_001.png"),
    ...
]
```

---

### 4. **Text Cleaner** (`text_cleaner.py`)
**Refinería de texto legal multimodal con perfiles especializados.**

#### Características:
- 🧹 **Perfiles Múltiples**: General, Legal Colombia, Contratos, OCR
- 🧹 **Normalización de Unidades**: m³, L/s, hectáreas
- 🧹 **Inyección de Jerarquía**: Convierte secciones a Markdown
- 🧹 **Eliminación de Ruido**: Filtros específicos para normativa colombiana
- 🧹 **Corrección OCR**: Arregla confusiones típicas (l/I/1, O/0)
- 🧹 **Opcional**: Remoción de acentos para búsqueda insensible

#### Cuándo Usar:
- Después de extraer texto con loader
- Antes del chunking
- Para normalizar salida de OCR
- Cuando necesitas preparar texto para embeddings

#### Configuración:
```python
from src.ingestion.processors.text_cleaner import get_text_cleaner

cleaner = get_text_cleaner(remove_accents=False)

# Limpiar texto con perfil específico
cleaned = cleaner.clean(
    text=raw_text,
    profile="legal_colombia"  # "general", "contract", "ocr_output"
)
```

#### Perfiles Disponibles:

**1. General** (`general`):
```python
# Limpieza básica universal
- Normaliza espacios múltiples
- Elimina espacios al inicio/final
```

**2. Legal Colombia** (`legal_colombia`) — **PERFIL MAESTRO**:
```python
# Optimizado para Resoluciones Administrativas (SDA, CAR, ANLA)
- Normaliza encabezados de resoluciones
- Inyecta jerarquía Markdown (##, ###, ####)
- Elimina ruido específico (Decreto 1072, EVA, Diario Oficial)
- Normaliza unidades técnicas (m³, L/s)
- Preserva estructura para Adaptive Chunker
```

**3. Contratos** (`contract`):
```python
# Especializado para contratos y cláusulas civiles
- Hereda limpieza de "legal_colombia"
- Normaliza "CLÁUSULA" y "LAS PARTES" a Markdown
```

**4. OCR Output** (`ocr_output`):
```python
# Limpieza agresiva de artefactos de OCR
- Corrige confusiones: l/I/1, O/0
- Normaliza separador decimal (coma → punto)
- Elimina espacios anómalos
```

#### Normalización de Secciones (Legal Colombia):
```python
section_map = {
    "ANTECEDENTES": "## ANTECEDENTES",
    "CONSIDERANDO": "## CONSIDERANDO",
    "CONSIDERACIONES TÉCNICAS": "## CONSIDERACIONES TÉCNICAS",
    "ANÁLISIS AMBIENTAL": "## ANÁLISIS AMBIENTAL",
    "RESUELVE": "## RESUELVE",
    "ARTÍCULO": "### ARTÍCULO",
}
```

#### Filtros de Ruido:
```python
noise_patterns = [
    r"Departamento Administrativo de la Función Pública",
    r"Decreto 1072 de 2015.*EVA.*Gestor Normativo",
    r"Diario Oficial No\.\s*\d+",
    r"_{4,}|-{4,}",  # Líneas de subrayado
]
```

#### Normalización de Unidades Técnicas:
```python
# Volúmenes
r'(\d+)\.?(\d*)\s*m³' → r'\1.\2 m³'

# Caudales
r'(\d+)\.?(\d*)\s*L/s' → r'\1.\2 L/s'
```

#### Ejemplo de Uso:
```python
raw_text = """
Departamento Administrativo de la Función Pública
RESOLUCIÓN No. 001
CONSIDERANDO
Que el caudal es de 15,5 L/s...
RESUELVE
ARTÍCULO 1. Aprobar...
"""

cleaned = cleaner.clean(raw_text, profile="legal_colombia")

# Resultado:
"""
RESOLUCIÓN No. 001
## CONSIDERANDO
Que el caudal es de 15.5 L/s...
## RESUELVE
### ARTÍCULO 1. Aprobar...
"""
```

---

## 🔄 Pipeline Completo de Procesamiento

### Flujo Recomendado:
```python
from src.ingestion.loaders.pdf_docling import get_docling_loader
from src.ingestion.processors.text_cleaner import get_text_cleaner
from src.ingestion.processors.adaptive_chunker import get_adaptive_chunker
from src.ingestion.processors.metadata_extractor import get_metadata_extractor

# 1. Cargar PDF
loader = get_docling_loader()
raw_docs = loader.load("data/input/resolucion_001.pdf")

# 2. Limpiar texto
cleaner = get_text_cleaner()
for doc in raw_docs:
    doc.page_content = cleaner.clean(doc.page_content, profile="legal_colombia")

# 3. Chunking adaptativo
chunker = get_adaptive_chunker(chunk_size=1000, chunk_overlap=200)
chunks = chunker.chunk(raw_docs)

# 4. Enriquecer metadata
extractor = get_metadata_extractor()
final_docs = extractor.enrich_documents(chunks)

print(f"Documentos finales: {len(final_docs)}")
```

### Pipeline con OCR Preprocessing:
```python
from src.ingestion.processors.ocr_preprocessor import get_ocr_preprocessor
from src.ingestion.loaders.pdf_docling import get_docling_loader

# 1. Preprocesar imágenes
preprocessor = get_ocr_preprocessor()
image_paths = preprocessor.process_pdf("data/input/escaneado.pdf")

# 2. Cargar con Docling (usa imágenes preprocesadas)
loader = get_docling_loader(images_scale=3.0)
docs = loader.load_multiple([str(p) for p in image_paths])

# 3. Continuar con limpieza, chunking y metadata...
```

---

## 📊 Comparación de Procesadores

| Procesador | Entrada | Salida | Cuándo Usar |
|------------|---------|--------|-------------|
| **OCR Preprocessor** | PDF escaneado | Imágenes PNG | Antes de OCR |
| **Text Cleaner** | Texto crudo | Texto limpio | Después de loader |
| **Adaptive Chunker** | Documentos | Chunks | Después de limpieza |
| **Metadata Extractor** | Chunks | Chunks enriquecidos | Antes de indexar |

---

## 🎯 Mejores Prácticas

### 1. Orden de Procesamiento:
```
PDF → Loader → Text Cleaner → Adaptive Chunker → Metadata Extractor → Vectorstore
```

### 2. Perfiles de Limpieza:
- **Resoluciones SDA/CAR/ANLA**: `legal_colombia`
- **Contratos civiles**: `contract`
- **Salida de Tesseract/RapidOCR**: `ocr_output`
- **Documentos genéricos**: `general`

### 3. Tamaños de Chunk:
- **Artículos cortos**: `chunk_size=750`
- **Artículos largos**: `chunk_size=1000`
- **Documentos complejos**: `chunk_size=1200`
- **Overlap recomendado**: `20-25%` del chunk_size

### 4. OCR Preprocessing:
- Solo para PDFs con `quality_score < 0.4`
- Usar `target_dpi=300` para balance velocidad/calidad
- Guardar imágenes en `debug_ocr/` para inspección

---

## 🐛 Troubleshooting

### Chunks muy pequeños o muy grandes:
```python
# Ajustar chunk_size y overlap
chunker = get_adaptive_chunker(
    chunk_size=1200,    # Aumentar si chunks muy pequeños
    chunk_overlap=250   # Aumentar para más contexto
)
```

### Metadata no se extrae:
```python
# Verificar que el texto contiene patrones legales
extractor = get_metadata_extractor()
metadata = extractor.extract_from_text(text, source_path="test.pdf")
print(metadata)  # Inspeccionar qué se extrajo
```

### OCR Preprocessor falla en Windows:
```python
# Usar nombres de archivo sin acentos
# El preprocessor ya maneja esto internamente con regex
```

### Text Cleaner elimina contenido importante:
```python
# Usar perfil menos agresivo
cleaned = cleaner.clean(text, profile="general")

# O desactivar remoción de acentos
cleaner = get_text_cleaner(remove_accents=False)
```

---

## 📚 Referencias

- **LangChain Text Splitters**: https://python.langchain.com/docs/modules/data_connection/document_transformers/
- **OpenCV**: https://docs.opencv.org/
- **Unidecode**: https://pypi.org/project/Unidecode/
- **Regex Legal Patterns**: Basado en normativa colombiana (Decreto 1072, Resoluciones SDA)

---

## 👥 Mantenimiento

**Autor**: Ronny Vallejos  
**Última Actualización**: 28 de Abril de 2026  
**Versión**: 2.5  
**Proyecto**: RAG Analista Legal Colombiano
