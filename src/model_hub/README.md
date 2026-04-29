# 🤖 Model Hub Module

## Descripción General

El módulo **Model Hub** gestiona la selección y configuración de modelos LLM para diferentes tareas del sistema RAG. Implementa un patrón de registro centralizado que permite usar modelos específicos optimizados para cada tipo de operación (generación, verificación, grading).

## 📦 Componentes

### 1. **registry.py**
**Propósito**: Registro centralizado de modelos disponibles

**Estructura**:
```python
MODEL_REGISTRY = {
    "generate": {
        "model_id": "gpt-4o",
        "temperature": 0.3,
        "max_tokens": 2000,
        "description": "Modelo potente para generación de respuestas legales"
    },
    "grade": {
        "model_id": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 500,
        "description": "Modelo ligero para clasificación de relevancia"
    },
    "verify": {
        "model_id": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 500,
        "description": "Modelo para verificación de alucinaciones"
    }
}
```

**Ventajas**:
- 🎯 **Optimización por tarea**: Modelo adecuado para cada operación
- 💰 **Control de costos**: Modelos ligeros para tareas simples
- ⚙️ **Configuración centralizada**: Un solo lugar para cambios
- 🔄 **Fácil experimentación**: Cambiar modelos sin tocar código

---

### 2. **selector.py**
**Propósito**: Selección inteligente de modelos

**Funcionalidades**:
- **Selección por tarea**: Elige modelo óptimo según operación
- **Fallback automático**: Si un modelo falla, usa alternativa
- **Balanceo de carga**: Distribuye entre modelos disponibles
- **Monitoreo de costos**: Tracking de uso por modelo

**Uso**:
```python
from src.model_hub.selector import select_model

# Selección automática por tarea
model = select_model(task="generate")
# Returns: ChatOpenAI(model="gpt-4o", temperature=0.3)

model = select_model(task="grade")
# Returns: ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
```

**Estrategias de Selección**:

#### **A. Por Tarea**
```python
TASK_TO_MODEL = {
    "generate": "gpt-4o",        # Calidad máxima
    "grade": "gpt-4o-mini",      # Rápido y económico
    "verify": "gpt-4o-mini",     # Clasificación binaria
    "expand": "gpt-4o",          # HyDE y Multi-Query
    "compress": "gpt-4o"         # Extracción precisa
}
```

#### **B. Por Complejidad**
```python
if query_complexity > 0.8:
    return "gpt-4o"              # Queries complejas
elif query_complexity > 0.5:
    return "gpt-4o-mini"         # Queries medias
else:
    return "gpt-3.5-turbo"       # Queries simples
```

#### **C. Por Costo/Latencia**
```python
if priority == "quality":
    return "gpt-4o"
elif priority == "speed":
    return "gpt-4o-mini"
elif priority == "cost":
    return "gpt-3.5-turbo"
```

---

## 🎯 Ventajas del Sistema

### Optimización
- 🎯 **Modelo adecuado**: Cada tarea usa el modelo óptimo
- 💰 **Ahorro de costos**: Modelos ligeros donde es posible
- ⚡ **Latencia reducida**: Modelos rápidos para tareas simples

### Flexibilidad
- 🔄 **Fácil cambio**: Modificar modelos sin tocar código
- 🧪 **Experimentación**: Probar diferentes configuraciones
- 🔌 **Extensible**: Agregar nuevos modelos fácilmente

### Observabilidad
- 📊 **Tracking de uso**: Monitoreo por modelo y tarea
- 💰 **Control de costos**: Visibilidad de gastos
- 📈 **Métricas**: Performance por modelo

---

## 🔧 Uso

### Configuración Básica

```python
from src.config import get_llm

# Obtener modelo para tarea específica
llm_generate = get_llm(task="generate")
llm_grade = get_llm(task="grade")
llm_verify = get_llm(task="verify")

# Usar modelo
response = llm_generate.invoke("¿Cuáles son los requisitos?")
```

### Configuración Avanzada

```python
from src.model_hub.registry import MODEL_REGISTRY

# Modificar configuración de modelo
MODEL_REGISTRY["generate"]["temperature"] = 0.5
MODEL_REGISTRY["generate"]["max_tokens"] = 3000

# Agregar nuevo modelo
MODEL_REGISTRY["summarize"] = {
    "model_id": "gpt-4o-mini",
    "temperature": 0.3,
    "max_tokens": 1000,
    "description": "Modelo para resúmenes"
}
```

### Monitoreo de Costos

```python
from src.model_hub.selector import get_usage_stats

stats = get_usage_stats()
print(f"Tokens usados: {stats['total_tokens']}")
print(f"Costo estimado: ${stats['estimated_cost']:.2f}")
print(f"Modelo más usado: {stats['most_used_model']}")
```

---

## 📊 Comparación de Modelos

| Modelo | Tarea | Tokens/s | Costo (1M tokens) | Calidad |
|--------|-------|----------|-------------------|---------|
| gpt-4o | generate | 50 | $5.00 | ⭐⭐⭐⭐⭐ |
| gpt-4o-mini | grade | 200 | $0.15 | ⭐⭐⭐⭐ |
| gpt-4o-mini | verify | 200 | $0.15 | ⭐⭐⭐⭐ |
| gpt-3.5-turbo | fallback | 300 | $0.50 | ⭐⭐⭐ |

---

## 🚀 Roadmap

- [ ] Soporte para modelos locales (Ollama, LM Studio)
- [ ] Balanceo de carga entre múltiples modelos
- [ ] A/B testing automático de modelos
- [ ] Fine-tuning de modelos para dominio legal
- [ ] Integración con AWS Bedrock, Azure OpenAI

---

**Última actualización**: 2026-04-28
**Versión**: 2.0.0
**Mantenedor**: Equipo de Model Hub
