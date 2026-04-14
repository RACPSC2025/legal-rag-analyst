"""
Amatia Express Legal Agent AI — Streamlit MVP
─────────────────────────────────────────────
Modos de operación:
  📚 Biblioteca Jurídica  → RAG permanente sobre ChromaDB (CRAG + Self-RAG)
  📑 Mesa de Trabajo      → Consulta temporal de PDFs sin indexar

Módulos propios requeridos:
  src/core/__init__.py          → get_graph, RagState
  src/retrieval/__init__.py     → get_vector_store, get_document_count
  src/ingestion/__init__.py     → load_pdfs, LoaderType
  src/services/pdf_direct_service.py
  src/services/specialized_analysis.py
"""

import warnings
import logging

warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("transformers").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

import streamlit as st
import os
import sys
import uuid
import json
from pathlib import Path

# ── Rutas del proyecto ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Imports del core (deben existir antes de arrancar) ─────────────────────
from src.core import get_graph, RagState
from src.services.pdf_direct_service import query_pdf_direct
from src.services.specialized_analysis import query_specialized_analysis
from src.retrieval import get_document_count, reset_vector_store
from src.ingestion import load_pdfs, LoaderType

# ── Configuración de página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Amatia Express Legal Agent AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background-color: #fcfcfc; }

[data-testid="stSidebar"] {
    background-color: #0f172a;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label { color: #f8fafc !important; }

.stButton>button {
    width: 100%;
    border-radius: 8px;
    height: 3.2em;
    background-color: #2563eb;
    color: white;
    font-weight: 600;
    border: none;
    transition: all 0.3s ease;
}
.stButton>button:hover {
    background-color: #1d4ed8;
    box-shadow: 0 4px 12px rgba(37,99,235,0.3);
}

.status-card {
    padding: 20px;
    border-radius: 12px;
    background-color: white;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}
.mode-indicator {
    padding: 8px 14px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 10px;
}
.mode-biblio { background-color: #dcfce7; color: #166534; }
.mode-mesa   { background-color: #dbeafe; color: #1e40af; }

.stTabs [data-baseweb="tab-list"] { gap: 20px; padding: 0 10px; }
.stTabs [data-baseweb="tab"] {
    height: 45px;
    background-color: transparent;
    border: none;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    color: #2563eb !important;
    border-bottom: 2px solid #2563eb !important;
}
</style>
""", unsafe_allow_html=True)

# ── Estado de sesión ────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "messages": [],
        "session_pdf_paths": [],
        "app_mode": "Biblioteca",        # "Biblioteca" | "Mesa"
        "specialized_mode": False,       # Toggle análisis crítico JSON
        "selected_loader": LoaderType.PYMUPDF,  # Loader de ingestion
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_state()


# ── Grafo LangGraph como singleton de Streamlit (no se recompila en cada rerun) ──
@st.cache_resource(show_spinner=False)
def _get_cached_graph():
    return get_graph()


# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='text-align:center;padding:10px 0;'>
            <h1 style='font-size:2.2em;margin-bottom:0;'>⚖️</h1>
            <h2 style='font-size:1.4em;color:white;margin-top:10px;'>Amatia Express</h2>
            <p style='color:#94a3b8;font-size:0.9em;'>Legal Agent AI</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("🛠️ Modo de Trabajo")
    mode_label = st.radio(
        "Seleccione funcionalidad:",
        ["📚 Biblioteca Jurídica", "📑 Mesa de Trabajo (Caso)"],
        index=0 if st.session_state.app_mode == "Biblioteca" else 1,
        help="Biblioteca: RAG Permanente · Mesa: Análisis Temporal",
    )
    st.session_state.app_mode = "Biblioteca" if "Biblioteca" in mode_label else "Mesa"

    st.markdown("---")

    doc_count = get_document_count()
    st.metric("Documentos Indexados", doc_count)

    # Toggle análisis crítico — accesible desde ambas pestañas del chat
    st.session_state.specialized_mode = st.toggle(
        "🔬 Análisis Crítico (JSON)",
        value=st.session_state.specialized_mode,
        help="Activa análisis jurídico estructurado (solo Modo Mesa).",
    )

    st.markdown("---")

    if st.button("🔄 Limpiar Chat"):
        st.session_state.messages = []
        st.rerun()


# ── Header principal ────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([0.8, 0.2])
with col_h1:
    st.title("Amatia Express Legal Agent AI")
    st.markdown("_Tu consultor jurídico experto e inteligente._")
with col_h2:
    if st.session_state.app_mode == "Biblioteca":
        st.markdown('<div class="mode-indicator mode-biblio">MODO BIBLIOTECA</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mode-indicator mode-mesa">MODO MESA DE TRABAJO</div>', unsafe_allow_html=True)


# ── Pestañas ────────────────────────────────────────────────────────────────
tab_chat, tab_admin = st.tabs(["💬 Centro de Consultas", "⚙️ Gestión de Datos"])


# ═══════════════════════════════════════════════════════════════════════════
# TAB: GESTIÓN DE DATOS
# ═══════════════════════════════════════════════════════════════════════════
with tab_admin:
    st.subheader("Panel de Administración de Información")
    col_adm1, col_adm2 = st.columns([0.6, 0.4])

    with col_adm1:

        # ── MODO BIBLIOTECA: ingesta permanente ────────────────────────────
        if st.session_state.app_mode == "Biblioteca":
            st.markdown("### 📥 Ingesta a Memoria Permanente")
            st.write("Los documentos serán fragmentados, embebidos y almacenados en ChromaDB.")

            # Selector de loader
            loader_option = st.selectbox(
                "Motor de extracción PDF",
                options={
                    "PyMuPDF (rápido, texto nativo — recomendado)": LoaderType.PYMUPDF,
                    "Docling (tablas complejas, columnas múltiples → Markdown)": LoaderType.DOCLING,
                }.keys(),
                help=(
                    "PyMuPDF: ideal para la mayoría de decretos y leyes en texto digital.\n"
                    "Docling: úsalo cuando el PDF tenga tablas de artículos o gacetas con columnas."
                ),
            )
            loader_map = {
                "PyMuPDF (rápido, texto nativo — recomendado)": LoaderType.PYMUPDF,
                "Docling (tablas complejas, columnas múltiples → Markdown)": LoaderType.DOCLING,
            }
            st.session_state.selected_loader = loader_map[loader_option]

            if st.session_state.selected_loader == LoaderType.DOCLING:
                use_ocr = st.checkbox(
                    "Activar OCR (para PDFs escaneados sin capa de texto)",
                    value=False,
                    help="Aumenta el tiempo de procesamiento significativamente.",
                )
            else:
                use_ocr = False

            files = st.file_uploader(
                "Cargar leyes, decretos o contratos base",
                type=["pdf"],
                accept_multiple_files=True,
                key="ingest_uploader",
            )

            if st.button("🚀 Incorporar a Biblioteca"):
                if not files:
                    st.warning("Selecciona al menos un PDF para continuar.")
                else:
                    save_dir = PROJECT_ROOT / "temp_uploads"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    paths = []
                    for f in files:
                        p = save_dir / f.name
                        p.write_bytes(f.read())
                        paths.append(str(p))

                    loader_label = "Docling" if st.session_state.selected_loader == LoaderType.DOCLING else "PyMuPDF"

                    # ── UI de progreso con barra y mensajes dinámicos ──
                    progress_bar = st.progress(0, text="📄 Preparando documentos...")
                    status_text = st.empty()

                    def _progress_callback(stage: str, progress_pct: float, detail: str = ""):
                        """Actualiza la barra de progreso y el mensaje de estado."""
                        progress_bar.progress(progress_pct / 100, text=stage)
                        if detail:
                            status_text.info(detail)

                    try:
                        from src.ingestion.ingest_pipeline import (
                            run_ingestion_pipeline,
                            _validate_pdf_paths,
                            _batch_add_documents,
                        )
                        from src.config import get_embeddings, settings
                        from src.ingestion.factory import load_pdfs
                        from langchain_chroma import Chroma

                        _progress_callback("📄 Cargando PDFs...", 10,
                            f"Leyendo {len(paths)} archivo(s) con {loader_label}...")

                        loader_kwargs = {}
                        if st.session_state.selected_loader == LoaderType.DOCLING:
                            loader_kwargs["use_ocr"] = use_ocr

                        documents = load_pdfs(
                            paths,
                            loader_type=st.session_state.selected_loader,
                            **loader_kwargs,
                        )

                        if not documents:
                            progress_bar.empty()
                            status_text.empty()
                            st.error("No se pudieron extraer fragmentos de los PDFs.")
                            for p in paths:
                                try:
                                    os.remove(p)
                                except Exception:
                                    pass
                        else:
                            _progress_callback("🧠 Generando embeddings...", 30,
                                f"{len(documents)} fragmentos extraídos. Enviando a Bedrock...")

                            embeddings = get_embeddings()
                            vector_store = Chroma(
                                persist_directory=str(settings.STORAGE_PATH),
                                embedding_function=embeddings,
                                collection_name=settings.COLLECTION_NAME,
                            )

                            # Ejecutar batch con actualización visual
                            total = len(documents)
                            batch_size = settings.BATCH_SIZE
                            added = 0
                            num_batches = (total + batch_size - 1) // batch_size

                            for i in range(0, total, batch_size):
                                batch = documents[i : i + batch_size]
                                batch_num = i // batch_size + 1
                                pct = 30 + int((batch_num / num_batches) * 60)

                                _progress_callback(
                                    f"🧠 Indexando lote {batch_num}/{num_batches}...",
                                    pct,
                                    f"Fragmento {i+1}–{min(i + batch_size, total)} de {total}"
                                )

                                vector_store.add_documents(batch)
                                added += len(batch)

                                # Pequeña pausa entre batches
                                if i + batch_size < total:
                                    import time
                                    time.sleep(0.5)

                            # Resetear singleton del vector store
                            from src.retrieval import reset_vector_store
                            reset_vector_store()

                            _progress_callback("✅ Finalizando...", 100,
                                f"{added} fragmentos indexados correctamente.")

                            # Limpiar temporales
                            for p in paths:
                                try:
                                    os.remove(p)
                                except Exception:
                                    pass

                            # Pequeña pausa para que el usuario vea el 100%
                            import time
                            time.sleep(0.8)

                            progress_bar.empty()
                            status_text.empty()

                            if added > 0:
                                st.success(
                                    f"✅ {added} fragmentos indexados "
                                    f"desde {len(paths)} archivo(s) con {loader_label}."
                                )
                                st.rerun()
                            else:
                                st.error("No se indexaron documentos. Revisa los logs.")

                    except Exception as e:
                        progress_bar.empty()
                        status_text.empty()
                        st.error(f"Error en pipeline de ingesta: {e}")

        # ── MODO MESA: carga temporal ──────────────────────────────────────
        else:
            st.markdown("### 📑 Preparación de Caso (Mesa de Trabajo)")
            st.write("Los archivos se usan solo en esta sesión. No se guardan en la base de datos.")

            files = st.file_uploader(
                "Cargar archivos del caso (sentencias, demandas, contratos)",
                type=["pdf"],
                accept_multiple_files=True,
                key="session_uploader",
            )

            if st.button("🔍 Preparar para Análisis"):
                if not files:
                    st.warning("Selecciona al menos un PDF para continuar.")
                else:
                    # Limpiar archivos de sesión anteriores
                    for old_path in st.session_state.session_pdf_paths:
                        try:
                            os.remove(old_path)
                        except Exception:
                            pass

                    save_dir = PROJECT_ROOT / "session_pdfs"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    paths = []
                    for f in files:
                        p = save_dir / f"{uuid.uuid4().hex[:6]}_{f.name}"
                        p.write_bytes(f.read())
                        paths.append(str(p))

                    st.session_state.session_pdf_paths = paths
                    st.success(
                        f"✅ {len(paths)} documento(s) listo(s) en la mesa de trabajo. "
                        f"Usa la pestaña 'Centro de Consultas' para hacer preguntas."
                    )

            # Mostrar archivos activos en la mesa
            if st.session_state.session_pdf_paths:
                st.markdown("**Archivos activos en la mesa:**")
                for p in st.session_state.session_pdf_paths:
                    st.caption(f"📄 {Path(p).name}")

                if st.button("🗑️ Limpiar Mesa"):
                    for p in st.session_state.session_pdf_paths:
                        try:
                            os.remove(p)
                        except Exception:
                            pass
                    st.session_state.session_pdf_paths = []
                    st.rerun()

    with col_adm2:
        st.markdown("""
        <div class="status-card">
            <h4>💡 Guía de modos</h4>
            <p><b>Biblioteca:</b> Conocimiento permanente que el agente recuerda entre sesiones.
            Ideal para normativa base (Decreto 1072, CST, Código General del Proceso).</p>
            <hr style="border-color:#e2e8f0;margin:12px 0;">
            <p><b>Mesa de Trabajo:</b> Para documentos confidenciales o análisis de un solo uso.
            Los archivos se eliminan al limpiar la mesa.</p>
            <hr style="border-color:#e2e8f0;margin:12px 0;">
            <p><b>Análisis Crítico:</b> Actívalo desde el sidebar para obtener un análisis jurídico
            estructurado en JSON (riesgos, obligaciones, plazos).</p>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB: CENTRO DE CONSULTAS (CHAT)
# ═══════════════════════════════════════════════════════════════════════════
with tab_chat:

    # Mostrar historial
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            content = msg["content"]
            meta = msg.get("metadata", {})

            # Renderizado especial para respuestas JSON
            if meta.get("mode") == "specialized":
                try:
                    st.json(json.loads(content))
                except Exception:
                    st.markdown(content)
            else:
                st.markdown(content)

            # Fuentes citadas
            if meta.get("source_docs"):
                with st.expander("🔍 Ver fuentes y citas"):
                    for i, doc in enumerate(meta["source_docs"]):
                        if isinstance(doc, dict):
                            source_name = doc.get("source", "Documento del caso")
                            content_text = doc.get("content", str(doc))
                        else:
                            source_name = str(doc)
                            content_text = ""
                        st.caption(f"**Referencia {i+1}:** {source_name}")
                        if content_text:
                            st.info(content_text[:500] + ("..." if len(content_text) > 500 else ""))

    # ── Input del usuario ──────────────────────────────────────────────────
    query = st.chat_input("Escriba su requerimiento legal aquí...")

    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Consultando inteligencia jurídica..."):
                try:
                    app_mode = st.session_state.app_mode
                    paths = st.session_state.session_pdf_paths
                    use_specialized = st.session_state.specialized_mode

                    # ── Mesa de Trabajo ────────────────────────────────────
                    if app_mode == "Mesa":
                        if not paths:
                            respuesta = (
                                "⚠️ La mesa de trabajo está vacía. "
                                "Sube documentos en la pestaña '⚙️ Gestión de Datos'."
                            )
                            metadata = {"mode": "error"}

                        elif use_specialized:
                            result = query_specialized_analysis(paths, query)
                            respuesta = result["answer"]
                            metadata = {
                                "source_docs": [{"source": s} for s in result.get("source_docs", [])],
                                "mode": "specialized",
                            }

                        else:
                            result = query_pdf_direct(paths, query)
                            respuesta = result["answer"]
                            metadata = {
                                "source_docs": [{"source": s} for s in result.get("source_docs", [])],
                                "mode": "direct",
                            }

                    # ── Biblioteca (RAG vectorial) ─────────────────────────
                    else:
                        if get_document_count() == 0:
                            respuesta = (
                                "⚠️ La Biblioteca está vacía. "
                                "Incorpora documentos en '⚙️ Gestión de Datos'."
                            )
                            metadata = {"mode": "error"}
                        else:
                            graph = _get_cached_graph()
                            final_state = graph.invoke(RagState(question=query))
                            respuesta = final_state["generation"]
                            metadata = {
                                "source_docs": [
                                    {"source": s}
                                    for s in final_state.get("source_docs", [])
                                ],
                                "mode": "vector",
                                "attempts": final_state.get("attempts", 1),
                                "grade": final_state.get("grade", ""),
                            }

                    # ── Render de la respuesta ─────────────────────────────
                    if metadata.get("mode") == "specialized":
                        try:
                            st.json(json.loads(respuesta))
                        except Exception:
                            st.markdown(respuesta)
                    else:
                        st.markdown(respuesta)

                    # Metadata de debug en modo Biblioteca
                    if metadata.get("mode") == "vector":
                        col_m1, col_m2 = st.columns(2)
                        col_m1.caption(f"Intentos: {metadata.get('attempts', 1)}")
                        col_m2.caption(f"Calidad: {metadata.get('grade', '—')}")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": respuesta,
                        "metadata": metadata,
                    })

                except Exception as e:
                    st.error(f"❌ Error técnico: {e}")
                    logger.exception("Error en consulta")
