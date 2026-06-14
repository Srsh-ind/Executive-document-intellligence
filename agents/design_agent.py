import json
import random
import requests

from agents.json_utils import extract_json


VLLM_URL = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2-7B-Instruct"


THEME_CATEGORIES = {
    "corporate": [
        "consulting_blue",
        "minimal_white",
        "slate_cyan",
        "charcoal_white"
    ],
    "boardroom": [
        "boardroom_dark",
        "navy_gold",
        "black_gold",
        "luxury_dark"
    ],
    "growth": [
        "emerald_growth",
        "teal_clean",
        "orange_black",
        "warm_corporate"
    ],
    "modern": [
        "purple_modern",
        "midnight_indigo",
        "gradient_neon",
        "glassmorphism"
    ],
    "health_public": [
        "healthcare_light",
        "soft_green",
        "sandstone",
        "calm_blue"
    ]
}


SHAPE_FAMILIES = {
    "geometric": [
        "quarter_circle",
        "half_circle",
        "circle_orbits",
        "large_circle_cutout"
    ],
    "editorial": [
        "large_side_panel",
        "full_bleed_banner",
        "vertical_band",
        "corner_accent"
    ],
    "dashboard": [
        "modular_grid",
        "metric_strip",
        "sidebar_metrics",
        "kpi_ribbon"
    ],
    "cards": [
        "floating_cards",
        "glass_cards",
        "stacked_cards",
        "offset_cards"
    ],
    "motion": [
        "diagonal_panels",
        "curved_wave",
        "roadmap_curve",
        "timeline_dots"
    ],
    "texture": [
        "gradient_mesh",
        "dot_pattern",
        "hex_pattern",
        "organic_blob"
    ]
}


SUPPORTED_CHART_STYLES = [
    "clean_executive",
    "minimal_dashboard",
    "bold_consulting",
    "dark_analytics",
    "soft_corporate",
    "investor_style"
]


SUPPORTED_PHOTO_STYLES = [
    "none",
    "abstract_business",
    "industry_context",
    "editorial",
    "background_texture"
]


SUPPORTED_ICON_STYLES = [
    "none",
    "line_icons",
    "filled_icons",
    "minimal_symbols",
    "duotone_icons"
]


SUPPORTED_DENSITY = ["low", "medium", "high"]


def call_llm(prompt, max_tokens=1600):
    response = requests.post(
        VLLM_URL,
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.55,
            "max_tokens": max_tokens
        },
        timeout=180
    )

    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def flatten(values):
    items = []

    for value in values:
        if isinstance(value, list):
            items.extend(value)
        else:
            items.append(value)

    return items


SUPPORTED_THEMES = flatten(THEME_CATEGORIES.values())
SUPPORTED_SHAPES = flatten(SHAPE_FAMILIES.values())


def safe_list(value):
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def choose_random_theme():
    category = random.choice(list(THEME_CATEGORIES.keys()))
    return random.choice(THEME_CATEGORIES[category])


def choose_random_shape():
    family = random.choice(list(SHAPE_FAMILIES.keys()))
    return random.choice(SHAPE_FAMILIES[family])


def fallback_design(analysis, storyboard):
    deck_theme = choose_random_theme()
    shape_language = choose_random_shape()

    return {
        "deck_theme": deck_theme,
        "theme_category": "auto",
        "shape_family": "auto",
        "shape_language": shape_language,
        "visual_density": "medium",
        "chart_style": "clean_executive",
        "photo_style": "abstract_business",
        "icon_style": "line_icons",
        "design_rationale": "Fallback design selected because the model response was unavailable or invalid.",
        "slides": [
            {
                "title": slide.get("title", ""),
                "visual_treatment": treatment_for_layout(slide.get("layout", "")),
                "accent_style": "subtle",
                "image_query": "",
                "shape_usage": "medium",
                "design_note": "Use clean spacing, strong hierarchy, and minimal text."
            }
            for slide in storyboard
        ]
    }


def treatment_for_layout(layout):
    if layout in ["hero_cover"]:
        return "hero"

    if layout in ["summary_dashboard"]:
        return "summary"

    if layout in [
        "kpi_dashboard",
        "dashboard_grid",
        "performance_dashboard",
        "split_metrics_chart"
    ]:
        return "dashboard"

    if layout in [
        "comparison_dashboard",
        "before_after",
        "donut_insights"
    ]:
        return "chart-heavy"

    if layout in [
        "action_tracker",
        "recommendation_roadmap",
        "roadmap",
        "timeline"
    ]:
        return "roadmap"

    if layout in [
        "risk_dashboard",
        "opportunity_dashboard"
    ]:
        return "risk-board"

    if layout in ["closing_slide"]:
        return "minimal"

    return "card-grid"


def clean_design(design, storyboard):
    if not isinstance(design, dict):
        return fallback_design({}, storyboard)

    theme_category = design.get("theme_category", "")
    if theme_category not in THEME_CATEGORIES:
        theme_category = "auto"

    deck_theme = design.get("deck_theme", "")
    if deck_theme not in SUPPORTED_THEMES:
        deck_theme = choose_random_theme()

    shape_family = design.get("shape_family", "")
    if shape_family not in SHAPE_FAMILIES:
        shape_family = "auto"

    shape_language = design.get("shape_language", "")
    if shape_language not in SUPPORTED_SHAPES:
        shape_language = choose_random_shape()

    visual_density = design.get("visual_density", "medium")
    if visual_density not in SUPPORTED_DENSITY:
        visual_density = "medium"

    chart_style = design.get("chart_style", "clean_executive")
    if chart_style not in SUPPORTED_CHART_STYLES:
        chart_style = "clean_executive"

    photo_style = design.get("photo_style", "abstract_business")
    if photo_style not in SUPPORTED_PHOTO_STYLES:
        photo_style = "abstract_business"

    icon_style = design.get("icon_style", "line_icons")
    if icon_style not in SUPPORTED_ICON_STYLES:
        icon_style = "line_icons"

    raw_slides = safe_list(design.get("slides"))

    slides = []

    for index, storyboard_slide in enumerate(storyboard):
        raw = raw_slides[index] if index < len(raw_slides) and isinstance(raw_slides[index], dict) else {}

        treatment = raw.get("visual_treatment", "")
        if not treatment:
            treatment = treatment_for_layout(storyboard_slide.get("layout", ""))

        accent_style = raw.get("accent_style", "subtle")
        if accent_style not in ["subtle", "bold", "geometric", "editorial", "minimal"]:
            accent_style = "subtle"

        shape_usage = raw.get("shape_usage", "medium")
        if shape_usage not in ["none", "light", "medium", "heavy"]:
            shape_usage = "medium"

        slides.append({
            "title": storyboard_slide.get("title", ""),
            "layout": storyboard_slide.get("layout", ""),
            "story_role": storyboard_slide.get("story_role", ""),
            "visual_treatment": treatment,
            "accent_style": accent_style,
            "image_query": raw.get("image_query", ""),
            "shape_usage": shape_usage,
            "design_note": raw.get("design_note", "")
        })

    return {
        "deck_theme": deck_theme,
        "theme_category": theme_category,
        "shape_family": shape_family,
        "shape_language": shape_language,
        "visual_density": visual_density,
        "chart_style": chart_style,
        "photo_style": photo_style,
        "icon_style": icon_style,
        "design_rationale": design.get("design_rationale", ""),
        "slides": slides
    }


def create_design_spec(analysis, storyboard):
    compact = {
        "title": analysis.get("title", ""),
        "document_type": analysis.get("document_type", ""),
        "audience": analysis.get("audience", ""),
        "core_message": analysis.get("core_message", ""),
        "storyboard": [
            {
                "title": slide.get("title", ""),
                "story_role": slide.get("story_role", ""),
                "layout": slide.get("layout", ""),
                "density": slide.get("density", ""),
                "so_what": slide.get("so_what", "")
            }
            for slide in storyboard
        ]
    }

    prompt = f"""
You are a senior presentation design director for premium decks.

Your job:
Choose the design system for this PowerPoint deck.

You do NOT write content.
You do NOT change titles.
You do NOT invent facts.
You only choose visual direction.

Design standard:
- Looks like a premium consulting, investor, strategy, or executive dashboard deck.
- Does not look like default PowerPoint.
- Does not look AI-generated.
- Uses strong hierarchy, whitespace, grids, shapes, visual rhythm, and restraint.
- Slides should feel varied but consistent.
- Avoid every slide looking like identical cards.
- Use charts, dashboards, visual metaphors, shapes, icons, and photos only when useful.
- Use one consistent deck theme and one consistent shape language.

Theme categories:
{json.dumps(THEME_CATEGORIES, indent=2)}

Shape families:
{json.dumps(SHAPE_FAMILIES, indent=2)}

Chart styles:
{json.dumps(SUPPORTED_CHART_STYLES)}

Photo styles:
{json.dumps(SUPPORTED_PHOTO_STYLES)}

Icon styles:
{json.dumps(SUPPORTED_ICON_STYLES)}

Theme guidance:
- boardroom themes fit finance, strategy, investor, executive, technology, and leadership decks.
- corporate themes fit operations, policy, research, management, and general business decks.
- growth themes fit sales, market, product, transformation, and opportunity decks.
- modern themes fit innovation, AI, technology, product, and future-looking decks.
- health_public themes fit healthcare, public sector, social impact, compliance, and people-focused decks.
These are guidance only. Choose based on tone and audience.

Shape guidance:
- geometric: strong identity, strategy, dashboard, modern executive feel.
- editorial: high-end consulting, summary-heavy, narrative slides.
- dashboard: KPI-heavy, reporting, operational performance.
- cards: modular insight decks and comparison stories.
- motion: transformation, roadmap, sales, growth, future path.
- texture: premium background depth, modern or abstract decks.

Return valid JSON only.

Schema:
{{
  "deck_theme": "",
  "theme_category": "",
  "shape_family": "",
  "shape_language": "",
  "visual_density": "low/medium/high",
  "chart_style": "",
  "photo_style": "",
  "icon_style": "",
  "design_rationale": "",
  "slides": [
    {{
      "title": "",
      "visual_treatment": "hero/summary/dashboard/chart-heavy/card-grid/roadmap/risk-board/minimal",
      "accent_style": "subtle/bold/geometric/editorial/minimal",
      "image_query": "",
      "shape_usage": "none/light/medium/heavy",
      "design_note": ""
    }}
  ]
}}

Rules:
- deck_theme must be one listed in theme categories.
- theme_category must be one of the theme category keys.
- shape_family must be one of the shape family keys.
- shape_language must be one listed under shape families.
- chart_style must be one listed above.
- photo_style must be one listed above.
- icon_style must be one listed above.
- Use one deck_theme for the full deck.
- Use one shape_language for the full deck.
- Do not put photos on every slide.
- image_query should be empty unless a slide benefits from a photo or abstract visual.
- Make slide treatments varied.
- Summary slide should feel editorial and strong.
- KPI/dashboard slides should feel structured and data-rich.
- Recommendation/action slides should feel decisive and structured.
- Closing slide should be minimal.
- Do not change slide titles.
- Do not invent slide content.

Input:
{json.dumps(compact, indent=2)}
"""

    try:
        output = call_llm(prompt)
        parsed = extract_json(output)

        if not parsed:
            return fallback_design(analysis, storyboard)

        return clean_design(parsed, storyboard)

    except Exception:
        return fallback_design(analysis, storyboard)