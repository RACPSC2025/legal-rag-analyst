"""
Metrics Dashboard — Visualización de Resultados RAGAS
────────────────────────────────────────────────────
Genera visualizaciones y análisis de los reportes RAGAS.

Uso:
    python tests/evaluation/metrics_dashboard.py ragas_report_full_20260427_143022.json
    python tests/evaluation/metrics_dashboard.py --compare report1.json report2.json

Autor: Fenix Tech Líder
Fecha: 2026-04-27
Versión: 1.0.0
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# ── Análisis de resultados ───────────────────────────────────────────────────

class MetricsDashboard:
    """
    Analizador y visualizador de reportes RAGAS.
    """
    
    def __init__(self, report_path: Path):
        """
        Inicializa el dashboard con un reporte.
        
        Args:
            report_path: Ruta al archivo JSON del reporte RAGAS.
        """
        with open(report_path, "r", encoding="utf-8") as f:
            self.report = json.load(f)
        
        self.results = self.report["results"]
    
    def analyze_by_category(self) -> Dict[str, Dict[str, float]]:
        """
        Analiza métricas agrupadas por categoría legal.
        
        Returns:
            Diccionario con métricas promedio por categoría.
        """
        categories: Dict[str, List[Dict]] = {}
        
        # Agrupar por categoría
        for result in self.results:
            if result.get("error"):
                continue
            
            cat = result["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)
        
        # Calcular promedios por categoría
        analysis = {}
        for cat, results in categories.items():
            metrics = [r["metrics"] for r in results]
            
            analysis[cat] = {
                "count": len(results),
                "avg_faithfulness": sum(m["faithfulness"] for m in metrics) / len(metrics),
                "avg_relevancy": sum(m["answer_relevancy"] for m in metrics) / len(metrics),
                "avg_precision": sum(m["context_precision"] for m in metrics) / len(metrics),
                "avg_recall": sum(m["context_recall"] for m in metrics) / len(metrics),
                "avg_correctness": sum(m["answer_correctness"] for m in metrics) / len(metrics),
                "avg_latency": sum(m["latency_seconds"] for m in metrics) / len(metrics),
            }
        
        return analysis
    
    def identify_weak_questions(self, threshold: float = 0.6) -> List[Dict[str, Any]]:
        """
        Identifica preguntas con scores bajos que requieren atención.
        
        Args:
            threshold: Score mínimo aceptable (default: 0.6).
            
        Returns:
            Lista de preguntas con scores por debajo del threshold.
        """
        weak_questions = []
        
        for result in self.results:
            if result.get("error"):
                continue
            
            metrics = result["metrics"]
            overall = (
                metrics["faithfulness"] * 0.30 +
                metrics["answer_relevancy"] * 0.25 +
                metrics["context_precision"] * 0.20 +
                metrics["context_recall"] * 0.15 +
                metrics["answer_correctness"] * 0.10
            )
            
            if overall < threshold:
                weak_questions.append({
                    "question_id": result["question_id"],
                    "category": result["category"],
                    "question": result["question"],
                    "overall_score": round(overall, 3),
                    "weakest_metric": self._find_weakest_metric(metrics),
                    "metrics": metrics
                })
        
        # Ordenar por score (peores primero)
        weak_questions.sort(key=lambda x: x["overall_score"])
        
        return weak_questions
    
    def _find_weakest_metric(self, metrics: Dict[str, float]) -> str:
        """Identifica la métrica más débil."""
        metric_scores = {
            "faithfulness": metrics["faithfulness"],
            "answer_relevancy": metrics["answer_relevancy"],
            "context_precision": metrics["context_precision"],
            "context_recall": metrics["context_recall"],
            "answer_correctness": metrics["answer_correctness"],
        }
        
        return min(metric_scores, key=metric_scores.get)
    
    def generate_recommendations(self) -> List[str]:
        """
        Genera recomendaciones basadas en el análisis de métricas.
        
        Returns:
            Lista de recomendaciones accionables.
        """
        recommendations = []
        
        # Analizar métricas globales
        avg_faith = self.report["avg_faithfulness"]
        avg_rel = self.report["avg_answer_relevancy"]
        avg_prec = self.report["avg_context_precision"]
        avg_rec = self.report["avg_context_recall"]
        avg_corr = self.report["avg_answer_correctness"]
        
        # Faithfulness baja → problema en generación
        if avg_faith < 0.7:
            recommendations.append(
                "⚠️ FAITHFULNESS BAJA: El LLM está inventando información. "
                "Recomendación: Ajustar el prompt de generación para ser más estricto "
                "con las citas y verificar el nodo check_hallucination."
            )
        
        # Answer Relevancy baja → problema en comprensión de pregunta
        if avg_rel < 0.7:
            recommendations.append(
                "⚠️ ANSWER RELEVANCY BAJA: Las respuestas no están enfocadas en la pregunta. "
                "Recomendación: Mejorar el prompt de generación para que responda "
                "directamente lo que se pregunta."
            )
        
        # Context Precision baja → retrieval trae docs irrelevantes
        if avg_prec < 0.7:
            recommendations.append(
                "⚠️ CONTEXT PRECISION BAJA: El retrieval está trayendo documentos irrelevantes. "
                "Recomendación: Ajustar los pesos de RRF, mejorar Query Expansion, "
                "o revisar la calidad de los embeddings."
            )
        
        # Context Recall baja → retrieval no encuentra docs correctos
        if avg_rec < 0.7:
            recommendations.append(
                "⚠️ CONTEXT RECALL BAJA: El retrieval no está encontrando los documentos correctos. "
                "Recomendación: Aumentar top_k, mejorar el chunking para preservar contexto, "
                "o revisar si los documentos están correctamente indexados."
            )
        
        # Answer Correctness baja → respuesta incorrecta
        if avg_corr < 0.6:
            recommendations.append(
                "⚠️ ANSWER CORRECTNESS BAJA: Las respuestas no coinciden con la ground truth. "
                "Recomendación: Revisar si el modelo tiene suficiente capacidad, "
                "mejorar el contexto recuperado, o ajustar el prompt de generación."
            )
        
        # Latencia alta
        avg_latency = self.report["avg_latency_seconds"]
        if avg_latency > 10:
            recommendations.append(
                f"⚠️ LATENCIA ALTA ({avg_latency:.1f}s): El sistema es lento. "
                "Recomendación: Optimizar Query Expansion (reducir n_queries), "
                "usar modelos más rápidos para grading, o implementar caché más agresivo."
            )
        
        # Si todo está bien
        if not recommendations:
            recommendations.append(
                "✅ SISTEMA EN BUEN ESTADO: Todas las métricas están por encima de los umbrales. "
                "Continuar monitoreando y considerar optimizaciones incrementales."
            )
        
        return recommendations
    
    def print_dashboard(self):
        """Imprime el dashboard completo en consola."""
        print("\n" + "="*100)
        print("📊 DASHBOARD DE MÉTRICAS RAGAS")
        print("="*100)
        
        # Información general
        print(f"\n📋 Dataset: {self.report['dataset_name']}")
        print(f"📅 Fecha de evaluación: {self.report['evaluation_date']}")
        print(f"✅ Preguntas exitosas: {self.report['successful_evaluations']}/{self.report['total_questions']}")
        
        if self.report['failed_evaluations'] > 0:
            print(f"❌ Preguntas fallidas: {self.report['failed_evaluations']}")
        
        # Métricas globales
        print("\n" + "-"*100)
        print("📈 MÉTRICAS GLOBALES")
        print("-"*100)
        
        overall = self.report['avg_overall_score']
        status = "🟢 EXCELENTE" if overall >= 0.8 else "🟡 BUENO" if overall >= 0.6 else "🔴 NECESITA MEJORA"
        
        print(f"Overall Score:        {overall:.3f} {status}")
        print(f"Faithfulness:         {self.report['avg_faithfulness']:.3f} {'✅' if self.report['avg_faithfulness'] >= 0.7 else '⚠️'}")
        print(f"Answer Relevancy:     {self.report['avg_answer_relevancy']:.3f} {'✅' if self.report['avg_answer_relevancy'] >= 0.7 else '⚠️'}")
        print(f"Context Precision:    {self.report['avg_context_precision']:.3f} {'✅' if self.report['avg_context_precision'] >= 0.7 else '⚠️'}")
        print(f"Context Recall:       {self.report['avg_context_recall']:.3f} {'✅' if self.report['avg_context_recall'] >= 0.7 else '⚠️'}")
        print(f"Answer Correctness:   {self.report['avg_answer_correctness']:.3f} {'✅' if self.report['avg_answer_correctness'] >= 0.6 else '⚠️'}")
        
        # Rendimiento
        print("\n" + "-"*100)
        print("⚡ RENDIMIENTO")
        print("-"*100)
        print(f"Latencia promedio:    {self.report['avg_latency_seconds']:.2f}s")
        print(f"Tokens totales:       {self.report['total_tokens_used']:,}")
        
        # Análisis por categoría
        print("\n" + "-"*100)
        print("📂 ANÁLISIS POR CATEGORÍA")
        print("-"*100)
        
        category_analysis = self.analyze_by_category()
        for cat, metrics in category_analysis.items():
            overall_cat = (
                metrics["avg_faithfulness"] * 0.30 +
                metrics["avg_relevancy"] * 0.25 +
                metrics["avg_precision"] * 0.20 +
                metrics["avg_recall"] * 0.15 +
                metrics["avg_correctness"] * 0.10
            )
            print(f"\n{cat} ({metrics['count']} preguntas):")
            print(f"  Overall: {overall_cat:.3f} | Faith: {metrics['avg_faithfulness']:.2f} | "
                  f"Rel: {metrics['avg_relevancy']:.2f} | Prec: {metrics['avg_precision']:.2f}")
        
        # Preguntas débiles
        weak = self.identify_weak_questions(threshold=0.6)
        if weak:
            print("\n" + "-"*100)
            print(f"⚠️ PREGUNTAS QUE REQUIEREN ATENCIÓN ({len(weak)} encontradas)")
            print("-"*100)
            
            for i, q in enumerate(weak[:5], 1):  # Mostrar top 5
                print(f"\n{i}. [{q['question_id']}] Score: {q['overall_score']:.3f}")
                print(f"   Categoría: {q['category']}")
                print(f"   Métrica más débil: {q['weakest_metric']}")
                print(f"   Pregunta: {q['question'][:100]}...")
        
        # Recomendaciones
        print("\n" + "-"*100)
        print("💡 RECOMENDACIONES")
        print("-"*100)
        
        recommendations = self.generate_recommendations()
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec}")
        
        print("\n" + "="*100 + "\n")
    
    def export_html_report(self, output_path: Path):
        """
        Exporta el dashboard como HTML para visualización web.
        
        Args:
            output_path: Ruta donde guardar el HTML.
        """
        html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard RAGAS - {self.report['dataset_name']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .metric-item {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            color: #666;
            margin-top: 5px;
        }}
        .status-good {{ color: #10b981; }}
        .status-warning {{ color: #f59e0b; }}
        .status-bad {{ color: #ef4444; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #667eea;
            color: white;
        }}
        .recommendation {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Dashboard RAGAS - RAG Legal Colombiano</h1>
        <p>Dataset: {self.report['dataset_name']}</p>
        <p>Fecha: {self.report['evaluation_date']}</p>
    </div>
    
    <div class="metric-grid">
        <div class="metric-item">
            <div class="metric-value status-{'good' if self.report['avg_overall_score'] >= 0.8 else 'warning' if self.report['avg_overall_score'] >= 0.6 else 'bad'}">
                {self.report['avg_overall_score']:.3f}
            </div>
            <div class="metric-label">Overall Score</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">{self.report['avg_faithfulness']:.3f}</div>
            <div class="metric-label">Faithfulness</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">{self.report['avg_answer_relevancy']:.3f}</div>
            <div class="metric-label">Answer Relevancy</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">{self.report['avg_context_precision']:.3f}</div>
            <div class="metric-label">Context Precision</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">{self.report['avg_context_recall']:.3f}</div>
            <div class="metric-label">Context Recall</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">{self.report['avg_latency_seconds']:.2f}s</div>
            <div class="metric-label">Latencia Promedio</div>
        </div>
    </div>
    
    <div class="metric-card">
        <h2>📂 Análisis por Categoría</h2>
        <table>
            <thead>
                <tr>
                    <th>Categoría</th>
                    <th>Preguntas</th>
                    <th>Overall</th>
                    <th>Faithfulness</th>
                    <th>Relevancy</th>
                    <th>Precision</th>
                </tr>
            </thead>
            <tbody>
"""
        
        category_analysis = self.analyze_by_category()
        for cat, metrics in category_analysis.items():
            overall_cat = (
                metrics["avg_faithfulness"] * 0.30 +
                metrics["avg_relevancy"] * 0.25 +
                metrics["avg_precision"] * 0.20 +
                metrics["avg_recall"] * 0.15 +
                metrics["avg_correctness"] * 0.10
            )
            html += f"""
                <tr>
                    <td>{cat}</td>
                    <td>{metrics['count']}</td>
                    <td>{overall_cat:.3f}</td>
                    <td>{metrics['avg_faithfulness']:.3f}</td>
                    <td>{metrics['avg_relevancy']:.3f}</td>
                    <td>{metrics['avg_precision']:.3f}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
    </div>
    
    <div class="metric-card">
        <h2>💡 Recomendaciones</h2>
"""
        
        recommendations = self.generate_recommendations()
        for rec in recommendations:
            html += f'<div class="recommendation">{rec}</div>\n'
        
        html += """
    </div>
</body>
</html>
"""
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        print(f"📄 Reporte HTML generado: {output_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Dashboard de visualización de métricas RAGAS"
    )
    parser.add_argument(
        "report",
        type=str,
        help="Ruta al archivo JSON del reporte RAGAS"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generar reporte HTML adicional"
    )
    
    args = parser.parse_args()
    
    report_path = Path(args.report)
    
    if not report_path.exists():
        print(f"❌ Reporte no encontrado: {report_path}")
        sys.exit(1)
    
    # Crear dashboard
    dashboard = MetricsDashboard(report_path)
    
    # Mostrar en consola
    dashboard.print_dashboard()
    
    # Generar HTML si se solicita
    if args.html:
        html_path = report_path.with_suffix(".html")
        dashboard.export_html_report(html_path)


if __name__ == "__main__":
    main()
