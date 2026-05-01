"""
Nodos del grafo RAG Legal — Proyecto Fénix v2.5.

Patrón: CRAG (Corrective RAG) + Self-RAG + Hierarchical Retrieval + Verifiable Generation
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config import get_llm, settings
from src.core.state import RagState
from src.retrieval.hierarchical_retriever import get_hierarchical_retriever
from src.cache import legal_cache
from src.schemas.graph_outputs import GradeOutput, HallucinationOutput
from src.schemas.legal_output import LegalAnswer, LegalCitation, LegalRequirement
from src.services.citation_verifier import CitationVerifier

logger = logging.getLogger(__name__)


# ====================== NODOS ======================

def retrieve(state: RagState) -> dict:
    """
    Nodo de recuperación híbrida v2 con Query Expansion + Contextual Compression.
    """
    logger.info(f"[RETRIEVE v2] Pregunta: {state.question}")

    # ── Paso 0: Verificar Caché ───────────────────────────────────
    cached_response, layer = legal_cache.get(state.question)
    if cached_response:
        logger.info(f"[RETRIEVE v2] ✅ HIT en caché ({layer}). Saltando ejecución.")
        return {
            "generation": cached_response.get("answer", ""),
            "source_docs": cached_response.get("sources", []),
            "is_cached": True
        }

    from src.retrieval import get_vector_store
    from src.retrieval.hybrid_search import get_hybrid_retriever
    from src.retrieval.query_expansion import expand_query
    from src.retrieval.contextual_compression import compress_documents
    
    try:
        # ── Paso 1: Query Expansion ──────────────────────────────────────────
        logger.info("[RETRIEVE v2] Paso 1/4: Expandiendo query...")
        expanded = expand_query(state.question, n_queries=3, use_hyde=True)
        
        # ── Paso 2: Hybrid Retrieval v2 ──────────────────────────────────────
        logger.info("[RETRIEVE v2] Paso 2/4: Ejecutando Hybrid Retrieval...")
        vector_store = get_vector_store()
        hybrid_retriever = get_hybrid_retriever(vector_store)
        
        docs = hybrid_retriever.retrieve(
            query=expanded.normalized,
            hyde_doc=expanded.hyde_doc,
            extra_queries=expanded.queries,
            top_k=settings.TOP_K
        )
        
        # ── Paso 3: Contextual Compression ───────────────────────────────────
        logger.info("[RETRIEVE v2] Paso 3/4: Aplicando Contextual Compression...")
        compressed_docs = compress_documents(docs, state.question, use_llm=True)
        docs = compressed_docs
        
        return {"documents": docs}

    except Exception as e:
        logger.error(f"[RETRIEVE v2] ❌ Error: {e}. Aplicando fallback...")
        vector_store = get_vector_store()
        docs = vector_store.similarity_search(state.question, k=settings.TOP_K)
        return {"documents": docs}

# ── Grading de Documentos ───────────────────────────────────────────────────

_GRADE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Eres un juez legal experto colombiano. Decide si un fragmento normativo es RELEVANTE.
    Responde 'si' si el fragmento aporta CUALQUIER información útil (artículos, tablas, requisitos)."""),
    ("human", "Pregunta: {question}\n\nFragmento:\n{document}"),
])

def grade_documents(state: RagState) -> dict:
    """Evalúa la relevancia de los documentos recuperados."""
    llm = get_llm(task="grade")
    structured_llm = llm.with_structured_output(GradeOutput)
    chain = _GRADE_PROMPT | structured_llm

    relevant_docs: List[Document] = []
    for doc in state.documents:
        try:
            result = chain.invoke({"question": state.question, "document": doc.page_content})
            if result.score.strip().lower() == "si":
                relevant_docs.append(doc)
        except Exception as e:
            logger.error(f"[GRADE] Error: {e}")

    if not relevant_docs and state.documents:
        relevant_docs = state.documents[:3]

    return {
        "documents": relevant_docs,
        "grade": "útil" if relevant_docs else "no_útil",
    }

# ── Generación de Respuesta (Structured Output) ──────────────────────────

_GENERATION_SYSTEM_PROMPT = """Eres Legal Agent, un analista jurídico senior experto en normativa colombiana. 
Genera una RESPUESTA TÉCNICA basada EXCLUSIVAMENTE en el contexto recuperado.

REGLAS DE ORO:
1. CITAS TEXTUALES: Por cada afirmación, debes extraer una 'quote' literal del documento.
2. IDENTIFICACIÓN: Usa el 'article_id' exacto del contexto (ej: 2.2.1.4 o Art. 15).
3. FIDELIDAD: No parafrasees artículos críticos. Si no estás seguro, no lo cites.
4. ESTRUCTURA: Separa tu razonamiento jurídico de las evidencias documentales."""

def generate(state: RagState) -> dict:
    """Genera respuesta legal estructurada inicial."""
    if not state.documents:
        return {"generation": "Sin información suficiente.", "source_docs": []}

    llm = get_llm(task="generate")
    logger.info(f"🧠 Usando {getattr(llm, 'model_id', 'LLM')} para [GENERACIÓN ESTRUCTURADA]")
    
    # Preparar contexto para el LLM
    context_text = "\n\n---\n\n".join([
        f"[Doc {i+1} | Source: {d.metadata.get('source', 'N/A')} | Article: {d.metadata.get('article', 'N/A')}]:\n{d.page_content}"
        for i, d in enumerate(state.documents)
    ])
    
    # Configurar structured output
    structured_llm = llm.with_structured_output(LegalAnswer)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", _GENERATION_SYSTEM_PROMPT),
        ("human", "Consulta: {question}\n\nContexto Legal:\n{context}")
    ])
    
    try:
        # Si hay feedback de una verificación fallida anterior, lo incluimos
        human_input = {"question": state.question, "context": context_text}
        
        if getattr(state, "verification_feedback", None):
            logger.info("[GENERATE] Recibido feedback de auditoría. Aplicando corrección...")
            prompt.append(("assistant", "Respuesta previa fallida por discrepancias."))
            prompt.append(("human", f"CORRIGE basándote en este feedback: {state.verification_feedback}"))
            
        response_obj: LegalAnswer = (prompt | structured_llm).invoke(human_input)
        
        return {
            "legal_answer": response_obj,
            "generation": response_obj.answer,
            "attempts": state.attempts + 1
        }
            
    except Exception as e:
        logger.error(f"[GENERATE] Error en generación estructurada: {e}")
        return {"generation": "Error crítico de estructura.", "source_docs": []}

# ── Verificación de Citas y Auditoría (Audit Node) ──────────────────────────

def verify_citations_node(state: RagState) -> dict:
    """
    Nodo Auditor: Verifica la fidelidad de las citas generadas y la exactitud de cifras.
    Actualiza el objeto LegalAnswer con estados de verificación, scores y discrepancias.
    """
    logger.info("[AUDIT] Iniciando auditoría técnica (Citas + Números)...")
    
    legal_answer: LegalAnswer = state.legal_answer
    if not legal_answer:
        logger.warning("[AUDIT] No hay objeto legal_answer para auditar.")
        return {"verification_passed": True}
        
    retrieved_docs = [
        {"page_content": d.page_content, "metadata": d.metadata} 
        for d in state.documents
    ]
    
    verifier = CitationVerifier(threshold=0.85)
    
    # Ejecutar auditoría dual: Citas + Números
    verified_citations, numeric_discrepancies = verifier.audit_response(
        llm_answer=legal_answer.answer,
        citations=legal_answer.citations,
        context=retrieved_docs
    )
    
    # Actualizar objeto original con hallazgos
    legal_answer.citations = verified_citations
    legal_answer.numeric_discrepancies = numeric_discrepancies
    
    # Reconstruir para disparar validadores de Pydantic
    updated_answer = LegalAnswer(**legal_answer.model_dump())
    summary = updated_answer.verification_summary()
    
    passed = summary["verification_passed"]
    
    if not passed:
        logger.warning(f"[AUDIT] ❌ Auditoría fallida: {len(summary['failed_citations'])} citas y {len(numeric_discrepancies)} números incorrectos.")
        
        # Feedback detallado combinando ambos tipos de fallos
        feedback_parts = []
        if summary["failed_citations"]:
            feedback_parts.append(f"FALLOS EN CITAS: {summary['failed_citations']}")
        if numeric_discrepancies:
            feedback_parts.append(f"FALLOS NUMÉRICOS: {numeric_discrepancies}")
            
        return {
            "legal_answer": updated_answer,
            "verification_passed": False,
            "verification_feedback": " | ".join(feedback_parts)
        }
    
    logger.info(f"[AUDIT] ✅ Auditoría exitosa. Confidence: {updated_answer.confidence_score:.2f}")
    return {
        "legal_answer": updated_answer,
        "verification_passed": True,
        "confidence_score": updated_answer.confidence_score
    }

# ── Verificación de Alucinaciones (LLM-based) ───────────────────────────

_HALLUCINATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Eres un auditor jurídico. Compara RESPUESTA vs DOCUMENTOS. Detecta datos inventados."),
    ("human", "DOCUMENTOS:\n{documents}\n\nRESPUESTA:\n{generation}")
])

def check_hallucination(state: RagState) -> dict:
    """Detecta alucinaciones mediante razonamiento de LLM."""
    if not state.documents: return {"grade": "no_útil", "hallucination_score": 1.0}

    context = "\n---\n".join(doc.page_content[:2000] for doc in state.documents)
    llm = get_llm(task="verify")
    structured_llm = llm.with_structured_output(HallucinationOutput)
    
    try:
        res: HallucinationOutput = (_HALLUCINATION_PROMPT | structured_llm).invoke({
            "documents": context, "generation": state.generation
        })
        score = 0.0 if res.score.lower() == "limpio" else 1.0
        return {"grade": "útil" if score == 0.0 else "alucinación", "hallucination_score": score}
    except:
        return {"grade": "alucinación", "hallucination_score": 0.5}

def no_answer(state: RagState) -> dict:
    """Fallback."""
    return {"generation": "No se encontró información relevante para sustentar una respuesta legal verificable.", "source_docs": []}
