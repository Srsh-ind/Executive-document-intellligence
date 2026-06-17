import json


def extract_json(text):
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
        pass

    # ↓ NEW: try truncation repair by stripping incomplete trailing content
    try:
        # Remove the last incomplete key-value pair and close braces
        repaired = re.sub(r',\s*"[^"]*"\s*:\s*[^}]*$', '', candidate)
        # Re-close any unclosed brackets/braces
        open_brackets = repaired.count('[') - repaired.count(']')
        open_braces = repaired.count('{') - repaired.count('}')
        repaired += ']' * open_brackets + '}' * open_braces
        return json.loads(repaired)
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