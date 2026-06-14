import os

from ingestion.data_extractor import extract_document_data
from ingestion.chunker import chunk_text

from agents import ai_analyzer
from agents.chart_agent import create_visual_assets
from agents.storyboard_agent import build_storyboard
from agents.storyboard_normalizer import normalize_storyboard
from agents.design_agent import create_design_spec

from presentation.theme_engine import create_theme_spec
from presentation import ppt_builder


def run_pipeline(file_path, create_ppt=True, verbose=True):
    result = {}

    if verbose:
        print("1. Extracting document...")

    doc_data = extract_document_data(file_path)
    result["doc_data"] = doc_data

    if verbose:
        print("Text length:", len(doc_data.get("text", "")))
        print("Tables:", len(doc_data.get("tables", [])))
        print("Numbers:", len(doc_data.get("numbers", [])))
        print("Metric cards:", len(doc_data.get("metric_cards", [])))
        print("Chart candidates:", len(doc_data.get("chart_candidates", [])))

    if verbose:
        print("\n2. Chunking...")

    chunks = chunk_text(doc_data["text"])
    result["chunks"] = chunks

    if verbose:
        print("Chunks:", len(chunks))

    if verbose:
        print("\n3. Running AI analysis...")

    analysis = ai_analyzer.analyze_chunks(
        chunks,
        tables=doc_data.get("tables", []),
        chart_candidates=doc_data.get("chart_candidates", []),
        numbers=doc_data.get("numbers", []),
        metric_cards=doc_data.get("metric_cards", []),
        sections=doc_data.get("sections", [])
    )

    # Preserve structured extraction data
    analysis["tables"] = doc_data.get("tables", [])
    analysis["numbers"] = doc_data.get("numbers", [])
    analysis["metric_cards"] = doc_data.get("metric_cards", [])
    analysis["chart_candidates"] = doc_data.get("chart_candidates", [])
    analysis["sections"] = doc_data.get("sections", [])

    result["analysis_before_charts"] = analysis

    if verbose:
        print("Analysis keys:", analysis.keys())
        print("Metrics:", len(analysis.get("metrics", [])))
        print("Risks:", len(analysis.get("risks", [])))
        print("Recommendations:", len(analysis.get("recommendations", [])))

    if verbose:
        print("\n4. Creating visual assets...")

    analysis = create_visual_assets(analysis)
    result["analysis"] = analysis

    if verbose:
        print("Chart paths:", len(analysis.get("chart_paths", [])))
        for chart in analysis.get("chart_paths", []):
            print(chart)

    if verbose:
        print("\n5. Building storyboard...")

    storyboard = build_storyboard(analysis)
    result["storyboard_raw"] = storyboard

    clean_storyboard = normalize_storyboard(storyboard)
    result["storyboard"] = clean_storyboard

    if verbose:
        for i, slide in enumerate(clean_storyboard, 1):
            print(i, slide.get("layout"), "-", slide.get("title"))
            print("cards:", len(slide.get("cards", [])))
            print("bullets:", len(slide.get("bullets", [])))
            print("blocks:", len(slide.get("blocks", [])))

    if verbose:
        print("\n6. Creating design spec...")

    design_spec = create_design_spec(analysis, clean_storyboard)
    result["design_spec"] = design_spec

    if verbose:
        print("Theme:", design_spec.get("deck_theme"))
        print("Shape:", design_spec.get("shape_language"))
        print("Chart style:", design_spec.get("chart_style"))

    if verbose:
        print("\n7. Creating theme spec...")

    theme_spec = create_theme_spec(design_spec)
    result["theme_spec"] = theme_spec

    if verbose:
        print("Final theme:", theme_spec.get("theme_name"))

    if create_ppt:
        if verbose:
            print("\n8. Building PPT...")

        ppt_path = ppt_builder.create_ppt_from_pipeline(
            analysis=analysis,
            storyboard=clean_storyboard,
            design_spec=design_spec,
            theme_spec=theme_spec
        )

        result["ppt_path"] = ppt_path

        if verbose:
            print("PPT created:", ppt_path)

    return result