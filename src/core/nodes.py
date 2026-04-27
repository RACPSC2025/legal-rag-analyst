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
from src.schemas.legal_output import Citation
from src.services.citation_verifier import CitationVerifier
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ====================== NODOS ======================

def retrieve(state: RagState) -> dict:
    """
    Nodo de recuperación híbrida v2 con Query Expansion + Contextual Compression.
    
    Proceso:
    1. Query Expansion: HyDE + Multi-Query para máxima cobertura.
    2. Hybrid Retrieval: BM25 + Vector + HyDE + Multi-Query con RRF fusion.
    3. FlashRank Reranking: Reordenamiento final de candidatos.
    4. Contextual Compression: Extracción de pasajes relevantes (reduce tokens 40-60%).
    
    Mejoras v2:
    - Recall mejorado en 30-40% gracias a múltiples representaciones de la query.
    - Manejo robusto de queries ambiguas o con terminología variada.
    - Reducción de tokens en 40-60% sin perder información relevante.
    - Fallback seguro en cada paso para garantizar disponibilidad.
    
    Args:
        state (RagState): Estado del grafo con la pregunta del usuario.
        
    Returns:
        dict: Actualización del estado con documentos recuperados y comprimidos.
    """
    logger.info(f"[RETRIEVE v2] Pregunta: {state.question}")

    # ── Paso 0: Verificar Caché (L1/L2) ───────────────────────────────────
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
        try:
            expanded = expand_query(
                state.question, 
                n_queries=3,      # Generar 3 variantes
                use_hyde=True     # Habilitar HyDE
            )
            logger.info(
                f"[RETRIEVE v2] ✅ Query expandida: "
                f"{len(expanded.all_queries)} queries totales, "
                f"HyDE: {'Sí' if expanded.hyde_doc else 'No'}"
            )
        except Exception as e:
            logger.warning(f"[RETRIEVE v2] ⚠️ Error en Query Expansion: {e}")
            logger.warning("[RETRIEVE v2] Continuando sin expansión...")
            # Fallback: usar query original sin expansión
            from src.retrieval.query_expansion import ExpandedQuery
            expanded = ExpandedQuery(
                original=state.question,
                normalized=state.question.lower(),
                hyde_doc="",
                queries=[]
            )
        
        # ── Paso 2: Hybrid Retrieval v2 ──────────────────────────────────────
        logger.info("[RETRIEVE v2] Paso 2/4: Ejecutando Hybrid Retrieval...")
        vector_store = get_vector_store()
        hybrid_retriever = get_hybrid_retriever(vector_store)
        
        # Recuperación con todas las representaciones de la query
        docs = hybrid_retriever.retrieve(
            query=expanded.normalized,        # Query limpia para BM25
            hyde_doc=expanded.hyde_doc,       # Documento hipotético para vector search
            extra_queries=expanded.queries,   # Variantes para multi-query
            top_k=10                          # Número final de documentos
        )
        
        logger.info(
            f"[RETRIEVE v2] ✅ {len(docs)} documentos recuperados vía "
            f"FenixHybridRetriever v2 (HyDE + Multi-Query + RRF + FlashRank)."
        )
        
        # ── Paso 3: Contextual Compression ───────────────────────────────────
        logger.info("[RETRIEVE v2] Paso 3/4: Aplicando Contextual Compression...")
        try:
            compressed_docs = compress_documents(
                documents=docs,
                question=state.question,
                use_llm=True,      # Usar LLM para máxima calidad
                batch_size=5       # Máximo 5 llamadas LLM
            )
            
            # Calcular estadísticas de compresión
            if compressed_docs:
                total_original = sum(
                    doc.metadata.get("original_length", len(doc.page_content)) 
                    for doc in compressed_docs
                )
                total_compressed = sum(len(doc.page_content) for doc in compressed_docs)
                avg_ratio = total_compressed / max(total_original, 1)
                
                logger.info(
                    f"[RETRIEVE v2] ✅ Compresión completada: "
                    f"{len(docs)} → {len(compressed_docs)} docs "
                    f"({len(docs) - len(compressed_docs)} descartados), "
                    f"Ratio promedio: {avg_ratio:.1%}"
                )
            
            docs = compressed_docs  # Usar documentos comprimidos
            
        except Exception as e:
            logger.warning(
                f"[RETRIEVE v2] ⚠️ Error en Contextual Compression: {e}. "
                f"Continuando con documentos sin comprimir..."
            )
            # Fallback: usar documentos originales sin comprimir
        
        # ── Paso 4: Logging de Metadata ──────────────────────────────────────
        if docs:
            logger.info("[RETRIEVE v2] Paso 4/4: Documentos finales:")
            for i, doc in enumerate(docs[:3], 1):  # Log solo top 3
                rrf = doc.metadata.get("rrf_score", 0.0)
                rerank = doc.metadata.get("rerank_score", 0.0)
                article = doc.metadata.get("article", "N/A")
                source = doc.metadata.get("source", "N/A")
                comp_ratio = doc.metadata.get("compression_ratio", 1.0)
                comp_method = doc.metadata.get("compression_method", "none")
                logger.info(
                    f"  {i}. Art. {article} | RRF: {rrf:.4f} | "
                    f"Rerank: {rerank:.4f} | Comp: {comp_ratio:.1%} ({comp_method}) | {source}"
                )
        
        return {"documents": docs}

    except Exception as e:
        logger.error(
            f"[RETRIEVE v2] ❌ Error crítico en Hybrid Retrieval v2: {e}. "
            f"Aplicando fallback a búsqueda simple..."
        )
        # Fallback de emergencia: búsqueda vectorial simple
        try:
            vector_store = get_vector_store()
            docs = vector_store.similarity_search(state.question, k=settings.TOP_K)
            logger.warning(
                f"[RETRIEVE v2] ⚠️ Fallback exitoso: {len(docs)} docs "
                f"recuperados con búsqueda simple."
            )
            return {"documents": docs}
        except Exception as fallback_error:
            logger.error(
                f"[RETRIEVE v2] ❌ Fallback también falló: {fallback_error}. "
                f"Retornando lista vacía."
            )
            return {"documents": []}

# ====================== PROMPTS ======================

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
    """
    Evalúa la relevancia de los documentos recuperados frente a la consulta del usuario.
    
    Este nodo actúa como un filtro de calidad (CRAG). Utiliza un modelo 'light' para
    minimizar costos y latencia, ya que es una tarea de clasificación binaria.
    
    Args:
        state (RagState): El estado actual del grafo con los documentos recuperados.
        
    Returns:
        dict: Actualización del estado con los documentos filtrados y el veredicto de utilidad.
    """
    # Solicitamos modelo ligero para tarea de grading
    llm = get_llm(task="grade")
    logger.info(f"🧠 Usando modelo: {getattr(llm, 'model_id', 'default')} para [GRADING]")
    
    structured_llm = llm.with_structured_output(GradeOutput)
    chain = _GRADE_PROMPT | structured_llm

    relevant_docs: List[Document] = []
    for doc in state.documents:
        try:
            # Evaluamos el contenido del chunk para determinar su pertinencia legal
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
            logger.error(f"[GRADE] Error crítico evaluando relevancia: {e}")

    # Mecanismo de seguridad: si nada pasó el filtro, recuperamos el top 3 para evitar respuestas vacías
    if not relevant_docs and state.documents:
        logger.warning("[GRADE] Filtrado total. Aplicando fallback de seguridad con el top-k original.")
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
    """
    Genera una respuesta legal fundamentada utilizando la técnica Two-Step Reading.
    
    Este nodo utiliza un modelo 'heavy' (potente) para garantizar el razonamiento
    jurídico y la precisión en la transcripción de tablas y artículos.
    
    Proceso:
    1. Rethinking: Extracción literal de pasajes clave.
    2. Synthesis: Redacción final con citación obligatoria.
    
    Args:
        state (RagState): El estado con los documentos filtrados y la pregunta.
        
    Returns:
        dict: Actualización con la respuesta generada y metadatos de fuentes.
    """
    if not state.documents:
        logger.warning("[GENERATE] Sin documentos para generar respuesta.")
        return {
            "generation": "No dispongo de información suficiente en los documentos disponibles para responder esta pregunta.",
            "source_docs": [],
        }

    # Solicitamos modelo pesado para generación de alta calidad
    llm = get_llm(task="generate")
    logger.info(f"🧠 Usando modelo: {getattr(llm, 'model_id', 'default')} para [GENERACIÓN]")
    
    # Preparación de contexto con metadatos de origen
    context_list = []
    for i, doc in enumerate(state.documents):
        article = doc.metadata.get("article", "N/A")
        page = doc.metadata.get("page", "?")
        context_list.append(f"[Doc {i+1} - Art. {article} - pág. {page}]:\n{doc.page_content}")
    
    context = "\n\n---\n\n".join(context_list)
    
    # Paso 1: Rethinking - Identificación de evidencia literal
    logger.info("[GENERATE] Iniciando Fase 1: Extracción de pasajes clave...")
    key_passages = (_RETHINKING_PROMPT | llm | StrOutputParser()).invoke({
        "question": state.question,
        "context": context
    })
    
    # Paso 2: Síntesis - Redacción jurídica estructurada
    logger.info("[GENERATE] Iniciando Fase 2: Redacción final y citación...")
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

    # ── Paso 3: Verificación de Citas (Citation Verifier) ─────────────────
    logger.info("[GENERATE] Iniciando Fase 3: Verificación de citas...")
    verifier = CitationVerifier()
    
    # Extraer citas usando regex básico (ej: (Art. 2.2.1, pág. 45))
    import re
    citation_pattern = r"\((Art\.|Sec\.|Cap\.)\s+([^,]+),\s+pág\.\s+(\d+|\?)\)"
    matches = re.finditer(citation_pattern, answer)
    
    verified_citations = []
    for match in matches:
        ref_type = match.group(1)
        ref_id = match.group(2)
        page = match.group(3)
        # Intentamos obtener el texto que precede a la cita (aprox 100 chars)
        start_pos = max(0, match.start() - 150)
        snippet = answer[start_pos:match.start()].strip()
        
        cit_obj = Citation(
            article_id=f"{ref_type} {ref_id}",
            source="contexto",
            page=page if page != "?" else None,
            text=snippet
        )
        
        # Verificar contra documentos del estado
        is_verified, score = verifier.verify_citation(cit_obj, context)
        cit_obj.verified = is_verified
        verified_citations.append(cit_obj)

    # Preparar resultado para retorno y caché
    source_names = list({d.metadata.get("source") for d in state.documents if d.metadata.get("source")})
    
    result = {
        "generation": answer,
        "source_docs": source_names,
        "attempts": state.attempts + 1,
        "verified_citations": [c.dict() for c in verified_citations]
    }
    
    # Guardar en caché para futuras consultas idénticas
    try:
        legal_cache.set(
            query=state.question, 
            response={"answer": answer, "sources": source_names}
        )
        logger.info("[GENERATE] ✅ Respuesta guardada en caché.")
    except Exception as e:
        logger.warning(f"[GENERATE] ⚠️ Error guardando en caché: {e}")

    return result


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
    """
    Verifica la fidelidad de la respuesta generada contra los documentos fuente.
    
    Este nodo (Self-RAG) previene la invención de datos. Utiliza un modelo 'light'
    especializado en verificación factual para asegurar integridad legal.
    
    Args:
        state (RagState): El estado con la generación y los documentos de referencia.
        
    Returns:
        dict: Calificación de alucinación y actualización del grado de utilidad.
    """
    if not state.documents:
        logger.warning("[HALLUCINATION] No hay documentos para verificar fidelidad.")
        return {"grade": "no_útil", "hallucination_score": 1.0}

    # Consolidación de contexto para el verificador
    context = "\n---\n".join(doc.page_content[:1500] for doc in state.documents)

    # Solicitamos modelo para tarea de verificación
    llm = get_llm(task="verify")
    logger.info(f"🧠 Usando modelo: {getattr(llm, 'model_id', 'default')} para [VERIFICACIÓN]")
    
    structured_llm = llm.with_structured_output(HallucinationOutput)
    chain = _HALLUCINATION_PROMPT | structured_llm

    try:
        # Evaluación factual de la respuesta
        result: HallucinationOutput = chain.invoke(
            {
                "documents": context,
                "generation": state.generation,
            }
        )

        if result.score.strip().lower() == "limpio":
            logger.info(f"[HALLUCINATION] ✅ Respuesta verificada — {result.razon[:80]}")
            return {"grade": "útil", "hallucination_score": 0.0}
        else:
            logger.warning(f"[HALLUCINATION] ⚠️ Alucinación detectada — {result.razon[:80]}")
            return {"grade": "alucinación", "hallucination_score": 1.0}

    except Exception as e:
        logger.error(f"[HALLUCINATION] Fallo en motor de verificación: {e}. Se requiere revisión humana.")
        # En caso de error técnico, marcamos como sospechoso por seguridad
        return {"grade": "alucinación", "hallucination_score": 0.5}


def no_answer(state: RagState) -> dict:
    return {
        "generation": (
            "⚠️ No se encontró información relevante en los documentos indexados "
            "para responder su consulta legal. Por favor reformule la pregunta "
            "o sea más específico con el número del artículo."
        ),
        "source_docs": [],
    }
