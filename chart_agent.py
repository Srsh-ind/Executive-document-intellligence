import os
import matplotlib.pyplot as plt


def _safe_float(value):
    """
    Converts string/numeric values into float.
    """
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


def _get_chart_data(visual):
    """
    Extracts valid labels and numeric values from visual data.
    """
    labels = []
    values = []

    for row in visual.get("data", []):
        if not isinstance(row, dict):
            continue

        label = str(row.get("label", "")).strip()
        value = _safe_float(row.get("value"))

        if label and value is not None:
            labels.append(label)
            values.append(value)

    return labels, values


def create_bar_chart(visual, index):
    """
    Creates a bar chart for category comparisons.
    """
    labels, values = _get_chart_data(visual)

    if not labels:
        return None

    path = f"outputs/chart_{index}.png"

    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values)
    plt.title(visual.get("title", "Category Comparison"))
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def create_line_chart(visual, index):
    """
    Creates a line chart for trends.
    """
    labels, values = _get_chart_data(visual)

    if not labels:
        return None

    path = f"outputs/chart_{index}.png"

    plt.figure(figsize=(8, 4.5))
    plt.plot(labels, values, marker="o")
    plt.title(visual.get("title", "Trend Analysis"))
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def create_pie_chart(visual, index):
    """
    Creates a pie chart for part-to-whole data.
    """
    labels, values = _get_chart_data(visual)

    if not labels:
        return None

    path = f"outputs/chart_{index}.png"

    plt.figure(figsize=(7, 4.8))
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    plt.title(visual.get("title", "Share Breakdown"))
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def create_progress_chart(visual, index):
    """
    Creates a horizontal progress chart for percentages.
    """
    labels, values = _get_chart_data(visual)

    if not labels:
        return None

    values = [min(max(v, 0), 100) for v in values]
    path = f"outputs/chart_{index}.png"

    plt.figure(figsize=(8, 4.5))
    plt.barh(labels, values)
    plt.xlim(0, 100)
    plt.xlabel("Percent")
    plt.title(visual.get("title", "Progress Snapshot"))
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

    return path


def create_chart_for_visual(visual, index):
    """
    Chooses the right chart function.
    """
    chart_type = str(visual.get("chart_type", "")).lower()

    if chart_type == "bar":
        return create_bar_chart(visual, index)

    if chart_type == "line":
        return create_line_chart(visual, index)

    if chart_type == "pie":
        return create_pie_chart(visual, index)

    if chart_type == "progress":
        return create_progress_chart(visual, index)

    return None


def create_visual_assets(analysis):
    """
    Creates chart PNGs from analysis['visuals'].
    Adds chart file paths into analysis['chart_paths'].
    """
    os.makedirs("outputs", exist_ok=True)

    chart_paths = []

    for index, visual in enumerate(analysis.get("visuals", [])[:6], start=1):
        if not isinstance(visual, dict):
            continue

        path = create_chart_for_visual(visual, index)

        if path:
            chart_paths.append({
                "title": visual.get("title", f"Chart {index}"),
                "insight": visual.get("insight", ""),
                "chart_type": visual.get("chart_type", "chart"),
                "path": path
            })

    analysis["chart_paths"] = chart_paths
    return analysis