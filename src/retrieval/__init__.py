"""
Módulo de retrieval — punto de entrada unificado para el vector store.

Exporta:
- get_vector_store()     → instancia Chroma singleton (usada en nodes.py)
- get_strict_retriever() → retriever similarity_search directo
- get_document_count()   → número de docs indexados (usada en app.py sidebar)
- reset_vector_store()   → fuerza reconexión (usada post-ingesta para refrescar BM25)
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_chroma import Chroma

logger = logging.getLogger(__name__)

# ── Singleton del vector store ─────────────────────────────────────────────
# Evita reconexiones innecesarias en cada llamada del nodo retrieve.
# Se resetea explícitamente después de ingestar nuevos documentos.

_vector_store: Optional[Chroma] = None


def get_vector_store() -> Chroma:
    """
    Retorna el vector store Chroma como singleton.

    Se conecta a la colección existente en disco (persist_directory).
    No crea documentos — solo abre la conexión.

    Returns:
        Chroma: Instancia conectada a la colección configurada.
    """
    global _vector_store
    if _vector_store is None:
        from src.config import settings, get_embeddings

        logger.info(
            f"Conectando a ChromaDB → colección '{settings.COLLECTION_NAME}' "
            f"en '{settings.STORAGE_PATH}'"
        )
        _vector_store = Chroma(
            persist_directory=settings.STORAGE_PATH,
            embedding_function=get_embeddings(),
            collection_name=settings.COLLECTION_NAME,
        )
    return _vector_store


def reset_vector_store() -> None:
    """
    Fuerza reconexión en la próxima llamada a get_vector_store().

    Útil después de ingestar nuevos documentos para refrescar el índice BM25
    y asegurar que el singleton apunta a los datos actualizados.
    """
    global _vector_store
    _vector_store = None
    logger.info("Vector store singleton reseteado — próxima llamada reconectará a ChromaDB.")


def get_strict_retriever(k: int = None):
    """
    Retorna un retriever de búsqueda por similitud directa.

    Args:
        k: Número de documentos a recuperar (default: settings.TOP_K).

    Returns:
        Retriever configurado con similarity_search.
    """
    from src.config import settings

    k = k or settings.TOP_K
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})


def get_document_count() -> int:
    """
    Retorna el número de fragmentos indexados en ChromaDB.

    Usado en el sidebar de Streamlit para mostrar el estado de la biblioteca.
    Retorna 0 si la colección no existe o está vacía, sin lanzar excepciones.

    Returns:
        int: Número de documentos en la colección.
    """
    try:
        store = get_vector_store()
        collection = store._collection
        return collection.count()
    except Exception as e:
        logger.warning(f"No se pudo contar documentos en ChromaDB: {e}")
        return 0


__all__ = [
    "get_vector_store",
    "reset_vector_store",
    "get_strict_retriever",
    "get_document_count",
]

