import warnings
import logging

# Suprimir warnings específicos de transformers sobre __path__
warnings.filterwarnings(
    "ignore", 
    message=".*Accessing `__path__` from.*", 
    category=DeprecationWarning,
    module="transformers"
)

# También reducir logging de transformers
logging.getLogger("transformers").setLevel(logging.ERROR)

import streamlit as st
import os
import sys
import tempfile
import uuid
from pathlib import Path

# CRÍTICO: Agregar la RAÍZ del proyecto al PATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Imports ABSOLUTOS desde src
from src.retrieval.hierarchical_retriever import get_hierarchical_retriever
from src.core import get_graph, RagState
from src.services.pdf_direct_service import query_pdf_direct
from src.services.specialized_analysis import query_specialized_analysis
from src.retrieval import get_document_count
from src.ingestion import get_loader, LoaderType

st.set_page_config(
    page_title="Analista Juridico",
    page_icon="⚖️",
    layout="wide",
)

# --- CSS PERSONALIZADO PARA SIDEBAR ---
st.markdown("""
    <style>
        /* Reducir espacio superior del sidebar */
        [data-testid="stSidebarContent"] {
            padding-top: 1rem !important;
        }
        /* Compactar elementos dentro del sidebar */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.5rem !important;
        }
        /* Reducir márgenes de los widgets de Streamlit en el sidebar */
        [data-testid="stSidebar"] .stButton, [data-testid="stSidebar"] .stDownloadButton {
            margin-bottom: -10px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("⚖️ Analista Juridico")
st.markdown("""
**Asistente Jurídico Autónomo.** Desarrollado con LangGraph, implementa patrones avanzados:
*CRAG* (filtrado de documentos irrelevantes) y *Self-RAG* (verificación anti-alucinaciones).
Potenciado por **AWS Bedrock** (Amazon Nova Lite + Titan Embeddings v2).
""")

with st.sidebar:
    st.header("🏢 Base de Conocimiento")

    doc_count = get_document_count()
    if doc_count > 0:
        st.success(f"📚 {doc_count} documentos indexados")
    else:
        st.warning("⚠️ Base de datos vacía")

    st.divider()

    st.subheader("📤 Cargar PDF(s)")
    mode = st.radio(
        "Modo de consulta:",
        ["Usar base de datos vectorial", "Cargar PDF(s) temporal"],
        horizontal=True,
    )

    if mode == "Usar base de datos vectorial" and doc_count == 0:
        st.info(
            "💡 La base de datos está vacía. Use 'Cargar PDF(s) temporal' para consultar sin indexar."
        )

    pdf_files = st.file_uploader(
        "Seleccionar archivo(s) PDF",
        type=["pdf"],
        accept_multiple_files=(mode == "Cargar PDF(s) temporal"),
    )

    st.divider()
    st.subheader("🛠️ Opciones Avanzadas")
    specialized_mode = st.toggle(
        "Activar Modo Análisis Crítico (JSON)",
        help="Utiliza un prompt especializado para generar un análisis profundo en formato JSON estructurado."
    )

    index_after = False

    if mode == "Cargar PDF(s) temporal" and pdf_files:
        index_after = st.checkbox("Indexar después de consultar", value=False)

    if pdf_files and st.button("Procesar"):
        session_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "session_pdfs"
        )
        os.makedirs(session_dir, exist_ok=True)

        # Normalizar: convertir a lista siempre
        if isinstance(pdf_files, list):
            uploaded_list = pdf_files
        else:
            uploaded_list = [pdf_files] if pdf_files else []

        temp_paths = []
        for uploaded_file in uploaded_list:
            if uploaded_file is None:
                continue

            unique_name = f"{uuid.uuid4().hex[:8]}_{uploaded_file.name}"
            temp_path = os.path.join(session_dir, unique_name)

            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())

            temp_paths.append(temp_path)
            uploaded_file.seek(0)

        with st.spinner("Procesando PDF(s)..."):
            try:
                if mode == "Cargar PDF(s) temporal":
                    st.session_state.temp_pdf_paths = temp_paths
                    st.session_state.pdf_mode = "direct"
                    st.session_state.index_after = index_after

                    st.success(
                        f"✅ {len(temp_paths)} PDF(s) cargado(s) para consulta temporal"
                    )

                    if index_after:
                        st.info(
                            "Los PDFs se indexarán permanentemente **después** de la primera consulta."
                        )
                    else:
                        st.info("Los PDFs se mantendrán solo durante esta sesión.")

                else:
                    # Modo indexación normal
                    from src.ingestion import load_pdfs, LoaderType
                    from langchain_chroma import Chroma
                    from src.config import settings, get_embeddings

                    docs = load_pdfs(temp_paths, LoaderType.PYMUPDF)
                    if docs:
                        embeddings = get_embeddings()
                        vector_store = Chroma(
                            persist_directory=settings.STORAGE_PATH,
                            embedding_function=embeddings,
                            collection_name=settings.COLLECTION_NAME,
                        )
                        vector_store.add_documents(docs)
                        st.success(f"✅ Indexado: {len(docs)} chunks")

            except Exception as e:
                st.error(f"❌ Error: {e}")
            finally:
                # Solo borrar en modo indexación normal
                if mode != "Cargar PDF(s) temporal":
                    for temp_path in temp_paths:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Escriba su consulta legal...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            try:
                pdf_mode = st.session_state.get("pdf_mode") == "direct"
                temp_paths = st.session_state.get("temp_pdf_paths", [])
                index_after = st.session_state.get("index_after", False)

                if not pdf_mode and not temp_paths and doc_count == 0:
                    st.info(
                        "⚠️ La base de datos está vacía. Use el modo 'Cargar PDF(s) temporal' para consultar."
                    )
                    respuesta = "La base de datos vectorial está vacía. Por favor seleccione el modo 'Cargar PDF(s) temporal' en la barra lateral o ingeste documentos primero."
                    metadata = {"mode": "fallback", "source_docs": []}
                elif specialized_mode and temp_paths:
                    # NUEVO: Modo de Análisis Especializado JSON
                    result = query_specialized_analysis(temp_paths, prompt)
                    respuesta = result["answer"]
                    metadata = {
                        "source_docs": result["source_docs"],
                        "mode": "specialized",
                    }
                elif pdf_mode and temp_paths:
                    result = query_pdf_direct(temp_paths, prompt)
                    respuesta = result["answer"]
                    metadata = {
                        "source_docs": result["source_docs"],
                        "mode": "pdf_direct",
                    }

                    if index_after and result["source_docs"]:
                        st.info("🔄 Indexando documentos...")
                        from src.ingestion import load_pdfs, LoaderType
                        from langchain_chroma import Chroma
                        from src.config import settings, get_embeddings

                        docs = load_pdfs(temp_paths, LoaderType.PYMUPDF)
                        if docs:
                            embeddings = get_embeddings()
                            vector_store = Chroma(
                                persist_directory=settings.STORAGE_PATH,
                                embedding_function=embeddings,
                                collection_name=settings.COLLECTION_NAME,
                            )
                            vector_store.add_documents(docs)
                            st.success(f"✅ Indexado: {len(docs)} chunks")

                        st.session_state.pdf_mode = None
                        st.session_state.temp_pdf_paths = []
                        st.session_state.index_after = False
                else:
                    graph = get_graph()
                    estado_inicial = RagState(question=prompt)
                    final_state = graph.invoke(estado_inicial)

                    respuesta = final_state["generation"]
                    metadata = {
                        "source_docs": final_state.get("source_docs", []),
                        "mode": "vector",
                    }

            except Exception as e:
                respuesta = f"Error: {e}"
                metadata = {}

        st.session_state.messages.append(
        {
            "role": "assistant",
            "content": respuesta,
            "metadata": metadata,
        }
    )

    # RE-RENDERIZAR LA RESPUESTA CON FORMATO ESPECIAL SI ES NECESARIO
    if metadata.get("mode") == "specialized":
        with st.chat_message("assistant"):
            try:
                import json
                json_data = json.loads(respuesta)
                st.success("📊 Análisis Crítico Estructurado Generado")
                st.json(json_data, expanded=True)
            except:
                st.code(respuesta, language="json")
    else:
        with st.chat_message("assistant"):
            st.markdown(respuesta)
