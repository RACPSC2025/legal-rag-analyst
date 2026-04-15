"""
Pipeline de Ingestión Profesional — "Golden Markdown Library" 
─────────────────────────────────────────────────────────────
Orquesta el flujo:
    PDF ──► Análisis (QualityDetector) ──► Golden MD (MarkdownService)
    Golden MD ──► Limpieza (TextCleaner) ──► Chunks (AdaptiveChunker) ──► ChromaDB

Beneficios:
  • Máxima precisión en tablas y jerarquía legal.
  • Ahorro de hasta 70% en tokens de Bedrock.
  • Respaldo permanente de documentos procesados.
"""

from __future__ import annotations
import argparse
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import settings, get_embeddings
from src.retrieval import reset_vector_store
from src.services.markdown_service import MarkdownLibrary, MarkdownConversionService
from src.ingestion.detectors.quality_detector import PDFQualityDetector
from src.ingestion.processors.text_cleaner import get_text_cleaner
from src.ingestion.processors.adaptive_chunker import get_adaptive_chunker
from src.ingestion.processors.metadata_extractor import get_metadata_extractor

logger = logging.getLogger(__name__)

def _resolve_input_paths(paths: List[str | Path]) -> List[Path]:
    """Valida y resuelve rutas a archivos PDF o Markdown."""
    resolved: List[Path] = []
    for raw_path in paths:
        p = Path(raw_path)
        if p.is_dir():
            resolved.extend(sorted(p.glob("**/*.pdf")))
            resolved.extend(sorted(p.glob("**/*.md")))
        elif p.is_file() and p.suffix.lower() in [".pdf", ".md"]:
            resolved.append(p)
        else:
            logger.warning(f"[PIPELINE] Ruta ignorada (no es PDF/MD válida): {raw_path}")
    
    if not resolved:
        raise ValueError("No se encontraron archivos válidos (PDF/MD) para procesar.")
    
    logger.info(f"[PIPELINE] {len(resolved)} archivo(s) identificado(s) para proceso.")
    return resolved

def _batch_index_documents(vector_store: Chroma, documents: List[Document], batch_size: int = 20) -> int:
    """Indexa documentos en lotes para evitar límites de la API de Bedrock."""
    total = len(documents)
    added = 0
    for i in range(0, total, batch_size):
        batch = documents[i : i + batch_size]
        try:
            vector_store.add_documents(batch)
            added += len(batch)
            logger.info(f"[PIPELINE] Indexados {added}/{total} fragmentos ({ (added/total)*100:.1f}%).")
            if i + batch_size < total:
                time.sleep(1.0) # Pausa de seguridad para rate-limiting
        except Exception as e:
            logger.error(f"[PIPELINE] Error indexando lote: {e}")
            continue
    return added

def run_ingestion_pipeline(
    paths: List[str | Path],
    force_reconvert: bool = False,
    collection_name: Optional[str] = None,
    storage_path: Optional[str] = None,
) -> dict:
    """
    Ejecuta el pipeline maestro de nivel industrial.
    """
    collection_name = collection_name or settings.COLLECTION_NAME
    storage_path = storage_path or settings.STORAGE_PATH
    
    logger.info("🚀 Iniciando Pipeline Maestro (Golden MD Architecture)")
    
    # ── 1. Inicializar Componentes ───────────────────────────────────────────
    quality_detector = PDFQualityDetector()
    cleaner = get_text_cleaner()
    chunker = get_adaptive_chunker(chunk_size=800, overlap=150)
    metadata_extractor = get_metadata_extractor()
    
    all_chunks: List[Document] = []
    processed_files = []
    errors = []

    # ── 2. Resolver Rutas ────────────────────────────────────────────────────
    try:
        input_files = _resolve_input_paths(paths)
    except Exception as e:
        return {"error": str(e)}

    # ── 3. Procesamiento Estratificado ───────────────────────────────────────
    for file_path in input_files:
        try:
            logger.info(f"📄 Procesando: {file_path.name}")
            
            # A. Obtener Golden MD (vía cache o conversión)
            if file_path.suffix.lower() == ".pdf":
                # Análisis de calidad para log y métricas
                quality = quality_detector.analyze(file_path)
                
                # Conversión / Recuperación de la Golden Copy
                # Note: MarkdownConversionService ya maneja el cache internamente
                conv_result = MarkdownConversionService.convert_and_save(
                    file_path, 
                    use_ocr=quality.needs_ocr(),
                    force_reconvert=force_reconvert
                )
                md_path = conv_result["md_path"]
                tool_used = conv_result["tool"]
            else:
                md_path = file_path
                tool_used = "direct_md"

            # B. Cargar Contenido para Procesamiento
            # La Golden MD Library guarda el archivo con un header YAML que debemos quitar
            md_content_raw = md_path.read_text(encoding="utf-8")
            # Quitar header YAML si existe (--- ... ---)
            if md_content_raw.startswith("---"):
                end_header = md_content_raw.find("\n---\n", 3)
                if end_header != -1:
                    md_content_raw = md_content_raw[end_header + 5:].strip()

            # C. Refinería de Texto (Limpieza Legal)
            # El perfil 'legal_colombia' inyecta los headers ## para el AdaptiveChunker
            cleaned_content = cleaner.clean(md_content_raw, profile="legal_colombia")

            # D. Chunking Jerárquico Adaptativo
            file_metadata = {
                "source": file_path.name,
                "original_format": file_path.suffix.lower()[1:],
                "extraction_tool": tool_used,
                "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            
            chunks = chunker.split_text(cleaned_content, metadata=file_metadata)
            
            # E. Enriquecimiento de Metadata Legal
            enriched_chunks = metadata_extractor.enrich_documents(chunks)
            all_chunks.extend(enriched_chunks)
            
            processed_files.append(file_path.name)
            logger.info(f"✅ {file_path.name} -> {len(enriched_chunks)} chunks enriquecidos.")

        except Exception as e:
            msg = f"Error procesando {file_path.name}: {e}"
            logger.error(f"[PIPELINE] {msg}")
            errors.append(msg)

    if not all_chunks:
        logger.warning("[PIPELINE] No se generaron fragmentos para indexar.")
        return {"processed": processed_files, "errors": errors, "indexed": 0}

    # ── 4. Indexación en ChromaDB ────────────────────────────────────────────
    try:
        embeddings = get_embeddings()
        vector_store = Chroma(
            persist_directory=str(storage_path),
            embedding_function=embeddings,
            collection_name=collection_name,
        )
        
        indexed_count = _batch_index_documents(vector_store, all_chunks)
        
        # Refrescar BM25/Singletons
        reset_vector_store()
        
        logger.info(f"✨ Proceso completado exitosamente. {indexed_count} chunks en '{collection_name}'.")
        
        return {
            "status": "success",
            "processed_files": processed_files,
            "total_chunks": len(all_chunks),
            "indexed_chunks": indexed_count,
            "errors": errors
        }

    except Exception as e:
        msg = f"Error crítico en indexación: {e}"
        logger.error(msg)
        return {"status": "partial_failure", "errors": errors + [msg]}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    
    parser = argparse.ArgumentParser(description="Pipeline Maestro RAG Legal — Golden MD Edition")
    parser.add_argument("--paths", nargs="+", required=True, help="Rutas a procesar (PDF/MD)")
    parser.add_argument("--force", action="store_true", help="Forzar reconversión de Golden MD")
    
    args = parser.parse_args()
    
    res = run_ingestion_pipeline(args.paths, force_reconvert=args.force)
    print("\n" + "="*50)
    print("RESUMEN DE INGESTIÓN PROFESIONAL")
    print("="*50)
    print(f"Archivos procesados: {len(res.get('processed_files', []))}")
    print(f"Chunks generados:    {res.get('total_chunks', 0)}")
    print(f"Chunks indexados:    {res.get('indexed_chunks', 0)}")
    if res.get("errors"):
        print(f"Errores detectados:  {len(res['errors'])}")
    print("="*50)
