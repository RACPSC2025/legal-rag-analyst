# 🔧 Utils Module

## Descripción General

El módulo **Utils** proporciona utilidades y funciones auxiliares reutilizables en todo el sistema RAG Legal. Incluye helpers para procesamiento de texto, manejo de archivos, validaciones y funciones comunes.

## 📦 Componentes Típicos

### 1. **text_utils.py**
**Propósito**: Utilidades de procesamiento de texto

**Funciones**:
```python
def normalize_text(text: str) -> str:
    """Normaliza texto: lowercase, sin acentos, etc."""
    
def extract_article_number(text: str) -> Optional[str]:
    """Extrae número de artículo del texto"""
    # "Art. 2.2.2.4.11" → "2.2.2.4.11"
    
def clean_whitespace(text: str) -> str:
    """Limpia espacios múltiples y saltos de línea"""
    
def truncate_text(text: str, max_length: int) -> str:
    """Trunca texto preservando palabras completas"""
```

---

### 2. **file_utils.py**
**Propósito**: Utilidades de manejo de archivos

**Funciones**:
```python
def ensure_dir(path: Path) -> Path:
    """Crea directorio si no existe"""
    
def get_file_hash(path: Path) -> str:
    """Calcula hash MD5 de archivo"""
    
def safe_filename(name: str) -> str:
    """Convierte string a nombre de archivo seguro"""
    # "Decreto 1082/2015" → "decreto_1082_2015"
    
def list_files_recursive(directory: Path, pattern: str) -> List[Path]:
    """Lista archivos recursivamente con patrón"""
```

---

### 3. **validation_utils.py**
**Propósito**: Validaciones comunes

**Funciones**:
```python
def is_valid_article_id(article_id: str) -> bool:
    """Valida formato de ID de artículo"""
    # "2.2.2.4.11" → True
    # "abc" → False
    
def is_valid_year(year: int) -> bool:
    """Valida año razonable"""
    # 1900 <= year <= 2100
    
def validate_pdf(path: Path) -> bool:
    """Verifica que archivo sea PDF válido"""
```

---

### 4. **date_utils.py**
**Propósito**: Utilidades de fechas

**Funciones**:
```python
def parse_legal_date(text: str) -> Optional[datetime]:
    """Parsea fechas en formatos legales colombianos"""
    # "15 de marzo de 2015" → datetime(2015, 3, 15)
    
def format_legal_date(date: datetime) -> str:
    """Formatea fecha en formato legal"""
    # datetime(2015, 3, 15) → "15 de marzo de 2015"
```

---

### 5. **logging_utils.py**
**Propósito**: Utilidades de logging

**Funciones**:
```python
def log_execution_time(func):
    """Decorator para loggear tiempo de ejecución"""
    
def log_with_context(logger, level, message, **context):
    """Log con contexto estructurado"""
    
def setup_file_logger(name: str, log_file: Path):
    """Configura logger con archivo"""
```

---

## 🎯 Ventajas del Módulo

### Reutilización
- ♻️ **DRY**: No repetir código
- 🔌 **Modular**: Funciones independientes
- 📦 **Importable**: Fácil usar en cualquier módulo

### Mantenibilidad
- 🧪 **Testeable**: Funciones puras fáciles de testear
- 📝 **Documentado**: Docstrings claros
- 🔄 **Evolución**: Cambios centralizados

### Consistencia
- ✅ **Estándares**: Comportamiento uniforme
- 🎯 **Validaciones**: Reglas centralizadas
- 📊 **Logging**: Formato consistente

---

## 🔧 Uso

### Procesamiento de Texto

```python
from src.utils.text_utils import normalize_text, extract_article_number

# Normalizar texto
text = "Artículo 2.2.2.4.11 - Negociadores"
normalized = normalize_text(text)
# "articulo 2.2.2.4.11 - negociadores"

# Extraer número de artículo
article_num = extract_article_number(text)
# "2.2.2.4.11"
```

### Manejo de Archivos

```python
from src.utils.file_utils import ensure_dir, safe_filename

# Asegurar directorio existe
output_dir = ensure_dir(Path("data/processed"))

# Nombre de archivo seguro
filename = safe_filename("Decreto 1082/2015")
# "decreto_1082_2015"
```

### Validaciones

```python
from src.utils.validation_utils import is_valid_article_id

# Validar ID de artículo
if is_valid_article_id("2.2.2.4.11"):
    process_article()
```

### Logging con Contexto

```python
from src.utils.logging_utils import log_execution_time, log_with_context

@log_execution_time
def expensive_operation():
    # Automáticamente logea tiempo de ejecución
    pass

# Log estructurado
log_with_context(
    logger, 
    "info", 
    "Query processed",
    query="¿Requisitos?",
    latency_ms=1234,
    cache_hit=True
)
```

---

## 📚 Mejores Prácticas

1. **Funciones puras**: Sin efectos secundarios cuando sea posible
2. **Type hints**: Siempre especificar tipos
3. **Docstrings**: Documentar propósito y ejemplos
4. **Tests**: Cada función debe tener tests
5. **Naming**: Nombres descriptivos y consistentes

---

**Última actualización**: 2026-04-28
**Versión**: 2.0.0
**Mantenedor**: Equipo de Utils
