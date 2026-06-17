import os
from pptx import Presentation
from pptx.util import Inches

from agents.storyboard_agent import build_storyboard
from agents.design_agent import create_design_spec
from agents.storyboard_normalizer import normalize_storyboard
from agents.chart_agent import create_visual_assets

from presentation.theme_engine import create_theme_spec
from presentation.layout_library import LAYOUT_RENDERERS


CHART_LAYOUTS = {
    "performance_dashboard",
    "split_metrics_chart",
    "comparison_dashboard",
    "donut_insights",
    "dashboard_grid",
}


def storyboard_has_chart_slide(storyboard):
    return any(s.get("layout") in CHART_LAYOUTS for s in storyboard)


def count_chart_slides(storyboard):
    return sum(1 for s in storyboard if s.get("layout") in CHART_LAYOUTS)


def inject_chart_slides(storyboard, analysis):
    """
    Ensure chart_paths are distributed across chart-type slides.
    If there are more charts than chart slides, inject extra slides.
    """
    charts = analysis.get("chart_paths", []) or []
    if not charts:
        return storyboard

    # Make sure there is at least one chart slide
    if not storyboard_has_chart_slide(storyboard):
        circular = [c for c in charts if str(c.get("chart_type","")).lower() in ("donut","doughnut","pie")]
        layout = "donut_insights" if len(circular) >= max(len(charts) // 2, 1) else "performance_dashboard"
        chart_slide = {
            "layout": layout,
            "title": "Performance Trends",
            "headline": "Quantitative evidence from the document",
            "message": "Charts summarising key patterns in the data.",
            "story_role": "performance",
            "cards": [], "bullets": [], "blocks": [],
            "so_what": "These patterns guide where management attention is needed.",
        }
        # Insert after summary slide (index 1)
        insert_at = min(1, len(storyboard))
        storyboard = storyboard[:insert_at] + [chart_slide] + storyboard[insert_at:]

    # Add enough chart slides to cover all charts (1 slide per 4 charts)
    chart_slide_count = count_chart_slides(storyboard)
    needed_slides = max(1, (len(charts) + 3) // 4)  # ceil(charts / 4)
    slides_to_add = needed_slides - chart_slide_count

    close_idx = next(
        (i for i, s in enumerate(storyboard) if s.get("layout") == "closing_slide"),
        len(storyboard)
    )

    for extra_n in range(max(0, slides_to_add)):
        extra = {
            "layout": "performance_dashboard",
            "title": f"Data Insights {'II III IV V'.split()[extra_n] if extra_n < 4 else str(extra_n + 2)}",
            "headline": "Further quantitative evidence from the document",
            "message": "Additional charts extracted from the document.",
            "story_role": "trend",
            "cards": [], "bullets": [], "blocks": [],
            "so_what": "These trends provide deeper analytical context.",
        }
        storyboard = storyboard[:close_idx] + [extra] + storyboard[close_idx:]
        close_idx += 1  # keep inserting before closing

    return storyboard


def create_ppt_from_pipeline(analysis, storyboard, design_spec, theme_spec):
    os.makedirs("outputs", exist_ok=True)

    storyboard = inject_chart_slides(storyboard, analysis)
    storyboard = normalize_storyboard(storyboard, analysis=analysis)

    # Reset chart distribution cursors so each run starts fresh
    analysis.pop("_perf_chart_cursor", None)
    analysis.pop("_grid_chart_cursor", None)

    prs = Presentation()
    prs.slide_width  = Inches(13.33)
    prs.slide_height = Inches(7.5)

    page = 1
    for slide_data in storyboard:
        layout   = slide_data.get("layout", "insight_dashboard")
        renderer = LAYOUT_RENDERERS.get(layout, LAYOUT_RENDERERS["insight_dashboard"])
        renderer(prs, slide_data, analysis, theme_spec, page)
        page += 1

    ppt_file = "outputs/executive_insight_presentation.pptx"
    prs.save(ppt_file)
    return ppt_file


def create_ppt(analysis):
    storyboard   = normalize_storyboard(build_storyboard(analysis))
    design_spec  = create_design_spec(analysis, storyboard)
    theme_spec   = create_theme_spec(design_spec)
    analysis     = create_visual_assets(analysis, theme=theme_spec)

    return create_ppt_from_pipeline(
        analysis=analysis,
        storyboard=storyboard,
        design_spec=design_spec,
        theme_spec=theme_spec,
    )