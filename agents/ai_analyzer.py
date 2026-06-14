import json
import requests

from agents.json_utils import extract_json, validate_analysis


VLLM_URL = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2-7B-Instruct"


def call_llm(prompt, max_tokens=2500):
    response = requests.post(
        VLLM_URL,
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": max_tokens
        },
        timeout=180
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def analyze_single_chunk(chunk):
    prompt = f"""
You are a strict fact extraction analyst.

Extract only grounded facts from this document chunk.

Return valid JSON only.

Format:
{{
  "key_points": [],
  "important_numbers": [],
  "findings": [],
  "caveats": [],
  "possible_actions": []
}}

Rules:
- Use only the chunk.
- Do not invent.
- Preserve exact numbers and labels.
- Do not create slides yet.
- Keep each list under 5 items.

DOCUMENT CHUNK:
{chunk}
"""

    output = call_llm(prompt, max_tokens=900)
    parsed = extract_json(output)

    if parsed:
        return parsed

    return {
        "key_points": [],
        "important_numbers": [],
        "findings": [],
        "caveats": [],
        "possible_actions": []
    }


def build_visuals_from_storyline(storyline, chart_candidates):
    selected = []

    titles_needed = set()

    for slide in storyline:
        visual_title = slide.get("visual_title", "")
        if visual_title:
            titles_needed.add(visual_title.strip().lower())

    for chart in chart_candidates:
        title = chart.get("title", "")
        if title.strip().lower() in titles_needed:
            selected.append({
                "title": title,
                "chart_type": chart.get("chart_type", "bar"),
                "insight": "",
                "data": chart.get("data", [])
            })

    return selected[:4]


def analysis_error():
    return validate_analysis({
        "title": "Executive Insight Report",
        "document_type": "Parse Error",
        "executive_summary": "The model response could not be parsed.",
        "core_message": "Structured analysis failed.",
        "metrics": [],
        "key_findings": [],
        "insights": [],
        "risks": [],
        "opportunities": [],
        "recommendations": [],
        "limitations": [],
        "visuals": [],
        "storyline": [],
        "conclusion": "No reliable conclusion could be generated."
    })


def synthesize_results(
    chunk_results,
    original_text,
    tables,
    chart_candidates,
    numbers,
    metric_cards,
    sections
):
    prompt = f"""
You are an executive presentation strategist.

Create a visual-first executive presentation plan from the document.

Return valid JSON only.

SOURCE PRIORITY:
1. EXTRACTED TABLES
2. DETERMINISTIC CHART CANDIDATES
3. ORIGINAL DOCUMENT TEXT
4. EXTRACTED CHUNK DATA

STRICT RULES:
- Use only provided source facts.
- Do not invent data.
- Do not copy large text.
- Convert facts into insights.
- Slide titles must be conclusions, not labels.
- Prefer visuals, KPI cards, charts, tables, and callouts over paragraphs.
- Use fewer slides with stronger messages.
- Merge weak or single-point ideas.
- Do not make a slide unless it helps an executive understand or decide.
- If a visual helps, select it from DETERMINISTIC CHART CANDIDATES.
- Do not create fake chart data.

OUTPUT SCHEMA:
{{
  "title": "",
  "document_type": "",
  "audience": "",
  "executive_summary": "",
  "core_message": "",

  "metrics": [
    {{
      "name": "",
      "value": "",
      "interpretation": ""
    }}
  ],

  "key_findings": [],
  "insights": [],
  "risks": [],
  "opportunities": [],
  "recommendations": [
    {{
      "priority": "High/Medium/Low",
      "recommendation": "",
      "business_impact": ""
    }}
  ],
  "limitations": [],

  "storyline": [
    {{
      "slide_title": "",
      "layout": "executive_summary/kpi_dashboard/chart_with_callout/insight_cards/recommendation_table/conclusion",
      "importance": 1,
      "message": "",
      "bullets": [],
      "cards": [
        {{
          "label": "",
          "value": "",
          "note": ""
        }}
      ],
      "needs_visual": false,
      "visual_title": ""
    }}
  ],

  "conclusion": ""
}}

LAYOUT GUIDANCE:
- executive_summary: one strong message + 3 short bullets.
- kpi_dashboard: 4 to 6 KPI cards.
- chart_with_callout: one chart + one executive interpretation.
- insight_cards: 3 to 4 visual cards.
- recommendation_table: actions in a table.
- conclusion: short final executive message.

TITLE GUIDANCE:
Bad: Revenue by Month
Good: Growth accelerated, but profitability pressure increased

Bad: Risks
Good: Margin, cash, and execution signals require management attention

Bad: Recommendations
Good: Three actions can protect growth quality

LIMITS:
- Maximum 8 storyline slides.
- Maximum 6 metrics.
- Maximum 5 bullets per slide.
- Maximum 6 KPI cards.
- Use visual_title only if it exactly matches a chart candidate title.

ORIGINAL DOCUMENT TEXT:
{original_text[:12000]}

EXTRACTED TABLES:
{json.dumps(tables, indent=2)}

DETERMINISTIC CHART CANDIDATES:
{json.dumps(chart_candidates, indent=2)}

EXTRACTED NUMBERS:
{json.dumps(numbers[:100], indent=2)}

EXTRACTED CHUNK DATA:
{json.dumps(chunk_results, indent=2)}

METRIC CARDS:
{json.dumps(metric_cards, indent=2)}

DOCUMENT SECTIONS:
{json.dumps(sections, indent=2)}
"""

    output = call_llm(prompt, max_tokens=4000)
    parsed = extract_json(output)

    if not parsed:
        return analysis_error()

    analysis = validate_analysis(parsed)
    analysis.setdefault("storyline", [])

    analysis["visuals"] = build_visuals_from_storyline(
        analysis["storyline"],
        chart_candidates
    )

    return analysis


def analyze_chunks(
    chunks,
    tables=None,
    chart_candidates=None,
    numbers=None,
    metric_cards=None,
    sections=None
):
    tables = tables or []
    chart_candidates = chart_candidates or []
    numbers = numbers or []
    metric_cards = metric_cards or []
    sections = sections or []

    chunk_results = []

    for chunk in chunks[:8]:
        chunk_results.append(analyze_single_chunk(chunk))

    original_text = "\n\n".join(chunks[:8])

    analysis = synthesize_results(
        chunk_results,
        original_text,
        tables,
        chart_candidates,
        numbers,
        metric_cards,
        sections
      )

    analysis["tables"] = tables
    analysis["chart_candidates"] = chart_candidates
    analysis["numbers"] = numbers
    analysis["metric_cards"] = metric_cards
    analysis["sections"] = sections

    return analysis