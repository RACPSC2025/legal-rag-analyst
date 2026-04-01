"""
Nodos del grafo RAG Legal — Proyecto Fénix.

Patrón: CRAG (Corrective RAG) + Self-RAG + Hierarchical Retrieval
"""

from __future__ import annotations

import logging
from typing import List

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config import get_llm, settings
from src.core.state import RagState
from src.retrieval.hierarchical_retriever import get_hierarchical_retriever
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ====================== NODOS ======================

def retrieve(state: RagState) -> dict:
    """Nodo de recuperación híbrida (BM25 + Vector + FlashRank)."""
    logger.info(f"[RETRIEVE] Pregunta: {state.question}")

    from src.retrieval import get_vector_store
    from src.retrieval.hybrid_search import get_hybrid_retriever
    
    try:
        vector_store = get_vector_store()
        hybrid_retriever = get_hybrid_retriever(vector_store)
        
        # Recuperación Híbrida: BM25 para keywords exactas + Vector para semántica
        # Reranking integrado para seleccionar los mejores 10
        docs = hybrid_retriever.retrieve(state.question, top_k=10)
        
        logger.info(f"[RETRIEVE] {len(docs)} documentos recuperados vía FenixHybridRetriever.")
        return {"documents": docs}

    except Exception as e:
        logger.error(f"[RETRIEVE] Error en Hybrid Retrieval: {e}. Fallback a búsqueda simple.")
        vector_store = get_vector_store()
        docs = vector_store.similarity_search(state.question, k=settings.TOP_K)
        return {"documents": docs}

# ====================== RESTO DE NODOS (sin cambios mayores) ======================

class GradeOutput(BaseModel):
    score: str = Field(description="'si' si el documento es relevante, 'no' en caso contrario.")
    razon: str = Field(description="Explicación breve del veredicto.")


class HallucinationOutput(BaseModel):
    score: str = Field(description="'limpio' o 'alucinacion'")
    razon: str = Field(description="Explicación de la evaluación.")


_GRADE_PROMPT = ChatPromptTemplate.from_messages(
      [
        (
            "system",
            """Eres un juez legal experto colombiano. Tu trabajo es decidir si un fragmento \
de un documento normativo es RELEVANTE para responder una pregunta concreta.

REGLAS CRÍTICAS:
1. Si el fragmento contiene TABLAS, LISTAS de requisitos, CIFRAS o PROCEDIMIENTOS relacionados con la pregunta, DEBES marcarlo como 'si'.
2. No descartes fragmentos densos o técnicos; en derecho, los detalles son la respuesta.
3. Si el fragmento menciona el número del artículo solicitado (ej: 2.2.2.4.11), SIEMPRE di 'si'.
4. Responde 'si' si el fragmento aporta CUALQUIER información útil, aunque no sea la respuesta completa.
5. Solo di 'no' si el fragmento es completamente ajeno al tema de la pregunta.""",
        ),
        ("human", "Pregunta: {question}\n\nFragmento del documento:\n{document}"),
    ]
)

def grade_documents(state: RagState) -> dict:
    """Evalúa relevancia de cada documento recuperado con criterio amplio."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(GradeOutput)
    chain = _GRADE_PROMPT | structured_llm

    relevant_docs: List[Document] = []
    for doc in state.documents:
        try:
            # Evaluamos el contenido completo del chunk (1500 chars) para no perder la tabla
            result = chain.invoke({
                "question": state.question,
                "document": doc.page_content,
            })
            if result.score.strip().lower() == "si":
                relevant_docs.append(doc)
                logger.info(f"[GRADE] ✅ Relevante (Motivo: {result.razon[:80]})")
            else:
                logger.info(f"[GRADE] ❌ Ignorado (Motivo: {result.razon[:80]})")
        except Exception as e:
            logger.warning(f"[GRADE] Error evaluando documento: {e}")

    # Si el grader fue muy estricto y no dejó nada, pero recuperamos documentos, 
    # dejamos pasar al menos los 2 mejores como fallback de seguridad.
    if not relevant_docs and state.documents:
        logger.warning("[GRADE] El evaluador fue demasiado estricto. Aplicando fallback de seguridad.")
        relevant_docs = state.documents[:3]

    return {
        "documents": relevant_docs,
        "grade": "útil" if relevant_docs else "no_útil",
    }


_GENERATE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Eres Legal Agent, un asistente legal especializado en normativa colombiana.

REGLAS ESTRICTAS — incumplirlas está PROHIBIDO:
1. Responde ÚNICAMENTE con información contenida en los DOCUMENTOS FUENTE proporcionados.
2. Si la respuesta no está en los documentos, di exactamente: \
"No dispongo de información suficiente en los documentos disponibles para responder esta pregunta."
3. Al final de CADA PÁRRAFO o punto clave, cita entre paréntesis el artículo/sección y página. \
Formato: (Art. X.X.X, pág. N) o (Sec. Título, pág. N)
4. No añadas opiniones, interpretaciones o conocimiento externo.
5. Usa un lenguaje claro, formal y preciso.""",
        ),
        (
            "human",
            """DOCUMENTOS FUENTE:
{context}

PREGUNTA:
{question}

RESPUESTA:""",
        ),
    ]
)


_RETHINKING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Eres un analista jurídico senior. Tu tarea es extraer pasajes EXACTOS y DATOS TÉCNICOS (tablas, cifras, requisitos) de los documentos para responder una consulta. No resumas, extrae la evidencia literal."),
    ("human", "Consulta: {question}\n\nDocumentos:\n{context}\n\nExtrae los pasajes clave:")
])

def generate(state: RagState) -> dict:
    """Generación con técnica de Two-Step Reading (Rethinking - Módulo 08)."""
    if not state.documents:
        return {
            "generation": "No dispongo de información suficiente en los documentos disponibles para responder esta pregunta.",
            "source_docs": [],
        }

    llm = get_llm()
    
    # Paso 1: Identificar pasajes clave (Rethinking)
    context_list = []
    for i, doc in enumerate(state.documents):
        article = doc.metadata.get("article", "N/A")
        page = doc.metadata.get("page", "?")
        context_list.append(f"[Doc {i+1} - Art. {article} - pág. {page}]:\n{doc.page_content}")
    
    context = "\n\n---\n\n".join(context_list)
    
    key_passages = (_RETHINKING_PROMPT | llm | StrOutputParser()).invoke({
        "question": state.question,
        "context": context
    })
    
    # Paso 2: Generación final con los pasajes identificados
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Eres Legal Agent, asistente experto en normativa colombiana.
        REGLAS ESTRICTAS:
        1. Usa los PASAJES CLAVE extraídos para dar una respuesta técnica y literal.
        2. Si hay TABLAS o listas de negociadores, transcríbelas íntegramente con claridad.
        3. Cita siempre el artículo y página al final de cada punto relevante.
        4. Si la información no es concluyente o faltan datos de la tabla, indícalo.
        5. No añadas opiniones o conocimiento externo."""),
        ("human", "Consulta: {question}\n\nPasajes Clave Identificados:\n{passages}\n\nContexto Completo de Referencia:\n{context}")
    ])
    
    answer = (prompt | llm | StrOutputParser()).invoke({
        "question": state.question,
        "passages": key_passages,
        "context": context
    })

    return {
        "generation": answer,
        "source_docs": list({d.metadata.get("source") for d in state.documents if d.metadata.get("source")}),
        "attempts": state.attempts + 1,
    }


_HALLUCINATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Eres un verificador de precisión factual para documentos legales colombianos.

Tu tarea: comparar la RESPUESTA GENERADA contra los DOCUMENTOS FUENTE y detectar \
si la respuesta contiene afirmaciones que NO están respaldadas por los documentos.

REGLAS:
- score = 'limpio': TODA afirmación de la respuesta tiene respaldo explícito en los documentos.
- score = 'alucinacion': al menos UNA afirmación no está en los documentos o está distorsionada.
- Sé estricto. En dominio legal, una invención puede tener consecuencias graves.""",
        ),
        (
            "human",
            """DOCUMENTOS FUENTE:
{documents}

RESPUESTA GENERADA:
{generation}""",
        ),
    ]
)


def check_hallucination(state: RagState) -> dict:
    """Verifica que la respuesta generada esté completamente respaldada."""
    if not state.documents:
        return {"grade": "no_útil", "hallucination_score": 0.0}

    # Aumentamos a 1500 para que el verificador vea la tabla completa
    context = "\n---\n".join(doc.page_content[:1500] for doc in state.documents)

    llm = get_llm()
    structured_llm = llm.with_structured_output(HallucinationOutput)
    chain = _HALLUCINATION_PROMPT | structured_llm

    try:
        result: HallucinationOutput = chain.invoke(
            {
                "documents": context,
                "generation": state.generation,
            }
        )

        if result.score.strip().lower() == "limpio":
            logger.info(
                f"[HALLUCINATION] ✅ Respuesta verificada — {result.razon[:80]}"
            )
            return {"grade": "útil", "hallucination_score": 0.0}
        else:
            logger.warning(
                f"[HALLUCINATION] ⚠️ Posible alucinación — {result.razon[:80]}"
            )
            return {"grade": "alucinación", "hallucination_score": 0.9}

    except Exception as e:
        logger.error(
            f"[HALLUCINATION] Error en verificación: {e}. Se aprueba por defecto."
        )
        return {"grade": "útil", "hallucination_score": 0.0}


def no_answer(state: RagState) -> dict:
    return {
        "generation": (
            "⚠️ No se encontró información relevante en los documentos indexados "
            "para responder su consulta legal. Por favor reformule la pregunta "
            "o sea más específico con el número del artículo."
        ),
        "source_docs": [],
    }
