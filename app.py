import os
import streamlit as st

from data_extractor import extract_document_data
from chunker import chunk_text
import ai_analyzer
from chart_agent import create_visual_assets
import ppt_builder
from slide_planner import build_slide_plan


st.set_page_config(
    page_title="Executive Insight Generator",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Executive Insight Generator")
st.caption(
    "Upload any document and generate a visual-first PowerPoint summary."
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

    if st.button("Generate Presentation"):
        with st.spinner("Extracting document structure..."):
            doc_data = extract_document_data(file_path)

        with st.expander("Extractor output", expanded=False):
            st.write({
                "text_length": len(doc_data.get("text", "")),
                "tables": len(doc_data.get("tables", [])),
                "numbers": len(doc_data.get("numbers", [])),
                "metric_cards": len(doc_data.get("metric_cards", [])),
                "chart_candidates": len(doc_data.get("chart_candidates", [])),
                "sections": len(doc_data.get("sections", [])),
            })

        with st.spinner("Chunking document..."):
            chunks = chunk_text(doc_data["text"])

        with st.spinner("Running AI analysis..."):
            analysis = ai_analyzer.analyze_chunks(
                chunks,
                tables=doc_data.get("tables", []),
                chart_candidates=doc_data.get("chart_candidates", []),
                numbers=doc_data.get("numbers", []),
                metric_cards=doc_data.get("metric_cards", []),
                sections=doc_data.get("sections", [])
            )

        with st.spinner("Creating visual assets..."):
            analysis = create_visual_assets(analysis)

        with st.spinner("Planning slides..."):
            slide_plan = build_slide_plan(analysis)

        with st.spinner("Building PowerPoint..."):
            ppt_path = ppt_builder.create_ppt(analysis)

        st.success("Presentation generated!")

        st.subheader("Document Type")
        st.info(analysis.get("document_type", "Unknown"))

        st.subheader("Summary")
        st.write(analysis.get("executive_summary", "No summary generated."))

        st.subheader("Core Message")
        st.write(analysis.get("core_message", "No core message generated."))

        st.subheader("Slide Plan")
        for i, slide in enumerate(slide_plan, 1):
            st.markdown(
                f"**{i}. {slide.get('title', 'Insight')}**  \n"
                f"`{slide.get('type', '')}`"
            )

        st.subheader("Metric Cards")
        metrics = analysis.get("metrics", [])

        if metrics:
            cols = st.columns(3)

            for i, metric in enumerate(metrics[:6]):
                with cols[i % 3]:
                    if isinstance(metric, dict):
                        st.metric(
                            label=metric.get("name", "Metric"),
                            value=metric.get("value", "")
                        )
                        if metric.get("interpretation"):
                            st.caption(metric.get("interpretation"))
                    else:
                        st.write(metric)
        else:
            st.caption("No structured metrics generated.")

        st.subheader("Insights")
        for item in analysis.get("insights", [])[:6]:
            st.markdown(f"- {item}")

        st.subheader("Recommended Actions")
        recommendations = analysis.get("recommendations", [])

        if recommendations:
            for rec in recommendations:
                if isinstance(rec, dict):
                    st.markdown(
                        f"""
**{rec.get("priority", "Medium")} Priority**  
{rec.get("recommendation", "")}

_Impact:_ {rec.get("business_impact", "")}
"""
                    )
                else:
                    st.markdown(f"- {rec}")
        else:
            st.caption("No recommendations generated.")

        chart_paths = analysis.get("chart_paths", [])

        if chart_paths:
            st.subheader("Generated Charts")

            cols = st.columns(2)

            for i, chart in enumerate(chart_paths):
                with cols[i % 2]:
                    st.image(
                        chart["path"],
                        caption=chart["title"],
                        use_container_width=True
                    )
                    st.caption(chart.get("insight", ""))
        else:
            st.subheader("Generated Charts")
            st.caption("No chart-ready numeric data was selected for this document.")

        with open(ppt_path, "rb") as file:
            st.download_button(
                label="📥 Download PowerPoint",
                data=file,
                file_name="executive_insight_presentation.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )