"""
Servicio PDF Directo - Versión FINAL Anti-Alucinación (Legal Colombia)
"""

import logging
import re
from pathlib import Path
from typing import List

import fitz
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config import settings

logger = logging.getLogger(__name__)

# Prompt ultra-estricto
_DIRECT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Eres Agent Layer, asistente legal colombiano. 

REGLAS ABSOLUTAS (violarlas es inaceptable):
- Copia ÚNICAMENTE texto que exista literalmente en el documento.
- Nunca agregues, inventes, completes ni parafrasees principios o párrafos.
- Si el artículo tiene solo 2 puntos, responde SOLO con esos 2 puntos.
- Nunca agregues listas de más puntos ni párrafos de conclusión como "Estos principios buscan...".
- Si no puedes copiar el artículo completo literalmente, responde exactamente:
  "No encontré información relevante en el documento para responder esta pregunta."

Precisión jurídica > todo. Solo copia literal."""),

    ("human", """DOCUMENTO (solo el texto relevante del PDF):

{context}

PREGUNTA: {question}

Responde copiando **literal y exactamente** el artículo solicitado. 
No agregues nada que no esté escrito en el documento.
Si no está completo o no lo encuentras, usa exactamente: "No encontré información relevante en el documento para responder esta pregunta."

RESPUESTA:""")
])

def _clean_text_basic(text: str) -> str:
    """Limpieza básica para contexto LLM - NO altera estructura de saltos ni inserta formato."""
    if not text:
        return ""
    # Limpieza de ruidos de encabezados/pies de página
    text = re.sub(r"Departamento Administrativo de la Función Pública", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Decreto 1072 de 2015 Sector Trabajo\s*\d+\s*EVA - Gestor Normativo", "", text, flags=re.IGNORECASE)
    text = re.sub(r"_{4,}|-{4,}", "", text)
    text = re.sub(r"\[Página \d+\]", "", text)
    
    # Normalizar solo saltos excesivos, mantener estructura de líneas base del PDF
    text = re.sub(r"\n{4,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()

def _format_legal_output(text: str) -> str:
    """Formatea la respuesta final para el usuario: une líneas rotas y añade saltos en parágrafos."""
    if not text:
        return ""
    # Unir líneas que quedaron rotas por el PDF (palabras separadas por un solo salto)
    text = re.sub(r"(\w)\n(\w)", r"\1 \2", text)
    
    # --- MEJORA DE LEGIBILIDAD ---
    # Insertar salto de línea antes de cada PARÁGRAFO
    text = re.sub(r"([\.])?\s*(PARÁGRAFO\s*\d+[:\.]?)", r"\1\n\n\2", text, flags=re.IGNORECASE)
    
    # Insertar salto de línea antes de citas bibliográficas finales
    text = re.sub(r"\s*(\(Decreto\s*\d+\s*de\s*\d+.*?\))", r"\n\n\1", text)
    
    # Limpiar excesos
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()

def _extract_exact_article(text: str, article_num: str = "2.2.6.9.3.2") -> str:
    """Extrae el artículo solicitado con una regex más flexible y amplia."""
    # Captura desde el ARTÍCULO hasta el siguiente marcador mayor o fin de texto
    pattern = rf"(ARTÍCULO\s*{re.escape(article_num)}.*?(?=\nARTÍCULO|\nCAPÍTULO|\nPARTE|\Z))"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        # Devolvemos el texto con limpieza básica para el LLM
        return _clean_text_basic(match.group(1).strip())
    return ""

def get_large_context_llm():
    from langchain_aws import ChatBedrock
    import boto3
    
    model_id = settings.AWS_MODEL_LARGE_CONTEXT
    provider = "amazon" if "nova" in model_id.lower() else "meta"
    
    # Crear sesión explícita para asegurar credenciales
    session = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN if settings.AWS_SESSION_TOKEN else None,
        region_name=settings.AWS_REGION,
    )
    client = session.client("bedrock-runtime", region_name=settings.AWS_REGION)
    
    return ChatBedrock(
        client=client,
        model_id=model_id,
        provider=provider,
        temperature=0.0,
        max_tokens=2048,
        region_name=settings.AWS_REGION,
    )

def query_pdf_direct(pdf_paths: List[str | Path], question: str) -> dict:
    logger.info(f"[PDF_DIRECT] Procesando {len(pdf_paths)} PDF(s)")

    full_text = ""
    sources = []
    for pdf_path in pdf_paths:
        try:
            doc = fitz.open(str(pdf_path))
            for page in doc:
                full_text += page.get_text("text") + "\n\n"
            doc.close()
            sources.append(Path(pdf_path).name)
        except Exception as e:
            logger.error(f"Error: {e}")

    if not full_text.strip():
        return {"answer": "No se pudieron cargar los PDFs proporcionados.", "source_docs": [], "mode": "pdf_direct"}

    # Limpieza básica inicial
    clean_full = _clean_text_basic(full_text)

    # Detectar el número de artículo solicitado
    article_match = re.search(r"(\d+(\.\d+)*)", question)
    requested_article = article_match.group(1) if article_match else None

    # Extracción estructurada del artículo
    exact_article = ""
    if requested_article:
        exact_article = _extract_exact_article(clean_full, requested_article)
        if exact_article:
            logger.info(f"[PDF_DIRECT] Art. {requested_article} extraído con éxito.")
        else:
            logger.warning(f"[PDF_DIRECT] No se pudo extraer Art. {requested_article} literalmente.")

    # Contexto para el LLM (literal)
    context_to_llm = exact_article if exact_article else clean_full[:150000]

    llm = get_large_context_llm()
    chain = _DIRECT_PROMPT | llm | StrOutputParser()

    try:
        # El LLM genera la respuesta literal
        answer = chain.invoke({"context": context_to_llm, "question": question})
        
        # Aplicamos el formateo de legibilidad SOLO a la respuesta final
        answer = _format_legal_output(answer)

        # Validación final fuerte contra alucinaciones
        if any(x in answer for x in ["3.", "4.", "5.", "6.", "7.", "8.", "9.", "10."]) and "Estos principios buscan" in answer:
            answer = "No encontré información relevante en el documento para responder esta pregunta."

    except Exception as e:
        logger.error(f"Error LLM: {e}")
        answer = "Error al procesar el documento."

    return {
        "answer": answer,
        "source_docs": sources,
        "mode": "pdf_direct",
    }