import random


THEMES = {

    "boardroom_dark": {
        "background": "0F172A",
        "surface": "1E293B",
        "primary": "3B82F6",
        "secondary": "38BDF8",
        "accent": "F59E0B",
        "success": "10B981",
        "danger": "EF4444",
        "text": "FFFFFF",
        "subtext": "CBD5E1",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.15,
        "shadow": True,
        "gradient": False
    },

    "consulting_blue": {
        "background": "FFFFFF",
        "surface": "F8FAFC",
        "primary": "1D4ED8",
        "secondary": "60A5FA",
        "accent": "F97316",
        "success": "16A34A",
        "danger": "DC2626",
        "text": "111827",
        "subtext": "6B7280",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.12,
        "shadow": True,
        "gradient": False
    },

    "minimal_white": {
        "background": "FFFFFF",
        "surface": "FFFFFF",
        "primary": "111827",
        "secondary": "6B7280",
        "accent": "2563EB",
        "success": "22C55E",
        "danger": "EF4444",
        "text": "111827",
        "subtext": "64748B",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.05,
        "shadow": False,
        "gradient": False
    },

    "emerald_growth": {
        "background": "F0FDF4",
        "surface": "FFFFFF",
        "primary": "10B981",
        "secondary": "34D399",
        "accent": "0EA5E9",
        "success": "22C55E",
        "danger": "EF4444",
        "text": "14532D",
        "subtext": "4B5563",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.18,
        "shadow": True,
        "gradient": True
    },

    "navy_gold": {
        "background": "111827",
        "surface": "1F2937",
        "primary": "D4AF37",
        "secondary": "FCD34D",
        "accent": "60A5FA",
        "success": "10B981",
        "danger": "EF4444",
        "text": "FFFFFF",
        "subtext": "D1D5DB",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.12,
        "shadow": True,
        "gradient": True
    },

    "slate_cyan": {
        "background": "FFFFFF",
        "surface": "F1F5F9",
        "primary": "0F172A",
        "secondary": "06B6D4",
        "accent": "0EA5E9",
        "success": "16A34A",
        "danger": "DC2626",
        "text": "0F172A",
        "subtext": "475569",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.1,
        "shadow": True,
        "gradient": False
    },

    "charcoal_white": {
        "background": "FFFFFF",
        "surface": "F4F4F5",
        "primary": "27272A",
        "secondary": "71717A",
        "accent": "2563EB",
        "success": "22C55E",
        "danger": "DC2626",
        "text": "18181B",
        "subtext": "52525B",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.06,
        "shadow": False,
        "gradient": False
    },

    "black_gold": {
        "background": "0A0A0A",
        "surface": "1A1A1A",
        "primary": "D4AF37",
        "secondary": "F5D061",
        "accent": "E8C766",
        "success": "22C55E",
        "danger": "EF4444",
        "text": "FFFFFF",
        "subtext": "C9C9C9",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.06,
        "shadow": True,
        "gradient": False
    },

    "luxury_dark": {
        "background": "1C1C2B",
        "surface": "2A2A3D",
        "primary": "C9A646",
        "secondary": "8E8FFA",
        "accent": "F4D58D",
        "success": "4ADE80",
        "danger": "F87171",
        "text": "F5F5F5",
        "subtext": "B8B8CC",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.14,
        "shadow": True,
        "gradient": True
    },

    "teal_clean": {
        "background": "F0FDFA",
        "surface": "FFFFFF",
        "primary": "0D9488",
        "secondary": "2DD4BF",
        "accent": "F59E0B",
        "success": "22C55E",
        "danger": "EF4444",
        "text": "134E4A",
        "subtext": "475569",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.14,
        "shadow": True,
        "gradient": False
    },

    "orange_black": {
        "background": "111111",
        "surface": "1F1F1F",
        "primary": "F97316",
        "secondary": "FB923C",
        "accent": "FACC15",
        "success": "22C55E",
        "danger": "EF4444",
        "text": "FFFFFF",
        "subtext": "D4D4D4",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.08,
        "shadow": True,
        "gradient": False
    },

    "warm_corporate": {
        "background": "FFF7ED",
        "surface": "FFFFFF",
        "primary": "C2410C",
        "secondary": "FB923C",
        "accent": "1D4ED8",
        "success": "16A34A",
        "danger": "DC2626",
        "text": "451A03",
        "subtext": "78716C",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.16,
        "shadow": True,
        "gradient": False
    },

    "purple_modern": {
        "background": "F5F3FF",
        "surface": "FFFFFF",
        "primary": "7C3AED",
        "secondary": "A78BFA",
        "accent": "EC4899",
        "success": "22C55E",
        "danger": "EF4444",
        "text": "2E1065",
        "subtext": "6D28D9",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.18,
        "shadow": True,
        "gradient": True
    },

    "midnight_indigo": {
        "background": "0B1026",
        "surface": "1A2150",
        "primary": "6366F1",
        "secondary": "818CF8",
        "accent": "22D3EE",
        "success": "34D399",
        "danger": "F87171",
        "text": "FFFFFF",
        "subtext": "C7D2FE",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.16,
        "shadow": True,
        "gradient": True
    },

    "gradient_neon": {
        "background": "10001A",
        "surface": "1F0033",
        "primary": "A855F7",
        "secondary": "EC4899",
        "accent": "22D3EE",
        "success": "4ADE80",
        "danger": "F87171",
        "text": "FFFFFF",
        "subtext": "E9D5FF",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.2,
        "shadow": True,
        "gradient": True
    },

    "glassmorphism": {
        "background": "EFF6FF",
        "surface": "FFFFFF",
        "primary": "3B82F6",
        "secondary": "93C5FD",
        "accent": "8B5CF6",
        "success": "22C55E",
        "danger": "EF4444",
        "text": "1E293B",
        "subtext": "64748B",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.22,
        "shadow": True,
        "gradient": True
    },

    "healthcare_light": {
        "background": "F0F9FF",
        "surface": "FFFFFF",
        "primary": "0284C7",
        "secondary": "38BDF8",
        "accent": "14B8A6",
        "success": "22C55E",
        "danger": "EF4444",
        "text": "0C4A6E",
        "subtext": "475569",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.16,
        "shadow": True,
        "gradient": False
    },

    "soft_green": {
        "background": "F0FDF4",
        "surface": "FFFFFF",
        "primary": "15803D",
        "secondary": "4ADE80",
        "accent": "0D9488",
        "success": "22C55E",
        "danger": "EF4444",
        "text": "14532D",
        "subtext": "4B5563",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.18,
        "shadow": True,
        "gradient": False
    },

    "sandstone": {
        "background": "FAF7F2",
        "surface": "FFFFFF",
        "primary": "92400E",
        "secondary": "D97706",
        "accent": "0D9488",
        "success": "16A34A",
        "danger": "DC2626",
        "text": "44403C",
        "subtext": "78716C",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.14,
        "shadow": False,
        "gradient": False
    },

    "calm_blue": {
        "background": "F8FAFC",
        "surface": "FFFFFF",
        "primary": "2563EB",
        "secondary": "93C5FD",
        "accent": "F472B6",
        "success": "22C55E",
        "danger": "EF4444",
        "text": "1E3A8A",
        "subtext": "64748B",

        "font_title": "Aptos Display",
        "font_body": "Aptos",

        "border_radius": 0.16,
        "shadow": False,
        "gradient": False
    }

}


SHAPE_FAMILIES = {

    "modular_grid": {

        "card_radius": 0.15,
        "card_shadow": True,
        "header_band": True,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "quarter_circle": {

        "card_radius": 0.18,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": True,
        "circle_cutout": True,
        "wave": False
    },

    "half_circle": {

        "card_radius": 0.16,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": True,
        "circle_cutout": True,
        "wave": False
    },

    "circle_orbits": {

        "card_radius": 0.2,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": True,
        "circle_cutout": True,
        "wave": False
    },

    "large_circle_cutout": {

        "card_radius": 0.2,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": True,
        "circle_cutout": True,
        "wave": False
    },

    "large_side_panel": {

        "card_radius": 0.08,
        "card_shadow": False,
        "header_band": True,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "full_bleed_banner": {

        "card_radius": 0.08,
        "card_shadow": False,
        "header_band": True,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "vertical_band": {

        "card_radius": 0.1,
        "card_shadow": False,
        "header_band": True,
        "corner_shape": True,
        "circle_cutout": False,
        "wave": False
    },

    "corner_accent": {

        "card_radius": 0.12,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": True,
        "circle_cutout": False,
        "wave": False
    },

    "metric_strip": {

        "card_radius": 0.12,
        "card_shadow": True,
        "header_band": True,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "sidebar_metrics": {

        "card_radius": 0.12,
        "card_shadow": True,
        "header_band": True,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "kpi_ribbon": {

        "card_radius": 0.14,
        "card_shadow": True,
        "header_band": True,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "curved_wave": {

        "card_radius": 0.18,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": True
    },

    "floating_cards": {

        "card_radius": 0.22,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "glass_cards": {

        "card_radius": 0.24,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "stacked_cards": {

        "card_radius": 0.2,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "offset_cards": {

        "card_radius": 0.2,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "diagonal_panels": {

        "card_radius": 0.1,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": True,
        "circle_cutout": False,
        "wave": False
    },

    "roadmap_curve": {

        "card_radius": 0.16,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": True
    },

    "timeline_dots": {

        "card_radius": 0.16,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "gradient_mesh": {

        "card_radius": 0.18,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "dot_pattern": {

        "card_radius": 0.14,
        "card_shadow": False,
        "header_band": False,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "hex_pattern": {

        "card_radius": 0.14,
        "card_shadow": False,
        "header_band": False,
        "corner_shape": False,
        "circle_cutout": False,
        "wave": False
    },

    "organic_blob": {

        "card_radius": 0.22,
        "card_shadow": True,
        "header_band": False,
        "corner_shape": True,
        "circle_cutout": True,
        "wave": True
    }

}


CHART_STYLES = {

    "minimal_dashboard": {
        "show_grid": False,
        "show_legend": True,
        "line_width": 3,
        "marker_size": 7
    },

    "clean_executive": {
        "show_grid": True,
        "show_legend": True,
        "line_width": 2,
        "marker_size": 5
    },

    "bold_consulting": {
        "show_grid": False,
        "show_legend": False,
        "line_width": 4,
        "marker_size": 8
    },

    "dark_analytics": {
        "show_grid": True,
        "show_legend": True,
        "line_width": 3,
        "marker_size": 6
    },

    "soft_corporate": {
        "show_grid": True,
        "show_legend": True,
        "line_width": 2,
        "marker_size": 5
    },

    "investor_style": {
        "show_grid": False,
        "show_legend": True,
        "line_width": 3,
        "marker_size": 6
    }

}


ICON_STYLES = {

    "line_icons": {
        "fill": False
    },

    "filled_icons": {
        "fill": True
    },

    "minimal_symbols": {
        "fill": False
    }

}


# ── Document-type → theme mapping ────────────────────────────────────────────
# Maps document/audience keywords to preferred theme names.
# This is used when the LLM always picks the same theme (e.g. boardroom_dark)
# or when the LLM is offline.
_DOCTYPE_THEME_MAP = {
    "earnings":          "consulting_blue",
    "transcript":        "slate_cyan",
    "financial":         "consulting_blue",
    "investor":          "navy_gold",
    "strategy":          "boardroom_dark",
    "annual report":     "charcoal_white",
    "healthcare":        "healthcare_light",
    "health":            "healthcare_light",
    "public sector":     "calm_blue",
    "government":        "calm_blue",
    "technology":        "midnight_indigo",
    "ai":                "purple_modern",
    "innovation":        "purple_modern",
    "sales":             "emerald_growth",
    "marketing":         "warm_corporate",
    "telecom":           "slate_cyan",
    "manufacturing":     "charcoal_white",
    "pharma":            "healthcare_light",
    "banking":           "navy_gold",
    "insurance":         "consulting_blue",
    "retail":            "orange_black",
    "sustainability":    "emerald_growth",
    "startup":           "gradient_neon",
}

# Shape language key aliases — design_agent uses different names than theme_engine
_SHAPE_KEY_ALIASES = {
    # design_agent name → theme_engine SHAPE_FAMILIES key
    "quarter_circle":       "quarter_circle",
    "half_circle":          "half_circle",
    "circle_orbits":        "circle_orbits",
    "large_circle_cutout":  "large_circle_cutout",
    "large_side_panel":     "large_side_panel",
    "full_bleed_banner":    "full_bleed_banner",
    "vertical_band":        "vertical_band",
    "corner_accent":        "corner_accent",
    "modular_grid":         "modular_grid",
    "metric_strip":         "metric_strip",
    "sidebar_metrics":      "sidebar_metrics",
    "kpi_ribbon":           "kpi_ribbon",
    "floating_cards":       "floating_cards",
    "glass_cards":          "glass_cards",
    "stacked_cards":        "stacked_cards",
    "offset_cards":         "offset_cards",
    "diagonal_panels":      "diagonal_panels",
    "curved_wave":          "curved_wave",
    "roadmap_curve":        "roadmap_curve",
    "timeline_dots":        "timeline_dots",
    "gradient_mesh":        "gradient_mesh",
    "dot_pattern":          "dot_pattern",
    "hex_pattern":          "hex_pattern",
    "organic_blob":         "organic_blob",
    # generic fallback aliases from design_agent
    "geometric":            "quarter_circle",
    "editorial":            "large_side_panel",
    "dashboard":            "modular_grid",
    "cards":                "floating_cards",
    "motion":               "diagonal_panels",
    "texture":              "gradient_mesh",
}

def _infer_theme_from_analysis(design_spec):
    """
    Pick a theme based on the document title/type/audience when the LLM
    chose a generic or repeated theme.
    """
    text_to_scan = " ".join([
        str(design_spec.get("title", "")),
        str(design_spec.get("document_type", "")),
        str(design_spec.get("audience", "")),
        str(design_spec.get("deck_theme", "")),
    ]).lower()

    for keyword, theme in _DOCTYPE_THEME_MAP.items():
        if keyword in text_to_scan and theme in THEMES:
            return theme

    return None


def _resolve_shape(shape_name):
    """Resolve shape name through aliases, return valid SHAPE_FAMILIES key."""
    if shape_name in SHAPE_FAMILIES:
        return shape_name
    aliased = _SHAPE_KEY_ALIASES.get(shape_name)
    if aliased and aliased in SHAPE_FAMILIES:
        return aliased
    return None


# Themes that the LLM defaults to too often — if chosen, try context-based override
_OVERUSED_THEMES = {"boardroom_dark"}


def create_theme_spec(design_spec):

    # ── 1. Resolve theme name ──────────────────────────────────────────────────
    theme_name = design_spec.get("deck_theme", "")

    # If LLM picked an overused/generic theme, try to infer a better one
    if theme_name in _OVERUSED_THEMES:
        inferred = _infer_theme_from_analysis(design_spec)
        if inferred:
            theme_name = inferred

    # Validate
    if theme_name not in THEMES:
        inferred = _infer_theme_from_analysis(design_spec)
        theme_name = inferred if inferred else random.choice([
            "consulting_blue", "slate_cyan", "navy_gold",
            "charcoal_white", "midnight_indigo", "emerald_growth"
        ])

    # ── 2. Resolve shape family ────────────────────────────────────────────────
    raw_shape  = design_spec.get("shape_language", "")
    shape_name = _resolve_shape(raw_shape)
    if shape_name is None:
        # Pick a shape family that suits the theme
        dark_themes   = {"boardroom_dark", "navy_gold", "black_gold", "midnight_indigo",
                         "luxury_dark", "gradient_neon"}
        light_themes  = {"minimal_white", "charcoal_white", "sandstone", "calm_blue",
                         "soft_green", "healthcare_light"}
        if theme_name in dark_themes:
            shape_name = random.choice(["quarter_circle", "large_circle_cutout", "circle_orbits"])
        elif theme_name in light_themes:
            shape_name = random.choice(["modular_grid", "metric_strip", "floating_cards"])
        else:
            shape_name = random.choice(["modular_grid", "quarter_circle", "floating_cards",
                                        "large_side_panel", "diagonal_panels"])

    # ── 3. Chart style ─────────────────────────────────────────────────────────
    chart_style_name = design_spec.get("chart_style", "")
    if chart_style_name not in CHART_STYLES:
        dark_themes = {"boardroom_dark", "navy_gold", "black_gold", "midnight_indigo",
                       "luxury_dark", "gradient_neon", "glassmorphism"}
        chart_style_name = "dark_analytics" if theme_name in dark_themes else "clean_executive"

    # ── 4. Icon style ──────────────────────────────────────────────────────────
    icon_style_name = design_spec.get("icon_style", "line_icons")
    if icon_style_name not in ICON_STYLES:
        icon_style_name = "line_icons"

    return {

        "theme_name": theme_name,

        "colors": THEMES[theme_name],

        "shapes": SHAPE_FAMILIES[shape_name],

        "charts": CHART_STYLES[chart_style_name],

        "icons": ICON_STYLES[icon_style_name],

        "density": design_spec.get("visual_density", "medium"),

        "photo_style": design_spec.get(
            "photo_style",
            "abstract_business"
        )
    }