"""
Hierarchical Retriever para RAG Legal Colombiano
- Level 1: Summaries (por página o artículo)
- Level 2: Detailed chunks con overlap
Adaptado para LangGraph + Chroma + Bedrock
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Imports ABSOLUTOS desde Rag_Legal
from src.config import settings, get_llm, get_embeddings
from src.ingestion.pdf_simple import get_pymupdf_loader

logger = logging.getLogger(__name__)


class HierarchicalLegalRetriever:
    """Retriever jerárquico optimizado para documentos legales."""

    def __init__(
        self,
        collection_name: str = None,
        chunk_size: int = 1100,
        chunk_overlap: int = 300,
        summary_chunk_size: int = 2000,
    ):
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.summary_chunk_size = summary_chunk_size

        self.embeddings = get_embeddings()

        # Vector stores
        self.summary_store = None
        self.detailed_store = None

    def _create_summary(self, doc: Document) -> Document:
        """Crea un resumen compacto de un documento/página."""
        llm = get_llm()
        
        # Prompt para resumir
        summary_prompt = ChatPromptTemplate.from_template(
            "Eres un experto legal colombiano. Resume el siguiente fragmento normativo en 2-3 oraciones concisas y precisas, "
            "capturando la esencia jurídica y los sujetos/acciones mencionados.\n\n"
            "Texto: {text}"
        )

        # Chain manual
        summarize_chain = summary_prompt | llm | StrOutputParser()

        summary_text = summarize_chain.invoke({"text": doc.page_content})

        return Document(
            page_content=summary_text,
            metadata={
                **doc.metadata,
                "is_summary": True,
                "original_content_length": len(doc.page_content),
            }
        )

    def build_hierarchical_index(self, pdf_paths: List[str | Path]):
        """Construye los dos niveles: summaries + detailed chunks."""
        logger.info(f"Construyendo índice jerárquico para {len(pdf_paths)} PDFs...")

        loader = get_pymupdf_loader(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        documents = loader.load_multiple(pdf_paths)

        # --- Nivel 1: Summaries ---
        summaries = []
        for doc in documents:
            if len(doc.page_content) > 800:  # Solo resumir documentos largos
                summary_doc = self._create_summary(doc)
                summaries.append(summary_doc)
            else:
                summaries.append(doc)

        # --- Nivel 2: Detailed chunks (ya vienen del loader) ---

        # Crear vector stores
        self.summary_store = Chroma.from_documents(
            documents=summaries,
            embedding=self.embeddings,
            collection_name=f"{self.collection_name}_summary",
            persist_directory=settings.STORAGE_PATH,
        )

        self.detailed_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=f"{self.collection_name}_detailed",
            persist_directory=settings.STORAGE_PATH,
        )

        logger.info(f"Índice jerárquico creado: {len(summaries)} summaries | {len(documents)} detailed chunks")
        return self.summary_store, self.detailed_store

    def retrieve(self, query: str, k_summaries: int = 4, k_chunks: int = 8) -> List[Document]:
        """Recuperación jerárquica: primero summaries → luego detailed chunks."""
        if not self.summary_store or not self.detailed_store:
            logger.warning("Vector stores no inicializados. Usando solo detailed store.")
            if self.detailed_store:
                return self.detailed_store.similarity_search(query, k=k_chunks * 2)
            return []

        # Paso 1: Buscar en summaries (contexto amplio)
        top_summaries = self.summary_store.similarity_search(query, k=k_summaries)

        # Paso 2: Recuperar chunks detallados relacionados con las páginas/artículos de los summaries
        relevant_docs = []
        seen_pages = set()

        for summary in top_summaries:
            page = summary.metadata.get("page")
            article = summary.metadata.get("article")

            if page:
                seen_pages.add(page)

            # Buscar en detailed store filtrando por página o artículo
            if article:
                filter_dict = {"article": article}
                page_chunks = self.detailed_store.similarity_search(
                    query, k=k_chunks // 2, filter=filter_dict
                )
                relevant_docs.extend(page_chunks)
            elif page:
                filter_dict = {"page": page}
                page_chunks = self.detailed_store.similarity_search(
                    query, k=k_chunks // 2, filter=filter_dict
                )
                relevant_docs.extend(page_chunks)
            else:
                # Fallback: búsqueda normal
                relevant_docs.extend(
                    self.detailed_store.similarity_search(query, k=2)
                )

        # Eliminar duplicados y ordenar por relevancia
        unique_docs = []
        seen = set()
        for doc in relevant_docs:
            doc_id = doc.metadata.get("chunk_index") or id(doc)
            if doc_id not in seen:
                seen.add(doc_id)
                unique_docs.append(doc)

        logger.info(f"Recuperados {len(unique_docs)} chunks detallados vía hierarchical retrieval")
        return unique_docs[:k_chunks]


# Factory function para usar en tu app
def get_hierarchical_retriever(**kwargs):
    return HierarchicalLegalRetriever(**kwargs)
