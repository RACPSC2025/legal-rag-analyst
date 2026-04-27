"""
Semantic Cache Manager (L3) — Analista Legal v2
────────────────────────────────────────────────────────────
Búsqueda por similitud vectorial para consultas similares.
"""

import logging
import json
from typing import Optional, Tuple, Dict, Any
from langchain_chroma import Chroma
from src.config import settings, get_embeddings

logger = logging.getLogger(__name__)

class SemanticCache:
    """
    Capa 3 de Caché: Similitud Semántica.
    Utiliza ChromaDB para encontrar consultas con significado similar.
    """
    
    def __init__(self, threshold: float = 0.90):
        self.threshold = threshold
        self.collection_name = "legal_cache_semantic"
        self._vector_store = None
        
    @property
    def vector_store(self) -> Chroma:
        """Inicialización perezosa del vector store para el caché."""
        if self._vector_store is None:
            try:
                self._vector_store = Chroma(
                    persist_directory=settings.STORAGE_PATH,
                    embedding_function=get_embeddings(),
                    collection_name=self.collection_name,
                )
                logger.info(f"[L3 CACHE] Conectado a colección semántica: {self.collection_name}")
            except Exception as e:
                logger.error(f"[L3 CACHE] Error conectando a ChromaDB: {e}")
                raise
        return self._vector_store

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Busca una consulta similar en el vector store.
        Retorna la respuesta si la similitud supera el umbral.
        """
        try:
            # Búsqueda por similitud con score
            results = self.vector_store.similarity_search_with_relevance_scores(query, k=1)
            
            if not results:
                return None
                
            doc, score = results[0]
            
            if score >= self.threshold:
                logger.info(f"[L3 CACHE] ✅ HIT Semántico! Score: {score:.4f}")
                # El contenido de la respuesta se guarda en el metadata como JSON string
                return json.loads(doc.metadata.get("response_json", "{}"))
            
            logger.info(f"[L3 CACHE] ❌ MISS Semántico (Mejor score: {score:.4f} < {self.threshold})")
            return None
            
        except Exception as e:
            logger.warning(f"[L3 CACHE] Error en búsqueda semántica: {e}")
            return None

    def set(self, query: str, response: Dict[str, Any]):
        """
        Guarda una nueva consulta y su respuesta en el vector store semántico.
        """
        try:
            # Convertir respuesta a JSON string para almacenamiento en metadata
            response_json = json.dumps(response)
            
            self.vector_store.add_texts(
                texts=[query],
                metadatas=[{
                    "response_json": response_json,
                    "query_original": query
                }]
            )
            logger.info("[L3 CACHE] ✅ Consulta guardada en base vectorial semántica.")
        except Exception as e:
            logger.error(f"[L3 CACHE] Error guardando en caché semántico: {e}")
