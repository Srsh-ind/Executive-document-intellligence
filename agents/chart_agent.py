import os
import math
import copy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

STANDARD_CHART_FIGSIZE = (8, 4.5)
STANDARD_CHART_DPI = 180


def safe_float(value):
    try:
        if isinstance(value, str):
            value = value.strip()
            # Handle accounting negatives such as $(0.12), (1), or (1.2)%.
            negative = value.startswith("(") and value.endswith(")")
            value = (
                value.replace("$", "")
                    .replace(",", "")
                    .replace("%", "")
                    .replace("(", "")
                    .replace(")", "")
                    .strip()
            )
            multiplier = 1.0
            if value.upper().endswith("M"):
                multiplier = 1e6
                value = value[:-1]
            elif value.upper().endswith("B"):
                multiplier = 1e9
                value = value[:-1]
            elif value.upper().endswith("K"):
                multiplier = 1e3
                value = value[:-1]
            out = float(value) * multiplier
            return -out if negative else out
        out = float(value)
        if not math.isfinite(out):
            return None
        return out
    except Exception:
        return None


def get_chart_data(visual):
    labels, values = [], []
    for row in visual.get("data", []):
        label = str(row.get("label", "")).strip()
        value = safe_float(row.get("value"))
        if label and value is not None:
            labels.append(label)
            values.append(value)
    return labels, values


def hex_to_rgb01(hex_color):
    hex_color = str(hex_color or "").replace("#", "").strip()
    if len(hex_color) != 6:
        hex_color = "1D4ED8"
    return tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))




def _is_percent_visual(visual):
    title = str(visual.get("title", "")).lower()
    return any(k in title for k in ("%", "percent", "percentage", "margin", "rate", "share", "mix", "conversion", "churn", "return"))


def format_value_label(value, visual=None):
    """Compact labels so chart data labels don't overlap or show raw millions."""
    try:
        v = float(value)
    except Exception:
        return str(value)
    if visual is not None and _is_percent_visual(visual) and abs(v) <= 100:
        return f"{v:.1f}%" if abs(v - round(v)) > 0.05 else f"{v:.0f}%"
    av = abs(v)
    if av >= 1_000_000_000:
        return f"{v/1_000_000_000:.1f}B"
    if av >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if av >= 1_000:
        return f"{v/1_000:.1f}K"
    return f"{v:.1f}" if abs(v - round(v)) > 0.05 else f"{v:.0f}"


def get_chart_palette(theme):
    theme  = theme or {}
    colors = theme.get("colors", {}) if isinstance(theme, dict) else {}

    primary    = colors.get("primary",    "1D4ED8")
    secondary  = colors.get("secondary",  "60A5FA")
    accent     = colors.get("accent",     "F97316")
    success    = colors.get("success",    "16A34A")
    danger     = colors.get("danger",     "DC2626")
    background = colors.get("background", "FFFFFF")
    surface    = colors.get("surface",    "F8FAFC")
    text       = colors.get("text",       "111827")
    subtext    = colors.get("subtext",    "6B7280")

    cycle = [primary, accent, secondary, success, danger, subtext,
             "9333EA", "0891B2", "B45309", "065F46"]
    cycle = [hex_to_rgb01(c) for c in cycle]

    return {
        "cycle":      cycle,
        "background": hex_to_rgb01(background),
        "surface":    hex_to_rgb01(surface),
        "text":       hex_to_rgb01(text),
        "subtext":    hex_to_rgb01(subtext),
        "primary":    hex_to_rgb01(primary),
        "accent":     hex_to_rgb01(accent),
    }


def apply_theme_style(fig, ax, palette, chart_settings=None, show_grid=None):
    chart_settings = chart_settings or {}
    fig.patch.set_facecolor(palette["background"])
    ax.set_facecolor(palette["surface"])
    ax.title.set_color(palette["text"])
    ax.xaxis.label.set_color(palette["subtext"])
    ax.yaxis.label.set_color(palette["subtext"])
    ax.tick_params(colors=palette["subtext"])
    for spine in ax.spines.values():
        spine.set_color(palette["subtext"])
        spine.set_alpha(0.20)
    use_grid = chart_settings.get("show_grid", True) if show_grid is None else show_grid
    if use_grid:
        ax.grid(True, axis="y", color=palette["subtext"], alpha=0.12, linewidth=0.7, linestyle="--")
        ax.set_axisbelow(True)
    else:
        ax.grid(False)


def _shorten_labels(labels, max_len=14):
    """Wrap long axis labels without adding ellipsis markers."""
    import textwrap
    out = []
    for label in labels:
        label = str(label or "").strip().replace("…", "")
        label = __import__("re").sub(r"\.{3,}", "", label)
        if len(label) <= max_len:
            out.append(label)
            continue
        parts = textwrap.wrap(label, width=max_len, break_long_words=False)[:2]
        out.append("\n".join(parts) if parts else label[:max_len])
    return out


def create_bar_chart(visual, index, theme=None):
    labels, values = get_chart_data(visual)
    if len(labels) < 2:
        return None

    palette       = get_chart_palette(theme)
    chart_settings = (theme or {}).get("charts", {})
    path          = f"outputs/chart_{index}.png"

    fig, ax = plt.subplots(figsize=STANDARD_CHART_FIGSIZE)
    bar_colors = [palette["cycle"][i % len(palette["cycle"])] for i in range(len(labels))]
    short_labels = _shorten_labels(labels)

    bars = ax.bar(short_labels, values, color=bar_colors, edgecolor="none", width=0.62)

    # Value labels on top of bars
    for bar, val in zip(bars, values):
        h = bar.get_height()
        label_text = format_value_label(val, visual)
        offset = (max(values) - min(values) or max(abs(v) for v in values) or 1) * 0.025
        y = h + offset if h >= 0 else h - offset
        va = "bottom" if h >= 0 else "top"
        ax.text(bar.get_x() + bar.get_width() / 2, y,
                label_text, ha="center", va=va,
                fontsize=8, color=palette["text"], fontweight="bold")

    ax.set_title(visual.get("title", "Comparison"), fontsize=12, fontweight="bold",
                 pad=10, color=palette["text"])
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    ax.tick_params(axis="y", labelsize=8)

    apply_theme_style(fig, ax, palette, chart_settings)
    fig.tight_layout(pad=1.5)
    fig.savefig(path, dpi=STANDARD_CHART_DPI, facecolor=palette["background"])
    plt.close(fig)
    return path


def create_line_chart(visual, index, theme=None):
    labels, values = get_chart_data(visual)
    if len(labels) < 2:
        return None

    palette       = get_chart_palette(theme)
    chart_settings = (theme or {}).get("charts", {})
    path          = f"outputs/chart_{index}.png"

    fig, ax = plt.subplots(figsize=STANDARD_CHART_FIGSIZE)
    line_width  = chart_settings.get("line_width", 2.2)
    marker_size = chart_settings.get("marker_size", 6)

    x_idx = range(len(labels))
    ax.plot(x_idx, values, marker="o", linewidth=line_width, markersize=marker_size,
            color=palette["primary"], markerfacecolor=palette["accent"],
            markeredgecolor=palette["background"], markeredgewidth=1.5)
    ax.fill_between(x_idx, values, alpha=0.08, color=palette["primary"])

    # Data point labels: keep monthly/long series readable by labeling
    # alternating points plus the first and last point.
    for idx, (xi, val) in enumerate(zip(x_idx, values)):
        if len(values) > 8 and idx not in (0, len(values) - 1) and idx % 2 == 1:
            continue
        label_text = format_value_label(val, visual)
        ax.text(xi, val + (max(values) - min(values)) * 0.04,
                label_text, ha="center", va="bottom",
                fontsize=8, color=palette["text"])

    short_labels = _shorten_labels(labels)
    ax.set_xticks(list(x_idx))
    ax.set_xticklabels(short_labels, rotation=30, ha="right", fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title(visual.get("title", "Trend"), fontsize=12, fontweight="bold",
                 pad=10, color=palette["text"])

    apply_theme_style(fig, ax, palette, chart_settings)
    fig.tight_layout(pad=1.5)
    fig.savefig(path, dpi=STANDARD_CHART_DPI, facecolor=palette["background"])
    plt.close(fig)
    return path


def _has_negative_or_zero_issue(values):
    """Return True when values are unsafe for pie/donut charts.

Matplotlib pie/donut cannot handle negative values.  It also behaves badly
with NaN/inf and all-zero/negative totals.  Treat all of those as unsafe so
we can render the same evidence as a bar chart instead of stopping the whole
pipeline.
    """
    try:
        vals = [float(v) for v in values]
        if not vals:
            return True
        if any((not math.isfinite(v)) for v in vals):
            return True
        if any(v < 0 for v in vals):
            return True
        if sum(vals) <= 0:
            return True
        return False
    except Exception:
        return True


def _render_circular_chart(visual, index, theme, donut=False):
    labels, values = get_chart_data(visual)
    if len(labels) < 2 or len(labels) > 8:
        return None

    # Pie/donut charts cannot display negative values.  Some financial bridge
    # and variance charts include negatives, so render those as bar charts
    # instead of crashing with: Wedge sizes 'x' must be non negative values.
    if _has_negative_or_zero_issue(values):
        return create_bar_chart(visual, index, theme)

    palette = get_chart_palette(theme)
    path    = f"outputs/chart_{index}.png"

    fig, ax = plt.subplots(figsize=STANDARD_CHART_FIGSIZE)
    colors  = [palette["cycle"][i % len(palette["cycle"])] for i in range(len(labels))]

    wedge_kwargs   = {"width": 0.42} if donut else {}
    pctdistance    = 0.78 if donut else 0.70

    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct="%1.1f%%",
        startangle=90, colors=colors,
        pctdistance=pctdistance,
        radius=1.12,
        wedgeprops={"edgecolor": palette["background"], "linewidth": 2, **wedge_kwargs},
        textprops={"color": palette["text"], "fontsize": 9},
    )

    for autotext in autotexts:
        autotext.set_fontsize(8)
        autotext.set_fontweight("bold")
        autotext.set_color(palette["background"] if not donut else palette["text"])

    # Legend instead of inline labels (avoids label clipping)
    short_labels = _shorten_labels(labels, 18)
    patches = [mpatches.Patch(color=colors[i], label=short_labels[i])
               for i in range(len(labels))]
    ax.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.5, -0.10),
              ncol=min(len(labels), 3), fontsize=8,
              frameon=False, labelcolor=palette["text"])
    ax.set_aspect("equal")

    ax.set_title(visual.get("title", "Composition" if not donut else "Share Breakdown"),
                 fontsize=12, fontweight="bold", pad=10, color=palette["text"])

    fig.patch.set_facecolor(palette["background"])
    fig.tight_layout(pad=1.5)
    fig.savefig(path, dpi=STANDARD_CHART_DPI, facecolor=palette["background"])
    plt.close(fig)
    return path


def create_pie_chart(visual, index, theme=None):
    return _render_circular_chart(visual, index, theme, donut=False)


def create_donut_chart(visual, index, theme=None):
    return _render_circular_chart(visual, index, theme, donut=True)


def create_chart_for_visual(visual, index, theme=None):
    chart_type = str(visual.get("chart_type", "bar")).lower()
    labels, values = get_chart_data(visual)

    # Defensive guard before calling ax.pie.  Even if upstream labels a signed
    # variance/bridge chart as pie, render it as a bar chart.
    if chart_type in ("pie", "donut", "doughnut") and _has_negative_or_zero_issue(values):
        safe_visual = copy.deepcopy(visual)
        safe_visual["chart_type"] = "bar"
        return create_bar_chart(safe_visual, index, theme)

    try:
        if chart_type == "line":
            return create_line_chart(visual, index, theme)
        if chart_type == "pie":
            return create_pie_chart(visual, index, theme)
        if chart_type in ("donut", "doughnut"):
            return create_donut_chart(visual, index, theme)
        return create_bar_chart(visual, index, theme)
    except ValueError as exc:
        # Last-resort protection for Matplotlib pie errors such as:
        # "Wedge sizes 'x' must be non negative values".
        if "wedge" in str(exc).lower() or "non negative" in str(exc).lower():
            safe_visual = copy.deepcopy(visual)
            safe_visual["chart_type"] = "bar"
            return create_bar_chart(safe_visual, index, theme)
        raise


def create_visual_assets(analysis, theme=None):
    """
    Render chart images for all chart candidates.
    FIX: removed cap of 4 — all valid charts are rendered.
    """
    os.makedirs("outputs", exist_ok=True)

    visuals    = analysis.get("visuals", []) or []
    candidates = analysis.get("chart_candidates", []) or []

    # Merge: visuals (AI-selected) first, then remaining candidates not in visuals
    seen_titles   = set()
    ordered       = []

    for v in visuals:
        key = str(v.get("title", "")).strip().lower()
        if key and key not in seen_titles:
            ordered.append(v)
            seen_titles.add(key)

    for c in candidates:
        key = str(c.get("title", "")).strip().lower()
        if key and key not in seen_titles:
            ordered.append(c)
            seen_titles.add(key)

    chart_paths  = []
    render_seen  = set()

    for visual in ordered:
        title = str(visual.get("title", "Chart")).strip()
        key   = title.lower()
        if key in render_seen:
            continue

        index = len(chart_paths) + 1
        try:
            path = create_chart_for_visual(visual, index, theme)
        except Exception as exc:
            # One bad chart should never stop the presentation pipeline.
            # Try a forced bar chart, then skip only that chart if it still fails.
            print(f"[chart_agent] chart failed for '{title}': {exc}; trying bar fallback")
            try:
                safe_visual = copy.deepcopy(visual)
                safe_visual["chart_type"] = "bar"
                path = create_bar_chart(safe_visual, index, theme)
            except Exception as fallback_exc:
                print(f"[chart_agent] skipped chart '{title}' after fallback failed: {fallback_exc}")
                continue

        if not path:
            continue

        chart_paths.append({
            "title":      title,
            "insight":    visual.get("insight", ""),
            "chart_type": visual.get("chart_type", "bar"),
            "path":       path,
        })
        render_seen.add(key)

    analysis["chart_paths"] = chart_paths
    print(f"[chart_agent] rendered {len(chart_paths)} charts")
    return analysis