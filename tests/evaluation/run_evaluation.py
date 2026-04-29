"""
Run Evaluation — Orquestador Maestro de Evaluación RAGAS
────────────────────────────────────────────────────────
Script principal que ejecuta el pipeline completo de evaluación:
  1. Ejecuta RAGAS evaluator
  2. Genera dashboard de métricas
  3. Exporta reportes HTML
  4. Envía notificaciones (opcional)

Uso:
    python tests/evaluation/run_evaluation.py
    python tests/evaluation/run_evaluation.py --quick
    python tests/evaluation/run_evaluation.py --dataset custom_dataset.json

Autor: Fenix Tech Líder
Fecha: 2026-04-27
Versión: 1.0.0
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
from datetime import datetime

# Añadir src al path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ragas_evaluator import RAGASEvaluator
from metrics_dashboard import MetricsDashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)


def run_full_evaluation(
    dataset_name: str = "golden_dataset.json",
    quick_mode: bool = False,
    generate_html: bool = True
):
    """
    Ejecuta el pipeline completo de evaluación.
    
    Args:
        dataset_name: Nombre del archivo de dataset.
        quick_mode: Si True, evalúa solo 5 preguntas.
        generate_html: Si True, genera reporte HTML.
    """
    eval_dir = Path(__file__).parent
    dataset_path = eval_dir / dataset_name
    
    if not dataset_path.exists():
        logger.error(f"❌ Dataset no encontrado: {dataset_path}")
        sys.exit(1)
    
    # Generar nombre de reporte
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "quick" if quick_mode else "full"
    report_path = eval_dir / f"ragas_report_{mode}_{timestamp}.json"
    
    logger.info("="*80)
    logger.info("🚀 INICIANDO PIPELINE DE EVALUACIÓN RAGAS")
    logger.info("="*80)
    logger.info(f"Dataset: {dataset_name}")
    logger.info(f"Modo: {'Rápido (5 preguntas)' if quick_mode else 'Completo'}")
    logger.info(f"Reporte: {report_path.name}")
    logger.info("="*80 + "\n")
    
    # Paso 1: Ejecutar evaluación RAGAS
    logger.info("📊 Paso 1/3: Ejecutando evaluación RAGAS...")
    evaluator = RAGASEvaluator()
    report = evaluator.evaluate_dataset(dataset_path, quick_mode=quick_mode)
    
    # Guardar reporte JSON
    evaluator.save_report(report, report_path)
    
    # Mostrar resumen
    evaluator.print_summary(report)
    
    # Paso 2: Generar dashboard de métricas
    logger.info("\n📈 Paso 2/3: Generando dashboard de métricas...")
    dashboard = MetricsDashboard(report_path)
    dashboard.print_dashboard()
    
    # Paso 3: Generar reporte HTML
    if generate_html:
        logger.info("\n📄 Paso 3/3: Generando reporte HTML...")
        html_path = report_path.with_suffix(".html")
        dashboard.export_html_report(html_path)
        logger.info(f"✅ Reporte HTML disponible en: {html_path}")
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("✅ EVALUACIÓN COMPLETADA EXITOSAMENTE")
    logger.info("="*80)
    logger.info(f"📊 Reporte JSON: {report_path}")
    if generate_html:
        logger.info(f"📄 Reporte HTML: {html_path}")
    logger.info(f"⭐ Overall Score: {report.avg_overall_score:.3f}")
    logger.info("="*80 + "\n")
    
    # Retornar paths para uso programático
    return {
        "json_report": report_path,
        "html_report": html_path if generate_html else None,
        "overall_score": report.avg_overall_score
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Orquestador maestro de evaluación RAGAS"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="golden_dataset.json",
        help="Nombre del archivo de dataset (default: golden_dataset.json)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Modo rápido: evalúa solo 5 preguntas"
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="No generar reporte HTML"
    )
    
    args = parser.parse_args()
    
    try:
        run_full_evaluation(
            dataset_name=args.dataset,
            quick_mode=args.quick,
            generate_html=not args.no_html
        )
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Evaluación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error durante la evaluación: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
