import streamlit as st
import os

from rag import index_pdf, retrieve
from kg import query_kg
from llm import generate_answer
from router import is_definition_query

PDF_DIR = "data/pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

st.title("🦅 NexRag – Hybrid RAG Assistant")

uploaded = st.file_uploader("Upload PDF", type="pdf")

if uploaded:
    path = os.path.join(PDF_DIR, uploaded.name)
    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())

    index_pdf(path)
    st.success("PDF indexed successfully!")

    question = st.chat_input("Ask a question")
    if question:
        st.chat_message("user").write(question)

        answer_given = False  # control flag

        # --------- ROUTE 1: Knowledge Graph ----------
        if is_definition_query(question):
            kg_answer = query_kg(question)

            if kg_answer:
                st.chat_message("assistant").write("📘 **From Knowledge Graph:**\n\n" + kg_answer)
                answer_given = True

        # --------- ROUTE 2: PDF RAG (fallback or normal queries) ----------
        if not answer_given:
            docs = retrieve(question)

            if not docs:
                st.chat_message("assistant").write("I don't know.")
            else:
                context = "\n\n".join(docs[:4])
                try:
                    answer = generate_answer(question, context)
                    st.chat_message("assistant").write("📄 **From PDF:**\n\n" + answer)
                except Exception as e:
                    st.chat_message("assistant").write(
                        "⚠️ The answer could not be generated due to a model error. Please try again."
                    )

