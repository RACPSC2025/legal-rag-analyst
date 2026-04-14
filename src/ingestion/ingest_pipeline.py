"""
Pipeline de Ingestion Completo — RAG Legal Colombiano.

Orquesta el flujo:
    PDF(s) → Loader (PyMuPDF / Docling) → Chunks → Embeddings (Bedrock) → ChromaDB

Uso directo desde CLI:
    python -m src.ingestion.ingest_pipeline --paths data/input/ --loader docling

Uso desde código:
    from src.ingestion.ingest_pipeline import run_ingestion_pipeline
    run_ingestion_pipeline(["data/input/decreto_1072.pdf"], loader_type="docling")
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import settings, get_embeddings
from src.ingestion.factory import LoaderType, load_pdfs
from src.retrieval import reset_vector_store

logger = logging.getLogger(__name__)


def _validate_pdf_paths(pdf_paths: List[str | Path]) -> List[Path]:
    """
    Valida que todas las rutas a PDFs existan y sean válidas.

    Fail fast: si alguna ruta no es un archivo PDF existente,
    lanza excepción antes de comenzar el pipeline.

    Args:
        pdf_paths: Lista de rutas a validar (archivos o directorios).

    Returns:
        Lista de Path válidos a archivos PDF.

    Raises:
        FileNotFoundError: Si algún PDF no existe.
        ValueError: Si no se encontraron PDFs válidos.
    """
    resolved_paths: List[Path] = []

    for raw_path in pdf_paths:
        p = Path(raw_path)
        if p.is_dir():
            # Si es directorio, tomar todos los PDFs recursivamente
            dir_pdfs = sorted(p.glob("**/*.pdf"))
            if not dir_pdfs:
                logger.warning(f"Directorio sin archivos PDF: {p}")
            resolved_paths.extend(dir_pdfs)
        elif p.is_file() and p.suffix.lower() == ".pdf":
            resolved_paths.append(p)
        else:
            raise FileNotFoundError(f"Ruta no válida (no es PDF ni directorio): {raw_path}")

    if not resolved_paths:
        raise ValueError("No se encontraron PDFs válidos en las rutas proporcionadas.")

    logger.info(f"[INGEST] {len(resolved_paths)} archivo(s) PDF validado(s).")
    return resolved_paths


def _batch_add_documents(
    vector_store: Chroma,
    documents: List[Document],
    batch_size: int = None,
) -> int:
    """
    Agrega documentos a ChromaDB en lotes para evitar timeouts de Bedrock.

    Args:
        vector_store: Instancia de Chroma conectada.
        documents: Lista de Documents a indexar.
        batch_size: Tamaño del lote (default: settings.BATCH_SIZE).

    Returns:
        Número total de documentos agregados exitosamente.
    """
    batch_size = batch_size or settings.BATCH_SIZE
    total = len(documents)
    added = 0

    for i in range(0, total, batch_size):
        batch = documents[i : i + batch_size]
        try:
            vector_store.add_documents(batch)
            added += len(batch)
            pct = (added / total) * 100
            logger.info(
                f"[INGEST] Lote {i // batch_size + 1}: "
                f"{added}/{total} docs ({pct:.1f}%) indexados."
            )
            # Pequeña pausa para no saturar la API de Bedrock Embeddings
            if i + batch_size < total:
                time.sleep(0.5)

        except Exception as e:
            logger.error(f"[INGEST] Error en lote {i // batch_size + 1}: {e}")
            # Continuar con el siguiente lote en lugar de abortar todo
            continue

    return added


def run_ingestion_pipeline(
    pdf_paths: List[str | Path],
    loader_type: str = LoaderType.PYMUPDF,
    collection_name: Optional[str] = None,
    storage_path: Optional[str] = None,
    batch_size: Optional[int] = None,
    loader_kwargs: Optional[dict] = None,
) -> dict:
    """
    Ejecuta el pipeline completo de ingestion.

    Args:
        pdf_paths:        Lista de rutas a PDFs a ingestar.
        loader_type:      'pymupdf' | 'docling' | 'llamaparse'
        collection_name:  Nombre de la colección ChromaDB (default: settings.COLLECTION_NAME)
        storage_path:     Ruta de persistencia ChromaDB (default: settings.STORAGE_PATH)
        batch_size:       Tamaño de lote para embeddings (default: settings.BATCH_SIZE)
        loader_kwargs:    Kwargs adicionales para el loader (chunk_size, use_ocr, etc.)

    Returns:
        dict con:
            - "docs_loaded":   int  — fragmentos extraídos por el loader
            - "docs_indexed":  int  — fragmentos efectivamente indexados en Chroma
            - "sources":       list — nombres de archivos procesados
            - "loader_used":   str  — tipo de loader empleado
            - "errors":        list — errores no fatales ocurridos
    """
    collection_name = collection_name or settings.COLLECTION_NAME
    storage_path = storage_path or settings.STORAGE_PATH
    loader_kwargs = loader_kwargs or {}

    logger.info(
        f"[INGEST] Iniciando pipeline | loader={loader_type} | "
        f"{len(pdf_paths)} archivo(s) | colección='{collection_name}'"
    )

    result = {
        "docs_loaded": 0,
        "docs_indexed": 0,
        "sources": [],
        "loader_used": loader_type,
        "errors": [],
    }

    # ── 1. Cargar y chunkear PDFs ──────────────────────────────────────────
    try:
        documents = load_pdfs(
            [str(p) for p in pdf_paths],
            loader_type=loader_type,
            **loader_kwargs,
        )
        result["docs_loaded"] = len(documents)
        result["sources"] = list(
            {doc.metadata.get("source", "unknown") for doc in documents}
        )
        logger.info(f"[INGEST] {len(documents)} fragmentos extraídos de {len(pdf_paths)} PDF(s).")

    except Exception as e:
        msg = f"Error crítico en carga de PDFs: {e}"
        logger.error(f"[INGEST] {msg}")
        result["errors"].append(msg)
        return result

    if not documents:
        logger.warning("[INGEST] No se extrajeron documentos. Abortando.")
        return result

    # ── 2. Conectar a ChromaDB ─────────────────────────────────────────────
    try:
        embeddings = get_embeddings()
        vector_store = Chroma(
            persist_directory=str(storage_path),
            embedding_function=embeddings,
            collection_name=collection_name,
        )
        logger.info(f"[INGEST] ChromaDB conectado en '{storage_path}'.")

    except Exception as e:
        msg = f"Error conectando a ChromaDB: {e}"
        logger.error(f"[INGEST] {msg}")
        result["errors"].append(msg)
        return result

    # ── 3. Indexar en lotes ────────────────────────────────────────────────
    added = _batch_add_documents(vector_store, documents, batch_size)
    result["docs_indexed"] = added

    # ── 4. Resetear el singleton del vector store para refrescar BM25 ──────
    reset_vector_store()

    logger.info(
        f"[INGEST] ✅ Pipeline completado: "
        f"{added}/{len(documents)} fragmentos indexados en '{collection_name}'."
    )
    return result


# ── CLI Entry Point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Pipeline de ingestion RAG Legal Colombiano"
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        required=True,
        help="Ruta(s) a PDF(s) o directorio de PDFs. Ej: data/input/ decreto.pdf",
    )
    parser.add_argument(
        "--loader",
        choices=["pymupdf", "docling", "llamaparse"],
        default="pymupdf",
        help="Tipo de loader a usar (default: pymupdf)",
    )
    parser.add_argument(
        "--collection",
        default=None,
        help="Nombre de la colección ChromaDB (default: desde .env)",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Activar OCR en Docling para PDFs escaneados (solo con --loader docling)",
    )
    args = parser.parse_args()

    # Resolver rutas: validar que existan
    try:
        pdf_paths = _validate_pdf_paths(args.paths)
    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        exit(1)

    loader_kwargs = {}
    if args.loader == "docling" and args.ocr:
        loader_kwargs["use_ocr"] = True

    result = run_ingestion_pipeline(
        pdf_paths=pdf_paths,
        loader_type=args.loader,
        collection_name=args.collection,
        loader_kwargs=loader_kwargs,
    )

    print("\n" + "=" * 60)
    print("RESULTADO DEL PIPELINE DE INGESTION")
    print("=" * 60)
    print(f"  Loader usado:         {result['loader_used']}")
    print(f"  PDFs procesados:      {len(result['sources'])}")
    print(f"  Fuentes:              {', '.join(result['sources'])}")
    print(f"  Fragmentos extraídos: {result['docs_loaded']}")
    print(f"  Fragmentos indexados: {result['docs_indexed']}")
    if result["errors"]:
        print(f"  Errores:              {len(result['errors'])}")
        for err in result["errors"]:
            print(f"    ✗ {err}")
    print("=" * 60)
