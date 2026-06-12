def recommend_slide_plan(analysis):
    """
    Creates a dynamic slide plan.
    It does not force risk/recommendation slides for every document.
    """
    slides = [
        {"title": "Executive Summary", "type": "summary"}
    ]

    if analysis.get("metrics"):
        slides.append({"title": "Key Metrics & Signals", "type": "metrics"})

    if analysis.get("chart_paths") or analysis.get("visuals"):
        slides.append({"title": "Data Visualizations", "type": "charts"})

    if analysis.get("key_findings"):
        slides.append({
            "title": "Key Findings",
            "type": "bullets",
            "source": "key_findings"
        })

    if analysis.get("insights"):
        slides.append({
            "title": "Insight Themes",
            "type": "bullets",
            "source": "insights"
        })

    # if analysis.get("evidence"):
    #     slides.append({
    #         "title": "Supporting Evidence",
    #         "type": "bullets",
    #         "source": "evidence"
    #     })

    for section in analysis.get("sections", []):
        slides.append({
            "title": section.get("heading", "Document Section"),
            "type": "custom_section",
            "items": section.get("bullets", [])
        })

    if analysis.get("risks"):
        slides.append({
            "title": "Risks & Watchouts",
            "type": "bullets",
            "source": "risks"
        })

    if analysis.get("opportunities"):
        slides.append({
            "title": "Opportunities",
            "type": "bullets",
            "source": "opportunities"
        })

    if analysis.get("recommendations"):
        slides.append({
            "title": "Recommended Actions",
            "type": "recommendations"
        })

    if analysis.get("limitations"):
        slides.append({
            "title": "Limitations / Caveats",
            "type": "bullets",
            "source": "limitations"
        })

    slides.append({"title": "Conclusion", "type": "conclusion"})

    return slides