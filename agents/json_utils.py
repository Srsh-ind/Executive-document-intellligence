import json


def extract_json(text):
    """
    Extract valid JSON from model output.
    Prevents broken raw JSON from going into Streamlit/PPT.
    """
    if not text:
        return None

    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start:end + 1]

    try:
        return json.loads(candidate)
    except Exception:
        return None


def safe_list(value):
    """
    Ensures the value is always a list.
    """
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [str(value)]


def validate_analysis(data):
    """
    Ensures final analysis always has the same structure.
    """
    if not isinstance(data, dict):
        data = {}

    defaults = {
        "title": "Executive Insight Report",
        "document_type": "Unknown",
        "audience": "Executive audience",
        "executive_summary": "",
        "core_message": "",
        "domain": {},
        "detected_domain": {},
        "domain_reasoning_summary": "",
        "sections": [],
        "key_findings": [],
        "insights": [],
        "explainable_insights": [],
        "evidence": [],
        "explainability": {},
        "metrics": [],
        "risks": [],
        "opportunities": [],
        "recommendations": [],
        "limitations": [],
        "visuals": [],
        "conclusion": ""
    }

    for key, value in defaults.items():
        data.setdefault(key, value)

    for key in [
        "sections",
        "key_findings",
        "insights",
        "explainable_insights",
        "evidence",
        "metrics",
        "risks",
        "opportunities",
        "recommendations",
        "limitations",
        "visuals"
    ]:
        data[key] = safe_list(data.get(key))

    return data