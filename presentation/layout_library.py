from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches

from presentation.widgets import (
    add_background,
    add_title,
    add_subtitle,
    add_textbox,
    add_card,
    add_kpi_card,
    add_metric_strip,
    add_status_card,
    add_bullet_list,
    add_footer,
    add_progress_bar,
    rgb,
)

def get_chart_for_slide(analysis, index=0):
    charts = analysis.get("chart_paths", []) or []
    if len(charts) > index:
        return charts[index]
    return None


def add_chart_image(slide, chart, x, y, w):
    if not chart:
        return False

    path = chart.get("path")
    if not path:
        return False

    try:
        slide.shapes.add_picture(
            path,
            Inches(x),
            Inches(y),
            width=Inches(w)
        )
        return True
    except Exception:
        return False

def get_cards(slide):
    return slide.get("cards", []) or []


def get_bullets(slide):
    return slide.get("bullets", []) or []


def get_blocks(slide):
    return slide.get("blocks", []) or []


def card_text(card):
    if isinstance(card, dict):
        label = (
            card.get("label")
            or card.get("name")
            or card.get("priority")
            or card.get("title")
            or card.get("risk")
            or card.get("opportunity")
            or "Insight"
        )

        value = (
            card.get("value")
            or card.get("recommendation")
            or card.get("action")
            or card.get("risk")
            or card.get("opportunity")
            or card.get("item")
            or ""
        )

        note = (
            card.get("note")
            or card.get("interpretation")
            or card.get("description")
            or card.get("business_impact")
            or card.get("impact")
            or ""
        )

        return str(label), str(value), str(note)

    return "Insight", str(card), ""


def add_decorative_shape(slide, theme, x=10.8, y=-0.35):
    colors = theme["colors"]

    shape = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(x),
        Inches(y),
        Inches(2.5),
        Inches(2.5)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(colors["accent"])
    shape.line.color.rgb = rgb(colors["accent"])
    return shape


def render_summary_dashboard(prs, slide_data, analysis, theme, page):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, theme)
    add_decorative_shape(slide, theme)

    add_title(slide, slide_data.get("title", "Summary"), theme)
    add_subtitle(slide, slide_data.get("headline") or slide_data.get("message", ""), theme)

    add_metric_strip(slide, get_cards(slide_data), theme, x=0.65, y=1.45, w=12.0, h=1.15)

    blocks = get_blocks(slide_data)
    if not blocks:
        blocks = [
            {"label": "Key Message", "items": [slide_data.get("message", "")]},
            {"label": "So What", "items": [slide_data.get("so_what", "")]},
            {"label": "Next", "items": get_bullets(slide_data)}
        ]

    positions = [(0.65, 3.0), (4.75, 3.0), (8.85, 3.0)]

    for i, block in enumerate(blocks[:3]):
        x, y = positions[i]
        add_card(
            slide,
            block.get("label", "Section"),
            "\n".join([str(item) for item in block.get("items", [])[:4]]),
            theme,
            x,
            y,
            3.65,
            2.75
        )

    add_footer(slide, theme, page)


def render_kpi_dashboard(prs, slide_data, analysis, theme, page):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, theme)

    add_title(slide, slide_data.get("title", "KPI Dashboard"), theme)
    add_subtitle(slide, slide_data.get("headline") or slide_data.get("message", ""), theme)

    cards = get_cards(slide_data)
    positions = [
        (0.7, 1.55), (4.7, 1.55), (8.7, 1.55),
        (0.7, 3.55), (4.7, 3.55), (8.7, 3.55)
    ]

    for i, card in enumerate(cards[:6]):
        label, value, note = card_text(card)
        x, y = positions[i]
        add_kpi_card(slide, label, value, note, theme, x, y, 3.55, 1.55)

    add_footer(slide, theme, page)


def render_insight_dashboard(prs, slide_data, analysis, theme, page):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, theme)

    add_title(slide, slide_data.get("title", "Insights"), theme)
    add_subtitle(slide, slide_data.get("headline") or slide_data.get("message", ""), theme)

    if slide_data.get("layout") in ["performance_dashboard", "split_metrics_chart"]:
        charts = analysis.get("chart_paths", []) or []

        if len(charts) >= 4:
        # if charts:
            positions = [
                (0.65, 1.35, 5.9),
                (6.75, 1.35, 5.9),
                (0.65, 4.05, 5.9),
                (6.75, 4.05, 5.9),
            ]
    
            for i, chart in enumerate(charts[:4]):
                x, y, w = positions[i]
                add_chart_image(slide, chart, x, y, w)
    
            add_footer(slide, theme, page)
            return

        elif len(charts) >= 2:
            positions = [
                (0.75, 1.6, 5.8),
                (6.85, 1.6, 5.8),
            ]
    
            for i, chart in enumerate(charts[:2]):
                x, y, w = positions[i]
                add_chart_image(slide, chart, x, y, w)
    
            add_card(
                slide,
                "Interpretation",
                slide_data.get("so_what") or slide_data.get("message", ""),
                theme,
                0.9,
                5.2,
                11.5,
                1.05
            )
    
            add_footer(slide, theme, page)
            return

        elif len(charts) == 1:
            add_chart_image(slide, charts[0], 0.8, 1.6, 7.2)
    
            add_card(
                slide,
                "Interpretation",
                slide_data.get("so_what") or slide_data.get("message", ""),
                theme,
                8.4,
                1.6,
                4.0,
                3.8
            )
    
            add_footer(slide, theme, page)
            return

    bullets = get_bullets(slide_data)
    cards = get_cards(slide_data)

    if not cards and not bullets:
        role = slide_data.get("story_role", "")

        if "risk" in role:
            cards = analysis.get("risks", [])[:6]
        elif "opportun" in role:
            cards = analysis.get("opportunities", [])[:6]
        elif "action" in role or "recommend" in role:
            cards = analysis.get("recommendations", [])[:6]
        elif "insight" in role:
            bullets = analysis.get("insights", [])[:6] or analysis.get("key_findings", [])[:6]
        else:
            bullets = analysis.get("key_findings", [])[:6]

    if cards:
        positions = [
            (0.7, 1.65), (4.7, 1.65), (8.7, 1.65),
            (0.7, 3.75), (4.7, 3.75), (8.7, 3.75)
        ]

        for i, card in enumerate(cards[:6]):
            label, value, note = card_text(card)
            add_card(slide, label, f"{value}\n{note}", theme, positions[i][0], positions[i][1], 3.55, 1.65)
    else:
        positions = [(0.85, 1.75), (4.85, 1.75), (8.85, 1.75)]
        for i, item in enumerate(bullets[:3]):
            add_card(slide, f"Insight {i+1}", str(item), theme, positions[i][0], positions[i][1], 3.45, 3.5)

    add_footer(slide, theme, page)


def render_risk_dashboard(prs, slide_data, analysis, theme, page):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, theme)

    add_title(slide, slide_data.get("title", "Risks"), theme)
    add_subtitle(slide, slide_data.get("headline") or slide_data.get("message", ""), theme)

    cards = get_cards(slide_data)

    if not cards:
        cards = analysis.get("risks", [])[:3] + analysis.get("opportunities", [])[:3]
    
    positions = [
        (0.75, 1.6), (4.75, 1.6), (8.75, 1.6),
        (0.75, 3.8), (4.75, 3.8), (8.75, 3.8)
    ]

    for i, card in enumerate(cards[:6]):
        label, value, note = card_text(card)
        status = "risk" if "risk" in slide_data.get("story_role", "") else "neutral"

        add_status_card(
            slide,
            value or "Risk",
            label,
            note,
            theme,
            positions[i][0],
            positions[i][1],
            3.5,
            1.75,
            status=status
        )

    add_footer(slide, theme, page)


def render_opportunity_dashboard(prs, slide_data, analysis, theme, page):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, theme)

    add_title(slide, slide_data.get("title", "Opportunities"), theme)
    add_subtitle(slide, slide_data.get("headline") or slide_data.get("message", ""), theme)

    cards = get_cards(slide_data)

    if not cards:
        cards = analysis.get("opportunities", [])[:6]

    positions = [
        (0.75, 1.6), (4.75, 1.6), (8.75, 1.6),
        (0.75, 3.8), (4.75, 3.8), (8.75, 3.8)
    ]

    for i, card in enumerate(cards[:6]):
        label, value, note = card_text(card)

        add_status_card(
            slide,
            value or "Opportunity",
            label,
            note,
            theme,
            positions[i][0],
            positions[i][1],
            3.5,
            1.75,
            status="success"
        )

    add_footer(slide, theme, page)


def render_action_tracker(prs, slide_data, analysis, theme, page):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, theme)

    add_title(slide, slide_data.get("title", "Actions"), theme)
    add_subtitle(slide, slide_data.get("headline") or slide_data.get("message", ""), theme)
    cards = get_cards(slide_data)

    if not cards:
        cards = analysis.get("recommendations", [])[:4]

    y = 1.55
    for i, card in enumerate(cards[:4]):
        label, value, note = card_text(card)

        add_status_card(
            slide,
            label,
            value,
            note,
            theme,
            0.85,
            y,
            11.65,
            1.05,
            status="action"
        )

        y += 1.25

    add_footer(slide, theme, page)


def render_roadmap(prs, slide_data, analysis, theme, page):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, theme)

    add_title(slide, slide_data.get("title", "Roadmap"), theme)
    add_subtitle(slide, slide_data.get("headline") or slide_data.get("message", ""), theme)

    colors = theme["colors"]

    # horizontal line
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(1.2),
        Inches(3.1),
        Inches(10.7),
        Inches(0.05)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = rgb(colors["accent"])
    line.line.color.rgb = rgb(colors["accent"])

    steps = get_cards(slide_data) or get_bullets(slide_data)

    if not steps:
        steps = analysis.get("recommendations", [])[:4]

    
    if not steps:
        steps = [
            "Near-term priorities",
            "Execution focus",
            "Scale initiatives",
            "Measure impact"
        ]

    x_positions = [1.0, 4.1, 7.2, 10.3]

    for i, step in enumerate(steps[:4]):
        x = x_positions[i]

        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(x),
            Inches(2.75),
            Inches(0.7),
            Inches(0.7)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = rgb(colors["accent"])
        circle.line.color.rgb = rgb(colors["accent"])

        add_textbox(slide, str(i + 1), x + 0.24, 2.88, 0.3, 0.2, 12, True, "FFFFFF")

        if isinstance(step, dict):
            title = step.get("label") or step.get("priority") or f"Step {i+1}"
            body = step.get("value") or step.get("recommendation") or step.get("note", "")
        else:
            title = f"Step {i+1}"
            body = str(step)

        add_card(slide, title, body, theme, x - 0.4, 3.75, 2.4, 1.45)

    add_footer(slide, theme, page)


def render_comparison_dashboard(prs, slide_data, analysis, theme, page):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, theme)

    add_title(slide, slide_data.get("title", "Comparison"), theme)
    add_subtitle(slide, slide_data.get("headline") or slide_data.get("message", ""), theme)

    cards = get_cards(slide_data)

    if len(cards) >= 2:
        left = cards[0]
        right = cards[1]

        l_label, l_value, l_note = card_text(left)
        r_label, r_value, r_note = card_text(right)

        add_kpi_card(slide, l_label, l_value, l_note, theme, 1.0, 1.8, 5.2, 3.2)
        add_kpi_card(slide, r_label, r_value, r_note, theme, 7.1, 1.8, 5.2, 3.2)
    else:
        # add_bullet_list(slide, get_bullets(slide), theme, 1.0, 1.8, 11.0, 4.0)
        add_bullet_list(slide, get_bullets(slide_data), theme, 1.0, 1.8, 11.0, 4.0)

    add_footer(slide, theme, page)


def render_closing_slide(prs, slide_data, analysis, theme, page):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, theme)
    add_decorative_shape(slide, theme, x=9.8, y=4.8)

    add_textbox(
        slide,
        slide_data.get("headline") or slide_data.get("title", "Conclusion"),
        1.0,
        2.0,
        11.0,
        1.2,
        font_size=30,
        bold=True,
        color=theme["colors"]["text"]
    )

    add_textbox(
        slide,
        slide_data.get("so_what") or slide_data.get("message", ""),
        1.05,
        3.35,
        10.5,
        1.2,
        font_size=16,
        bold=False,
        color=theme["colors"]["subtext"]
    )

    add_footer(slide, theme, page)


LAYOUT_RENDERERS = {
    "summary_dashboard": render_summary_dashboard,
    "kpi_dashboard": render_kpi_dashboard,
    "dashboard_grid": render_kpi_dashboard,
    "performance_dashboard": render_insight_dashboard,
    "split_metrics_chart": render_insight_dashboard,
    "insight_dashboard": render_insight_dashboard,
    "risk_dashboard": render_risk_dashboard,
    "opportunity_dashboard": render_opportunity_dashboard,
    "action_tracker": render_action_tracker,
    "recommendation_roadmap": render_roadmap,
    "roadmap": render_roadmap,
    "timeline": render_roadmap,
    "comparison_dashboard": render_comparison_dashboard,
    "before_after": render_comparison_dashboard,
    "closing_slide": render_closing_slide,
}