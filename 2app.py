import os
import streamlit as st

from data_extractor import extract_document_data
from chunker import chunk_text
import ai_analyzer
from agents import enrich_analysis
from chart_agent import create_visual_assets
import ppt_builder


st.set_page_config(
    page_title="Executive Document Intelligence",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Executive Document Intelligence")
st.caption(
    "Upload documents and automatically generate boardroom-ready PowerPoint presentations."
)

uploaded_file = st.file_uploader(
    "Upload a document",
    type=["pdf", "docx", "txt", "csv", "xlsx", "pptx"]
)


if uploaded_file:

    os.makedirs("temp", exist_ok=True)

    file_path = os.path.join("temp", uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    st.success(f"Uploaded: {uploaded_file.name}")

    if st.button("Generate Executive Analysis"):

        with st.spinner("Extracting document..."):

            doc_data = extract_document_data(file_path)

        with st.spinner("Chunking document..."):

            chunks = chunk_text(doc_data["text"])

        with st.spinner("Running AI analysis..."):

            analysis = ai_analyzer.analyze_chunks(
                chunks,
                tables=doc_data["tables"],
                chart_candidates=doc_data["chart_candidates"],
                numbers=doc_data["numbers"],
                metric_cards=doc_data["metric_cards"],
                sections=doc_data["sections"]
                
            )

        with st.spinner("Enriching insights..."):

            analysis = enrich_analysis(analysis)

        with st.spinner("Creating visual assets..."):

            analysis = create_visual_assets(analysis)

        with st.spinner("Building PowerPoint..."):

            ppt_path = ppt_builder.create_ppt(analysis)

        st.success("Presentation generated!")

        st.subheader("Document Type")

        st.info(analysis.get("document_type", "Unknown"))

        st.subheader("Executive Summary")

        st.write(
            analysis.get(
                "executive_summary",
                "No summary generated."
            )
        )

        st.subheader("Key Findings")

        for item in analysis.get("key_findings", []):
            st.markdown(f"- {item}")

        st.subheader("Risks")

        risks = analysis.get("risks", [])

        if risks:
            for r in risks:

                if isinstance(r, dict):
                    st.markdown(
                        f"- **{r.get('risk','')}**: {r.get('description','')}"
                    )
                else:
                    st.markdown(f"- {r}")

        st.subheader("Recommendations")

        recommendations = analysis.get("recommendations", [])

        if recommendations:

            for rec in recommendations:

                if isinstance(rec, dict):

                    st.markdown(
                        f"""
### {rec.get("priority","Medium")} Priority

**Recommendation**

{rec.get("recommendation","")}

**Business Impact**

{rec.get("business_impact","")}
"""
                    )

        st.subheader("Generated Charts")

        chart_paths = analysis.get("chart_paths", [])

        cols = st.columns(2)

        for i, chart in enumerate(chart_paths):

            with cols[i % 2]:

                st.image(
                    chart["path"],
                    caption=chart["title"],
                    use_container_width=True
                )

                st.caption(
                    chart.get("insight", "")
                )

        with open(ppt_path, "rb") as file:

            st.download_button(
                label="📥 Download PowerPoint",
                data=file,
                file_name="executive_document_intelligence.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )