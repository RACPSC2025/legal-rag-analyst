# PDF Loaders — Motores de Ingesta Multimodal

## 📋 Descripción General

Este módulo contiene **3 loaders especializados** para la extracción de texto de documentos PDF legales colombianos. Cada loader está optimizado para diferentes escenarios de calidad y complejidad documental.

## 🎯 Loaders Disponibles

### 1. **PyMuPDF Loader** (`pdf_pymupdf.py`)
**Motor rápido y eficiente para PDFs nativos de alta calidad.**

#### Características:
- ✅ **Velocidad**: Procesamiento ultrarrápido (< 1s por documento)
- ✅ **Precisión**: Extracción directa de texto nativo sin OCR
- ✅ **Estructura Legal**: Respeta artículos, capítulos y parágrafos
- ✅ **Contextual Headers**: Inyecta metadata en cada chunk para mejorar embeddings
- ✅ **Limpieza Inteligente**: Elimina ruido típico del Decreto 1072 y normativa colombiana

#### Cuándo Usar:
- PDFs generados digitalmente (Word → PDF, LaTeX → PDF)
- Documentos con texto seleccionable
- Normativa oficial (Decretos, Leyes, Resoluciones digitales)
- Cuando la velocidad es crítica

#### Configuración:
```python
from src.ingestion.loaders.pdf_pymupdf import get_pymupdf_loader

loader = get_pymupdf_loader(
    chunk_size=1000,        # Tamaño de fragmentos
    chunk_overlap=200,      # Solapamiento para contexto
    max_pages=400           # Límite de páginas
)

documents = loader.load("data/input/decreto_1072.pdf")
```

#### Separadores Jerárquicos:
```python
LEGAL_SEPARATORS = [
    "\nARTÍCULO ",      # Prioridad #1
    "\nCAPÍTULO ",
    "\nSECCIÓN ",
    "\nPARÁGRAFO ",
    "\n\n\n",           # Bloques grandes
    "\n\n",
    "\n",
    " ",
]
```

---

### 2. **Docling Loader** (`pdf_docling.py`)
**Motor avanzado con OCR industrial y procesamiento de tablas.**

#### Características:
- 🔥 **Visión Industrial**: Integración con OpenCV para preprocesamiento
- 🔥 **OCR Multilingüe**: RapidOCR con soporte español/inglés
- 🔥 **Tablas Estructuradas**: Extracción precisa de tablas complejas
- 🔥 **Escala 3.0**: Resolución aumentada para documentos escaneados
- 🔥 **Detección Automática**: Analiza calidad y aplica estrategia óptima
- 🔥 **Fallback Robusto**: Si falla, usa PyMuPDF como respaldo

#### Cuándo Usar:
- PDFs escaneados o fotocopiados
- Documentos con tablas complejas (tarifas, requisitos, plazos)
- Resoluciones administrativas con sellos y firmas
- Documentos con calidad de imagen baja o media

#### Configuración:
```python
from src.ingestion.loaders.pdf_docling import get_docling_loader

loader = get_docling_loader(
    chunk_size=750,
    chunk_overlap=180,
    table_mode="accurate",          # "fast" o "accurate"
    force_full_page_ocr=True,       # OCR en toda la página
    images_scale=3.0,               # Escala de resolución (1.0-4.0)
    use_ocr=True
)

documents = loader.load("data/input/resolucion_escaneada.pdf")
```

#### Pipeline de Procesamiento:
1. **Detección de Calidad** → `PDFQualityDetector` analiza el documento
2. **Preprocesamiento** → `OCRPreprocessor` aplica OpenCV (deskew, denoise, binarización)
3. **Conversión Docling** → Extracción con escala 3.0 y OCR
4. **Post-procesamiento de Tablas** → Normalización de formato Markdown
5. **Limpieza Legal** → `LegalTextCleaner` con perfil "legal_colombia"
6. **Chunking Adaptativo** → `AdaptiveChunker` respeta jerarquía legal
7. **Enriquecimiento** → `MetadataExtractor` agrega metadata estructurada

#### Estrategia de Calidad:
```python
if quality_score < 0.4 or recommendation in ("ocr_heavy", "docling"):
    # Aplicar Visión Industrial (OpenCV) + Docling Scale 3.0
    use_preprocessed = True
else:
    # Conversión Nativa de Alta Resolución
    use_preprocessed = False
```

---

### 3. **LlamaParse Loader** (`pdf_llamaparse.py`)
**Motor premium con IA para documentos ultra-complejos.**

#### Características:
- 💎 **IA Avanzada**: Modelo de lenguaje especializado en parsing
- 💎 **Formato Mixto**: Maneja texto, imágenes, tablas y gráficos
- 💎 **Calidad Premium**: Mejor precisión en documentos complejos
- 💎 **Multilingüe**: Soporte nativo para español
- ⚠️ **Costo por Página**: Servicio de pago (requiere API key)

#### Cuándo Usar:
- Documentos con formato extremadamente complejo
- Contratos con múltiples columnas y anotaciones
- Documentos con gráficos y diagramas técnicos
- Cuando PyMuPDF y Docling no son suficientes
- Presupuesto disponible para procesamiento premium

#### Configuración:
```python
from src.ingestion.loaders.pdf_llamaparse import get_llamaparse_loader

loader = get_llamaparse_loader(
    result_type="markdown",     # "text" o "markdown"
    language="es",              # Idioma del documento
    api_key="llx-...",          # API key de LlamaParse
    max_pages=350               # Límite de páginas
)

documents = loader.load("data/input/contrato_complejo.pdf")
```

#### Requisitos:
```bash
pip install llama-parse
```

#### Variables de Entorno:
```bash
LLAMA_PARSE_API_KEY=llx-your-api-key-here
```

---

## 🔄 Comparación de Loaders

| Característica | PyMuPDF | Docling | LlamaParse |
|----------------|---------|---------|------------|
| **Velocidad** | ⚡⚡⚡ Muy rápido | ⚡⚡ Moderado | ⚡ Lento |
| **Calidad OCR** | ❌ No tiene | ✅ Excelente | ✅ Premium |
| **Tablas** | ⚠️ Básico | ✅ Avanzado | ✅ Premium |
| **Costo** | 🆓 Gratis | 🆓 Gratis | 💰 Pago |
| **PDFs Nativos** | ✅ Perfecto | ✅ Bueno | ✅ Bueno |
| **PDFs Escaneados** | ❌ No funciona | ✅ Excelente | ✅ Premium |
| **Complejidad** | 🟢 Simple | 🟡 Media | 🟡 Media |
| **Dependencias** | Mínimas | OpenCV + Docling | API externa |

---

## 🎯 Estrategia de Selección Automática

El sistema usa `PDFQualityDetector` para elegir el loader óptimo:

```python
from src.ingestion.detectors.quality_detector import PDFQualityDetector

detector = PDFQualityDetector()
quality = detector.analyze("documento.pdf")

if quality.recommendation == "pymupdf":
    loader = get_pymupdf_loader()
elif quality.recommendation == "docling":
    loader = get_docling_loader()
elif quality.recommendation == "llamaparse":
    loader = get_llamaparse_loader()
```

### Criterios de Decisión:
- **Quality Score > 0.7** → PyMuPDF (rápido y eficiente)
- **Quality Score 0.4-0.7** → Docling (OCR moderado)
- **Quality Score < 0.4** → Docling con preprocesamiento intensivo
- **Tablas complejas detectadas** → Docling o LlamaParse
- **Presupuesto premium** → LlamaParse

---

## 📦 Interfaz Común (BasePDFLoader)

Todos los loaders heredan de `BasePDFLoader` y comparten la misma interfaz:

```python
from src.ingestion.base import BasePDFLoader

class CustomLoader(BasePDFLoader):
    @property
    def loader_type(self) -> str:
        return "custom_loader"
    
    @property
    def name(self) -> str:
        return "Custom Loader Name"
    
    def load(self, pdf_path: str | Path) -> List[Document]:
        # Implementación de carga
        pass
    
    def load_multiple(self, pdf_paths: List[str | Path]) -> List[Document]:
        # Implementación de carga múltiple
        pass
```

---

## 🔧 Uso Avanzado

### Carga Múltiple con Detección Automática:
```python
from pathlib import Path
from src.ingestion.detectors.quality_detector import PDFQualityDetector
from src.ingestion.loaders.pdf_pymupdf import get_pymupdf_loader
from src.ingestion.loaders.pdf_docling import get_docling_loader

detector = PDFQualityDetector()
pdf_files = list(Path("data/input").glob("*.pdf"))

all_documents = []
for pdf_path in pdf_files:
    quality = detector.analyze(pdf_path)
    
    if quality.recommendation == "pymupdf":
        loader = get_pymupdf_loader()
    else:
        loader = get_docling_loader()
    
    docs = loader.load(pdf_path)
    all_documents.extend(docs)

print(f"Total documentos cargados: {len(all_documents)}")
```

### Procesamiento en Batch:
```python
from src.ingestion.loaders.pdf_pymupdf import get_pymupdf_loader

loader = get_pymupdf_loader()
pdf_paths = [
    "data/input/decreto_1072.pdf",
    "data/input/resolucion_001.pdf",
    "data/input/ley_1234.pdf"
]

documents = loader.load_multiple(pdf_paths)
```

---

## 📊 Metadata Generada

Cada loader genera metadata estructurada en los documentos:

```python
{
    "source": "decreto_1072.pdf",
    "path": "/full/path/to/decreto_1072.pdf",
    "page": "15",
    "article": "2.2.4.1.2.3",
    "loader": "pymupdf_legal",
    "chunk_index": 42,
    "chunk_size": 987,
    "document_type": "decreto",
    "jurisdiction": "nacional",
    "resolution_number": "1072",
    "entity": "Ministerio del Trabajo",
    "issue_date": "26 de mayo de 2015",
    "legal_level": "article",
    "hierarchy": {
        "chapter": "CAPÍTULO 4",
        "section": "SECCIÓN 1",
        "article": "ARTÍCULO 2.2.4.1.2.3"
    }
}
```

---

## 🐛 Troubleshooting

### Error: "PDF no encontrado"
```python
# Verificar que el archivo existe
from pathlib import Path
pdf_path = Path("data/input/documento.pdf")
assert pdf_path.exists(), f"Archivo no encontrado: {pdf_path}"
```

### Error: "llama-parse no instalado"
```bash
pip install llama-parse
```

### Error: "Docling falla en Windows con acentos"
```python
# Docling usa codificación segura internamente
# Si persiste, usar PyMuPDF como fallback
```

### Rendimiento lento con Docling:
```python
# Reducir escala de imágenes
loader = get_docling_loader(images_scale=2.0)  # En lugar de 3.0

# O desactivar OCR completo
loader = get_docling_loader(force_full_page_ocr=False)
```

---

## 📚 Referencias

- **PyMuPDF**: https://pymupdf.readthedocs.io/
- **Docling**: https://github.com/DS4SD/docling
- **LlamaParse**: https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse/
- **BasePDFLoader**: `src/ingestion/base.py`
- **PDFQualityDetector**: `src/ingestion/detectors/README.md`

---

## 👥 Mantenimiento

**Autor**: Ronny Vallejos  
**Última Actualización**: 28 de Abril de 2026  
**Versión**: 2.5  
**Proyecto**: RAG Analista Legal Colombiano
