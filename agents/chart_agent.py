import os
import matplotlib.pyplot as plt


def safe_float(value):
    try:
        if isinstance(value, str):
            value = (
                value.replace("$", "")
                .replace(",", "")
                .replace("%", "")
                .replace("M", "")
                .replace("B", "")
                .strip()
            )
        return float(value)
    except Exception:
        return None


def get_chart_data(visual):
    labels = []
    values = []

    for row in visual.get("data", []):
        label = str(row.get("label", "")).strip()
        value = safe_float(row.get("value"))

        if label and value is not None:
            labels.append(label)
            values.append(value)

    return labels, values


def create_bar_chart(visual, index):
    labels, values = get_chart_data(visual)
    if len(labels) < 2:
        return None

    path = f"outputs/chart_{index}.png"

    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values)
    plt.title(visual.get("title", "Comparison"))
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def create_line_chart(visual, index):
    labels, values = get_chart_data(visual)
    if len(labels) < 2:
        return None

    path = f"outputs/chart_{index}.png"

    plt.figure(figsize=(8, 4.5))
    plt.plot(labels, values, marker="o")
    plt.title(visual.get("title", "Trend"))
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def create_pie_chart(visual, index):
    labels, values = get_chart_data(visual)
    if len(labels) < 2 or len(labels) > 6:
        return None

    path = f"outputs/chart_{index}.png"

    plt.figure(figsize=(7, 4.8))
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    plt.title(visual.get("title", "Composition"))
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def create_chart_for_visual(visual, index):
    chart_type = str(visual.get("chart_type", "bar")).lower()

    if chart_type == "line":
        return create_line_chart(visual, index)

    if chart_type == "pie":
        return create_pie_chart(visual, index)

    return create_bar_chart(visual, index)


def create_visual_assets(analysis):
    os.makedirs("outputs", exist_ok=True)

    visuals = analysis.get("visuals", []) or []
    candidates = analysis.get("chart_candidates", []) or []

    all_visuals = visuals + candidates

    chart_paths = []
    seen_titles = set()

    for visual in all_visuals:
        title = str(visual.get("title", "Chart")).strip()
        key = title.lower()

        if key in seen_titles:
            continue

        index = len(chart_paths) + 1
        path = create_chart_for_visual(visual, index)

        if not path:
            continue

        chart_paths.append({
            "title": title,
            "insight": visual.get("insight", ""),
            "chart_type": visual.get("chart_type", "chart"),
            "path": path
        })

        seen_titles.add(key)

    analysis["chart_paths"] = chart_paths
    return analysis