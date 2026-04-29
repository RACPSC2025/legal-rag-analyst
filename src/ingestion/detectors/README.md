# Detectors — Detección de Calidad de PDFs

## Descripción

Módulo de detección de calidad de documentos PDF antes de la ingesta. Determina si un PDF requiere OCR o puede procesarse directamente.

## Propósito

Antes de procesar un PDF, necesitamos saber:
- ¿Es un PDF nativo (con texto seleccionable)?
- ¿Es un PDF escaneado (imagen sin texto)?
- ¿Qué calidad tiene el documento?
- ¿Requiere preprocesamiento OCR?

## Componentes

### PDFQualityDetector

**Archivo**: `quality_detector.py`

**Responsabilidad**: Analizar la calidad de un PDF y determinar la estrategia de procesamiento.

**Métodos principales**:
```python
def detect_quality(pdf_path: Path) -> QualityReport:
    """
    Analiza un PDF y retorna un reporte de calidad.
    
    Returns:
        QualityReport con:
        - is_native: bool (¿tiene texto seleccionable?)
        - is_scanned: bool (¿es imagen escaneada?)
        - text_coverage: float (% de páginas con texto)
        - requires_ocr: bool (¿necesita OCR?)
        - quality_score: float (0.0-1.0)
    """
```

**Uso**:
```python
from src.ingestion.detectors import PDFQualityDetector

detector = PDFQualityDetector()
report = detector.detect_quality("documento.pdf")

if report.requires_ocr:
    print("PDF escaneado, requiere OCR")
else:
    print("PDF nativo, procesamiento directo")
```

## Flujo de Detección

```
PDF Input
    ↓
PDFQualityDetector
    ↓
Análisis de páginas
    ↓
¿Tiene texto?
    ├─ SÍ → PDF Nativo → Procesamiento directo
    └─ NO → PDF Escaneado → Requiere OCR
```

## Métricas de Calidad

| Métrica | Descripción | Rango |
|---------|-------------|-------|
| **text_coverage** | % de páginas con texto | 0.0 - 1.0 |
| **quality_score** | Calidad general del PDF | 0.0 - 1.0 |
| **is_native** | ¿Tiene texto seleccionable? | bool |
| **is_scanned** | ¿Es imagen escaneada? | bool |
| **requires_ocr** | ¿Necesita OCR? | bool |

## Criterios de Decisión

```python
if text_coverage > 0.8:
    # PDF nativo de buena calidad
    requires_ocr = False
elif text_coverage > 0.3:
    # PDF mixto (algunas páginas escaneadas)
    requires_ocr = True  # OCR solo para páginas sin texto
else:
    # PDF completamente escaneado
    requires_ocr = True
```

## Integración con Pipeline

El detector se usa automáticamente en el pipeline de ingesta:

```python
from src.ingestion.pipeline import run_ingestion_pipeline

# El pipeline detecta automáticamente la calidad
result = run_ingestion_pipeline(
    pdf_path="documento.pdf",
    loader_type="auto"  # Selección automática según calidad
)
```

## Extensión

Para agregar nuevos detectores:

1. Crear clase que herede de `BaseDetector` (si existe)
2. Implementar método `detect_quality()`
3. Retornar `QualityReport` estandarizado
4. Registrar en `__init__.py`

## Referencias

- **Pipeline de ingesta**: `src/ingestion/pipeline.py`
- **Preprocesador OCR**: `src/ingestion/processors/ocr_preprocessor.py`
- **Loaders**: `src/ingestion/loaders/`

---

**Autor**: Fenix Tech Líder  
**Fecha**: 2026-04-28  
**Versión**: 1.0.0
