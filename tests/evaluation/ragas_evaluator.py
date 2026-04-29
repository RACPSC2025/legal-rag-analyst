"""
RAGAS Evaluator — Sistema de Evaluación de Calidad RAG Legal
────────────────────────────────────────────────────────────
Evalúa el sistema RAG usando métricas RAGAS:
  • Faithfulness: Fidelidad de la respuesta a los documentos fuente
  • Answer Relevancy: Relevancia de la respuesta a la pregunta
  • Context Precision: Precisión de los documentos recuperados
  • Context Recall: Cobertura de la ground truth en el contexto
  • Answer Correctness: Exactitud de la respuesta vs ground truth

Uso:
    python tests/evaluation/ragas_evaluator.py --dataset golden_dataset.json
    python tests/evaluation/ragas_evaluator.py --quick  # Solo 5 preguntas

Autor: Fenix Tech Líder
Fecha: 2026-04-27
Versión: 1.0.0
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Añadir src al path para imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.graph import query as rag_query
from src.retrieval import get_vector_store, get_document_count

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)

# ── Dataclasses para resultados ──────────────────────────────────────────────

@dataclass
class RAGASMetrics:
    """Métricas RAGAS para una pregunta individual."""
    question_id: str
    faithfulness: float          # 0.0-1.0: Fidelidad a documentos fuente
    answer_relevancy: float      # 0.0-1.0: Relevancia de respuesta
    context_precision: float     # 0.0-1.0: Precisión de docs recuperados
    context_recall: float        # 0.0-1.0: Cobertura de ground truth
    answer_correctness: float    # 0.0-1.0: Exactitud vs ground truth
    latency_seconds: float       # Tiempo de respuesta
    tokens_used: int             # Tokens consumidos (estimado)
    
    def overall_score(self) -> float:
        """Score promedio ponderado."""
        return (
            self.faithfulness * 0.30 +
            self.answer_relevancy * 0.25 +
            self.context_precision * 0.20 +
            self.context_recall * 0.15 +
            self.answer_correctness * 0.10
        )

@dataclass
class EvaluationResult:
    """Resultado completo de evaluación de una pregunta."""
    question_id: str
    category: str
    question: str
    ground_truth: str
    generated_answer: str
    retrieved_docs: List[str]
    metrics: RAGASMetrics
    error: Optional[str] = None

@dataclass
class EvaluationReport:
    """Reporte agregado de toda la evaluación."""
    dataset_name: str
    evaluation_date: str
    total_questions: int
    successful_evaluations: int
    failed_evaluations: int
    avg_faithfulness: float
    avg_answer_relevancy: float
    avg_context_precision: float
    avg_context_recall: float
    avg_answer_correctness: float
    avg_overall_score: float
    avg_latency_seconds: float
    total_tokens_used: int
    results: List[EvaluationResult]

# ── Evaluadores de métricas individuales ─────────────────────────────────────

class FaithfulnessEvaluator:
    """
    Evalúa si la respuesta está fundamentada en los documentos recuperados.
    
    Método: Verifica que cada afirmación en la respuesta tenga soporte
    en al menos uno de los documentos fuente.
    """
    
    @staticmethod
    def evaluate(answer: str, context_docs: List[str]) -> float:
        """
        Calcula el score de faithfulness.
        
        Args:
            answer: Respuesta generada por el RAG.
            context_docs: Lista de documentos recuperados.
            
        Returns:
            Score 0.0-1.0 (1.0 = totalmente fiel).
        """
        if not answer or not context_docs:
            return 0.0
        
        # Combinar todos los documentos en un solo contexto
        full_context = " ".join(context_docs).lower()
        
        # Dividir respuesta en oraciones (heurística simple)
        import re
        sentences = [s.strip() for s in re.split(r'[.!?]+', answer) if s.strip()]
        
        if not sentences:
            return 0.0
        
        # Contar cuántas oraciones tienen soporte en el contexto
        supported = 0
        for sentence in sentences:
            # Extraer palabras clave de la oración (> 4 caracteres)
            keywords = set(re.findall(r'\b\w{4,}\b', sentence.lower()))
            if not keywords:
                continue
            
            # Verificar si al menos 60% de las keywords están en el contexto
            found = sum(1 for kw in keywords if kw in full_context)
            if found / len(keywords) >= 0.6:
                supported += 1
        
        return supported / len(sentences)


class AnswerRelevancyEvaluator:
    """
    Evalúa qué tan relevante es la respuesta para la pregunta.
    
    Método: Calcula similitud léxica entre pregunta y respuesta.
    """
    
    @staticmethod
    def evaluate(question: str, answer: str) -> float:
        """
        Calcula el score de relevancia.
        
        Args:
            question: Pregunta del usuario.
            answer: Respuesta generada.
            
        Returns:
            Score 0.0-1.0 (1.0 = máxima relevancia).
        """
        if not question or not answer:
            return 0.0
        
        import re
        
        # Extraer keywords de la pregunta (> 3 caracteres, sin stopwords)
        stopwords = {'que', 'cual', 'cuales', 'como', 'cuando', 'donde', 'quien', 
                     'para', 'por', 'con', 'sin', 'sobre', 'entre', 'son', 'es'}
        
        q_keywords = set(
            w.lower() for w in re.findall(r'\b\w{4,}\b', question)
            if w.lower() not in stopwords
        )
        
        if not q_keywords:
            return 0.5  # Pregunta muy corta, score neutro
        
        # Contar cuántas keywords de la pregunta aparecen en la respuesta
        answer_lower = answer.lower()
        found = sum(1 for kw in q_keywords if kw in answer_lower)
        
        # Score base por overlap
        overlap_score = found / len(q_keywords)
        
        # Bonus si la respuesta no es genérica (tiene contenido específico)
        specific_indicators = ['artículo', 'ley', 'decreto', 'resolución', 'parágrafo']
        has_specific = any(ind in answer_lower for ind in specific_indicators)
        
        if has_specific:
            overlap_score = min(1.0, overlap_score + 0.2)
        
        return overlap_score


class ContextPrecisionEvaluator:
    """
    Evalúa si los documentos recuperados son relevantes para la pregunta.
    
    Método: Verifica que los documentos contengan keywords de la pregunta.
    """
    
    @staticmethod
    def evaluate(question: str, context_docs: List[str]) -> float:
        """
        Calcula el score de precisión del contexto.
        
        Args:
            question: Pregunta del usuario.
            context_docs: Documentos recuperados.
            
        Returns:
            Score 0.0-1.0 (1.0 = todos los docs son relevantes).
        """
        if not question or not context_docs:
            return 0.0
        
        import re
        
        # Extraer keywords de la pregunta
        stopwords = {'que', 'cual', 'cuales', 'como', 'cuando', 'donde', 'quien'}
        q_keywords = set(
            w.lower() for w in re.findall(r'\b\w{4,}\b', question)
            if w.lower() not in stopwords
        )
        
        if not q_keywords:
            return 0.5
        
        # Evaluar cada documento
        relevant_docs = 0
        for doc in context_docs:
            doc_lower = doc.lower()
            # Doc es relevante si contiene al menos 40% de las keywords
            found = sum(1 for kw in q_keywords if kw in doc_lower)
            if found / len(q_keywords) >= 0.4:
                relevant_docs += 1
        
        return relevant_docs / len(context_docs)


class ContextRecallEvaluator:
    """
    Evalúa si el contexto recuperado cubre la ground truth.
    
    Método: Verifica que elementos clave de la ground truth estén en el contexto.
    """
    
    @staticmethod
    def evaluate(ground_truth: str, context_docs: List[str]) -> float:
        """
        Calcula el score de recall del contexto.
        
        Args:
            ground_truth: Respuesta esperada.
            context_docs: Documentos recuperados.
            
        Returns:
            Score 0.0-1.0 (1.0 = ground truth completamente cubierta).
        """
        if not ground_truth or not context_docs:
            return 0.0
        
        import re
        
        # Extraer elementos clave de la ground truth
        # (números, artículos, conceptos legales)
        gt_lower = ground_truth.lower()
        
        # Patrones importantes: números, artículos, porcentajes
        important_patterns = [
            r'\d+',                    # Números
            r'artículo\s+[\d\.]+',     # Artículos
            r'\d+%',                   # Porcentajes
            r'ley\s+\d+',              # Leyes
            r'decreto\s+\d+',          # Decretos
        ]
        
        gt_elements = set()
        for pattern in important_patterns:
            gt_elements.update(re.findall(pattern, gt_lower))
        
        # Extraer también keywords importantes (> 5 caracteres)
        gt_keywords = set(re.findall(r'\b\w{6,}\b', gt_lower))
        gt_elements.update(gt_keywords)
        
        if not gt_elements:
            return 0.5  # Ground truth muy genérica
        
        # Verificar cuántos elementos están en el contexto
        full_context = " ".join(context_docs).lower()
        found = sum(1 for elem in gt_elements if elem in full_context)
        
        return found / len(gt_elements)


class AnswerCorrectnessEvaluator:
    """
    Evalúa la exactitud de la respuesta comparada con la ground truth.
    
    Método: Similitud semántica y léxica entre respuesta y ground truth.
    """
    
    @staticmethod
    def evaluate(generated_answer: str, ground_truth: str) -> float:
        """
        Calcula el score de correctness.
        
        Args:
            generated_answer: Respuesta generada.
            ground_truth: Respuesta esperada.
            
        Returns:
            Score 0.0-1.0 (1.0 = respuesta perfecta).
        """
        if not generated_answer or not ground_truth:
            return 0.0
        
        import re
        
        # Normalizar textos
        gen_lower = generated_answer.lower()
        gt_lower = ground_truth.lower()
        
        # Extraer keywords de ground truth
        gt_keywords = set(re.findall(r'\b\w{4,}\b', gt_lower))
        
        if not gt_keywords:
            return 0.5
        
        # Contar overlap de keywords
        found = sum(1 for kw in gt_keywords if kw in gen_lower)
        keyword_score = found / len(gt_keywords)
        
        # Verificar elementos estructurales (números, artículos)
        gt_numbers = set(re.findall(r'\d+', gt_lower))
        gen_numbers = set(re.findall(r'\d+', gen_lower))
        
        if gt_numbers:
            number_score = len(gt_numbers & gen_numbers) / len(gt_numbers)
        else:
            number_score = 1.0
        
        # Score combinado (70% keywords, 30% números)
        return keyword_score * 0.7 + number_score * 0.3


# ── Orquestador principal ────────────────────────────────────────────────────

class RAGASEvaluator:
    """
    Orquestador principal de evaluación RAGAS.
    """
    
    def __init__(self):
        self.faithfulness_eval = FaithfulnessEvaluator()
        self.relevancy_eval = AnswerRelevancyEvaluator()
        self.precision_eval = ContextPrecisionEvaluator()
        self.recall_eval = ContextRecallEvaluator()
        self.correctness_eval = AnswerCorrectnessEvaluator()
    
    def evaluate_single_question(
        self, 
        test_case: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evalúa una pregunta individual del dataset.
        
        Args:
            test_case: Diccionario con question, ground_truth, etc.
            
        Returns:
            EvaluationResult con métricas completas.
        """
        question_id = test_case["id"]
        question = test_case["question"]
        ground_truth = test_case["ground_truth"]
        category = test_case["category"]
        
        logger.info(f"[{question_id}] Evaluando: {question[:80]}...")
        
        try:
            # Ejecutar el RAG
            start_time = time.time()
            result = rag_query(question)
            latency = time.time() - start_time
            
            generated_answer = result.get("answer", "")
            source_docs = result.get("source_docs", [])
            
            # Estimar tokens (heurística: ~4 caracteres por token)
            tokens_used = (len(question) + len(generated_answer)) // 4
            
            # Calcular métricas RAGAS
            faithfulness = self.faithfulness_eval.evaluate(
                generated_answer, source_docs
            )
            
            answer_relevancy = self.relevancy_eval.evaluate(
                question, generated_answer
            )
            
            context_precision = self.precision_eval.evaluate(
                question, source_docs
            )
            
            context_recall = self.recall_eval.evaluate(
                ground_truth, source_docs
            )
            
            answer_correctness = self.correctness_eval.evaluate(
                generated_answer, ground_truth
            )
            
            metrics = RAGASMetrics(
                question_id=question_id,
                faithfulness=faithfulness,
                answer_relevancy=answer_relevancy,
                context_precision=context_precision,
                context_recall=context_recall,
                answer_correctness=answer_correctness,
                latency_seconds=round(latency, 2),
                tokens_used=tokens_used
            )
            
            logger.info(
                f"[{question_id}] ✅ Evaluado | "
                f"Overall: {metrics.overall_score():.2f} | "
                f"Faithfulness: {faithfulness:.2f} | "
                f"Relevancy: {answer_relevancy:.2f}"
            )
            
            return EvaluationResult(
                question_id=question_id,
                category=category,
                question=question,
                ground_truth=ground_truth,
                generated_answer=generated_answer,
                retrieved_docs=source_docs,
                metrics=metrics,
                error=None
            )
        
        except Exception as e:
            logger.error(f"[{question_id}] ❌ Error: {e}")
            
            # Retornar resultado con error
            return EvaluationResult(
                question_id=question_id,
                category=category,
                question=question,
                ground_truth=ground_truth,
                generated_answer="",
                retrieved_docs=[],
                metrics=RAGASMetrics(
                    question_id=question_id,
                    faithfulness=0.0,
                    answer_relevancy=0.0,
                    context_precision=0.0,
                    context_recall=0.0,
                    answer_correctness=0.0,
                    latency_seconds=0.0,
                    tokens_used=0
                ),
                error=str(e)
            )
    
    def evaluate_dataset(
        self, 
        dataset_path: Path,
        quick_mode: bool = False
    ) -> EvaluationReport:
        """
        Evalúa todo el dataset.
        
        Args:
            dataset_path: Ruta al archivo JSON del dataset.
            quick_mode: Si True, solo evalúa 5 preguntas.
            
        Returns:
            EvaluationReport con resultados agregados.
        """
        logger.info(f"📊 Cargando dataset: {dataset_path}")
        
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
        
        test_cases = dataset["test_cases"]
        
        if quick_mode:
            test_cases = test_cases[:5]
            logger.info("⚡ Modo rápido: evaluando solo 5 preguntas")
        
        logger.info(f"📋 Total de preguntas a evaluar: {len(test_cases)}")
        logger.info(f"📚 Documentos indexados: {get_document_count()}")
        
        # Evaluar cada pregunta
        results: List[EvaluationResult] = []
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"Pregunta {i}/{len(test_cases)}")
            logger.info(f"{'='*80}")
            
            result = self.evaluate_single_question(test_case)
            results.append(result)
            
            # Pausa entre preguntas para no saturar Bedrock
            if i < len(test_cases):
                time.sleep(2)
        
        # Calcular métricas agregadas
        successful = [r for r in results if r.error is None]
        failed = [r for r in results if r.error is not None]
        
        if successful:
            avg_faithfulness = sum(r.metrics.faithfulness for r in successful) / len(successful)
            avg_relevancy = sum(r.metrics.answer_relevancy for r in successful) / len(successful)
            avg_precision = sum(r.metrics.context_precision for r in successful) / len(successful)
            avg_recall = sum(r.metrics.context_recall for r in successful) / len(successful)
            avg_correctness = sum(r.metrics.answer_correctness for r in successful) / len(successful)
            avg_overall = sum(r.metrics.overall_score() for r in successful) / len(successful)
            avg_latency = sum(r.metrics.latency_seconds for r in successful) / len(successful)
            total_tokens = sum(r.metrics.tokens_used for r in successful)
        else:
            avg_faithfulness = avg_relevancy = avg_precision = 0.0
            avg_recall = avg_correctness = avg_overall = 0.0
            avg_latency = total_tokens = 0
        
        report = EvaluationReport(
            dataset_name=dataset["dataset_info"]["name"],
            evaluation_date=datetime.now().isoformat(),
            total_questions=len(test_cases),
            successful_evaluations=len(successful),
            failed_evaluations=len(failed),
            avg_faithfulness=round(avg_faithfulness, 3),
            avg_answer_relevancy=round(avg_relevancy, 3),
            avg_context_precision=round(avg_precision, 3),
            avg_context_recall=round(avg_recall, 3),
            avg_answer_correctness=round(avg_correctness, 3),
            avg_overall_score=round(avg_overall, 3),
            avg_latency_seconds=round(avg_latency, 2),
            total_tokens_used=total_tokens,
            results=results
        )
        
        return report
    
    def save_report(self, report: EvaluationReport, output_path: Path):
        """Guarda el reporte en formato JSON."""
        report_dict = asdict(report)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Reporte guardado en: {output_path}")
    
    def print_summary(self, report: EvaluationReport):
        """Imprime un resumen del reporte en consola."""
        print("\n" + "="*80)
        print("📊 RESUMEN DE EVALUACIÓN RAGAS")
        print("="*80)
        print(f"Dataset: {report.dataset_name}")
        print(f"Fecha: {report.evaluation_date}")
        print(f"Total preguntas: {report.total_questions}")
        print(f"Exitosas: {report.successful_evaluations}")
        print(f"Fallidas: {report.failed_evaluations}")
        print("\n" + "-"*80)
        print("MÉTRICAS PROMEDIO")
        print("-"*80)
        print(f"Overall Score:        {report.avg_overall_score:.3f} ⭐")
        print(f"Faithfulness:         {report.avg_faithfulness:.3f}")
        print(f"Answer Relevancy:     {report.avg_answer_relevancy:.3f}")
        print(f"Context Precision:    {report.avg_context_precision:.3f}")
        print(f"Context Recall:       {report.avg_context_recall:.3f}")
        print(f"Answer Correctness:   {report.avg_answer_correctness:.3f}")
        print("\n" + "-"*80)
        print("RENDIMIENTO")
        print("-"*80)
        print(f"Latencia promedio:    {report.avg_latency_seconds:.2f}s")
        print(f"Tokens totales:       {report.total_tokens_used:,}")
        print("="*80 + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Evaluador RAGAS para RAG Legal Colombiano"
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
        "--output",
        type=str,
        default=None,
        help="Ruta de salida para el reporte (default: auto-generado)"
    )
    
    args = parser.parse_args()
    
    # Rutas
    eval_dir = Path(__file__).parent
    dataset_path = eval_dir / args.dataset
    
    if not dataset_path.exists():
        logger.error(f"❌ Dataset no encontrado: {dataset_path}")
        sys.exit(1)
    
    # Generar nombre de reporte
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode = "quick" if args.quick else "full"
        output_path = eval_dir / f"ragas_report_{mode}_{timestamp}.json"
    
    # Ejecutar evaluación
    evaluator = RAGASEvaluator()
    
    logger.info("🚀 Iniciando evaluación RAGAS...")
    report = evaluator.evaluate_dataset(dataset_path, quick_mode=args.quick)
    
    # Guardar y mostrar resultados
    evaluator.save_report(report, output_path)
    evaluator.print_summary(report)
    
    logger.info("✅ Evaluación completada exitosamente")


if __name__ == "__main__":
    main()
