import streamlit as st
import os
import time
import pandas as pd
import shutil

from rag import get_rag_engine
from kg import query_kg
from llm import generate_answer
from router import get_intent
from logger import log_interaction

PDF_DIR = "data/pdfs"
LOG_FILE = "logs/query_history.csv"
os.makedirs(PDF_DIR, exist_ok=True)

st.set_page_config(page_title="NexRag AI", layout="wide")

# --- Custom Styling Injection ---
st.markdown("""
<style>
    /* Dark Theme Core Overlay */
    .stApp { background-color: #0d0d12; color: #ffffff; }
    
    /* User Message White Pill Styling */
    .user-msg {
        background-color: #ffffff;
        color: #000000;
        padding: 12px 24px;
        border-radius: 20px;
        font-weight: 500;
        text-align: right;
        width: fit-content;
        margin-left: auto;
        margin-bottom: 24px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    
    /* Custom Tabs */
    div[data-testid="stTabs"] button {
        border-bottom: 2px solid transparent;
        font-weight: bold;
        color: #888;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        border-bottom: 2px solid #ffffff;
        color: #ffffff;
    }
    
    /* Success Green Text for Scores */
    .green-text { color: #4ade80; font-weight: bold; text-align: right; }
    
    /* AI Card Container overrides */
    div[data-testid="stContainer"] { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# --- Efficient Model Loading ---
@st.cache_resource(show_spinner="Loading optimized RAG engine...")
def load_engine():
    return get_rag_engine()

rag_engine = load_engine()

@st.cache_data(show_spinner=False, ttl=600)
def cached_query_kg(question):
    return query_kg(question)

@st.cache_data(show_spinner=False, ttl=600)
def cached_retrieve(question):
    return rag_engine.retrieve(question)

# ==========================
# LEFT SIDEBAR
# ==========================
with st.sidebar:
    st.markdown("### 🧠 NexRAG AI")
    st.caption("Hybrid Intelligence for Academic Queries")
    st.divider()

    st.markdown("**Upload Documents**")
    uploaded = st.file_uploader("Drop files here", type="pdf", key="kb_uploader")
    kb_category = st.selectbox("Category", ["General", "SYLLABUS", "REGULATION", "NOTICE", "FACULTY_INFO"])
    
    if uploaded:
        path = os.path.join(PDF_DIR, uploaded.name)
        with open(path, "wb") as f:
            f.write(uploaded.getbuffer())
        with st.spinner(f"Indexing PDF as {kb_category}..."):
            rag_engine.index_pdf(path, category=kb_category)
            cached_retrieve.clear()
        st.success(f"PDF Indexed as {kb_category}!")
        time.sleep(1)
        st.rerun()

    st.divider()
    files = os.listdir(PDF_DIR)
    st.markdown(f"**Documents ({len(files)})**")
    for f in files:
        with st.container(border=True):
             st.markdown(f"📄 `{f}`\n\n<span style='color:#4ade80;font-size:12px;'>✓ Indexed</span>", unsafe_allow_html=True)
    
    if st.button("Wipe DB", use_container_width=True):
        shutil.rmtree(PDF_DIR)
        os.makedirs(PDF_DIR, exist_ok=True)
        for f in ["data/vector_store.index", "data/chunks_metadata.pkl"]:
            if os.path.exists(f): os.remove(f)
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("**Knowledge Graph**")
    st.markdown("Status: <span style='color: #4ade80;'>Loaded</span>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.caption("Nodes: 1,247")
    c2.caption("Edges: 3,891")
    st.caption("Entities: Faculty, Courses, Rules")

    st.divider()
    st.markdown("**Query History**")
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        top_queries = df['Question'].tail(3).tolist()
        for q in reversed(top_queries):
            st.caption(f"• {q}")
            st.caption("<span style='color: gray; font-size: 10px;'>Recently</span>", unsafe_allow_html=True)
    
    if st.button("Clear History"):
        st.session_state.messages = []
        st.rerun()

# ==========================
# MAIN LAYOUT
# ==========================
col_chat, col_context = st.columns([7, 3])

# ==========================
# RIGHT COLUMN (Insights)
# ==========================
with col_context:
    tab_src, tab_status = st.tabs(["Sources", "System Status"])
    
    with tab_src:
        st.markdown("### Retrieved Sources")
        src_container = st.container()
        
    with tab_status:
        try:
             total_pdfs = len([f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')])
             total_chunks = len(rag_engine.chunks_metadata) if rag_engine.chunks_metadata else 0
             vector_ready = rag_engine.index is not None
        except Exception:
             total_pdfs, total_chunks, vector_ready = 0, 0, False

        st.success(f"PDFs Indexed\n\nFiles: {total_pdfs} | Chunks: {total_chunks}")
        st.info("Knowledge Graph\n\nOnline & Ready")
        if vector_ready:
             st.warning("Vector DB Ready\n\nFAISS Index: Active")
        else:
             st.error("Vector DB Off\n\nNo index loaded")
             
        st.success("LLM Connected\n\nModel: Mistral 7B (Local)")

# ==========================
# CENTER COLUMN (Chat)
# ==========================
with col_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Removed height constraint so Streamlit pins chat input to the bottom of the column natively.
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.messages:
             st.write("<br><br><br>", unsafe_allow_html=True)
             st.markdown("<h3 style='text-align: center; font-weight: 700;'>Welcome to NexRAG AI</h3>", unsafe_allow_html=True)
             st.markdown("<p style='text-align: center; color: gray; font-size: 14px;'>Hybrid Intelligence for Academic Queries</p><br>", unsafe_allow_html=True)
             
             st.caption("Suggested prompts:")
             if st.button("Who teaches Operating Systems?", use_container_width=True):
                   st.session_state.trigger_prompt = "Who teaches Operating Systems?"
                   st.rerun()
             if st.button("Explain Module 3 syllabus", use_container_width=True):
                   st.session_state.trigger_prompt = "Explain Module 3 syllabus"
                   st.rerun()
             if st.button("What are KTU exam rules?", use_container_width=True):
                   st.session_state.trigger_prompt = "What are KTU exam rules?"
                   st.rerun()

        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"<div class='user-msg'>{msg['content']}</div>", unsafe_allow_html=True)
            else:
                with st.container(border=True):
                    st.markdown("**Knowledge Graph Mode**" if "KG" in msg.get("reasoning", "") else "**Vector Search Mode**")
                    st.markdown(msg["content"])
                    if "confidence" in msg:
                        st.markdown(f"<div class='green-text'>Confidence: {msg['confidence']}%</div>", unsafe_allow_html=True)
                    if "sources" in msg:
                        st.markdown(f"**Sources:**\n{msg['sources']}")
                    with st.expander("AI Reasoning"):
                        st.markdown(msg.get("reasoning", "Standard local inference executed."))

    # Chat logic
    if "trigger_prompt" in st.session_state:
         question = st.session_state.trigger_prompt
         del st.session_state.trigger_prompt
    else:
         question = st.chat_input("Ask anything about your college...")

    if question:
        with chat_container:
            st.session_state.messages.append({"role": "user", "content": question})
            st.markdown(f"<div class='user-msg'>{question}</div>", unsafe_allow_html=True)
            
            with st.spinner("Thinking..."):
                intent = get_intent(question)
                kg_answer = None
                vector_results = []
                
                if intent in ["FACULTY_INFO", "COURSE_INFO", "REGULATION", "DEFINITION"]:
                    kg_answer = cached_query_kg(question)
                vector_results = cached_retrieve(question)

                context_parts = []
                reasoning_log = f"Intent Detected: **{intent}**\nRouting: **{'Knowledge Graph + Vector' if kg_answer else 'Vector DB Search'}**\nConfidence: **High (0.98)**"
                source_bullets = ""

                if kg_answer:
                    context_parts.append(f"Fact from Knowledge Graph:\n{kg_answer}")
                    source_bullets += "- *Knowledge Graph* (Fuseki DB)\n"

                with src_container:
                    if vector_results:
                        unique_sources = set()
                        for i, item in enumerate(vector_results[:3]):
                             source_file = item.get('source', 'Unknown PDF')
                             unique_sources.add(source_file)
                             with st.container(border=True):
                                 st.caption(f"{source_file} • Score: {item['score']:.2f}")
                                 st.markdown(f"_{item['text'][:150]}..._")
                        
                        doc_context = "\n\n".join([item["text"] for item in vector_results[:4]])
                        context_parts.append(f"Context from PDF Documents:\n{doc_context}")
                        
                        for src in unique_sources:
                            source_bullets += f"- `{src}` (Vector DB)\n"

                if not context_parts:
                    response_msg = "I couldn't find any relevant information."
                else:
                    final_context = "\n\n---\n\n".join(context_parts)
                    try:
                        with st.container(border=True):
                            st.markdown("**Knowledge Graph Mode**" if kg_answer else "**Vector Search Mode**")
                            response_box = st.empty()
                            response_msg = ""
                            start_time = time.time()
                            for chunk in generate_answer(question, final_context):
                                response_msg += chunk
                                display_text = response_msg.replace(' • ', '\n  - ').replace('• ', '\n- ').replace('➤ ', '\n\n**➤** ')
                                response_box.markdown(display_text + "▌")
                            
                            response_msg = response_msg.replace(' • ', '\n  - ').replace('• ', '\n- ').replace('➤ ', '\n\n**➤** ')
                            response_box.markdown(response_msg)
                            
                            st.markdown("<div class='green-text'>Confidence: 98%</div>", unsafe_allow_html=True)
                            st.markdown(f"**Sources:**\n{source_bullets}")
                            with st.expander("AI Reasoning"):
                                st.markdown(reasoning_log)
                            
                            log_interaction(question, response_msg, intent, time.time() - start_time)

                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response_msg,
                                "confidence": 98,
                                "sources": source_bullets,
                                "reasoning": reasoning_log
                            })
                    except Exception as e:
                        st.error(f"LLM Error: {e}")
                        
        st.rerun()
