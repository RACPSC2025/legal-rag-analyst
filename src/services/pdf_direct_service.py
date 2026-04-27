"""
Servicio PDF Directo — v2 FINAL (bugs de corte y duplicacion resueltos)

BUGS CORREGIDOS vs version original:
─────────────────────────────────────
BUG 1 — Articulo cortado en cambio de pagina:
  Causa:  _extract_text() concatenaba paginas crudas. El pie de pagina
          "Decreto 1072 de 2015 Sector Trabajo 9 EVA - Gestor Normativo"
          quedaba incrustado en PARAGRAFO 1, cortando "...de este [pie]
          [encabezado] Decreto para que..."
  Fix:    _clean_page_text() limpia cada pagina ANTES de concatenar.
          _join_broken_sentences() une parrafos que quedaron rotos en el
          limite de pagina (terminan sin puntuacion, el siguiente no es
          inicio de articulo/paragrafo/cita).

BUG 2 — Respuesta duplicada en la UI:
  Causa:  El prompt pedia "copia literal", el LLM repetia el contexto
          completo, y la UI mostraba contexto + respuesta identicos.
  Fix:    Prompt reformulado para extraccion estructurada y completa,
          sin instruccion de copia literal.

Dependencia nueva: pdfplumber (en lugar de fitz/PyMuPDF directo)
  pip install pdfplumber
"""

import logging
import re
from pathlib import Path
from typing import List

import pdfplumber
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config import settings

logger = logging.getLogger(__name__)


_DIRECT_PROMPT = ChatPromptTemplate.from_messages([
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
     "7. Formato limpio: numerales en lineas separadas, paragrafos claramente diferenciados."),
    ("human",
     "DOCUMENTO (texto extraido del PDF):\n\n{context}\n\n"
     "CONSULTA: {question}\n\n"
     "Proporciona el articulo completo, incluyendo todos sus numerales y paragrafos:")
])


def _clean_page_text(text: str) -> str:
    """
    Limpia UNA pagina: elimina encabezados y pies del Decreto 1072.
    Se llama por pagina ANTES de concatenar para que no queden incrustados
    en medio de articulos que cruzan el limite de pagina.
    """
    if not text:
        return ""
    text = re.sub(
        r"Decreto\s+1072\s+de\s+2015\s+Sector\s+Trabajo\s*\d*\s*EVA\s*[-]?\s*Gestor\s+Normativo",
        "", text, flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Departamento\s+Administrativo\s+de\s+la\s+Funci[oó]n\s+P[uú]blica",
        "", text, flags=re.IGNORECASE,
    )
    text = re.sub(r"_{4,}|-{4,}", "", text)
    lines = [ln for ln in text.split("\n") if ln.strip()]
    return "\n".join(lines).strip()


def _join_broken_sentences(text: str) -> str:
    """
    Une parrafos rotos en limites de pagina.
    Si un parrafo no cierra con puntuacion y el siguiente no es inicio
    de ARTICULO/CAPITULO/PARAGRAFO/cita, los une con un espacio.
    Trabaja a nivel de parrafo (bloques separados por linea vacia) para
    manejar el caso donde el pie de pagina genera un doble salto.
    """
    paragraphs = re.split(r"\n\n+", text)
    result = []
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i].strip()
        if i + 1 < len(paragraphs):
            next_para = paragraphs[i + 1].strip()
            last_char = para[-1] if para else ""
            is_open = last_char not in ".;:)]\""
            is_continuation = next_para and not re.match(
                r"^(ART[IÍ]CULO|CAP[IÍ]TULO|SECCI[OÓ]N|P[AÁ]R[AÁ]GRAFO|\d+\.\s|\(Decreto|\(Par[aá]grafo)",
                next_para, re.IGNORECASE,
            )
            if is_open and is_continuation:
                result.append(para + " " + next_para)
                i += 2
                continue
        result.append(para)
        i += 1
    return "\n\n".join(result)


def _format_legal_output(text: str) -> str:
    """Formatea la respuesta final para legibilidad del usuario."""
    if not text:
        return ""

    # Eliminar Markdown del LLM (itálicas con *, negritas con **)
    text = text.replace("**", "").replace("*", "")

    # ── FASE 1: Corregir artefactos del LLM ──────────────────────────

    # 1a. Paréntesis huérfano: "(\nParágrafo adicionado" → "(Parágrafo adicionado"
    text = re.sub(r"\(\s*\n+\s*([^(\n])", r"(\1", text)

    # 1b. PARÁGRAFO separado del número: "PARÁGRAFO\n1." → "PARÁGRAFO 1."
    text = re.sub(
        r"(P[AÁ]R[AÁ]GRAFO)\s*\n+\s*(\d+\.?)\s*",
        lambda m: m.group(1) + " " + m.group(2) + " ",
        text,
    )

    # ── FASE 2: Unir y normalizar ─────────────────────────────────────

    # 2a. Unir líneas rotas DENTRO de párrafos (solo entre minúsculas)
    text = re.sub(r"([a-záéíóúüñA-ZÁÉÍÓÚÜÑ,;])\n([a-záéíóúüñ])", r"\1 \2", text)

    # 2b. Normalizar saltos excesivos
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 2c. Numerales en línea separada — con exclusión de PARÁGRAFO
    def _numeral_newline(match):
        """Solo inserta \n si el contexto NO es un PARÁGRAFO."""
        full = match.group(0)
        start = max(0, match.start() - 20)
        prefix = text[start:match.start()]
        # Si justo antes viene "PARÁGRAFO", NO insertar salto
        if re.search(r"PARÁGRAFO\s*$", prefix, re.IGNORECASE):
            return full  # devolver sin cambios
        return "\n" + match.group(1)

    text = re.sub(r"\s+(\d+\.\s+[A-ZÁÉÍÓÚÜÑ])", _numeral_newline, text)

    # ── FASE 3: Estructurar elementos legales ─────────────────────────

    # 2d. Saltos dobles antes de PARÁGRAFO N.
    text = re.sub(r"\s*(P[AÁ]R[AÁ]GRAFO\s*\d+\.?\s*)", r"\n\n\1", text, flags=re.IGNORECASE)

    # 2e. Citas de Decreto al final — [\s\S] cruza saltos de línea
    text = re.sub(r"\s*(\(Decreto\s+\d+\s+de\s+\d+[\s\S]*?\))", r"\n\n\1", text)

    # 2f. Notas de parágrafo adicionado — [\s\S] cruza saltos de línea
    text = re.sub(r"\s*(\(Par[aá]grafo\s+adicionado[\s\S]*?\))", r"\n\1", text, flags=re.IGNORECASE)

    # ── FASE 4: Limpieza final ────────────────────────────────────────

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def _extract_full_text_multipage(pdf_path: Path) -> str:
    """
    Extrae texto del PDF limpiando encabezados/pies POR PAGINA antes de
    concatenar. Clave para evitar el corte de articulos en cambio de pagina.
    """
    pages = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                raw = page.extract_text() or ""
                clean = _clean_page_text(raw)
                if clean.strip():
                    pages.append(clean)
    except Exception as e:
        logger.error(f"[PDF_DIRECT] Error extrayendo '{pdf_path.name}': {e}")
    return "\n\n".join(pages)


def _extract_exact_article(text: str, article_num: str) -> str:
    """
    Extrae el articulo solicitado. Para ante el siguiente ARTICULO numerado,
    CAPITULO, SECCION, PARTE o fin de texto.
    """
    escaped = re.escape(article_num)
    pattern = (
        rf"(ART[IÍ]CULO\s*{escaped}\.?\s.*?"
        rf"(?=\nART[IÍ]CULO\s+[\d]|\nCAP[IÍ]TULO|\nSECCI[OÓ]N|\nPARTE|\Z))"
    )
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
        logger.info(f"[PDF_DIRECT] Art. {article_num} extraido — {len(extracted)} chars.")
        return extracted
    logger.warning(f"[PDF_DIRECT] Art. {article_num} no encontrado con regex.")
    return ""


def get_large_context_llm():
    """LLM de contexto largo para PDF directo (Nova Lite/Pro via Bedrock)."""
    from langchain_aws import ChatBedrock
    import boto3

    model_id = settings.AWS_MODEL_LARGE_CONTEXT
    provider = "amazon" if "nova" in model_id.lower() else "meta"
    session = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN if settings.AWS_SESSION_TOKEN else None,
        region_name=settings.AWS_REGION,
    )
    client = session.client("bedrock-runtime", region_name=settings.AWS_REGION)
    return ChatBedrock(
        client=client,
        model_id=model_id,
        provider=provider,
        temperature=0.0,
        max_tokens=2048,
        region_name=settings.AWS_REGION,
    )


def query_pdf_direct(pdf_paths: List[str | Path], question: str) -> dict:
    """
    Consulta directa a PDF(s) sin indexar.

    Flujo:
      1. Extraer texto limpiando encabezados/pies POR PAGINA.
      2. Unir parrafos rotos en limites de pagina.
      3. Si hay numero de articulo en la pregunta, extraer solo ese articulo.
      4. Enviar al LLM con prompt estructurado.
      5. Formatear respuesta para legibilidad.
    """
    logger.info(f"[PDF_DIRECT] {len(pdf_paths)} PDF(s) | '{question[:80]}'")

    full_text = ""
    sources = []

    for pdf_path in pdf_paths:
        pdf_path = Path(pdf_path)
        page_text = _extract_full_text_multipage(pdf_path)
        if page_text.strip():
            full_text += page_text + "\n\n"
            sources.append(pdf_path.name)

    if not full_text.strip():
        return {"answer": "No se pudieron cargar los PDFs.", "source_docs": [], "mode": "pdf_direct"}

    # Unir parrafos rotos en limites de pagina
    full_text = _join_broken_sentences(full_text)

    # Extraccion focalizada si hay numero de articulo en la pregunta
    article_match = re.search(r"(\d+(?:\.\d+){2,})", question)
    requested_article = article_match.group(1) if article_match else None

    if requested_article:
        exact = _extract_exact_article(full_text, requested_article)
        context_to_llm = exact if exact else full_text[:180_000]
        if not exact:
            logger.warning(f"[PDF_DIRECT] Fallback a texto completo para Art. {requested_article}")
    else:
        context_to_llm = full_text[:180_000]

    llm = get_large_context_llm()
    chain = _DIRECT_PROMPT | llm | StrOutputParser()

    try:
        raw_answer = chain.invoke({"context": context_to_llm, "question": question})
        answer = _format_legal_output(raw_answer)
    except Exception as e:
        logger.error(f"[PDF_DIRECT] Error LLM: {e}")
        answer = "Error al procesar con el modelo de lenguaje."

    return {"answer": answer, "source_docs": sources, "mode": "pdf_direct"}
