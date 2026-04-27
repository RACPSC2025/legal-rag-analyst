"""
Markdown Service — Golden Markdown Library (Versión Corregida)
"""

from __future__ import annotations

import hashlib
import json
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import settings
from src.ingestion.processors.text_cleaner import get_text_cleaner

# Ajuste: Usando logging estándar para evitar errores de importación si no existe config.logging
log = logging.getLogger(__name__)


_LIBRARY_ROOT = Path(settings.ROOT_DIR) / "data" / "processed" / "markdown"
_LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)
_MANIFEST_PATH = _LIBRARY_ROOT / "_manifest.json"


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest() -> dict:
    if _MANIFEST_PATH.exists():
        try:
            return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_manifest(manifest: dict):
    _MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


class MarkdownLibrary:
    """Gestión de Golden Markdown Library."""

    @staticmethod
    def exists(pdf_path: Path) -> bool:
        return _file_hash(pdf_path) in _load_manifest()

    @staticmethod
    def get_md_path(pdf_path: Path) -> Optional[Path]:
        fhash = _file_hash(pdf_path)
        manifest = _load_manifest()
        if fhash in manifest:
            md_path = Path(manifest[fhash]["md_path"])
            if md_path.exists():
                return md_path
        return None

    @staticmethod
    def save(pdf_path: Path, markdown_content: str, source_tool: str = "docling_advanced") -> Path:
        fhash = _file_hash(pdf_path)
        stem = re.sub(r"[^\w\-]", "_", pdf_path.stem)[:80]
        md_filename = f"{stem}_{fhash[:12]}.md"
        md_path = _LIBRARY_ROOT / md_filename

        header = f"---\nsource_pdf: {pdf_path.name}\nprocessed_at: {datetime.now(timezone.utc).isoformat()}\nsource_tool: {source_tool}\nfile_hash: {fhash}\n---\n\n"

        md_path.write_text(header + markdown_content.strip(), encoding="utf-8")

        manifest = _load_manifest()
        manifest[fhash] = {
            "pdf_name": pdf_path.name,
            "md_path": str(md_path),
            "md_filename": md_filename,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "source_tool": source_tool,
            "chars": len(markdown_content),
        }
        _save_manifest(manifest)

        log.info(f"[GOLDEN_MD] Guardado: {md_filename} ({len(markdown_content):,} chars)")
        return md_path


class MarkdownConversionService:
    """Servicio de conversión usando el DoclingLoader avanzado."""

    @staticmethod
    def convert_and_save(
        pdf_path: str | Path, 
        force_reconvert: bool = False,
        use_ocr: bool = True
    ) -> Dict[str, Any]:
        from src.ingestion.loaders.pdf_docling import get_docling_loader
        pdf_path = Path(pdf_path)

        if not force_reconvert and MarkdownLibrary.exists(pdf_path):
            md_path = MarkdownLibrary.get_md_path(pdf_path)
            log.info(f"[MD_SERVICE] Reutilizando Golden Copy: {pdf_path.name}")
            return {"md_path": md_path, "was_cached": True, "tool": "cached"}

        try:
            log.info(f"[MD_SERVICE] Convirtiendo con DoclingLoader avanzado: {pdf_path.name}")

            loader = get_docling_loader(
                use_ocr=use_ocr,
                force_full_page_ocr=True,
                images_scale=2.0,
                table_mode="accurate"
            )

            documents = loader.load(pdf_path)

            # Combinar todo el contenido de los chunks
            full_markdown = "\n\n".join([doc.page_content for doc in documents])

            md_path = MarkdownLibrary.save(pdf_path, full_markdown, source_tool="docling_advanced")

            return {
                "md_path": md_path,
                "chars": len(full_markdown),
                "tool": "docling_advanced",
                "was_cached": False,
                "chunks": len(documents),
                "tables": sum(1 for d in documents if "TABLA" in d.page_content.upper())
            }

        except Exception as e:
            log.error(f"[MD_SERVICE] Docling falló: {e}. Usando fallback básico.")
            # Fallback mínimo
            markdown = f"[ERROR] Falló conversión avanzada.\nArchivo: {pdf_path.name}\nError: {str(e)}"
            md_path = MarkdownLibrary.save(pdf_path, markdown, source_tool="error_fallback")
            return {"md_path": md_path, "chars": len(markdown), "tool": "error_fallback", "was_cached": False}


# Mantener compatibilidad con funciones antiguas si las usas
def _pdf_to_markdown_pdfplumber(pdf_path: Path) -> str:
    """Fallback simple (solo si es estrictamente necesario)."""
    return f"[FALLBACK] No se pudo procesar {pdf_path.name} con Docling."
