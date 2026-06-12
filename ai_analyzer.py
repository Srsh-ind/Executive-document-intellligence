import json
import requests

from json_utils import extract_json, validate_analysis


VLLM_URL = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2-7B-Instruct"


def call_llm(prompt, max_tokens=2500):
    """
    Sends prompt to local vLLM endpoint.
    """
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
    """
    Extracts raw facts from one document chunk.
    It does not create the final PPT narrative yet.
    """
    prompt = f"""
You are a document intelligence analyst.

Extract useful information from this document chunk.

The document may be:
- financial report
- research paper
- ISO/compliance document
- policy document
- legal/process document
- technical architecture document
- market report
- meeting transcript
- operational report
- raw table/data file

Return valid JSON only. No markdown.

Format:
{{
  "content_type": "",
  "key_points": [],
  "important_numbers": [],
  "tables_or_comparisons": [],
  "possible_findings": [],
  "possible_risks": [],
  "possible_recommendations": [],
  "possible_limitations": [],
  "visual_candidates": []
}}

Rules:
- Keep each list under 5 items.
- Extract numbers exactly as found.
- Do not invent values.
- Do not create final recommendations unless supported by the text.
- If the chunk is research-oriented, extract findings/method/evidence.
- If the chunk is financial, extract KPIs/trends/risks.
- If the chunk is compliance-oriented, extract controls/gaps/requirements.
- If the chunk is technical, extract architecture/components/tradeoffs.
- Preserve table names and row/column labels.
- For tables, extract rows as label-value pairs when possible.
- Do not generalize the topic.
- Do not mention data governance unless present in the document.

DOCUMENT CHUNK:
{chunk}
"""

    output = call_llm(prompt, max_tokens=1000)
    parsed = extract_json(output)

    if parsed:
        return parsed

    return {
        "content_type": "Unknown",
        "key_points": [],
        "important_numbers": [],
        "tables_or_comparisons": [],
        "possible_findings": [],
        "possible_risks": [],
        "possible_recommendations": [],
        "possible_limitations": [],
        "visual_candidates": []
    }


def analysis_error():
    """
    Safe fallback if model output is invalid.
    This prevents raw JSON from appearing in Streamlit/PPT.
    """
    return validate_analysis({
        "title": "Executive Insight Report",
        "document_type": "Parse Error",
        "executive_summary": (
            "The model response could not be parsed into valid structured output. "
            "Please rerun analysis or reduce the document size."
        ),
        "core_message": "Structured analysis was not completed.",
        "sections": [],
        "key_findings": [],
        "insights": [],
        "evidence": [],
        "metrics": [],
        "risks": [],
        "opportunities": [],
        "recommendations": [],
        "limitations": [],
        "visuals": [],
        "conclusion": "No reliable conclusion could be generated because the model output was incomplete."
    })


def synthesize_results(
        chunk_results,
        original_text,
        tables,
        chart_candidates,
        numbers
):
    """
    Converts extracted chunk facts into final adaptive analysis.
    Strictly grounded in document content.
    """
    prompt = f"""
You are a strict document-grounded analyst.

Create a concise executive analysis using ONLY the extracted document data below.

Return valid JSON only. No markdown. No explanation outside JSON.

CRITICAL RULES:
- Do not invent any company, metric, department, risk, chart, percentage, or recommendation.
- Use ONLY facts, numbers, entities, and themes explicitly present in EXTRACTED CHUNK DATA.
- If something is not present in the extracted data, do not include it.
- Do not create generic risks like data privacy, data governance, cybersecurity, or compliance unless explicitly present.
- Do not use outside knowledge.
- Do not create fake departments such as Sales, Marketing, HR, IT unless present in the document.
- Every visual must use numeric values found in the extracted data.
- Every visual title must correspond to actual document data.
- If numeric data exists, create visuals from it.
- If no numeric data exists, visuals must be [].
- document_type must be inferred from the document content.
- Keep the output concise and complete JSON.
- The ORIGINAL DOCUMENT TEXT is the source of truth.
- If EXTRACTED CHUNK DATA conflicts with ORIGINAL DOCUMENT TEXT, use ORIGINAL DOCUMENT TEXT.
- Every metric and chart value must be traceable to ORIGINAL DOCUMENT TEXT.
- Do not use years, values, products, departments, or categories that are absent from ORIGINAL DOCUMENT TEXT.
- EXTRACTED TABLES are the highest priority source.
- DETERMINISTIC CHART CANDIDATES contain exact values.
- Do not invent chart values.
- Prefer DETERMINISTIC CHART CANDIDATES over generating your own charts.
- Use ORIGINAL DOCUMENT TEXT as source of truth.
- If risks or recommendations are unsupported by document evidence, leave them empty.

Use this schema:
{{
  "title": "",
  "document_type": "",
  "audience": "",
  "executive_summary": "",
  "core_message": "",
  "sections": [
    {{
      "heading": "",
      "bullets": []
    }}
  ],
  "key_findings": [],
  "insights": [],
  "evidence": [],
  "metrics": [
    {{
      "name": "",
      "value": "",
      "interpretation": ""
    }}
  ],
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
  "visuals": [
    {{
      "title": "",
      "chart_type": "bar/line/pie/progress/table",
      "insight": "",
      "data": [
        {{"label": "", "value": 0}}
      ]
    }}
  ],
  "conclusion": ""
}}

For the Northbridge-style financial/operating document, examples of valid visuals are:
- Monthly revenue trend using Jan-Dec revenue values
- Gross margin trend using Jan-Dec gross margin values
- Cash balance trend using Jan-Dec cash balance values
- Regional FY2024 revenue by region
- Product category revenue by category
- Quarterly customer churn trend
- Quarterly employee attrition trend
- Selected raw transaction indicators over quarters

Examples of invalid visuals:
- Data utilization by department
- Data quality score
- Data privacy incidents
- Data governance compliance
- Any topic not directly present in the document

Limits:
- Maximum 5 metrics.
- Maximum 5 insights.
- Maximum 5 risks.
- Maximum 5 opportunities.
- Maximum 5 recommendations.
- Maximum 4 visuals.
- Maximum 12 data points per visual.
- Do not put arrays inside metrics.value.
- Put chart series only inside visuals.data.

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
"""

    output = call_llm(prompt, max_tokens=3500)
    parsed = extract_json(output)

    if parsed:
        return validate_analysis(parsed)

    return analysis_error()


def analyze_chunks(
    chunks,
    tables=None,
    chart_candidates=None,
    numbers=None
):
    if tables is None:
        tables = []

    if chart_candidates is None:
        chart_candidates = []

    if numbers is None:
        numbers = []
        
    chunk_results = []

    for chunk in chunks[:8]:
        chunk_results.append(analyze_single_chunk(chunk))

    original_text = "\n\n".join(chunks[:8])

    return synthesize_results(
        chunk_results,
        original_text,
        tables,
        chart_candidates,
        numbers
)