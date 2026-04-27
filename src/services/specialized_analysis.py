import logging
import re
import json
from pathlib import Path
from typing import List

import fitz
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.config import settings
from src.services.pdf_direct_service import get_large_context_llm

logger = logging.getLogger(__name__)


def _clean_text_basic(text: str) -> str:
    """Limpieza básica de ruidos de encabezados/pies de página del Decreto 1072."""
    if not text:
        return ""
    text = re.sub(r"Departamento Administrativo de la Función Pública", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Decreto 1072 de 2015 Sector Trabajo\s*\d+\s*EVA - Gestor Normativo", "", text, flags=re.IGNORECASE)
    text = re.sub(r"_{4,}|-{4,}", "", text)
    text = re.sub(r"\[Página \d+\]", "", text)
    text = re.sub(r"\n{4,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()

# --- PROMPT ESPECIALIZADO (SUMINISTRADO) ---
_SPECIALIZED_SYSTEM_PROMPT = """Eres un asistente legal especializado en análisis crítico de documentos jurídicos. 
Analiza ÚNICAMENTE el texto y la estructura proporcionados (sin acceso a fuentes externas) y genera un análisis 
PROFUNDO centrado en aspectos que no son evidentes en una lectura superficial. Tu análisis debe 
proporcionar perspectivas valiosas basadas exclusivamente en el contenido del documento. 

Genera un análisis ESTRICTAMENTE en formato JSON con la siguiente estructura:
{{
 "tipo_documento": "tipo de documento identificado",
 "tono_general": "imperativo/informativo/regulatorio/etc - analiza el tono dominante",
 "nivel_urgencia": 0,
 "nivel_coercion": 0,
 "obligaciones_criticas": [
    {{
        "texto": "texto de la obligación", 
        "sujeto": "responsable", 
        "plazo": "plazo identificado", 
        "consecuencia_incumplimiento": "multa/sanción identificada", 
        "nivel_criticidad": 1
    }}
 ],
 "temas_principales": ["lista de temas"],
 "plazos_inmediatos": ["lista de plazos"],
 "ambigüedades_identificadas": ["posibles imprecisiones"],
 "definiciones_clave": {{
    "término": "definición"
 }},
 "excepciones_mencionadas": ["excepciones"],
 "entidades_afectadas": ["entidades"],
 "referencias_internas": ["artículos/secciones"],
 "menciones_de_otras_leyes": ["nombres de leyes"],
 "analisis_critico": "análisis estratégico enfocado en aspectos no evidentes"
}}
"""

_SPECIALIZED_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SPECIALIZED_SYSTEM_PROMPT),
    ("human", "DOCUMENTO:\n\n{context}\n\nPREGUNTA ESPECÍFICA (si la hay):\n{question}\n\nResponde únicamente el JSON.")
])

def query_specialized_analysis(pdf_paths: List[str | Path], question: str) -> dict:
    """Ejecuta el análisis crítico especializado retornando JSON."""
    logger.info(f"[SPECIALIZED] Iniciando análisis para {len(pdf_paths)} PDFs")
    
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
            logger.error(f"Error cargando PDF: {e}")

    if not full_text.strip():
        return {"answer": "Error: No se pudo extraer texto.", "source_docs": [], "mode": "specialized"}

    # Usamos la limpieza básica para no perder nada del contenido original
    context = _clean_text_basic(full_text)[:180000] # Límite amplio para Nova 2 Lite
    
    llm = get_large_context_llm()
    chain = _SPECIALIZED_PROMPT | llm | StrOutputParser()

    try:
        response = chain.invoke({"context": context, "question": question})
        
        # Limpiar posibles bloques de código markdown ```json ... ```
        clean_response = re.sub(r"```json\s?|```", "", response).strip()
        
        # Validar si es JSON válido (opcional, para asegurar que el LLM cumplió)
        json.loads(clean_response) 
        
        return {
            "answer": clean_response,
            "source_docs": sources,
            "mode": "specialized"
        }
    except Exception as e:
        logger.error(f"Error en Análisis Especializado: {e}")
        return {
            "answer": f"Error procesando el análisis especializado: {str(e)}",
            "source_docs": sources,
            "mode": "specialized"
        }
