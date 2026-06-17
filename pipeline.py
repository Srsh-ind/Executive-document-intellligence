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
        print("=" * 60)
        print(f"Processing: {os.path.basename(file_path)}")
        print("=" * 60)

    # ── 1. Extract ────────────────────────────────────────────────
    if verbose: print("\n[1] Extracting document...")
    doc_data = extract_document_data(file_path)
    result["doc_data"] = doc_data

    if verbose:
        print(f"    Text length     : {len(doc_data.get('text', ''))}")
        print(f"    Tables          : {len(doc_data.get('tables', []))}")
        print(f"    Metric cards    : {len(doc_data.get('metric_cards', []))}")
        print(f"    Chart candidates: {len(doc_data.get('chart_candidates', []))}")
        print(f"    Sections        : {len(doc_data.get('sections', []))}")

    # ── 2. Chunk ──────────────────────────────────────────────────
    if verbose: print("\n[2] Chunking text...")
    chunks = chunk_text(doc_data["text"])
    if verbose: print(f"    Chunks: {len(chunks)}")

    # ── 3. AI Analysis ────────────────────────────────────────────
    if verbose: print("\n[3] Running AI analysis...")
    analysis = ai_analyzer.analyze_chunks(
        chunks,
        tables           = doc_data.get("tables", []),
        chart_candidates = doc_data.get("chart_candidates", []),
        numbers          = doc_data.get("numbers", []),
        metric_cards     = doc_data.get("metric_cards", []),
        sections         = doc_data.get("sections", []),
    )

    # Always carry through all extracted structured data
    analysis["tables"]           = doc_data.get("tables", [])
    analysis["numbers"]          = doc_data.get("numbers", [])
    analysis["metric_cards"]     = doc_data.get("metric_cards", [])
    analysis["chart_candidates"] = doc_data.get("chart_candidates", [])
    analysis["sections"]         = doc_data.get("sections", [])

    if verbose:
        print(f"    Title           : {analysis.get('title', '')[:60]}")
        print(f"    Metrics         : {len(analysis.get('metrics', []))}")
        print(f"    Key findings    : {len(analysis.get('key_findings', []))}")
        print(f"    Risks           : {len(analysis.get('risks', []))}")
        print(f"    Opportunities   : {len(analysis.get('opportunities', []))}")
        print(f"    Recommendations : {len(analysis.get('recommendations', []))}")
        print(f"    Visuals (AI)    : {len(analysis.get('visuals', []))}")

    # ── 4. Storyboard ─────────────────────────────────────────────
    if verbose: print("\n[4] Building storyboard...")
    storyboard = build_storyboard(analysis)
    # normalize_storyboard injects cover + closing automatically
    storyboard = normalize_storyboard(storyboard, analysis=analysis)

    if verbose:
        for i, s in enumerate(storyboard, 1):
            print(f"    {i:2d}. [{s.get('layout','?'):25s}] {s.get('title','')[:50]}")

    # ── 5. Design spec ────────────────────────────────────────────
    if verbose: print("\n[5] Creating design spec...")
    design_spec = create_design_spec(analysis, storyboard)

    # Carry document metadata into design_spec so theme_engine can infer theme
    design_spec["document_type"] = analysis.get("document_type", "")
    design_spec["title"]         = analysis.get("title", "")
    design_spec["audience"]      = analysis.get("audience", "")

    if verbose:
        print(f"    LLM theme    : {design_spec.get('deck_theme')}")
        print(f"    Shape        : {design_spec.get('shape_language')}")

    # ── 6. Theme spec ─────────────────────────────────────────────
    if verbose: print("\n[6] Resolving theme...")
    theme_spec = create_theme_spec(design_spec)

    if verbose:
        print(f"    Final theme  : {theme_spec['theme_name']}")

    # ── 7. Render charts ──────────────────────────────────────────
    if verbose: print("\n[7] Rendering charts...")
    analysis = create_visual_assets(analysis, theme=theme_spec)

    if verbose:
        print(f"    Charts rendered: {len(analysis.get('chart_paths', []))}")
        for c in analysis.get("chart_paths", []):
            print(f"      [{c.get('chart_type','?'):7s}] {c.get('title','')}")

    result["analysis"]  = analysis
    result["storyboard"] = storyboard
    result["design_spec"] = design_spec
    result["theme_spec"]  = theme_spec

    # ── 8. Build PPT ──────────────────────────────────────────────
    if create_ppt:
        if verbose: print("\n[8] Building PPT...")
        ppt_path = ppt_builder.create_ppt_from_pipeline(
            analysis    = analysis,
            storyboard  = storyboard,
            design_spec = design_spec,
            theme_spec  = theme_spec,
        )
        result["ppt_path"] = ppt_path
        if verbose:
            print(f"    Saved: {ppt_path}")
            print("=" * 60)

    return result