"""
Motor de Búsqueda Híbrido (BM25 + Vector + FlashRank)
Implementa RRF (Reciprocal Rank Fusion) para máxima precisión legal.
Basado en Módulo 10 y Módulo 08.
"""

import logging
from typing import List, Dict, Any
import numpy as np
from rank_bm25 import BM25Okapi
from flashrank import Ranker, RerankRequest
from langchain_core.documents import Document
from langchain_chroma import Chroma

from src.config import settings, get_embeddings

logger = logging.getLogger(__name__)

class FenixHybridRetriever:
    """Retriever Híbrido de Grado Industrial con Reranking."""

    def __init__(self, vector_store: Chroma):
        self.vector_store = vector_store
        self.embeddings = get_embeddings()
        self._bm25 = None
        self._all_docs = []
        self._reranker = None
        
        # Cargar documentos para BM25
        self._initialize_bm25()
        
        # Inicializar FlashRank (Lazy loading)
        try:
            self._reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir=str(settings.ROOT_DIR / "storage" / "models"))
        except Exception as e:
            logger.warning(f"No se pudo cargar FlashRank: {e}. Se usará solo Hybrid.")

    def _initialize_bm25(self):
        """Prepara el índice BM25 con todos los documentos de la colección."""
        try:
            # Obtener todos los documentos de Chroma
            collection = self.vector_store._collection
            results = collection.get()
            
            if not results["documents"]:
                logger.warning("No hay documentos en Chroma para inicializar BM25.")
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
            logger.error(f"Error inicializando BM25: {e}")

    def retrieve(self, query: str, top_k: int = 10) -> List[Document]:
        """Búsqueda Híbrida + Reranking."""
        
        # 1. Búsqueda Vectorial (Dense)
        vector_docs = self.vector_store.similarity_search(query, k=top_k * 2)
        
        # 2. Búsqueda BM25 (Sparse)
        bm25_docs = []
        if self._bm25:
            tokenized_query = query.lower().split()
            # Obtener scores y seleccionar los mejores
            scores = self._bm25.get_scores(tokenized_query)
            top_n_indices = np.argsort(scores)[::-1][:top_k * 2]
            bm25_docs = [self._all_docs[i] for i in top_n_indices if scores[i] > 0]

        # 3. Fusión y Deduplicación
        combined_docs = {d.page_content: d for d in vector_docs + bm25_docs}.values()
        candidates = list(combined_docs)
        
        logger.info(f"Hybrid: {len(candidates)} candidatos encontrados.")

        # 4. FlashRank Reranking
        if self._reranker and candidates:
            try:
                passages = [
                    {"id": i, "text": d.page_content, "meta": d.metadata} 
                    for i, d in enumerate(candidates)
                ]
                
                rerank_request = RerankRequest(query=query, passages=passages)
                results = self._reranker.rerank(rerank_request)
                
                # Reconstruir Documentos ordenados
                final_docs = []
                for res in results[:top_k]:
                    idx = res["id"]
                    doc = candidates[idx]
                    # Inyectar score de reranking en metadata
                    doc.metadata["rerank_score"] = res["score"]
                    final_docs.append(doc)
                
                logger.info(f"✅ Reranking completado. Top score: {results[0]['score']:.4f}")
                return final_docs
            except Exception as e:
                logger.error(f"Error en Reranking: {e}")
                return candidates[:top_k]
        
        return candidates[:top_k]

def get_hybrid_retriever(vector_store: Chroma) -> FenixHybridRetriever:
    return FenixHybridRetriever(vector_store)
