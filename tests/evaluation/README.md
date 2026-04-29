# 📊 Sistema de Evaluación RAGAS - RAG Legal Colombiano

Sistema completo de evaluación de calidad para el RAG Analista Legal usando métricas RAGAS (Retrieval-Augmented Generation Assessment).

## 🎯 Objetivo

Evaluar objetivamente la calidad del sistema RAG en 5 dimensiones críticas:

1. **Faithfulness** (Fidelidad): ¿La respuesta está fundamentada en los documentos fuente?
2. **Answer Relevancy** (Relevancia): ¿La respuesta es relevante para la pregunta?
3. **Context Precision** (Precisión): ¿Los documentos recuperados son relevantes?
4. **Context Recall** (Cobertura): ¿El contexto cubre toda la información necesaria?
5. **Answer Correctness** (Exactitud): ¿La respuesta coincide con la ground truth?

## 📁 Estructura

```
tests/evaluation/
├── golden_dataset.json          # Dataset con 22 preguntas reales
├── ragas_evaluator.py           # Motor de evaluación RAGAS
├── metrics_dashboard.py         # Visualización de métricas
├── run_evaluation.py            # Orquestador maestro
├── README.md                    # Esta documentación
└── ragas_report_*.json          # Reportes generados (git-ignored)
```

## 🚀 Uso Rápido

### Evaluación Completa (22 preguntas)

```bash
# Desde la raíz del proyecto
python tests/evaluation/run_evaluation.py
```

### Evaluación Rápida (5 preguntas)

```bash
python tests/evaluation/run_evaluation.py --quick
```

### Evaluación con Dataset Personalizado

```bash
python tests/evaluation/run_evaluation.py --dataset mi_dataset.json
```

## 📊 Componentes

### 1. Golden Dataset (`golden_dataset.json`)

Dataset curado con 22 preguntas reales de derecho colombiano distribuidas en 4 categorías:

- **Derecho Ambiental** (11 preguntas): Concesiones, licencias, tasas retributivas
- **Derecho Administrativo** (5 preguntas): Recursos, actos administrativos
- **Derecho Laboral** (4 preguntas): Prestaciones, indemnizaciones, jornadas
- **Derecho Tributario** (4 preguntas): IVA, renta, retención en la fuente

Cada pregunta incluye:
- `question`: Pregunta en lenguaje natural
- `ground_truth`: Respuesta esperada validada por experto
- `expected_sources`: Fuentes legales que deben citarse
- `difficulty`: Nivel de dificultad (easy/medium/hard)
- `requires_table`: Si la respuesta requiere preservar tablas

### 2. RAGAS Evaluator (`ragas_evaluator.py`)

Motor de evaluación que implementa 5 evaluadores especializados:

```python
from ragas_evaluator import RAGASEvaluator

evaluator = RAGASEvaluator()
report = evaluator.evaluate_dataset("golden_dataset.json")
```

**Métricas calculadas:**
- Faithfulness: 0.0-1.0 (1.0 = totalmente fiel)
- Answer Relevancy: 0.0-1.0 (1.0 = máxima relevancia)
- Context Precision: 0.0-1.0 (1.0 = todos los docs relevantes)
- Context Recall: 0.0-1.0 (1.0 = ground truth completamente cubierta)
- Answer Correctness: 0.0-1.0 (1.0 = respuesta perfecta)

**Overall Score:** Promedio ponderado de las 5 métricas.

### 3. Metrics Dashboard (`metrics_dashboard.py`)

Visualizador de resultados con análisis avanzado:

```bash
# Mostrar dashboard en consola
python tests/evaluation/metrics_dashboard.py ragas_report_full_20260427_143022.json

# Generar reporte HTML
python tests/evaluation/metrics_dashboard.py ragas_report_full_20260427_143022.json --html
```

**Análisis incluidos:**
- Métricas globales con indicadores de estado (🟢/🟡/🔴)
- Análisis por categoría legal
- Identificación de preguntas débiles
- Recomendaciones accionables automáticas

### 4. Run Evaluation (`run_evaluation.py`)

Orquestador que ejecuta el pipeline completo:

```bash
python tests/evaluation/run_evaluation.py
```

**Pipeline:**
1. Ejecuta evaluación RAGAS sobre el dataset
2. Genera reporte JSON con resultados detallados
3. Crea dashboard de métricas en consola
4. Exporta reporte HTML para visualización web

## 📈 Interpretación de Resultados

### Overall Score

| Score | Estado | Acción |
|-------|--------|--------|
| ≥ 0.80 | 🟢 EXCELENTE | Sistema production-ready |
| 0.60-0.79 | 🟡 BUENO | Optimizaciones menores |
| < 0.60 | 🔴 NECESITA MEJORA | Revisión crítica requerida |

### Métricas Individuales

#### Faithfulness < 0.7
**Problema:** El LLM está inventando información.  
**Solución:** Ajustar prompt de generación, verificar check_hallucination.

#### Answer Relevancy < 0.7
**Problema:** Respuestas no enfocadas en la pregunta.  
**Solución:** Mejorar prompt para responder directamente.

#### Context Precision < 0.7
**Problema:** Retrieval trae documentos irrelevantes.  
**Solución:** Ajustar pesos RRF, mejorar Query Expansion.

#### Context Recall < 0.7
**Problema:** Retrieval no encuentra documentos correctos.  
**Solución:** Aumentar top_k, mejorar chunking.

#### Answer Correctness < 0.6
**Problema:** Respuestas incorrectas vs ground truth.  
**Solución:** Revisar capacidad del modelo, mejorar contexto.

## 🔧 Configuración Avanzada

### Modificar Pesos del Overall Score

Editar en `ragas_evaluator.py`:

```python
def overall_score(self) -> float:
    return (
        self.faithfulness * 0.30 +        # Peso de fidelidad
        self.answer_relevancy * 0.25 +    # Peso de relevancia
        self.context_precision * 0.20 +   # Peso de precisión
        self.context_recall * 0.15 +      # Peso de cobertura
        self.answer_correctness * 0.10    # Peso de exactitud
    )
```

### Añadir Nuevas Preguntas al Dataset

Editar `golden_dataset.json`:

```json
{
  "id": "Q023",
  "category": "Derecho Ambiental",
  "question": "¿Cuál es el plazo para renovar una licencia ambiental?",
  "ground_truth": "La licencia ambiental debe renovarse...",
  "expected_sources": ["Decreto 1076 de 2015", "Artículo X"],
  "difficulty": "medium",
  "requires_table": false
}
```

### Ajustar Umbrales de Evaluación

Editar en `metrics_dashboard.py`:

```python
def identify_weak_questions(self, threshold: float = 0.6):
    # Cambiar threshold a 0.7 para ser más estricto
    ...
```

## 📊 Ejemplo de Reporte

```
📊 RESUMEN DE EVALUACIÓN RAGAS
================================================================================
Dataset: Golden Dataset - RAG Legal Colombiano
Fecha: 2026-04-27T14:30:22
Total preguntas: 22
Exitosas: 22
Fallidas: 0

--------------------------------------------------------------------------------
MÉTRICAS PROMEDIO
--------------------------------------------------------------------------------
Overall Score:        0.823 ⭐
Faithfulness:         0.856 ✅
Answer Relevancy:     0.812 ✅
Context Precision:    0.789 ✅
Context Recall:       0.801 ✅
Answer Correctness:   0.745 ✅

--------------------------------------------------------------------------------
RENDIMIENTO
--------------------------------------------------------------------------------
Latencia promedio:    6.45s
Tokens totales:       45,230
================================================================================
```

## 🎯 Mejores Prácticas

1. **Ejecutar evaluación después de cada cambio importante** en el sistema RAG
2. **Mantener el Golden Dataset actualizado** con preguntas reales de usuarios
3. **Validar ground truth con experto legal** antes de añadir al dataset
4. **Monitorear tendencias** comparando reportes históricos
5. **Priorizar métricas según el caso de uso** (ej: Faithfulness > Correctness para legal)

## 🔄 Integración Continua

### GitHub Actions (ejemplo)

```yaml
name: RAGAS Evaluation

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run RAGAS Evaluation
        run: python tests/evaluation/run_evaluation.py --quick
      - name: Upload Report
        uses: actions/upload-artifact@v2
        with:
          name: ragas-report
          path: tests/evaluation/ragas_report_*.json
```

## 📚 Referencias

- [RAGAS Framework](https://github.com/explodinggradients/ragas)
- [RAG Evaluation Best Practices](https://www.llamaindex.ai/blog/evaluating-rag)
- [LangChain Evaluation](https://python.langchain.com/docs/guides/evaluation)

## 🤝 Contribuciones

Para añadir nuevas métricas o evaluadores:

1. Crear nueva clase evaluadora en `ragas_evaluator.py`
2. Implementar método `evaluate()` que retorne score 0.0-1.0
3. Integrar en `RAGASEvaluator.evaluate_single_question()`
4. Actualizar `RAGASMetrics` dataclass con nueva métrica
5. Añadir visualización en `metrics_dashboard.py`

## 📝 Changelog

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0.0 | 2026-04-27 | Versión inicial con 5 métricas RAGAS |

---

*Sistema de evaluación diseñado por Fenix Tech Líder — Calidad de Producción 2026.*
