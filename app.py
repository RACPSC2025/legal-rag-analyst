import warnings
import logging

# Silenciar ruidos innecesarios de librerías
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("transformers").setLevel(logging.ERROR)

import streamlit as st
import os
import sys
import uuid
import json
from pathlib import Path

# Configuración de Rutas
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Imports del Core
from src.core import get_graph, RagState
from src.services.pdf_direct_service import query_pdf_direct
from src.services.specialized_analysis import query_specialized_analysis
from src.retrieval import get_document_count
from src.ingestion import load_pdfs, LoaderType

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Amatia Express Legal Agent AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS DE ALTA GAMA (ESTILO LEGAL TECH) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        .main {
            background-color: #fcfcfc;
        }
        
        /* Sidebar Estilizado */
        [data-testid="stSidebar"] {
            background-color: #0f172a;
            color: white;
            border-right: 1px solid #1e293b;
        }
        
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
            color: #f8fafc !important;
        }

        /* Botones Profesionales */
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
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }

        /* Contenedores de Estado */
        .status-card {
            padding: 20px;
            border-radius: 12px;
            background-color: white;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .mode-indicator {
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 10px;
        }
        
        .mode-biblio { background-color: #dcfce7; color: #166534; }
        .mode-mesa { background-color: #dbeafe; color: #1e40af; }

        /* Tabs Personalizados */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
            padding: 0 10px;
        }
        
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

# --- INICIALIZACIÓN DE ESTADO ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_pdf_paths" not in st.session_state:
    st.session_state.session_pdf_paths = []
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "Biblioteca" # Opciones: "Biblioteca", "Mesa"

# --- SIDEBAR: NAVEGACIÓN Y BRANDING ---
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; padding: 10px 0;'>
            <h1 style='font-size: 2.2em; margin-bottom: 0;'>⚖️</h1>
            <h2 style='font-size: 1.4em; color: white; margin-top: 10px;'>Amatia Express</h2>
            <p style='color: #94a3b8; font-size: 0.9em;'>Legal Agent AI</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Selector de Modo de Operación (Botones Limpios)
    st.subheader("🛠️ Modo de Trabajo")
    mode = st.radio(
        "Seleccione funcionalidad:",
        ["📚 Biblioteca Jurídica", "📑 Mesa de Trabajo (Caso)"],
        index=0 if st.session_state.app_mode == "Biblioteca" else 1,
        help="Biblioteca: RAG Permanente | Mesa: Análisis Temporal de Archivos."
    )
    st.session_state.app_mode = "Biblioteca" if "Biblioteca" in mode else "Mesa"
    
    st.markdown("---")
    
    # Información de la Base de Datos
    doc_count = get_document_count()
    st.metric("Documentos Indexados", doc_count)
    
    if st.button("🔄 Reiniciar Chat"):
        st.session_state.messages = []
        st.rerun()

# --- ÁREA PRINCIPAL ---
header_col1, header_col2 = st.columns([0.8, 0.2])
with header_col1:
    st.title("Amatia Express Legal Agent AI")
    st.markdown("_Tu consultor jurídico experto e inteligente._")

with header_col2:
    if st.session_state.app_mode == "Biblioteca":
        st.markdown('<div class="mode-indicator mode-biblio">MODO BIBLIOTECA</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mode-indicator mode-mesa">MODO MESA DE TRABAJO</div>', unsafe_allow_html=True)

# --- SISTEMA DE PESTAÑAS ---
tab_chat, tab_admin = st.tabs(["💬 Centro de Consultas", "⚙️ Gestión de Datos"])

# --- TAB 2: GESTIÓN DE DATOS (INGESTA VS CARGA TEMPORAL) ---
with tab_admin:
    st.subheader("Panel de Administración de Información")
    
    col_adm1, col_adm2 = st.columns([0.6, 0.4])
    
    with col_adm1:
        if st.session_state.app_mode == "Biblioteca":
            st.markdown("### 📥 Ingesta a Memoria Permanente")
            st.write("Suba documentos para que el agente los aprenda para siempre.")
            files = st.file_uploader("Cargar leyes, decretos o contratos base", type=["pdf"], accept_multiple_files=True, key="ingest")
            
            if st.button("🚀 Incorporar a Biblioteca"):
                if files:
                    with st.spinner("Ejecutando Pipeline de Ingesta (AWS Bedrock + ChromaDB)..."):
                        try:
                            from src.config import settings, get_embeddings
                            from langchain_chroma import Chroma
                            
                            # Guardar temporales para procesar
                            save_dir = os.path.join(PROJECT_ROOT, "temp_uploads")
                            os.makedirs(save_dir, exist_ok=True)
                            paths = []
                            for f in files:
                                p = os.path.join(save_dir, f.name)
                                with open(p, "wb") as fb: fb.write(f.read())
                                paths.append(p)
                            
                            # Cargar e Ingestar
                            docs = load_pdfs(paths, LoaderType.PYMUPDF)
                            if docs:
                                vector_store = Chroma(
                                    persist_directory=settings.STORAGE_PATH,
                                    embedding_function=get_embeddings(),
                                    collection_name=settings.COLLECTION_NAME
                                )
                                vector_store.add_documents(docs)
                                st.success(f"✅ Éxito: {len(docs)} fragmentos jurídicos incorporados permanentemente.")
                                for p in paths: os.remove(p)
                        except Exception as e:
                            st.error(f"Error en ingesta: {e}")
        else:
            st.markdown("### 📑 Preparación de Caso (Mesa de Trabajo)")
            st.write("Suba los documentos del caso actual. No se guardarán en la base de datos.")
            files = st.file_uploader("Cargar archivos del caso (Sentencias, Demandas)", type=["pdf"], accept_multiple_files=True, key="session")
            
            if st.button("🔍 Preparar para Análisis"):
                if files:
                    save_dir = os.path.join(PROJECT_ROOT, "session_pdfs")
                    os.makedirs(save_dir, exist_ok=True)
                    paths = []
                    for f in files:
                        p = os.path.join(save_dir, f"{uuid.uuid4().hex[:5]}_{f.name}")
                        with open(p, "wb") as fb: fb.write(f.read())
                        paths.append(p)
                    st.session_state.session_pdf_paths = paths
                    st.success(f"✅ {len(paths)} documentos listos en la mesa de trabajo.")
    
    with col_adm2:
        st.markdown("""
        <div class="status-card">
            <h4>💡 Tips de Experto</h4>
            <p><b>Biblioteca:</b> Use este modo para conocimiento general que el agente debe recordar en futuras sesiones.</p>
            <p><b>Mesa de Trabajo:</b> Use este modo para confidencialidad o análisis rápidos de un solo uso.</p>
        </div>
        """, unsafe_allow_html=True)
        
        specialized_mode = st.toggle("Activar Análisis Crítico (Formato JSON)", help="Ideal para detectar riesgos en contratos.")

# --- TAB 1: CENTRO DE CONSULTAS (CHAT) ---
with tab_chat:
    # Mostrar Mensajes
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "metadata" in msg and msg["metadata"].get("source_docs"):
                with st.expander("🔍 Ver Citas y Fuentes"):
                    for i, doc in enumerate(msg["metadata"]["source_docs"]):
                        # Verificación defensiva de tipo de dato
                        if isinstance(doc, dict):
                            source_name = doc.get('source', 'Documento del caso')
                            content_text = doc.get('content', str(doc))
                        else:
                            source_name = "Referencia del documento"
                            content_text = str(doc)
                            
                        st.caption(f"**Referencia {i+1}:** {source_name}")
                        st.info(content_text[:500] + "...")

    # Entrada de Usuario
    query = st.chat_input("Escriba su requerimiento legal aquí...")

    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Consultando inteligencia jurídica..."):
                try:
                    mode = st.session_state.app_mode
                    paths = st.session_state.session_pdf_paths
                    
                    if mode == "Mesa":
                        if not paths:
                            respuesta = "⚠️ La mesa de trabajo está vacía. Por favor, suba documentos en la pestaña 'Gestión de Datos'."
                            metadata = {"mode": "error"}
                        elif specialized_mode:
                            result = query_specialized_analysis(paths, query)
                            respuesta = result["answer"]
                            metadata = {"source_docs": result.get("source_docs", []), "mode": "specialized"}
                        else:
                            result = query_pdf_direct(paths, query)
                            respuesta = result["answer"]
                            metadata = {"source_docs": result.get("source_docs", []), "mode": "direct"}
                    else:
                        # Modo Biblioteca (Vectorial)
                        if doc_count == 0:
                            respuesta = "⚠️ La Biblioteca está vacía. Incorpore documentos en 'Gestión de Datos'."
                            metadata = {"mode": "error"}
                        else:
                            graph = get_graph()
                            final_state = graph.invoke(RagState(question=query))
                            respuesta = final_state["generation"]
                            metadata = {"source_docs": final_state.get("source_docs", []), "mode": "vector"}
                            
                    # Renderizado de Respuesta Especializada
                    if metadata.get("mode") == "specialized":
                        try:
                            json_res = json.loads(respuesta)
                            st.json(json_res)
                        except:
                            st.markdown(respuesta)
                    else:
                        st.markdown(respuesta)
                        
                    st.session_state.messages.append({"role": "assistant", "content": respuesta, "metadata": metadata})
                    
                except Exception as e:
                    st.error(f"Error técnico: {e}")

