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
from src.cache import legal_cache
from src.schemas.graph_outputs import GradeOutput, HallucinationOutput
from src.schemas.legal_output import LegalResponse, Citation, LegalRequirement
from src.services.citation_verifier import CitationVerifier
from pydantic import BaseModel, Field

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

# ── Generación de Respuesta (Two-Step Structured) ──────────────────────────

_RETHINKING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Eres un analista jurídico senior colombiano. Extrae pasajes EXACTOS y DATOS TÉCNICOS de los documentos. No resumas, extrae la evidencia literal."),
    ("human", "Consulta: {question}\n\nDocumentos:\n{context}\n\nExtrae evidencia:")
])

def generate(state: RagState) -> dict:
    """Genera respuesta legal estructurada (LegalResponse)."""
    if not state.documents:
        return {"generation": "Sin información suficiente.", "source_docs": []}

    llm = get_llm(task="generate")
    logger.info(f"🧠 Usando {getattr(llm, 'model_id', 'LLM')} para [GENERACIÓN]")
    
    # Contexto
    context = "\n\n---\n\n".join([
        f"[Doc {i+1} - {d.metadata.get('source', 'N/A')} - Art. {d.metadata.get('article', 'N/A')}]:\n{d.page_content}"
        for i, d in enumerate(state.documents)
    ])
    
    # Fase 1: Rethinking
    logger.info("[GENERATE] Fase 1: Rethinking...")
    key_passages = (_RETHINKING_PROMPT | llm | StrOutputParser()).invoke({
        "question": state.question, "context": context
    })
    
    # Fase 2: Síntesis Estructurada
    logger.info("[GENERATE] Fase 2: Síntesis...")
    structured_llm = llm.with_structured_output(LegalResponse)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Eres Legal Agent. Genera una RESPUESTA TÉCNICA basada en PASAJES y CONTEXTO.
        REGLAS:
        - CITAS: Objeto Citation con fragmento 'text' EXACTO.
        - REQUERIMIENTOS: Identifica plazos y obligaciones en 'requirements'."""),
        ("human", "Consulta: {question}\n\nEvidencia:\n{passages}\n\nContexto:\n{context}")
    ])
    
    try:
        response_obj: LegalResponse = (prompt | structured_llm).invoke({
            "question": state.question, "passages": key_passages, "context": context
        })
        
        # Fase 3: Verificación Fuzzy
        verifier = CitationVerifier(threshold=0.85)
        v_count = 0
        for cit in response_obj.citations:
            is_v, _ = verifier.verify_citation(cit, context)
            cit.verified = is_v
            if is_v: v_count += 1
        
        response_obj.confidence_score = round(v_count / len(response_obj.citations), 2) if response_obj.citations else 0.5
            
    except Exception as e:
        logger.error(f"[GENERATE] Error: {e}")
        return {"generation": "Error de estructura.", "source_docs": []}

    source_names = list({d.metadata.get("source") for d in state.documents if d.metadata.get("source")})
    
    try: legal_cache.set(state.question, response_obj.dict())
    except: pass

    return {
        "generation": response_obj.answer,
        "source_docs": source_names,
        "attempts": state.attempts + 1,
        "verified_citations": [c.dict() for c in response_obj.citations],
        "legal_requirements": [r.dict() for r in response_obj.requirements],
        "confidence_score": response_obj.confidence_score
    }

# ── Verificación de Alucinaciones ───────────────────────────────────────────

_HALLUCINATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Eres un auditor jurídico. Compara RESPUESTA vs DOCUMENTOS. Detecta datos inventados."),
    ("human", "DOCUMENTOS:\n{documents}\n\nRESPUESTA:\n{generation}")
])

def check_hallucination(state: RagState) -> dict:
    """Detecta alucinaciones."""
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
    return {"generation": "No se encontró información relevante.", "source_docs": []}
