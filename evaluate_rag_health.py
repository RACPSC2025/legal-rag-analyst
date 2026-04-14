
import re
import os
import sys
import json
import time
import pandas as pd
from pathlib import Path
from typing import List, Dict

# Configurar el PATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings, get_llm
from src.core import get_graph, RagState
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress

console = Console()

class EvaluationScore(BaseModel):
    faithfulness: int = Field(description="Puntuación de 0 a 5 sobre qué tan bien la respuesta se basa en los documentos.")
    completeness: int = Field(description="Puntuación de 0 a 5 sobre si la respuesta incluye todos los datos clave (como tablas).")
    citation_quality: int = Field(description="Puntuación de 0 a 5 sobre la precisión de las citas de artículos y páginas.")
    reasoning: str = Field(description="Breve explicación del veredicto del juez.")

GOLDEN_SET = [
    {
        "id": "Q1",
        "question": "¿Qué dice el artículo 2.2.2.4.11 sobre la tabla de negociadores por organización sindical?",
        "intent": "Verificar la recuperación íntegra de tablas complejas y cifras exactas."
    },
    {
        "id": "Q2",
        "question": "¿Cuál es el número máximo de negociadores en el ámbito nacional según el artículo 2.2.2.4.10?",
        "intent": "Validar la discriminación entre artículos similares (2.4.10 vs 2.4.11)."
    },
    {
        "id": "Q3",
        "question": "Describa la participación de la mujer sindicalista según el parágrafo 2 del artículo 2.2.2.4.10.",
        "intent": "Comprobar el manejo de parágrafos específicos y precisión de puntero legal."
    },
    {
        "id": "Q4",
        "question": "¿Qué requisitos de comparecencia se mencionan para conformar la Comisión Unificada Sindical?",
        "intent": "Evaluar la capacidad de síntesis de requisitos distribuidos en el texto."
    }
]

def get_judge_llm():
    """Usa Amazon Nova Pro como juez evaluador para máxima estabilidad."""
    from langchain_aws import ChatBedrock
    # Usamos Nova Pro (Nativo de Amazon para evitar errores de provider con Llama)
    model_id = "us.amazon.nova-pro-v1:0" 
    return ChatBedrock(
        model_id=model_id,
        provider="amazon",
        temperature=0.0,
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

def run_evaluation():
    console.print("[bold cyan]🚀 Iniciando Dashboard de Evaluación - Salud del RAG Legal[/bold cyan]\n")
    
    graph = get_graph()
    judge = get_judge_llm()
    # No usamos parser directo para mayor robustez manual
    
    results = []
    
    with Progress() as progress:
        task = progress.add_task("[green]Evaluando consultas...", total=len(GOLDEN_SET))
        
        for item in GOLDEN_SET:
            # 1. Ejecutar RAG
            start_time = time.time()
            state_input = RagState(question=item["question"])
            final_state = graph.invoke(state_input)
            latency = time.time() - start_time
            
            answer = final_state.get("generation", "Error en generación")
            docs = final_state.get("documents", [])
            context_text = "\n---\n".join([d.page_content for d in docs])
            
            # 2. Juzgar resultado
            eval_prompt = f"""Eres un Juez Auditor de Calidad para sistemas RAG Legales.
            Evalúa la RESPUESTA DEL SISTEMA basándote en el CONTEXTO RECUPERADO.
            
            CONTEXTO RECUPERADO:
            {context_text}
            
            PREGUNTA DEL USUARIO:
            {item['question']}
            
            RESPUESTA DEL SISTEMA:
            {answer}
            
            INSTRUCCIÓN: Responde EXCLUSIVAMENTE con un objeto JSON que tenga estos campos exactos:
            - faithfulness: (0-5) Puntuación de fidelidad al contexto.
            - completeness: (0-5) Puntuación de integridad (¿está la tabla completa?).
            - citation_quality: (0-5) Puntuación de citas precisas.
            - reasoning: Breve explicación del veredicto.
            """
            
            try:
                response = judge.invoke([
                    HumanMessage(content=eval_prompt)
                ])
                # Limpiar Markdown si existe (regex robusto para code blocks)
                raw_content = response.content if isinstance(response.content, str) else ""
                raw_content = re.sub(r"```(?:json)?\s*", "", raw_content)
                raw_content = re.sub(r"```\s*", "", raw_content)
                raw_content = raw_content.strip()
                score = json.loads(raw_content)
            except Exception as e:
                console.print(f"[red]Error evaluando {item['id']}: {e}[/red]")
                score = {"faithfulness": 0, "completeness": 0, "citation_quality": 0, "reasoning": f"Fallo: {e}"}

            results.append({
                "ID": item["id"],
                "Pregunta": item["question"],
                "Fidelidad": score.get("faithfulness", 0),
                "Integridad": score.get("completeness", 0),
                "Citas": score.get("citation_quality", 0),
                "Latencia": f"{latency:.2f}s",
                "Razonamiento": score.get("reasoning", "N/A")
            })
            
            progress.update(task, advance=1)

    # 3. Generar Informe
    df = pd.DataFrame(results)
    
    # Calcular promedios
    avg_faith = df["Fidelidad"].mean()
    avg_comp = df["Integridad"].mean()
    avg_cit = df["Citas"].mean()
    
    report_path = PROJECT_ROOT / "logs" / "RAG_HEALTH_REPORT.md"
    os.makedirs(PROJECT_ROOT / "logs", exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# ⚖️ Informe de Salud RAG - Analista Jurídico\n\n")
        f.write(f"**Fecha:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Puntuación General (Promedio):** {((avg_faith + avg_comp + avg_cit)/3):.2f}/5.0\n\n")
        
        f.write("## 📊 Métricas Clave\n")
        f.write(f"- **Fidelidad Literal:** {avg_faith:.2f}/5\n")
        f.write(f"- **Integridad de Datos/Tablas:** {avg_comp:.2f}/5\n")
        f.write(f"- **Calidad de Citas:** {avg_cit:.2f}/5\n\n")
        
        f.write("## 📝 Detalle por Consulta\n")
        f.write(df.to_markdown(index=False))
        
    console.print(f"\n✅ [bold green]Evaluación completada.[/bold green] Informe generado en: [bold white]{report_path}[/bold white]")
    
    # Mostrar resumen en consola
    console.print("\n[bold yellow]Resumen de Rendimiento:[/bold yellow]")
    console.print(f"Fidelidad: {avg_faith}/5 | Integridad: {avg_comp}/5 | Citas: {avg_cit}/5")

if __name__ == "__main__":
    run_evaluation()
