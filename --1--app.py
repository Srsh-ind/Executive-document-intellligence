import os
import streamlit as st

from helpers import ensure_directories
from document_reader import read_document
from chunker import chunk_text

# These will be added in Phase 2 and Phase 4
from ai_analyzer import analyze_chunks
from agents import enrich_analysis
from ppt_builder import create_ppt


st.set_page_config(
    page_title="Executive Document Intelligence",
    layout="wide"
)

ensure_directories()

st.title("Executive Document Intelligence")
st.caption("Powered by AMD GPU + vLLM + Qwen/Llama")

st.write(
    "Upload a business document such as PDF, DOCX, TXT, CSV, or Excel. "
    "The system extracts executive insights and generates a boardroom-ready PowerPoint."
)

uploaded_file = st.file_uploader(
    "Upload document",
    type=["pdf", "docx", "txt", "csv", "xlsx", "xls"]
)

if uploaded_file:
    file_path = os.path.join("temp", uploaded_file.name)

    with open(file_path, "wb") as file:
        file.write(uploaded_file.getbuffer())

    st.success("Document uploaded successfully.")

    with st.spinner("Reading document..."):
        document_text = read_document(file_path)

    with st.spinner("Chunking document..."):
        chunks = chunk_text(document_text)

    st.info(f"Document processed into {len(chunks)} chunks.")

    with st.spinner("Analyzing with Qwen/Llama via vLLM..."):
        analysis = analyze_chunks(chunks)

    with st.spinner("Running business analysis agents..."):
        final_analysis = enrich_analysis(analysis)

    st.subheader("Executive Summary")
    st.write(final_analysis.get("executive_summary", ""))

    col1, col2, col3 = st.columns(3)
    col1.metric("Document Type", final_analysis.get("document_type", "Unknown"))
    col2.metric("Insights", len(final_analysis.get("insights", [])))
    col3.metric("Recommendations", len(final_analysis.get("recommendations", [])))

    st.subheader("Key Insights")
    for item in final_analysis.get("insights", []):
        st.write("•", item)

    st.subheader("Risks")
    for item in final_analysis.get("risks", []):
        st.write("•", item)

    st.subheader("Opportunities")
    for item in final_analysis.get("opportunities", []):
        st.write("•", item)

    st.subheader("Recommendations")
    for rec in final_analysis.get("recommendations", []):
        if isinstance(rec, dict):
            st.write(f"**{rec.get('priority', 'Medium')}** — {rec.get('recommendation', '')}")
            st.caption(rec.get("business_impact", ""))
        else:
            st.write("•", rec)

    with st.spinner("Creating McKinsey-style PowerPoint..."):
        ppt_path = create_ppt(final_analysis)

    with open(ppt_path, "rb") as file:
        st.download_button(
            "Download Executive PPT",
            file,
            file_name="executive_document_intelligence.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )