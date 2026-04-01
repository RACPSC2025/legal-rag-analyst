"""
Retrieval module - Vector store y retriever.
"""

import logging
from langchain_chroma import Chroma

# Imports absolutos desde Rag_Legal
from src.config import settings, get_embeddings

logger = logging.getLogger(__name__)


def get_vector_store() -> Chroma:
    """Se conecta a la base de datos Chroma."""
    embeddings = get_embeddings()
    vector_store = Chroma(
        persist_directory=settings.STORAGE_PATH,
        embedding_function=embeddings,
        collection_name=settings.COLLECTION_NAME,
    )
    return vector_store


def get_strict_retriever(k: int = None):
    """Retorna un retriever estricto configurado."""
    k = k or settings.TOP_K
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})


def get_document_count() -> int:
    """Retorna el número de documentos en la BD vectorial."""
    try:
        vector_store = get_vector_store()
        return vector_store._collection.count()
    except Exception as e:
        logger.error(f"Error al contar documentos: {e}")
        return 0
