import copy
import html
import json
import os
import re
from typing import Any, Dict, List, Optional

import streamlit as st

# ── Must be first Streamlit call ──────────────────────────────────────────────
st.set_page_config(
    page_title="Agentic Document Intelligence Studio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# Imports
# ══════════════════════════════════════════════════════════════════════════════
from ingestion.data_extractor import extract_document_data
from ingestion.chunker import chunk_text
from agents import ai_analyzer
from agents.chart_agent import create_visual_assets
from agents.storyboard_agent import build_storyboard
from agents.storyboard_normalizer import normalize_storyboard
from agents.design_agent import create_design_spec
from presentation.theme_engine import create_theme_spec
from presentation.ppt_builder import create_ppt_from_pipeline

try:
    from agents.llm_client import MODEL_NAME
except Exception:
    MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "Qwen/Qwen3-8B")


def get_llm_display_name() -> str:
    """Return the Qwen/vLLM model label shown in the UI."""
    raw_name = os.environ.get("LLM_MODEL_NAME", MODEL_NAME or "Qwen/Qwen3-8B")
    return raw_name.replace("Qwen/", "") if "qwen" in raw_name.lower() else raw_name


DEFAULT_DECK_CHART_LIMIT = int(os.environ.get("DEFAULT_DECK_CHART_LIMIT", "8"))


def default_chart_indices(charts: List[Dict[str, Any]], limit: int = DEFAULT_DECK_CHART_LIMIT) -> List[int]:
    """Pick a concise default set for the first PPT.

    All rendered charts remain available on the dashboard for manual selection,
    but the first deck should not become a chart dump.
    """
    if not charts:
        return []

    def score(item):
        title = str(item.get("title", "")).lower()
        ctype = str(item.get("chart_type", "")).lower()
        s = 0
        if ctype in {"line", "bar"}:
            s += 4
        if ctype in {"pie", "donut", "doughnut"}:
            s += 2
        for token in ("revenue", "margin", "profit", "expense", "cash", "growth", "customer", "conversion", "bookings", "eps"):
            if token in title:
                s += 2
        return s

    ranked = sorted(range(len(charts)), key=lambda i: (-score(charts[i]), i))
    picked = sorted(ranked[: max(1, min(limit, len(charts)))])
    return picked


def _strip_user_hidden_markers(text: Any) -> str:
    """Remove evidence/debug markers from dashboard/PPT-visible text."""
    text = str(text or "").strip()
    lines = []
    for line in text.splitlines():
        low = line.strip().lower()
        if low.startswith(("audience:", "domain expected:", "prepared for:", "reporting period:", "source profile:")):
            continue
        lines.append(line)
    text = "\n".join(lines).strip()
    # Remove all evidence references, including "| Evidence: E012" and "Evidence IDs: E001, E004".
    text = re.sub(r"\s*\|?\s*Evidence\s*(?:IDs?|references?)?\s*[:：]\s*(?:E\d{3}(?:\s*[,;]\s*)?)+", "", text, flags=re.I)
    text = re.sub(r"\s*\(?\bE\d{3}(?:\s*[,;]\s*E\d{3})*\)?", "", text, flags=re.I)
    text = re.sub(r"^(Implication|Reasoning|Business implication)\s*[:：]\s*", "", text, flags=re.I)
    text = text.replace("Evidence → interpretation → implication:", "")
    text = text.replace("Evidence -> interpretation -> implication:", "")
    text = text.replace("Evidence → interpretation → action → expected impact:", "")
    text = text.replace("Evidence -> interpretation -> action -> expected impact:", "")
    text = re.sub(r"\bStrategies should focus on\s*$", "", text, flags=re.I)
    text = text.replace("…", "")
    text = re.sub(r"\.{3,}", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _visible_insight_text(item: Any) -> str:
    """Return the executive insight statement shown in dashboard and PPT."""
    if isinstance(item, dict):
        text = (
            item.get("claim")
            or item.get("insight")
            or item.get("finding")
            or item.get("text")
            or ""
        )
        return _strip_user_hidden_markers(text)
    return _strip_user_hidden_markers(item)


def _visible_reasoning_text(item: Any) -> str:
    """Return concise reasoning for an insight without exposing evidence IDs."""
    if not isinstance(item, dict):
        return ""
    text = item.get("reasoning") or item.get("why") or item.get("business_implication") or item.get("implication") or ""
    text = _strip_user_hidden_markers(text)
    low = text.lower()
    if not text or any(bad in low for bad in (
        "retrieved supporting evidence",
        "cited evidence",
        "evidence item",
        "directly derived",
        "contains a numeric document fact",
        "reasoning path is",
    )):
        return ""
    return text[:420].rstrip()


def _clean_exec_summary(summary: Any, analysis: Dict[str, Any]) -> str:
    """Hide technical fallback text and replace it with a blended insight."""
    summary = str(summary or "").strip()
    bad_markers = (
        "language model synthesis call was unavailable",
        "connect the llm endpoint",
        "ai analysis was unavailable",
    )
    if not summary or any(m in summary.lower() for m in bad_markers):
        source_items = (
            analysis.get("explainable_insights")
            or analysis.get("insights")
            or analysis.get("key_findings")
            or []
        )
        summary = " ".join(
            _visible_insight_text(x) for x in source_items[:2] if _visible_insight_text(x)
        ).strip()
    return _strip_user_hidden_markers(summary) or (
        "The uploaded document was converted into an evidence-backed executive view "
        "using extracted metrics, trends, risks, and recommended actions."
    )


def _clean_core_message(core: Any, analysis: Dict[str, Any]) -> str:
    """Show the core message as generated; allow it to match the summary if that is the strongest takeaway."""
    core = _strip_user_hidden_markers(core)

    # User preference: do not suppress or rewrite the core message just because
    # it overlaps with the insight summary. It should remain visible.
    if core:
        if not core.lower().startswith("core message"):
            core = f"Core message: {core}"
        return _strip_user_hidden_markers(core)

    # If the analyzer did not provide a core message, fall back to the executive
    # summary or first insight. This intentionally may be similar to the summary.
    summary = _clean_exec_summary(analysis.get("executive_summary"), analysis)
    if summary:
        return _strip_user_hidden_markers(f"Core message: {summary}")

    insight_items = analysis.get("explainable_insights") or analysis.get("insights") or analysis.get("key_findings") or []
    if insight_items:
        first = _visible_insight_text(insight_items[0])
        if first:
            return _strip_user_hidden_markers(f"Core message: {first}")

    return "Core message: use the strongest documented evidence to separate what happened, why it matters, and what leadership should do next."



# ══════════════════════════════════════════════════════════════════════════════
# Styling
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
<style>
    /* App background */
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(139, 92, 246, 0.12), transparent 34rem),
            radial-gradient(circle at top right, rgba(236, 72, 153, 0.06), transparent 30rem),
            linear-gradient(180deg, #f8fafc 0%, #ffffff 44%);
    }

    /* Keep the Upload button and file-type hint, but remove Streamlit's generated
       max-size text (for example: "200MB per file"). Streamlit renders the size
       and file formats as one helper string, so we hide that helper and re-add
       only the supported formats. */
    section[data-testid="stFileUploaderDropzone"] {
        gap: 0.85rem !important;
        min-height: 58px !important;
        align-items: center !important;
    }

    section[data-testid="stFileUploaderDropzone"] button {
        margin: 0 !important;
        flex-shrink: 0 !important;
    }

    /* Hide only the generated helper/limit text, not the uploader itself. */
    [data-testid="stFileUploaderDropzoneInstructions"],
    [data-testid="stFileUploaderDropzoneInstructions"] *,
    section[data-testid="stFileUploaderDropzone"] > div:not(:has(button)),
    section[data-testid="stFileUploaderDropzone"] button + div,
    section[data-testid="stFileUploaderDropzone"] button + span,
    section[data-testid="stFileUploaderDropzone"] button + p,
    section[data-testid="stFileUploaderDropzone"] button + small {
        display: none !important;
    }

    /* Add back the allowed file types without the size prefix. */
    section[data-testid="stFileUploaderDropzone"]::after {
        content: "PDF, DOCX, TXT, CSV, XLSX, PPTX";
        display: inline-block;
        color: #667085;
        font-size: 0.92rem;
        line-height: 1.35;
        white-space: nowrap;
    }

    /* File upload styling */
    [data-testid="stFileUploaderDropzone"] {
        border: 2px dashed #8b5cf6 !important;
        background: rgba(139, 92, 246, 0.055) !important;
        border-radius: 18px !important;
        padding: 1.1rem !important;
    }

    div.stButton > button, div.stDownloadButton > button {
        border-radius: 10px !important;
        min-height: 38px !important;
        padding: 0.38rem 0.95rem !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
    }

    /* Premium graphite + violet action styling. */
    div.stButton > button[kind="primary"],
    div.stDownloadButton > button[kind="primary"],
    button[data-testid="stBaseButton-primary"],
    .stDownloadButton button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(90deg, #111827 0%, #6d28d9 100%) !important;
        border: 0 !important;
        color: #ffffff !important;
        box-shadow: 0 10px 22px rgba(109, 40, 217, 0.18) !important;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stDownloadButton > button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        background: linear-gradient(90deg, #020617 0%, #7c3aed 100%) !important;
        color: #ffffff !important;
    }

    .hero-card {
        padding: 1.65rem 1.8rem;
        border-radius: 24px;
        background: linear-gradient(135deg, #020617 0%, #312e81 58%, #7c3aed 100%);
        color: white;
        box-shadow: 0 18px 44px rgba(49, 46, 129, 0.24);
        margin-bottom: 1.2rem;
    }
    .hero-card h1 {
        color: white;
        font-size: 2.25rem;
        line-height: 1.08;
        margin: 0 0 0.45rem 0;
    }
    .hero-card p {
        color: rgba(255, 255, 255, 0.86);
        font-size: 1.02rem;
        margin: 0;
    }

    .glass-card {
        border: 1px solid rgba(15, 23, 42, 0.08);
        background: rgba(255, 255, 255, 0.82);
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
        border-radius: 18px;
        padding: 1.05rem 1.15rem;
        min-height: 116px;
    }
    .section-title {
        margin-top: 0.4rem;
        margin-bottom: 0.6rem;
        font-weight: 800;
        font-size: 1.18rem;
        color: #0f172a;
    }
    .muted {
        color: #64748b;
        font-size: 0.92rem;
    }
    .workflow-current {
        margin: 0.45rem 0 0.55rem 0;
        padding: 0.9rem 1rem;
        border-radius: 16px;
        border: 1px solid rgba(139, 92, 246, 0.20);
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.11), rgba(168, 85, 247, 0.055));
        color: #0f172a;
    }
    .workflow-current .eyebrow {
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #6d28d9;
        margin-bottom: 0.22rem;
    }
    .workflow-current .title {
        font-size: 1rem;
        font-weight: 800;
        margin-bottom: 0.16rem;
    }
    .workflow-current .detail {
        color: #64748b;
        font-size: 0.9rem;
    }

    .agent-card {
        border-radius: 16px;
        padding: 0.8rem 0.85rem;
        border: 1px solid rgba(15, 23, 42, 0.08);
        background: #ffffff;
        min-height: 122px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.045);
        margin-bottom: 0.75rem;
    }
    .agent-card.done {
        border-color: rgba(34, 197, 94, 0.32);
        background: linear-gradient(180deg, rgba(34, 197, 94, 0.08), #ffffff 65%);
    }
    .agent-card.running {
        border-color: rgba(139, 92, 246, 0.38);
        background: linear-gradient(180deg, rgba(139, 92, 246, 0.10), #ffffff 68%);
    }
    .agent-card.error {
        border-color: rgba(239, 68, 68, 0.36);
        background: linear-gradient(180deg, rgba(239, 68, 68, 0.09), #ffffff 68%);
    }
    .agent-name {
        font-weight: 800;
        font-size: 0.94rem;
        color: #0f172a;
        margin-bottom: 0.3rem;
    }
    .agent-status {
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        color: #334155;
        margin-bottom: 0.35rem;
    }
    .agent-detail {
        font-size: 0.82rem;
        color: #64748b;
        line-height: 1.28;
    }
    .overview-card {
        border: 1px solid rgba(15, 23, 42, 0.08);
        background: rgba(255, 255, 255, 0.86);
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.045);
        border-radius: 16px;
        padding: 0.95rem 1rem;
        min-height: 96px;
    }
    .overview-label {
        color: #64748b;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.015em;
        margin-bottom: 0.35rem;
    }
    .overview-value {
        color: #111827;
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.15;
        overflow-wrap: anywhere;
    }

    .wrapped-metric-value {
        font-size: 1.35rem;
        line-height: 1.35;
        font-weight: 650;
        color: #111827;
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: normal;
        margin: 0.25rem 0 0.35rem 0;
    }


    .core-message {
        margin-top: 0.9rem;
        padding: 0.9rem 1rem;
        border-radius: 12px;
        background: #eaf4ff;
        color: #004f8f;
        line-height: 1.45;
        font-size: 0.98rem;
    }

</style>
""",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# Agent workflow state helpers
# ══════════════════════════════════════════════════════════════════════════════
AGENT_WORKFLOW: List[Dict[str, str]] = [
    {"key": "intake", "name": "Document Intake", "pending": "Waiting for upload"},
    {"key": "extract", "name": "Extraction Agent", "pending": "Ready to extract text, tables and charts"},
    {"key": "chunk", "name": "Chunking Agent", "pending": "Ready to split long context"},
    {"key": "analysis", "name": "Insight Analysis Agent", "pending": "Ready to identify metrics and insights"},
    {"key": "storyboard", "name": "Storyboard Agent", "pending": "Ready to plan slide narrative"},
    {"key": "design", "name": "Design Agent", "pending": "Ready to create presentation design"},
    {"key": "theme", "name": "Theme Agent", "pending": "Ready to resolve visual theme"},
    {"key": "charts", "name": "Chart Agent", "pending": "Ready to render visuals"},
    {"key": "ppt", "name": "PPT Builder Agent", "pending": "Ready to assemble the deck"},
]

STATUS_LABEL = {
    "pending": "Queued",
    "running": "Running",
    "done": "Done",
    "error": "Error",
    "skipped": "Skipped",
}

STATUS_ICON = {
    "pending": "○",
    "running": "◐",
    "done": "✓",
    "error": "!",
    "skipped": "–",
}


def fresh_agent_steps() -> Dict[str, Dict[str, str]]:
    return {
        step["key"]: {"status": "pending", "detail": step["pending"]}
        for step in AGENT_WORKFLOW
    }


def ensure_agent_steps() -> None:
    if "agent_steps" not in st.session_state or not isinstance(st.session_state.agent_steps, dict):
        st.session_state.agent_steps = fresh_agent_steps()
    else:
        # Keep compatibility if new steps are added later.
        for step in AGENT_WORKFLOW:
            st.session_state.agent_steps.setdefault(
                step["key"], {"status": "pending", "detail": step["pending"]}
            )


def set_agent_status(
    key: str,
    status: str,
    detail: str,
    placeholder: Optional[Any] = None,
    active_message: Optional[str] = None,
) -> None:
    ensure_agent_steps()
    st.session_state.agent_steps[key] = {"status": status, "detail": detail}
    if placeholder is not None:
        with placeholder.container():
            render_agent_workflow(active_message=active_message, compact=True)


def agent_progress_value() -> float:
    ensure_agent_steps()
    total = len(AGENT_WORKFLOW)
    done = sum(
        1
        for step in AGENT_WORKFLOW
        if st.session_state.agent_steps.get(step["key"], {}).get("status") in {"done", "skipped"}
    )
    running = any(
        st.session_state.agent_steps.get(step["key"], {}).get("status") == "running"
        for step in AGENT_WORKFLOW
    )
    progress = done / total if total else 0
    if running and done < total:
        progress = min((done + 0.45) / total, 0.99)
    return progress


def current_agent_status() -> Dict[str, str]:
    'Return one concise workflow status for display above the progress bar.'
    ensure_agent_steps()

    running = [
        step for step in AGENT_WORKFLOW
        if st.session_state.agent_steps.get(step["key"], {}).get("status") == "running"
    ]
    if running:
        step = running[0]
        detail = st.session_state.agent_steps.get(step["key"], {}).get("detail", step["pending"])
        return {"label": "Running now", "name": step["name"], "detail": detail}

    errored = [
        step for step in AGENT_WORKFLOW
        if st.session_state.agent_steps.get(step["key"], {}).get("status") == "error"
    ]
    if errored:
        step = errored[0]
        detail = st.session_state.agent_steps.get(step["key"], {}).get("detail", "Needs attention")
        return {"label": "Stopped at", "name": step["name"], "detail": detail}

    pending = [
        step for step in AGENT_WORKFLOW
        if st.session_state.agent_steps.get(step["key"], {}).get("status") == "pending"
    ]
    if pending:
        step = pending[0]
        detail = st.session_state.agent_steps.get(step["key"], {}).get("detail", step["pending"])
        return {"label": "Next step", "name": step["name"], "detail": detail}

    return {
        "label": "Workflow complete",
        "name": "Final presentation ready",
        "detail": "The downloadable PPT is ready.",
    }


def render_agent_workflow(active_message: Optional[str] = None, compact: bool = False) -> None:
    'Render a single, clean progress indicator instead of separate agent cards.'
    ensure_agent_steps()
    progress = agent_progress_value()
    pct = int(round(progress * 100))
    current = current_agent_status()
    detail = active_message or current["detail"]

    st.markdown('<div class="section-title">Agent Workflow</div>', unsafe_allow_html=True)
    st.markdown(
        f'''
<div class="workflow-current">
  <div class="eyebrow">{current["label"]} · {pct}% complete</div>
  <div class="title">{current["name"]}</div>
  <div class="detail">{detail}</div>
</div>
''',
        unsafe_allow_html=True,
    )
    st.progress(progress)


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline runner with visible agent-level progress
# ══════════════════════════════════════════════════════════════════════════════
def run_pipeline_with_agent_progress(file_path: str, progress_placeholder: Any = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    try:
        set_agent_status(
            "intake",
            "running",
            f"Preparing {os.path.basename(file_path)}",
            progress_placeholder,
            "Document intake running",
        )
        set_agent_status(
            "intake",
            "done",
            "File saved and queued for analysis",
            progress_placeholder,
            "Document intake complete.",
        )

        set_agent_status(
            "extract",
            "running",
            "Extracting text, tables, numbers, sections and chart candidates",
            progress_placeholder,
            "Extraction Agent running",
        )
        doc_data = extract_document_data(file_path)
        result["doc_data"] = doc_data
        set_agent_status(
            "extract",
            "done",
            f"{len(doc_data.get('text', '')):,} chars · {len(doc_data.get('tables', []))} tables · {len(doc_data.get('chart_candidates', []))} chart candidates",
            progress_placeholder,
            "Extraction Agent complete.",
        )

        set_agent_status(
            "chunk",
            "running",
            "Splitting long text into model-friendly chunks",
            progress_placeholder,
            "Chunking Agent running",
        )
        chunks = chunk_text(doc_data.get("text", ""))
        set_agent_status(
            "chunk",
            "done",
            f"Created {len(chunks)} context chunk(s)",
            progress_placeholder,
            "Chunking Agent complete.",
        )

        set_agent_status(
            "analysis",
            "running",
            "Generating executive summary, KPIs, risks, opportunities and recommendations",
            progress_placeholder,
            "Insight Analysis Agent running",
        )
        analysis = ai_analyzer.analyze_chunks(
            chunks,
            tables=doc_data.get("tables", []),
            chart_candidates=doc_data.get("chart_candidates", []),
            numbers=doc_data.get("numbers", []),
            metric_cards=doc_data.get("metric_cards", []),
            sections=doc_data.get("sections", []),
        )
        analysis["tables"] = doc_data.get("tables", [])
        analysis["numbers"] = doc_data.get("numbers", [])
        analysis["metric_cards"] = doc_data.get("metric_cards", [])
        analysis["chart_candidates"] = doc_data.get("chart_candidates", [])
        analysis["sections"] = doc_data.get("sections", [])
        set_agent_status(
            "analysis",
            "done",
            f"{len(analysis.get('metrics', []))} metrics · {len(analysis.get('insights', []) or analysis.get('key_findings', []))} insights · {len(analysis.get('recommendations', []))} recommendations",
            progress_placeholder,
            "Insight Analysis Agent complete.",
        )

        set_agent_status(
            "storyboard",
            "running",
            "Planning slide sequence and narrative arc",
            progress_placeholder,
            "Storyboard Agent running",
        )
        storyboard = build_storyboard(analysis)
        storyboard = normalize_storyboard(storyboard, analysis=analysis)
        set_agent_status(
            "storyboard",
            "done",
            f"Planned {len(storyboard)} slide(s)",
            progress_placeholder,
            "Storyboard Agent complete.",
        )

        set_agent_status(
            "design",
            "running",
            "Creating layout, density and visual design spec",
            progress_placeholder,
            "Design Agent running",
        )
        design_spec = create_design_spec(analysis, storyboard)
        design_spec["document_type"] = analysis.get("document_type", "")
        design_spec["title"] = analysis.get("title", "")
        design_spec["audience"] = analysis.get("audience", "")
        set_agent_status(
            "design",
            "done",
            f"Theme request: {design_spec.get('deck_theme', 'auto')} · Shape: {design_spec.get('shape_language', 'balanced')}",
            progress_placeholder,
            "Design Agent complete.",
        )

        set_agent_status(
            "theme",
            "running",
            "Resolving colors, typography and chart styling",
            progress_placeholder,
            "Theme Agent running",
        )
        theme_spec = create_theme_spec(design_spec)
        set_agent_status(
            "theme",
            "done",
            f"Resolved theme: {theme_spec.get('theme_name', 'default')}",
            progress_placeholder,
            "Theme Agent complete.",
        )

        set_agent_status(
            "charts",
            "running",
            "Rendering visual assets from tables and chart candidates",
            progress_placeholder,
            "Chart Agent running",
        )
        analysis = create_visual_assets(analysis, theme=theme_spec)
        all_charts = list(analysis.get("chart_paths", []) or [])
        selected_default = default_chart_indices(all_charts)
        analysis["all_chart_paths"] = all_charts
        analysis["selected_chart_indices"] = selected_default
        # Build the first PPT with only the strongest default charts. The dashboard
        # still shows every rendered chart, and users can rebuild with any selection.
        analysis["chart_paths"] = [all_charts[i] for i in selected_default]
        chart_count = len(all_charts)
        set_agent_status(
            "charts",
            "done" if chart_count else "skipped",
            f"Rendered {chart_count} chart(s)" if chart_count else "No chart-ready data detected",
            progress_placeholder,
            "Chart Agent complete.",
        )

        result["analysis"] = analysis
        result["storyboard"] = storyboard
        result["design_spec"] = design_spec
        result["theme_spec"] = theme_spec

        set_agent_status(
            "ppt",
            "running",
            "Assembling slides, visuals and executive narrative into PPTX",
            progress_placeholder,
            "PPT Builder Agent running",
        )
        ppt_path = create_ppt_from_pipeline(
            analysis=analysis,
            storyboard=storyboard,
            design_spec=design_spec,
            theme_spec=theme_spec,
        )
        result["ppt_path"] = ppt_path
        set_agent_status(
            "ppt",
            "done",
            f"Presentation built: {os.path.basename(ppt_path)}",
            progress_placeholder,
            "PPT Builder Agent complete.",
        )


        return result

    except Exception:
        # Mark the active running step as failed so the dashboard is useful even when the run breaks.
        ensure_agent_steps()
        running_key = next(
            (
                step["key"]
                for step in AGENT_WORKFLOW
                if st.session_state.agent_steps.get(step["key"], {}).get("status") == "running"
            ),
            None,
        )
        if running_key:
            set_agent_status(
                running_key,
                "error",
                "This step failed. Check the error message below.",
                progress_placeholder,
                "Pipeline stopped because one agent failed.",
            )
        raise


def uploaded_document_type_label(uploaded: Optional[Any]) -> str:
    if uploaded is None:
        return "Supported formats: PDF, DOCX, TXT, CSV, XLSX, PPTX"
    ext = os.path.splitext(uploaded.name)[1].lower().lstrip(".")
    labels = {
        "pdf": "PDF report",
        "docx": "Word document",
        "txt": "Text document",
        "csv": "CSV dataset",
        "xlsx": "Excel workbook",
        "pptx": "PowerPoint deck",
    }
    return labels.get(ext, "Uploaded document")


def infer_source_profile(analysis: Dict[str, Any], doc_data: Dict[str, Any]) -> str:
    """Return a clean business-facing source label for the dashboard.

    The LLM sometimes returns generic labels such as "Executive Presentation".
    This keeps the dashboard useful by normalising those labels into a more
    meaningful source profile.
    """
    raw = str(analysis.get("document_type") or analysis.get("doc_type") or "").strip()
    generic = {
        "",
        "unknown",
        "document",
        "business document",
        "report",
        "executive presentation",
        "executive summary",
        "presentation",
        "powerpoint deck",
    }
    if raw and raw.lower() not in generic:
        return raw

    text = " ".join(
        [
            str(analysis.get("executive_summary") or ""),
            str(analysis.get("core_message") or ""),
            str(doc_data.get("text") or "")[:6000],
        ]
    ).lower()

    if any(term in text for term in ("revenue", "profit", "margin", "ebitda", "cash flow", "operating income", "financial")):
        return "Financial Performance Report"
    if any(term in text for term in ("market size", "market research", "cagr", "tam", "sam", "consumer", "competitor")):
        return "Market Intelligence Report"
    if any(term in text for term in ("sales", "pipeline", "conversion", "quota", "customer acquisition", "funnel")):
        return "Commercial Performance Report"
    if any(term in text for term in ("risk", "compliance", "control", "audit", "regulation", "governance")):
        return "Risk & Compliance Brief"
    if any(term in text for term in ("roadmap", "strategy", "initiative", "priority", "transformation")):
        return "Strategic Business Brief"
    return "Business Intelligence Report"


def safe_html(value: Any) -> str:
    return html.escape(str(value if value is not None else "—"))


def overview_card(label: str, value: Any) -> None:
    st.markdown(
        f"""
<div class="overview-card">
  <div class="overview-label">{safe_html(label)}</div>
  <div class="overview-value">{safe_html(value)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def reset_app_state() -> None:
    for k in (
        "pipeline_result",
        "last_uploaded",
        "selected_charts",
        "final_ppt_path",
        "run_error",
    ):
        st.session_state[k] = None
    st.session_state.agent_steps = fresh_agent_steps()


# ══════════════════════════════════════════════════════════════════════════════
# Session state
# ══════════════════════════════════════════════════════════════════════════════
for key, default in [
    ("pipeline_result", None),
    ("last_uploaded", None),
    ("selected_charts", None),
    ("final_ppt_path", None),
    ("run_error", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default
ensure_agent_steps()


# ══════════════════════════════════════════════════════════════════════════════
# UI Header
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
<div class="hero-card">
    <h1>📊 Agentic Document Intelligence Studio</h1>
    <p>Turn documents into insights, dashboards, and presentations — powered by Qwen 3 on the AMD ROCm Platform with vLLM.</p>
</div>
""",
    unsafe_allow_html=True,
)

upload_col, _ = st.columns([2.35, 0.65])
with upload_col:
    uploaded_file = st.file_uploader(
        "Upload a document",
        type=["pdf", "docx", "txt", "csv", "xlsx", "pptx"],
        help="Supported formats: PDF, DOCX, TXT, CSV, XLSX, PPTX",
    )


if uploaded_file:
    os.makedirs("temp", exist_ok=True)
    file_path = os.path.join("temp", uploaded_file.name)

    # Reset session when a different file is uploaded
    if st.session_state.last_uploaded != uploaded_file.name:
        st.session_state.pipeline_result = None
        st.session_state.selected_charts = None
        st.session_state.final_ppt_path = None
        st.session_state.run_error = None
        st.session_state.agent_steps = fresh_agent_steps()

    action_col, _ = st.columns([0.85, 2.15])
    with action_col:
        generate_clicked = st.button(
            "🚀 Generate Presentation",
            type="primary",
            use_container_width=True,
        )

    if generate_clicked:
        with open(file_path, "wb") as f:
            uploaded_file.seek(0)
            f.write(uploaded_file.read())

        st.session_state.last_uploaded = uploaded_file.name
        st.session_state.pipeline_result = None
        st.session_state.selected_charts = None
        st.session_state.final_ppt_path = None
        st.session_state.run_error = None
        st.session_state.agent_steps = fresh_agent_steps()

        progress_placeholder = st.empty()
        try:
            result = run_pipeline_with_agent_progress(file_path, progress_placeholder)
            st.session_state.pipeline_result = result
            st.session_state.final_ppt_path = result.get("ppt_path")
            charts = result.get("analysis", {}).get("all_chart_paths") or result.get("analysis", {}).get("chart_paths", []) or []
            st.session_state.selected_charts = list(result.get("analysis", {}).get("selected_chart_indices", list(range(len(charts)))))
            progress_placeholder.empty()
            st.success("✅ Presentation generated successfully.")
        except Exception as exc:
            st.session_state.run_error = str(exc)
            st.error(f"❌ Error: {exc}")
            st.info("Please try a different document or check the failing agent step above.")

elif st.session_state.pipeline_result is None:
    st.markdown("---")
    render_agent_workflow(active_message="Upload a document to start. The active agent will appear here while the PPT is being generated.", compact=False)


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard — renders from session state; survives download button clicks
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.pipeline_result is not None:
    result = st.session_state.pipeline_result
    doc_data = result["doc_data"]
    analysis = result["analysis"]
    storyboard = result["storyboard"]
    chart_paths = analysis.get("all_chart_paths") or analysis.get("chart_paths", []) or []
    included_chart_paths = analysis.get("chart_paths", []) or []

    st.markdown("---")
    render_agent_workflow(active_message="Completed. Final presentation is ready for download.")

    st.markdown("---")
    insight_items = analysis.get("insights", []) or analysis.get("key_findings", []) or []
    ov1, ov2, ov3, ov4 = st.columns(4)
    with ov1:
        overview_card("Source Profile", infer_source_profile(analysis, doc_data))
    with ov2:
        overview_card("Slide Plan", f"{len(storyboard)} slides")
    with ov3:
        overview_card("Visuals Created", f"{len(included_chart_paths)} of {len(chart_paths)} charts")
    with ov4:
        overview_card("Insights Found", len(insight_items))

    # ── Summary ───────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Document Intelligence Dashboard</div>', unsafe_allow_html=True)
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.markdown("#### Insight Summary")
        st.write(_clean_exec_summary(analysis.get("executive_summary"), analysis))
        core_message = _clean_core_message(analysis.get("core_message"), analysis)
        if core_message:
            st.markdown(
                f'<div class="core-message"><b>Core message:</b> {html.escape(core_message.replace("Core message:", "").strip())}</div>',
                unsafe_allow_html=True,
            )
    with col_r:
        st.markdown("#### Document Info")
        domain_info = analysis.get("domain") or analysis.get("detected_domain") or {}
        if isinstance(domain_info, dict):
            domain_label = domain_info.get("label") or domain_info.get("domain") or domain_info.get("key") or "General"
            domain_confidence = domain_info.get("confidence", "")
        else:
            domain_label = str(domain_info or "General")
            domain_confidence = ""
        st.markdown(
            f"""
<div class="glass-card">
  <div><b>Text extracted:</b> {len(doc_data.get('text','')):,} chars</div>
  <div><b>Tables:</b> {len(doc_data.get('tables', []))}</div>
  <div><b>Metric cards:</b> {len(doc_data.get('metric_cards', []))}</div>
  <div><b>Chart candidates:</b> {len(doc_data.get('chart_candidates', []))}</div>
  <div><b>Detected domain:</b> {domain_label}</div>
  <div><b>Domain confidence:</b> {domain_confidence}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    # ── Metrics strip ─────────────────────────────────────────────────────────
    metrics = analysis.get("metrics", []) or []
    if metrics:
        st.markdown("---")
        st.markdown("#### Key Metrics")
        cols = st.columns(min(len(metrics), 4))
        for i, metric in enumerate(metrics[:4]):
            with cols[i]:
                if isinstance(metric, dict):
                    label = _strip_user_hidden_markers(metric.get("name") or metric.get("metric", "Metric"))
                    value = _strip_user_hidden_markers(metric.get("value", "—"))
                    note = _strip_user_hidden_markers(metric.get("interpretation", ""))
                    # Very long values such as multi-segment ACV do not fit in st.metric;
                    # render them as wrapped text so dashboard output matches PPT and never bleeds.
                    if len(value) > 24 or "," in value:
                        st.markdown(f"**{label}**")
                        st.markdown(
                            f'<div class="wrapped-metric-value">{html.escape(value)}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.metric(label=label, value=value)
                    if note:
                        st.caption(note)
                else:
                    st.write(_strip_user_hidden_markers(metric))

    # ── Content tabs ──────────────────────────────────────────────────────────
    st.markdown("---")
    tab_insights, tab_risks, tab_opps, tab_actions, tab_slides = st.tabs(
        ["💡 Insights", "⚠️ Risks", "🚀 Opportunities", "📋 Actions", "🗂️ Slide Plan"]
    )

    with tab_insights:
        items = analysis.get("explainable_insights", []) or analysis.get("insights", []) or analysis.get("key_findings", []) or []
        if items:
            seen = set()
            for item in items[:10]:
                text = _visible_insight_text(item)
                key = text.lower()[:180]
                if text and key not in seen:
                    st.markdown(f"- **{text}**")
                    reasoning = _visible_reasoning_text(item)
                    if reasoning:
                        st.caption(f"Reasoning: {reasoning}")
                    seen.add(key)
        else:
            st.caption("No insights generated.")

    with tab_risks:
        risks = analysis.get("risks", []) or []
        if risks:
            for item in risks[:10]:
                if isinstance(item, dict):
                    risk = _strip_user_hidden_markers(item.get('risk', 'Risk'))
                    desc = _strip_user_hidden_markers(item.get('description', ''))
                    st.markdown(f"- **{risk}**" + (f": {desc}" if desc else ""))
                    mitigation = _strip_user_hidden_markers(item.get("mitigation", ""))
                    if mitigation:
                        st.caption(f"Mitigation: {mitigation}")
                else:
                    st.markdown(f"- {_strip_user_hidden_markers(item)}")
        else:
            st.caption("No risks identified.")

    with tab_opps:
        opps = analysis.get("opportunities", []) or []
        if opps:
            for item in opps[:10]:
                if isinstance(item, dict):
                    opp = _strip_user_hidden_markers(item.get('opportunity', 'Opportunity'))
                    desc = _strip_user_hidden_markers(item.get('description', ''))
                    st.markdown(f"- **{opp}**" + (f": {desc}" if desc else ""))
                else:
                    st.markdown(f"- {_strip_user_hidden_markers(item)}")
        else:
            st.caption("No opportunities identified.")

    with tab_actions:
        recs = analysis.get("recommendations", []) or []
        if recs:
            for rec in recs[:12]:
                if isinstance(rec, dict):
                    priority = rec.get("priority", "Medium")
                    icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority, "🔵")
                    recommendation = _strip_user_hidden_markers(rec.get('recommendation', ''))
                    st.markdown(f"{icon} **{priority}** — {recommendation}")
                    impact = _strip_user_hidden_markers(rec.get("business_impact", ""))
                    if impact:
                        st.caption(f"Impact: {impact}")
                else:
                    st.markdown(f"- {_strip_user_hidden_markers(rec)}")
        else:
            st.caption("No recommendations generated.")

    with tab_slides:
        for i, slide in enumerate(storyboard, 1):
            st.markdown(
                f"**{i}. {slide.get('title', 'Slide')}** · `{slide.get('layout', '')}`  \n"
                f"{slide.get('headline', '')}"
            )

    # ── Chart selector ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 Select Charts to Include in Presentation")

    if not chart_paths:
        st.caption("No charts were generated for this document.")
    else:
        st.caption(
            f"{len(chart_paths)} charts were generated. Tick the ones you want — deselect any that are redundant or irrelevant."
        )
        selected = st.session_state.selected_charts
        if selected is None:
            selected = list(range(len(chart_paths)))
        new_selected: List[int] = []
        n_cols = 3
        idx = 0
        for row_charts in [chart_paths[i : i + n_cols] for i in range(0, len(chart_paths), n_cols)]:
            cols = st.columns(n_cols)
            for col, chart in zip(cols, row_charts):
                with col:
                    with st.container():
                        st.image(chart["path"], use_container_width=True)
                        if st.checkbox(
                            chart.get("title", f"Chart {idx + 1}"),
                            value=(idx in selected),
                            key=f"chart_sel_{idx}",
                        ):
                            new_selected.append(idx)
                        if chart.get("insight"):
                            st.caption(chart["insight"])
                idx += 1
        st.session_state.selected_charts = new_selected

        if st.button("🔄 Rebuild PPT with Selected Charts", use_container_width=True):
            with st.spinner("Rebuilding presentation with selected charts"):
                filtered = copy.deepcopy(analysis)
                if not new_selected:
                    st.warning("Select at least one chart before rebuilding the PPT.")
                    st.stop()
                filtered["chart_paths"] = [chart_paths[i] for i in sorted(new_selected)]
                filtered["all_chart_paths"] = chart_paths
                filtered["selected_chart_indices"] = sorted(new_selected)
                filtered.pop("_perf_chart_cursor", None)
                filtered.pop("_grid_chart_cursor", None)
                design_spec = create_design_spec(filtered, storyboard)
                design_spec["document_type"] = analysis.get("document_type", "")
                design_spec["title"] = analysis.get("title", "")
                design_spec["audience"] = analysis.get("audience", "")
                theme_spec = create_theme_spec(design_spec)
                ppt_path = create_ppt_from_pipeline(filtered, storyboard, design_spec, theme_spec)

                update_payload = {
                    "analysis": filtered,
                    "storyboard": storyboard,
                    "design_spec": design_spec,
                    "theme_spec": theme_spec,
                    "ppt_path": ppt_path,
                }

                st.session_state.pipeline_result.update(update_payload)
                st.session_state.final_ppt_path = st.session_state.pipeline_result["ppt_path"]
            st.success(f"✅ Rebuilt with {len(new_selected)} selected chart(s). Final PPT updated.")
            st.rerun()

    # ── Download ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📥 Download Your Presentation")
    ppt_to_download = st.session_state.final_ppt_path or result.get("ppt_path")
    if ppt_to_download and os.path.exists(ppt_to_download):
        dl_col, clear_col, meta_col = st.columns([1.05, 1.05, 2.4])
        with dl_col:
            with open(ppt_to_download, "rb") as f:
                st.download_button(
                    label="📥 Download PPT",
                    data=f,
                    file_name="agentic_document_intelligence_studio.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                    type="primary",
                )
        with clear_col:
            if st.button("🗑️ Clear", key="clear_after_download", use_container_width=True):
                reset_app_state()
                st.rerun()
        with meta_col:
            st.caption(f"File size: {os.path.getsize(ppt_to_download) / 1024:.0f} KB")

    st.caption("Agentic Document Intelligence Studio · Powered by Qwen 3 on the AMD ROCm Platform with vLLM")
