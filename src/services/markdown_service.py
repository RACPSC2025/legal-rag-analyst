"""
Markdown Service — "Golden Markdown Library"
─────────────────────────────────────────────
Capa de persistencia estructurada entre el PDF bruto y el motor de búsqueda.

Flujo completo:
    PDF ──► Docling ──► .md (Golden Copy) ──► RAG / Consulta directa

Ventajas de esta capa:
  • Tokens: Markdown plano cuesta ~70% menos que enviar el PDF al LLM.
  • Fidelidad: Las tablas legales quedan como | col | col |, perfectas para
    cualquier LLM barato (Nova Lite las entiende sin visión artificial).
  • Corrección humana: Un abogado puede editar el .md antes de indexar.
  • Respaldo permanente: El procesamiento Docling se hace una sola vez.
  • Consulta directa a .md: Más rápido que re-procesar el PDF cada vez.

Módulos exportados:
  MarkdownLibrary          — gestión de la biblioteca de archivos .md
  MarkdownConversionService— conversión PDF → .md con Docling / fallback fitz
  query_markdown_direct    — consulta directa a .md (reemplaza query_pdf_direct)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pdfplumber
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config import settings

logger = logging.getLogger(__name__)

# ── Rutas de la biblioteca ─────────────────────────────────────────────────
_LIBRARY_ROOT = Path(settings.ROOT_DIR) / "data" / "processed" / "markdown"
_LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)

_MANIFEST_PATH = _LIBRARY_ROOT / "_manifest.json"


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST — Registro de archivos procesados
# ═══════════════════════════════════════════════════════════════════════════

def _load_manifest() -> dict:
    """Carga el manifiesto de la biblioteca (hash → metadata)."""
    if _MANIFEST_PATH.exists():
        try:
            return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_manifest(manifest: dict) -> None:
    """Persiste el manifiesto."""
    _MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _file_hash(path: Path) -> str:
    """SHA-256 de los primeros 256KB del archivo (rápido, suficiente para PDFs legales)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(262144))
    return h.hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════════
# MARKDOWN LIBRARY — Gestión de la biblioteca
# ═══════════════════════════════════════════════════════════════════════════

class MarkdownLibrary:
    """
    Gestiona la colección de archivos .md procesados.

    Estructura en disco:
        data/processed/markdown/
            _manifest.json          — registro de todos los archivos
            decreto_1072_abc123.md  — Golden Copy del Decreto 1072
            contrato_xyz_def456.md  — Golden Copy de un contrato
    """

    @staticmethod
    def exists(pdf_path: Path) -> bool:
        """Indica si ya existe una Golden Copy para este PDF."""
        fhash = _file_hash(pdf_path)
        return fhash in _load_manifest()

    @staticmethod
    def get_md_path(pdf_path: Path) -> Optional[Path]:
        """Retorna la ruta al .md si existe, None en caso contrario."""
        fhash = _file_hash(pdf_path)
        manifest = _load_manifest()
        if fhash in manifest:
            md_path = Path(manifest[fhash]["md_path"])
            if md_path.exists():
                return md_path
        return None

    @staticmethod
    def get_md_content(pdf_path: Path) -> Optional[str]:
        """Lee el contenido Markdown de la Golden Copy."""
        md_path = MarkdownLibrary.get_md_path(pdf_path)
        if md_path:
            return md_path.read_text(encoding="utf-8")
        return None

    @staticmethod
    def save(pdf_path: Path, markdown_content: str, source_tool: str = "docling") -> Path:
        """
        Guarda el Markdown procesado como Golden Copy.

        Naming convention: {stem_limpio}_{hash8}.md
        El hash garantiza unicidad incluso si dos archivos tienen el mismo nombre.
        """
        fhash = _file_hash(pdf_path)
        stem = re.sub(r"[^\w\-]", "_", pdf_path.stem)[:60]
        md_filename = f"{stem}_{fhash[:8]}.md"
        md_path = _LIBRARY_ROOT / md_filename

        # Encabezado YAML-like con metadata
        header = (
            f"---\n"
            f"source_pdf: {pdf_path.name}\n"
            f"processed_at: {datetime.now(timezone.utc).isoformat()}\n"
            f"source_tool: {source_tool}\n"
            f"file_hash: {fhash}\n"
            f"---\n\n"
        )

        md_path.write_text(header + markdown_content, encoding="utf-8")

        # Actualizar manifiesto
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

        logger.info(f"[MD_LIBRARY] Golden Copy guardada: {md_filename} ({len(markdown_content):,} chars)")
        return md_path

    @staticmethod
    def list_all() -> list[dict]:
        """Lista todos los archivos en la biblioteca con su metadata."""
        manifest = _load_manifest()
        items = []
        for fhash, meta in manifest.items():
            md_path = Path(meta["md_path"])
            items.append({
                **meta,
                "exists_on_disk": md_path.exists(),
                "hash": fhash,
            })
        return sorted(items, key=lambda x: x.get("processed_at", ""), reverse=True)

    @staticmethod
    def delete(md_filename: str) -> bool:
        """Elimina una Golden Copy de la biblioteca."""
        md_path = _LIBRARY_ROOT / md_filename
        manifest = _load_manifest()
        # Buscar el hash correspondiente
        hash_to_delete = None
        for fhash, meta in manifest.items():
            if meta.get("md_filename") == md_filename:
                hash_to_delete = fhash
                break
        if hash_to_delete:
            del manifest[hash_to_delete]
            _save_manifest(manifest)
        if md_path.exists():
            md_path.unlink()
            logger.info(f"[MD_LIBRARY] Eliminado: {md_filename}")
            return True
        return False

    @staticmethod
    def get_library_root() -> Path:
        return _LIBRARY_ROOT


# ═══════════════════════════════════════════════════════════════════════════
# CONVERSION SERVICE — PDF → Markdown con Docling
# ═══════════════════════════════════════════════════════════════════════════

# Patrones de limpieza específicos del Decreto 1072 y normativa colombiana
_NOISE_PATTERNS = [
    (r"Decreto\s+1072\s+de\s+2015\s+Sector\s+Trabajo\s*\d*\s*EVA\s*[-]?\s*Gestor\s+Normativo", ""),
    (r"Departamento\s+Administrativo\s+de\s+la\s+Funci[oó]n\s+P[uú]blica", ""),
    (r"_{4,}|-{4,}", ""),
]


def _clean_markdown(text: str) -> str:
    """Limpieza de ruidos de encabezados/pies en el Markdown resultante."""
    for pattern, replacement in _NOISE_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # Normalizar saltos excesivos sin romper la estructura Markdown
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def _pdf_to_markdown_docling(pdf_path: Path, use_ocr: bool = False) -> tuple[str, str]:
    """
    Convierte PDF a Markdown usando Docling (IBM).
    Retorna (markdown_content, tool_name).
    """
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        artifacts_path = str(Path(settings.ROOT_DIR) / "storage" / "docling_models")

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = use_ocr
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    artifacts_path=artifacts_path,
                )
            }
        )

        result = converter.convert(str(pdf_path))
        markdown = result.document.export_to_markdown()
        cleaned = _clean_markdown(markdown)

        logger.info(f"[DOCLING] '{pdf_path.name}' → {len(cleaned):,} chars Markdown")
        return cleaned, "docling"

    except ImportError:
        logger.warning("[DOCLING] No instalado. Usando fallback pdfplumber.")
        return _pdf_to_markdown_pdfplumber(pdf_path), "pdfplumber_fallback"
    except Exception as e:
        logger.error(f"[DOCLING] Error en '{pdf_path.name}': {e}. Usando fallback.")
        return _pdf_to_markdown_pdfplumber(pdf_path), "pdfplumber_fallback"


def _pdf_to_markdown_pdfplumber(pdf_path: Path) -> str:
    """
    Fallback: convierte PDF a pseudo-Markdown usando pdfplumber.
    Detecta tablas y las exporta como tablas Markdown.
    Detecta líneas que parecen encabezados y les añade ##.
    """
    lines = []

    _ENCABEZADO_LEGAL = re.compile(
        r"^(ARTÍCULO|CAPÍTULO|SECCIÓN|PARÁGRAFO|PARTE\s+\d|TÍTULO)\s",
        re.IGNORECASE,
    )
    _NUMERAL = re.compile(r"^\d+\.\s")

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):

                # Intentar extraer tablas primero
                tables = page.extract_tables()
                table_bboxes = []
                for table in tables:
                    if not table or not table[0]:
                        continue
                    # Exportar como tabla Markdown
                    header = table[0]
                    sep = ["---"] * len(header)
                    md_table = "| " + " | ".join(str(c or "") for c in header) + " |\n"
                    md_table += "| " + " | ".join(sep) + " |\n"
                    for row in table[1:]:
                        md_table += "| " + " | ".join(str(c or "") for c in row) + " |\n"
                    lines.append(md_table)

                # Extraer texto restante
                raw = page.extract_text() or ""
                for line in raw.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    # Skip ruido de encabezado/pie de página
                    if re.search(r"EVA - Gestor Normativo|Función Pública", line, re.IGNORECASE):
                        continue
                    # Detectar encabezados legales → convertir a ## Markdown
                    if _ENCABEZADO_LEGAL.match(line):
                        lines.append(f"\n## {line}\n")
                    elif _NUMERAL.match(line):
                        lines.append(f"- {line}")
                    else:
                        lines.append(line)

    except Exception as e:
        logger.error(f"[PDFPLUMBER_FALLBACK] Error en '{pdf_path.name}': {e}")

    markdown = "\n".join(lines)
    return _clean_markdown(markdown)


class MarkdownConversionService:
    """
    Servicio de conversión PDF → Markdown.
    Guarda automáticamente en la Golden Library.
    """

    @staticmethod
    def convert_and_save(
        pdf_path: str | Path,
        use_ocr: bool = False,
        force_reconvert: bool = False,
    ) -> dict:
        """
        Convierte un PDF a Markdown y lo guarda en la biblioteca.

        Args:
            pdf_path:         Ruta al PDF.
            use_ocr:          Activar OCR en Docling (PDFs escaneados).
            force_reconvert:  Forzar reconversión aunque ya exista Golden Copy.

        Returns:
            dict con:
                md_path   — ruta al archivo .md guardado
                chars     — tamaño del Markdown
                tool      — herramienta usada
                was_cached — True si ya existía y se reutilizó
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

        # Reutilizar Golden Copy si existe
        if not force_reconvert and MarkdownLibrary.exists(pdf_path):
            md_path = MarkdownLibrary.get_md_path(pdf_path)
            logger.info(f"[MD_SERVICE] Reutilizando Golden Copy: {md_path.name}")
            return {
                "md_path": md_path,
                "chars": len(md_path.read_text(encoding="utf-8")),
                "tool": "cached",
                "was_cached": True,
            }

        # Convertir con Docling
        markdown_content, tool = _pdf_to_markdown_docling(pdf_path, use_ocr=use_ocr)

        if not markdown_content.strip():
            raise ValueError(f"No se pudo extraer texto de '{pdf_path.name}'")

        # Guardar en biblioteca
        md_path = MarkdownLibrary.save(pdf_path, markdown_content, source_tool=tool)

        return {
            "md_path": md_path,
            "chars": len(markdown_content),
            "tool": tool,
            "was_cached": False,
        }

    @staticmethod
    def convert_multiple(
        pdf_paths: list[str | Path],
        use_ocr: bool = False,
    ) -> list[dict]:
        """Convierte múltiples PDFs en lote."""
        results = []
        for pdf_path in pdf_paths:
            try:
                result = MarkdownConversionService.convert_and_save(pdf_path, use_ocr=use_ocr)
                results.append({"pdf": str(pdf_path), **result, "error": None})
            except Exception as e:
                logger.error(f"[MD_SERVICE] Error en '{pdf_path}': {e}")
                results.append({"pdf": str(pdf_path), "error": str(e)})
        return results


# ═══════════════════════════════════════════════════════════════════════════
# CONSULTA DIRECTA A MARKDOWN — Sin re-procesar el PDF
# ═══════════════════════════════════════════════════════════════════════════

_MARKDOWN_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Eres Amatia Legal Agent, asistente juridico especializado en normativa colombiana.\n\n"
     "REGLAS ABSOLUTAS:\n"
     "1. Responde UNICAMENTE con informacion del DOCUMENTO proporcionado.\n"
     "2. Reproduce el contenido del articulo solicitado de forma COMPLETA y estructurada.\n"
     "3. Incluye TODOS los numerales, paragrafos y notas de fuente (Decreto X de YYYY, art. N).\n"
     "4. NO omitas paragrafos aunque esten al final del articulo.\n"
     "5. NO repitas el mismo texto dos veces.\n"
     "6. Si el articulo no esta en el documento, responde exactamente:\n"
     '   "No encontre el articulo solicitado en el documento proporcionado."\n'
     "7. Las tablas en el documento ya estan en formato Markdown (|col|col|). "
     "Preservalas integras en tu respuesta.\n"
     "8. Formato limpio: numerales en lineas separadas, paragrafos claramente diferenciados."),
    ("human",
     "DOCUMENTO (formato Markdown — tablas y estructura preservadas):\n\n{context}\n\n"
     "CONSULTA: {question}\n\n"
     "Proporciona el articulo completo, incluyendo todos sus numerales, paragrafos y tablas:")
])


def _extract_article_from_markdown(markdown: str, article_num: str) -> str:
    """
    Extrae un artículo del texto Markdown.
    Primero intenta con encabezados Markdown (## ARTÍCULO X.X.X),
    luego con el texto plano del artículo.
    """
    escaped = re.escape(article_num)

    # Intento 1: Encabezado Markdown generado por Docling
    pattern_md = (
        rf"(#{1,4}\s*ART[IÍ]CULO\s*{escaped}\.?.*?"
        rf"(?=\n#{1,4}\s*ART[IÍ]CULO\s*\d|\n#{1,4}\s*CAP[IÍ]TULO|\n#{1,4}\s*SECCI[OÓ]N|\Z))"
    )
    match = re.search(pattern_md, markdown, re.DOTALL | re.IGNORECASE)
    if match:
        logger.info(f"[MD_QUERY] Art. {article_num} encontrado como encabezado Markdown.")
        return match.group(1).strip()

    # Intento 2: Texto plano (igual que en pdf_direct_service)
    pattern_plain = (
        rf"(ART[IÍ]CULO\s*{escaped}\.?\s.*?"
        rf"(?=\nART[IÍ]CULO\s+[\d]|\nCAP[IÍ]TULO|\nSECCI[OÓ]N|\nPARTE|\Z))"
    )
    match = re.search(pattern_plain, markdown, re.DOTALL | re.IGNORECASE)
    if match:
        logger.info(f"[MD_QUERY] Art. {article_num} encontrado como texto plano.")
        return match.group(1).strip()

    logger.warning(f"[MD_QUERY] Art. {article_num} no encontrado en el Markdown.")
    return ""


def _strip_yaml_header(markdown: str) -> str:
    """Elimina el encabezado YAML-like guardado por MarkdownLibrary.save()."""
    if markdown.startswith("---"):
        end = markdown.find("\n---\n", 3)
        if end != -1:
            return markdown[end + 5:].strip()
    return markdown


def query_markdown_direct(
    md_paths_or_pdf_paths: list[str | Path],
    question: str,
    prefer_golden_copy: bool = True,
) -> dict:
    """
    Consulta directa a archivos .md (Golden Copies) o PDFs.

    Si se pasan PDFs y prefer_golden_copy=True, busca automáticamente
    la Golden Copy correspondiente en la biblioteca antes de intentar
    leer el PDF. Si no existe Golden Copy, cae a query_pdf_direct.

    Args:
        md_paths_or_pdf_paths: Lista de rutas a .md o .pdf
        question:              Pregunta del usuario
        prefer_golden_copy:    Buscar Golden Copy si se pasa un PDF

    Returns:
        dict con answer, source_docs, mode, token_source
    """
    from src.services.pdf_direct_service import query_pdf_direct, _format_legal_output

    sources = []
    full_markdown = ""

    for path in md_paths_or_pdf_paths:
        path = Path(path)

        # ── Determinar el contenido Markdown a usar ──────────────────────
        markdown_content = None

        if path.suffix.lower() == ".md":
            # Archivo .md directo
            if path.exists():
                markdown_content = _strip_yaml_header(
                    path.read_text(encoding="utf-8")
                )
                sources.append(path.name)
            else:
                logger.warning(f"[MD_QUERY] Archivo .md no encontrado: {path}")

        elif path.suffix.lower() == ".pdf":
            # PDF — buscar Golden Copy primero
            if prefer_golden_copy and MarkdownLibrary.exists(path):
                md_content_raw = MarkdownLibrary.get_md_content(path)
                if md_content_raw:
                    markdown_content = _strip_yaml_header(md_content_raw)
                    sources.append(f"{path.name} (Golden MD)")
                    logger.info(f"[MD_QUERY] Usando Golden Copy para '{path.name}'")
            else:
                logger.info(f"[MD_QUERY] Sin Golden Copy para '{path.name}'. Fallback a PDF directo.")

        if markdown_content:
            full_markdown += markdown_content + "\n\n"

    # Si no hay Markdown disponible, delegar a query_pdf_direct
    if not full_markdown.strip():
        pdf_paths = [p for p in md_paths_or_pdf_paths if Path(p).suffix.lower() == ".pdf"]
        if pdf_paths:
            logger.info("[MD_QUERY] Sin Markdown disponible — delegando a query_pdf_direct.")
            result = query_pdf_direct(pdf_paths, question)
            result["mode"] = "pdf_direct_fallback"
            return result
        return {
            "answer": "No se encontraron documentos disponibles para consultar.",
            "source_docs": [],
            "mode": "error",
            "token_source": "none",
        }

    # ── Extracción focalizada del artículo ────────────────────────────────
    article_match = re.search(r"(\d+(?:\.\d+){2,})", question)
    requested_article = article_match.group(1) if article_match else None

    if requested_article:
        exact = _extract_article_from_markdown(full_markdown, requested_article)
        context_to_llm = exact if exact else full_markdown[:180_000]
        if not exact:
            logger.warning(f"[MD_QUERY] Fallback a texto completo para Art. {requested_article}")
    else:
        context_to_llm = full_markdown[:180_000]

    # ── Consulta al LLM ───────────────────────────────────────────────────
    from src.services.pdf_direct_service import get_large_context_llm
    llm = get_large_context_llm()
    chain = _MARKDOWN_QUERY_PROMPT | llm | StrOutputParser()

    try:
        raw_answer = chain.invoke({
            "context": context_to_llm,
            "question": question,
        })
        answer = _format_legal_output(raw_answer)
    except Exception as e:
        logger.error(f"[MD_QUERY] Error LLM: {e}")
        answer = "Error al procesar la consulta con el modelo de lenguaje."

    return {
        "answer": answer,
        "source_docs": sources,
        "mode": "markdown_direct",
        "token_source": "markdown",  # Para métricas de ahorro de tokens
    }
