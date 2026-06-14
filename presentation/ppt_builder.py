import os
from pptx import Presentation
from pptx.util import Inches

from agents.storyboard_agent import build_storyboard
from agents.design_agent import create_design_spec
from agents.storyboard_normalizer import normalize_storyboard
from agents.chart_agent import create_visual_assets

from presentation.theme_engine import create_theme_spec
from presentation.layout_library import LAYOUT_RENDERERS


def storyboard_has_chart_slide(storyboard):
    chart_layouts = {
        "performance_dashboard",
        "split_metrics_chart",
        "comparison_dashboard"
    }

    return any(
        slide.get("layout") in chart_layouts
        for slide in storyboard
    )


def build_chart_slide_from_analysis(analysis):
    charts = analysis.get("chart_paths", []) or []
    chart_titles = [chart.get("title", "Chart") for chart in charts[:4]]

    return {
        "layout": "performance_dashboard",
        "title": "Performance Trends",
        "headline": " | ".join(chart_titles[:2]) if chart_titles else "Quantitative trends",
        "message": "Charts summarize the strongest quantitative signals extracted from the document.",
        "story_role": "performance",
        "cards": [],
        "bullets": chart_titles,
        "blocks": [],
        "so_what": "The chart trends highlight the areas improving and the areas requiring management attention."
    }

def create_ppt_from_pipeline(analysis, storyboard, design_spec, theme_spec):
    os.makedirs("outputs", exist_ok=True)

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    page = 1

    if analysis.get("chart_paths") and not storyboard_has_chart_slide(storyboard):
        storyboard.insert(1, build_chart_slide_from_analysis(analysis))

    for slide_data in storyboard:
        layout = slide_data.get("layout", "insight_dashboard")
        renderer = LAYOUT_RENDERERS.get(layout, LAYOUT_RENDERERS["insight_dashboard"])

        renderer(
            prs,
            slide_data,
            analysis,
            theme_spec,
            page
        )

        page += 1

    ppt_file = "outputs/executive_insight_presentation.pptx"
    prs.save(ppt_file)

    return ppt_file


def create_ppt(analysis):
    analysis = create_visual_assets(analysis)

    storyboard = normalize_storyboard(build_storyboard(analysis))
    if analysis.get("chart_paths") and not storyboard_has_chart_slide(storyboard):
        storyboard.insert(1, build_chart_slide_from_analysis(analysis))
    design_spec = create_design_spec(analysis, storyboard)
    theme_spec = create_theme_spec(design_spec)

    return create_ppt_from_pipeline(
        analysis=analysis,
        storyboard=storyboard,
        design_spec=design_spec,
        theme_spec=theme_spec
    )