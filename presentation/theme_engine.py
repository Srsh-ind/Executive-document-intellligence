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

    "large_side_panel": {

        "card_radius": 0.08,
        "card_shadow": False,
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


def create_theme_spec(design_spec):

    theme_name = design_spec.get("deck_theme")

    if theme_name not in THEMES:
        theme_name = random.choice(list(THEMES.keys()))

    shape_name = design_spec.get("shape_language")

    if shape_name not in SHAPE_FAMILIES:
        shape_name = random.choice(list(SHAPE_FAMILIES.keys()))

    chart_style_name = design_spec.get("chart_style")

    if chart_style_name not in CHART_STYLES:
        chart_style_name = "clean_executive"

    icon_style_name = design_spec.get("icon_style")

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