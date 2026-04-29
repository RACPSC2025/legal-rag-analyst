"""
Motor de Búsqueda Híbrido v2 (BM25 + Vector + HyDE + Multi-Query + FlashRank)
──────────────────────────────────────────────────────────────────────────────
Implementa RRF (Reciprocal Rank Fusion) para máxima precisión legal.

Mejoras v2:
  • HyDE embedding: usa el documento hipotético para búsqueda vectorial
    en paralelo con la query original → fusión con RRF.
  • Multi-Query: ejecuta búsquedas con múltiples variantes de la query
    y fusiona resultados con RRF ponderado.
  • RRF mejorado: pesos diferenciados (vector > bm25 > hyde).
  • Logging detallado para trazabilidad completa.

Basado en: Módulo 10, Módulo 08 y mejores prácticas de Claude (Legal v2).

Autor: Fenix Tech Líder
Fecha: 2026-04-26
Versión: 2.0.0
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi
from flashrank import Ranker, RerankRequest
from langchain_core.documents import Document
from langchain_chroma import Chroma

from src.config import settings, get_embeddings
from src.retrieval.metadata_filters import extract_filters

logger = logging.getLogger(__name__)

# ── Pesos para RRF (Reciprocal Rank Fusion) ──────────────────────────────────
# Estos pesos determinan la importancia relativa de cada fuente de búsqueda
_W_VECTOR = 1.0      # Peso búsqueda vectorial (semántica)
_W_BM25 = 0.85       # Peso BM25 (keywords exactas)
_W_HYDE = 0.70       # Peso HyDE (orientativo, puede ser ruidoso)
_K_RRF = 60          # Constante K para RRF (estándar: 60)

class FenixHybridRetriever:
    """
    Retriever Híbrido v2 con HyDE, Multi-Query, RRF y FlashRank.
    
    Flujo de retrieve():
      1. Vector search (query original)         → lista A
      2. BM25 search (query normalizada)        → lista B
      3. HyDE vector search (si hyde_doc dado)  → lista C
      4. Repetir 1+2 para cada query alternativa → listas D, E...
      5. RRF fusion de todas las listas con pesos
      6. FlashRank reranking final
      
    Principios de diseño:
    - Stateless: cada llamada a retrieve() es independiente.
    - Fail-safe: si algo falla, degrada gracefully.
    - Logging completo: cada paso se registra para trazabilidad.
    """

    def __init__(self, vector_store: Chroma):
        """
        Inicializa el retriever híbrido.
        
        Args:
            vector_store: Instancia de Chroma con documentos indexados.
        """
        self.vector_store = vector_store
        self.embeddings = get_embeddings()
        self._bm25 = None
        self._all_docs = []
        self._reranker = None
        
        # Cargar documentos para BM25
        self._initialize_bm25()
        
        # Inicializar FlashRank (Lazy loading)
        try:
            self._reranker = Ranker(
                model_name="ms-marco-MiniLM-L-12-v2", 
                cache_dir=str(settings.ROOT_DIR / "storage" / "models")
            )
            logger.info("✅ FlashRank reranker inicializado.")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar FlashRank: {e}. Se usará solo Hybrid.")

    def _initialize_bm25(self):
        """Prepara el índice BM25 con todos los documentos de la colección."""
        try:
            # Obtener todos los documentos de Chroma
            collection = self.vector_store._collection
            results = collection.get()
            
            if not results["documents"]:
                logger.warning("⚠️ No hay documentos en Chroma para inicializar BM25.")
                return

            self._all_docs = []
            tokenized_corpus = []
            
            for i in range(len(results["documents"])):
                doc = Document(
                    page_content=results["documents"][i],
                    metadata=results["metadatas"][i]
                )
                self._all_docs.append(doc)
                tokenized_corpus.append(doc.page_content.lower().split())
            
            self._bm25 = BM25Okapi(tokenized_corpus)
            logger.info(f"✅ BM25 Inicializado con {len(self._all_docs)} documentos.")
        except Exception as e:
            logger.error(f"❌ Error inicializando BM25: {e}")

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        hyde_doc: str = "",
        extra_queries: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        Búsqueda Híbrida v2 con HyDE, Multi-Query, RRF y FlashRank.
        
        Args:
            query:            Query principal (pregunta del usuario).
            top_k:            Número final de documentos a retornar.
            hyde_doc:         Documento hipotético de HyDE (opcional).
            extra_queries:    Queries adicionales de Multi-Query (opcional).
            metadata_filter:  Filtro ChromaDB (ej. {"document_type": "decreto"}).
            
        Returns:
            Lista de Documents ordenados por relevancia con metadata enriquecida.
            
        Example:
            >>> from src.retrieval.query_expansion import expand_query
            >>> expanded = expand_query("¿Cuáles son los requisitos?")
            >>> docs = retriever.retrieve(
            ...     query=expanded.normalized,
            ...     hyde_doc=expanded.hyde_doc,
            ...     extra_queries=expanded.queries,
            ...     top_k=10
            ... )
        """
        logger.info(f"[HYBRID v2] Iniciando búsqueda híbrida para: '{query[:80]}...'")
        
        # ── TASK-014: Extracción automática de filtros de metadata ───────────
        if metadata_filter is None:
            auto_filters = extract_filters(query)
            if auto_filters:
                metadata_filter = auto_filters
                logger.info(f"[TASK-014] ✅ Filtros automáticos aplicados: {metadata_filter}")
        
        # Pool de candidatos más grande para RRF
        candidate_pool = top_k * 3
        
        # Lista de (docs, peso) para RRF fusion
        ranked_lists: List[tuple[List[Document], float]] = []
        
        # ── 1. Vector search con query original ──────────────────────────────
        vector_docs = self._vector_search(query, k=candidate_pool, filter=metadata_filter)
        if vector_docs:
            ranked_lists.append((vector_docs, _W_VECTOR))
            logger.info(f"[VECTOR] {len(vector_docs)} docs recuperados con query original.")
        
        # ── 2. BM25 search con query normalizada ─────────────────────────────
        bm25_docs = self._bm25_search(query, k=candidate_pool)
        if bm25_docs:
            ranked_lists.append((bm25_docs, _W_BM25))
            logger.info(f"[BM25] {len(bm25_docs)} docs recuperados con query normalizada.")
        
        # ── 3. HyDE vector search ─────────────────────────────────────────────
        if hyde_doc and hyde_doc.strip():
            hyde_docs = self._vector_search(hyde_doc, k=candidate_pool // 2, filter=metadata_filter)
            if hyde_docs:
                ranked_lists.append((hyde_docs, _W_HYDE))
                logger.info(f"[HYDE] {len(hyde_docs)} docs recuperados con embedding hipotético.")
        
        # ── 4. Multi-Query: queries alternativas ──────────────────────────────
        if extra_queries:
            for i, alt_query in enumerate(extra_queries[:3], 1):  # Máximo 3 variantes
                # Vector search con variante
                alt_vector = self._vector_search(alt_query, k=candidate_pool // 2, filter=metadata_filter)
                if alt_vector:
                    ranked_lists.append((alt_vector, _W_VECTOR * 0.8))  # Peso ligeramente menor
                    logger.info(f"[MULTI-QUERY {i}] {len(alt_vector)} docs con variante.")
                
                # BM25 search con variante
                alt_bm25 = self._bm25_search(alt_query, k=candidate_pool // 2)
                if alt_bm25:
                    ranked_lists.append((alt_bm25, _W_BM25 * 0.8))
        
        # ── 5. RRF Fusion ─────────────────────────────────────────────────────
        if not ranked_lists:
            logger.warning("[HYBRID v2] ⚠️ No se recuperaron documentos de ninguna fuente.")
            return []
        
        logger.info(f"[RRF] Fusionando {len(ranked_lists)} listas con RRF...")
        fused_docs = self._rrf_fusion(ranked_lists, top_k=candidate_pool)
        
        logger.info(f"[RRF] ✅ {len(fused_docs)} candidatos después de fusión.")
        
        # ── 6. FlashRank Reranking final ──────────────────────────────────────
        if self._reranker and fused_docs:
            try:
                passages = [
                    {"id": i, "text": d.page_content, "meta": d.metadata} 
                    for i, d in enumerate(fused_docs)
                ]
                
                rerank_request = RerankRequest(query=query, passages=passages)
                results = self._reranker.rerank(rerank_request)
                
                # Reconstruir Documentos ordenados
                final_docs = []
                for res in results[:top_k]:
                    idx = res["id"]
                    doc = fused_docs[idx]
                    # Inyectar scores en metadata
                    doc.metadata["rerank_score"] = res["score"]
                    doc.metadata["rrf_score"] = doc.metadata.get("rrf_score", 0.0)
                    final_docs.append(doc)
                
                logger.info(
                    f"[RERANK] ✅ Reranking completado. "
                    f"Top score: {results[0]['score']:.4f} | "
                    f"Retornando {len(final_docs)} docs."
                )
                return final_docs
            except Exception as e:
                logger.error(f"[RERANK] ❌ Error en reranking: {e}. Usando RRF puro.")
                return fused_docs[:top_k]
        
        logger.info(f"[HYBRID v2] ✅ Retornando {len(fused_docs[:top_k])} docs (sin reranking).")
        return fused_docs[:top_k]

    # ── Métodos auxiliares de búsqueda ────────────────────────────────────────
    
    def _vector_search(
        self, 
        query: str, 
        k: int, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Búsqueda vectorial en ChromaDB.
        
        Args:
            query: Texto para embedding y búsqueda.
            k: Número de documentos a recuperar.
            filter: Filtro de metadata opcional.
            
        Returns:
            Lista de Documents ordenados por similitud.
        """
        try:
            if filter:
                return self.vector_store.similarity_search(query, k=k, filter=filter)
            else:
                return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"[VECTOR] Error en búsqueda vectorial: {e}")
            return []
    
    def _bm25_search(self, query: str, k: int) -> List[Document]:
        """
        Búsqueda BM25 (sparse retrieval).
        
        Args:
            query: Query para tokenizar y buscar.
            k: Número de documentos a recuperar.
            
        Returns:
            Lista de Documents ordenados por score BM25.
        """
        if not self._bm25:
            return []
        
        try:
            tokenized_query = query.lower().split()
            scores = self._bm25.get_scores(tokenized_query)
            top_n_indices = np.argsort(scores)[::-1][:k]
            # Filtrar solo docs con score > 0
            return [self._all_docs[i] for i in top_n_indices if scores[i] > 0]
        except Exception as e:
            logger.error(f"[BM25] Error en búsqueda BM25: {e}")
            return []
    
    def _rrf_fusion(
        self, 
        ranked_lists: List[tuple[List[Document], float]], 
        top_k: int
    ) -> List[Document]:
        """
        Reciprocal Rank Fusion (RRF) con pesos.
        
        Fórmula: score(doc) = Σ weight_i / (K + rank_i)
        donde K = 60 (constante estándar), rank_i es la posición en la lista i.
        
        Args:
            ranked_lists: Lista de tuplas (docs, peso).
            top_k: Número de documentos a retornar.
            
        Returns:
            Lista de Documents ordenados por score RRF.
        """
        # Diccionario: page_content → (Document, score_acumulado)
        doc_scores: Dict[str, tuple[Document, float]] = {}
        
        for docs, weight in ranked_lists:
            for rank, doc in enumerate(docs, start=1):
                content = doc.page_content
                rrf_score = weight / (_K_RRF + rank)
                
                if content in doc_scores:
                    # Acumular score
                    existing_doc, existing_score = doc_scores[content]
                    doc_scores[content] = (existing_doc, existing_score + rrf_score)
                else:
                    # Nuevo documento
                    doc_scores[content] = (doc, rrf_score)
        
        # Ordenar por score descendente
        sorted_docs = sorted(
            doc_scores.values(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Inyectar score en metadata y retornar
        result = []
        for doc, score in sorted_docs[:top_k]:
            doc.metadata["rrf_score"] = round(score, 4)
            result.append(doc)
        
        return result


def get_hybrid_retriever(vector_store: Chroma) -> FenixHybridRetriever:
    """
    Factory function para obtener una instancia del retriever híbrido.
    
    Args:
        vector_store: Instancia de Chroma con documentos indexados.
        
    Returns:
        FenixHybridRetriever configurado y listo para usar.
    """
    return FenixHybridRetriever(vector_store)
