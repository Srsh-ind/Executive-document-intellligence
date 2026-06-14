import json
import requests

from agents.json_utils import extract_json


VLLM_URL = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2-7B-Instruct"
MAX_SLIDES = 12


SUPPORTED_LAYOUTS = [
    "hero_cover",
    "summary_dashboard",
    "agenda_cards",
    "kpi_dashboard",
    "dashboard_grid",
    "performance_dashboard",
    "comparison_dashboard",
    "split_metrics_chart",
    "insight_dashboard",
    "three_column_status",
    "risk_dashboard",
    "opportunity_dashboard",
    "action_tracker",
    "recommendation_roadmap",
    "timeline",
    "roadmap",
    "donut_insights",
    "before_after",
    "closing_slide"
]


LAYOUT_GUIDE = {
    "hero_cover": "Opening cover slide with strong title and minimal text.",
    "summary_dashboard": "Condensed executive summary: agenda/problem, key findings, next steps, and top metrics.",
    "agenda_cards": "Numbered agenda or section overview.",
    "kpi_dashboard": "Large KPI cards for important metrics.",
    "dashboard_grid": "Multi-widget dashboard mixing KPI cards, charts, and callouts.",
    "performance_dashboard": "Metrics plus visual trends or operational performance story.",
    "comparison_dashboard": "Side-by-side comparison across categories, periods, regions, segments, or options.",
    "split_metrics_chart": "Metrics on one side and chart/visual on the other.",
    "insight_dashboard": "Visual insight cards explaining the 'so what'.",
    "three_column_status": "Three-part status: strengths, concerns, priorities or current/future/actions.",
    "risk_dashboard": "Risks, challenges, gaps, issues, or watch areas.",
    "opportunity_dashboard": "Growth levers, improvement areas, upside potential.",
    "action_tracker": "Leadership actions with priority and impact.",
    "recommendation_roadmap": "Recommendations organized as sequence, roadmap, or phased plan.",
    "timeline": "Chronological progress, milestones, process, or evolution.",
    "roadmap": "Future path, implementation plan, or next steps.",
    "donut_insights": "Few percentage/share metrics with circular/donut style visuals.",
    "before_after": "Before/after, current vs target, previous vs current, change story.",
    "closing_slide": "Final takeaway and forward-looking close."
}


def call_llm(prompt, max_tokens=2200):
    response = requests.post(
        VLLM_URL,
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.45,
            "max_tokens": max_tokens
        },
        timeout=180
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def safe_list(value):
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def trim(value, limit):
    return safe_list(value)[:limit]


def recommendation_text(item):
    if isinstance(item, dict):
        return item.get("recommendation", "") or item.get("action", "") or item.get("value", "")
    return str(item)


def compact_analysis(analysis):
    return {
        "title": analysis.get("title", ""),
        "document_type": analysis.get("document_type", ""),
        "audience": analysis.get("audience", ""),
        "executive_summary": analysis.get("executive_summary", ""),
        "core_message": analysis.get("core_message", ""),
        "sections": trim(analysis.get("sections"), 8),
        "metrics": trim(analysis.get("metrics"), 10),
        "key_findings": trim(analysis.get("key_findings"), 8),
        "insights": trim(analysis.get("insights"), 8),
        "evidence": trim(analysis.get("evidence"), 6),
        "risks": trim(analysis.get("risks"), 6),
        "opportunities": trim(analysis.get("opportunities"), 6),
        "recommendations": trim(analysis.get("recommendations"), 6),
        "limitations": trim(analysis.get("limitations"), 5),
        "visuals": trim(analysis.get("visuals"), 8),
        "chart_paths": trim(analysis.get("chart_paths"), 8),
        "conclusion": analysis.get("conclusion", "")
    }


def fallback_summary_slide(analysis):
    return {
        "story_role": "summary",
        "layout": "summary_dashboard",
        "title": "Summary",
        "headline": analysis.get("core_message", "") or analysis.get("executive_summary", ""),
        "message": analysis.get("core_message", "") or analysis.get("executive_summary", ""),
        "blocks": [
            {
                "label": "Agenda",
                "items": trim(analysis.get("sections"), 3)
            },
            {
                "label": "Key Findings",
                "items": trim(analysis.get("key_findings"), 4)
            },
            {
                "label": "Next Steps",
                "items": [
                    recommendation_text(r)
                    for r in trim(analysis.get("recommendations"), 3)
                ]
            }
        ],
        "cards": trim(analysis.get("metrics"), 3),
        "bullets": [],
        "visual_title": "",
        "visual_style": "summary_dashboard",
        "density": "high",
        "so_what": analysis.get("core_message", "")
    }


def fallback_storyboard(analysis, max_slides=MAX_SLIDES):
    slides = [fallback_summary_slide(analysis)]

    if analysis.get("metrics"):
        slides.append({
            "story_role": "performance",
            "layout": "kpi_dashboard",
            "title": "Performance Snapshot",
            "headline": "The most important numeric signals are concentrated here.",
            "message": "Key quantitative signals extracted from the document.",
            "cards": trim(analysis.get("metrics"), 6),
            "bullets": [],
            "blocks": [],
            "visual_title": "",
            "visual_style": "kpi_cards",
            "density": "high",
            "so_what": "These indicators show the current state and priority areas."
        })

    if analysis.get("visuals") or analysis.get("chart_paths"):
        slides.append({
            "story_role": "trend",
            "layout": "performance_dashboard",
            "title": "Visual Trends",
            "headline": "The visual evidence highlights the key pattern.",
            "message": "Charts and visual candidates extracted from the document.",
            "cards": [],
            "bullets": [],
            "blocks": [],
            "visual_title": "",
            "visual_style": "charts",
            "density": "high",
            "so_what": "The pattern should guide leadership attention."
        })

    if analysis.get("insights") or analysis.get("key_findings"):
        slides.append({
            "story_role": "insights",
            "layout": "insight_dashboard",
            "title": "Key Insights",
            "headline": "The analysis points to a small set of decision-relevant themes.",
            "message": "What the information means and why it matters.",
            "bullets": trim(analysis.get("insights") or analysis.get("key_findings"), 5),
            "cards": [],
            "blocks": [],
            "visual_title": "",
            "visual_style": "insight_cards",
            "density": "medium",
            "so_what": "These insights explain the implication behind the facts."
        })

    if analysis.get("risks") or analysis.get("opportunities"):
        slides.append({
            "story_role": "risks_opportunities",
            "layout": "risk_dashboard",
            "title": "Areas Requiring Attention",
            "headline": "The document surfaces both risks and upside potential.",
            "message": "Risks and opportunities surfaced from the analysis.",
            "cards": trim(analysis.get("risks"), 3) + trim(analysis.get("opportunities"), 3),
            "bullets": [],
            "blocks": [],
            "visual_title": "",
            "visual_style": "risk_matrix",
            "density": "medium",
            "so_what": "Leadership should focus on the highest-impact watch areas."
        })

    if analysis.get("recommendations"):
        slides.append({
            "story_role": "actions",
            "layout": "action_tracker",
            "title": "Recommended Actions",
            "headline": "The next steps should be prioritized by impact and urgency.",
            "message": "Leadership-ready next steps.",
            "cards": trim(analysis.get("recommendations"), 5),
            "bullets": [],
            "blocks": [],
            "visual_title": "",
            "visual_style": "roadmap",
            "density": "medium",
            "so_what": "Execution focus determines whether the findings become measurable improvement."
        })

    if analysis.get("conclusion"):
        slides.append({
            "story_role": "closing",
            "layout": "closing_slide",
            "title": "Conclusion",
            "headline": analysis.get("conclusion", ""),
            "message": analysis.get("conclusion", ""),
            "cards": [],
            "bullets": [],
            "blocks": [],
            "visual_title": "",
            "visual_style": "minimal",
            "density": "low",
            "so_what": analysis.get("conclusion", "")
        })

    return slides[:max_slides]


def clean_slide(slide):
    layout = slide.get("layout", "")

    if layout not in SUPPORTED_LAYOUTS:
        layout = "insight_dashboard"

    return {
        "story_role": slide.get("story_role", ""),
        "layout": layout,
        "title": slide.get("title", "Insight"),
        "headline": slide.get("headline", ""),
        "message": slide.get("message", ""),
        "blocks": safe_list(slide.get("blocks")),
        "cards": safe_list(slide.get("cards")),
        "bullets": safe_list(slide.get("bullets")),
        "visual_title": slide.get("visual_title", ""),
        "visual_style": slide.get("visual_style", ""),
        "density": slide.get("density", "medium"),
        "so_what": slide.get("so_what", "")
    }


def build_storyboard(analysis, max_slides=MAX_SLIDES):
    data = compact_analysis(analysis)

    prompt = f"""
You are a senior McKinsey/BCG-style executive presentation storyboard designer.

Your task:
Turn the supplied document analysis into a visual-first boardroom PowerPoint storyboard.

You are NOT writing a report.
You are designing a leadership deck.

Core design principles:
- Ruthlessly edit.
- Minimal text.
- Prefer visual communication over bullets.
- Every slide must answer: "So what?"
- Each slide should have one clear message.
- Use charts, dashboards, comparisons, roadmaps, and visual metaphors wherever possible.
- Do not create slides just because data exists.
- Merge only when two slides would contain less than three meaningful elements each.
- Maximum {max_slides} slides.
- Do not invent facts.
- Do not invent metrics.
- Do not invent recommendations.
- Use only supplied analysis.
- Avoid generic repeated titles.
- Do not use "Executive Summary" or "Executive Conclusion".
- Use specific titles that sound human and boardroom-ready.

A strong deck usually contains, when evidence supports it:
1. A condensed summary dashboard with problem/agenda, key findings, and next steps.
2. A KPI/performance dashboard if quantifiable metrics exist.
3. A market/context/insight slide if findings or insights exist.
4. A risk/opportunity slide only if risks or opportunities are meaningful.
5. An action or roadmap slide if recommendations exist.
6. A closing slide only if it adds a distinct final takeaway.

Supported layout vocabulary:
{json.dumps(LAYOUT_GUIDE, indent=2)}

Choose layouts by communication need:
- If the slide summarizes the whole document, use summary_dashboard.
- If there are many metrics, use kpi_dashboard or dashboard_grid.
- If there are charts or visual patterns, use performance_dashboard, split_metrics_chart, donut_insights, comparison_dashboard, or before_after.
- If there are risks, issues, gaps, or challenges, use risk_dashboard.
- If there are opportunities, use opportunity_dashboard.
- If the slide is action-oriented, use action_tracker, recommendation_roadmap, roadmap, or timeline.
- If the content is mainly interpretation, use insight_dashboard or three_column_status.
- If there is no meaningful content for a slide, skip it.

Return valid JSON only.

Metric-rich documents should usually contain:

1. Summary Dashboard

2. KPI Dashboard
When 4 or more metrics exist.

3. Trend or Comparison Slide
When time-series, distributions, regions, segments or comparisons exist.

4. Insight Slide
When findings or observations exist.

5. Risk and Opportunity Slide
When risks or opportunities exist.

6. Action Slide
When recommendations exist.

7. Roadmap Slide
When implementation steps or future actions exist.

Do not merge these unless information is extremely sparse.

Schema:
{{
  "slides": [
    {{
      "story_role": "summary/performance/trend/comparison/insights/risk/opportunity/actions/future/closing",
      "layout": "one supported layout name",
      "title": "specific human title",
      "headline": "one strong sentence",
      "message": "short supporting message",
      "so_what": "why this slide matters",
      "blocks": [
        {{"label": "short label", "items": ["short item"]}}
      ],
      "cards": [],
      "bullets": [],
      "visual_title": "",
      "visual_style": "dashboard/chart/cards/roadmap/timeline/minimal",
      "density": "low/medium/high"
    }}
  ]
}}

Important:
- The first slide should usually be a summary_dashboard.
- Do NOT make every slide a card slide.
- Prefer different layouts across the deck.
- If charts are available, include at least one chart-oriented layout.
- If metrics are available, include at least one dashboard layout.
- Titles should be generated from the content, not generic labels.
- Keep bullets short and limited.
- Recommendations should be practical and evidence-based.

Mandatory layout rules:
- If metrics has 3 or more items, include exactly one KPI/dashboard slide using kpi_dashboard or dashboard_grid.
- Do not create risk_dashboard unless risks has at least one item.
- If risks is empty but limitations exist, use insight_dashboard or opportunity_dashboard, not risk_dashboard.
- If recommendations exist, use either action_tracker or recommendation_roadmap, not both unless there are 4+ recommendations.
- Avoid separate closing_slide if roadmap or action slide already gives a strong final takeaway.

Slide count guidance:

Simple documents:
4-5 slides
Typical executive documents:
6-8 slides
Metric-rich reports:
7-10 slides
Research documents:
5-7 slides
Do not aggressively compress slides.
Separate slides should exist when they communicate different ideas.
Examples:
Performance metrics -> KPI Dashboard
Trends and comparisons -> Performance Dashboard or Comparison Dashboard
Insights -> Insight Dashboard
Risks and opportunities -> Risk Dashboard or Three Column Status
Recommendations -> Action Tracker
Future initiatives -> Roadmap
Conclusion -> Closing Slide only if it adds new value.
Avoid creating only 3-4 slides for documents with substantial metrics and trends.

Analysis:
{json.dumps(data, indent=2)}
"""

    try:
        output = call_llm(prompt)
        parsed = extract_json(output)

        if not parsed or "slides" not in parsed:
            return fallback_storyboard(analysis, max_slides)

        slides = [
            clean_slide(slide)
            for slide in parsed.get("slides", [])
            if isinstance(slide, dict)
        ]

        if not slides:
            return fallback_storyboard(analysis, max_slides)

        return slides[:max_slides]

    except Exception:
        return fallback_storyboard(analysis, max_slides)


def build_slide_plan(analysis, max_slides=MAX_SLIDES):
    return build_storyboard(analysis, max_slides)