import json
import re

from agents.json_utils import extract_json, validate_analysis
from agents.llm_client import call_llm
from agents.rag_engine import build_rag_bundle, validate_explainable_analysis
from agents.domain_reasoning import (
    apply_domain_reasoning_layer,
    build_domain_prompt_context,
    classify_document_domain,
)


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
    try:
        output = call_llm(prompt, max_tokens=900)
        parsed = extract_json(output)
    except Exception as exc:
        print(f"[ai_analyzer] chunk analysis failed: {exc}")
        parsed = None

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
    seen = set()

    titles_needed = set()

    for slide in storyline:
        vt = slide.get("visual_title", "")
        if vt:
            titles_needed.add(vt.strip().lower())

    # --- Exact match ---
    for chart in chart_candidates:
        title = str(chart.get("title", "")).strip()
        key   = title.lower()
        if key and key in titles_needed and key not in seen:
            selected.append({
                "title":      title,
                "chart_type": chart.get("chart_type", "bar"),
                "insight":    "",
                "data":       chart.get("data", [])
            })
            seen.add(key)

    # --- Fuzzy match ---
    for chart in chart_candidates:
        title = str(chart.get("title", "")).strip()
        key   = title.lower()
        if not title or key in seen:
            continue
        for needed in titles_needed:
            if needed and (needed in key or key in needed):
                selected.append({
                    "title":      title,
                    "chart_type": chart.get("chart_type", "bar"),
                    "insight":    "",
                    "data":       chart.get("data", [])
                })
                seen.add(key)
                break

    # --- Always include circular charts (donut/pie) even if title didn't match ---
    for chart in chart_candidates:
        title = str(chart.get("title", "")).strip()
        key   = title.lower()
        if key in seen:
            continue
        if str(chart.get("chart_type", "")).lower() in ("donut", "doughnut", "pie"):
            selected.append({
                "title":      title,
                "chart_type": chart.get("chart_type", "bar"),
                "insight":    "",
                "data":       chart.get("data", [])
            })
            seen.add(key)

    # --- Fill remaining unmatched candidates (no cap) ---
    for chart in chart_candidates:
        title = str(chart.get("title", "")).strip()
        key   = title.lower()
        if not title or key in seen:
            continue
        selected.append({
            "title":      title,
            "chart_type": chart.get("chart_type", "bar"),
            "insight":    "",
            "data":       chart.get("data", [])
        })
        seen.add(key)

    # Return ALL — chart_agent will deduplicate; ppt_builder distributes across slides
    return selected


def analysis_error(tables=None, chart_candidates=None, metric_cards=None, sections=None):
    tables          = tables          or []
    chart_candidates = chart_candidates or []
    metric_cards    = metric_cards    or []
    sections        = sections        or []

    metrics = [{"name": c.get("label", "Metric"), "value": c.get("value", ""), "interpretation": ""}
               for c in metric_cards[:6]]
    key_findings = [f"Document includes a section on {s}." for s in sections[:6]]
    visuals = [{"title": c.get("title", "Chart"), "chart_type": c.get("chart_type", "bar"),
                "insight": "", "data": c.get("data", [])} for c in chart_candidates]

    return validate_analysis({
        "title": "Executive Insight Report",
        "document_type": "Document",
        "executive_summary": (
            "The document was converted into an evidence-backed executive view using "
            "extracted metrics, trends, risks, and recommended actions."
        ),
        "core_message": "Review the evidence-backed signals below.",
        "metrics": metrics,
        "key_findings": key_findings,
        "insights": [],
        "risks": [],
        "opportunities": [],
        "recommendations": [],
        "limitations": [
            "Some narrative synthesis may be limited when the language model endpoint is not reachable."
        ],
        "visuals": visuals,
        "storyline": [],
        "conclusion": "Use the evidence-backed signals to prioritize the next management actions.",
        "explainability": {"retrieval_stats": {}, "evidence_pack": []}
    })


def _text_from_item(item):
    if isinstance(item, dict):
        for key in ("insight", "finding", "risk", "opportunity", "recommendation", "value", "note", "interpretation", "text", "summary"):
            if item.get(key):
                return str(item.get(key))
        return " ".join(str(v) for v in item.values() if v)
    return str(item or "")


def _is_weak_insight(item):
    text = _text_from_item(item).strip()
    if len(text.split()) < 7:
        return True
    lower = text.lower()
    generic_phrases = (
        "requires attention",
        "potential for further growth",
        "opportunity to optimize",
        "balanced growth across",
        "operational challenges requiring attention",
        "key findings",
        "areas requiring attention",
        "improve margins",
    )
    if any(p in lower for p in generic_phrases) and not any(ch.isdigit() for ch in text):
        return True
    # Strong executive insights usually contain a number, named driver, or directional change.
    evidence_words = (
        "revenue", "margin", "expense", "ebitda", "cash", "churn", "conversion",
        "freight", "markdown", "labor", "inventory", "online", "customer", "region",
        "basis", "growth", "decline", "increase", "decrease", "improved", "down", "up",
    )
    if not any(ch.isdigit() for ch in text) and not any(w in lower for w in evidence_words):
        return True
    return False


def build_evidence_pack(chunks, metric_cards=None, chart_candidates=None, max_items=12):
    """Small RAG-style retriever over the uploaded document text.

    This is intentionally local and deterministic: it retrieves the most relevant
    snippets for executive themes, then passes those snippets to the LLM.  It is
    not the old QA agent and does not add a QA-analysis score/slide.
    """
    chunks = [c for c in (chunks or []) if str(c).strip()]
    metric_cards = metric_cards or []
    chart_candidates = chart_candidates or []

    themes = {
        "growth": ["revenue", "sales", "growth", "bookings", "region", "customer"],
        "profitability": ["gross margin", "margin", "ebitda", "profit", "markdown", "freight"],
        "costs": ["operating expense", "opex", "labor", "overtime", "marketing", "cost"],
        "operations": ["inventory", "warehouse", "capacity", "conversion", "return", "forecast"],
        "risk": ["risk", "pressure", "decline", "down", "churn", "constraint", "challenge"],
        "actions": ["recommend", "next step", "action", "invest", "optimize", "reduce", "improve"],
    }

    snippets = []
    seen = set()
    for theme, terms in themes.items():
        scored = []
        for idx, chunk in enumerate(chunks):
            low = chunk.lower()
            score = sum(low.count(t) for t in terms)
            score += min(5, sum(ch.isdigit() for ch in chunk) // 8)
            if score > 0:
                scored.append((score, idx, chunk))
        for score, idx, chunk in sorted(scored, reverse=True)[:2]:
            snippet = " ".join(str(chunk).split())[:700]
            key = snippet.lower()[:180]
            if key not in seen:
                snippets.append({"theme": theme, "source": f"chunk_{idx+1}", "evidence": snippet})
                seen.add(key)
            if len(snippets) >= max_items:
                break
        if len(snippets) >= max_items:
            break

    # Structured evidence is often more reliable than prose; add it explicitly.
    for card in metric_cards[:8]:
        label = card.get("label") or card.get("name") or "Metric"
        value = card.get("value") or card.get("amount") or ""
        note = card.get("note") or card.get("interpretation") or ""
        if value:
            snippets.append({"theme": "metric", "source": "metric_card", "evidence": f"{label}: {value}. {note}".strip()})
        if len(snippets) >= max_items + 6:
            break

    for chart in chart_candidates[:6]:
        data = chart.get("data") or []
        if len(data) >= 2:
            points = ", ".join(f"{d.get('label')}: {d.get('value')}" for d in data[:6])
            snippets.append({"theme": "visual", "source": "chart_candidate", "evidence": f"{chart.get('title', 'Chart')} — {points}"})
    return snippets[:max_items + 10]


def _chart_trend_sentence(chart):
    data = chart.get("data") or []
    if len(data) < 2:
        return ""
    try:
        first = float(data[0].get("value"))
        last = float(data[-1].get("value"))
    except Exception:
        return ""
    title = str(chart.get("title") or "Metric trend")
    first_label = str(data[0].get("label") or "first period")
    last_label = str(data[-1].get("label") or "latest period")
    delta = last - first
    direction = "increased" if delta > 0 else "decreased" if delta < 0 else "remained flat"
    if abs(first) > 0:
        pct = abs(delta) / abs(first) * 100
        return f"{title} {direction} from {first:g} in {first_label} to {last:g} in {last_label} ({pct:.1f}% change)."
    return f"{title} {direction} from {first:g} in {first_label} to {last:g} in {last_label}."


def _fallback_grounded_insights(metric_cards=None, chart_candidates=None, limit=5):
    insights = []
    for card in (metric_cards or [])[:8]:
        label = card.get("label") or card.get("name") or "Metric"
        value = card.get("value") or ""
        note = card.get("note") or card.get("interpretation") or ""
        if value:
            sentence = f"{label} stands at {value}"
            if note:
                sentence += f"; {note}"
            sentence = sentence.rstrip(".;") + "."
            if sentence not in insights:
                insights.append(sentence)
        if len(insights) >= limit:
            return insights

    for chart in (chart_candidates or [])[:8]:
        sentence = _chart_trend_sentence(chart)
        if sentence and sentence not in insights:
            insights.append(sentence)
        if len(insights) >= limit:
            break
    return insights[:limit]


def strengthen_analysis_quality(analysis, metric_cards=None, chart_candidates=None, evidence_pack=None):
    """Post-process LLM output so the deck does not contain generic insights."""
    metric_cards = metric_cards or []
    chart_candidates = chart_candidates or []
    evidence_pack = evidence_pack or []

    current = [_text_from_item(x) for x in analysis.get("insights", [])]
    strong = [x for x in current if x.strip() and not _is_weak_insight(x)]
    fallback = _fallback_grounded_insights(metric_cards, chart_candidates, limit=6)

    # Replace the insight set if most model insights are generic.
    if len(strong) < max(2, min(4, len(current))):
        merged = []
        for item in strong + fallback:
            if item and item not in merged:
                merged.append(item)
        analysis["insights"] = merged[:6]
    else:
        analysis["insights"] = strong[:6]

    if not analysis.get("key_findings") or all(_is_weak_insight(x) for x in analysis.get("key_findings", [])[:3]):
        analysis["key_findings"] = analysis.get("insights", [])[:5]

    # Keep a compact evidence trail for debugging / future citations in UI.
    analysis["evidence"] = evidence_pack[:12]
    return analysis


def _metric_value(metric_cards, analysis, *names):
    """Find a value in extracted metric cards or analysis metrics by label tokens."""
    candidates = []
    for card in (metric_cards or []):
        if isinstance(card, dict):
            candidates.append((str(card.get("label") or card.get("name") or ""), str(card.get("value") or "")))
    for card in (analysis.get("metrics", []) or []):
        if isinstance(card, dict):
            candidates.append((str(card.get("name") or card.get("metric") or card.get("label") or ""), str(card.get("value") or "")))
    name_sets = [[n.lower() for n in group] if isinstance(group, (list, tuple, set)) else [str(group).lower()] for group in names]
    for label, value in candidates:
        low = label.lower()
        if value and all(any(token in low for token in group) for group in name_sets):
            if "margin" in low and "%" not in value and re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value.strip()):
                return value.strip() + "%"
            return value
    return ""


def _find_evidence_ids(rag_bundle, *terms, limit=4):
    terms = [t.lower() for t in terms if t]
    ids = []
    for item in (rag_bundle or {}).get("evidence_pack", []) or []:
        text = str(item.get("text") or item.get("evidence") or "").lower()
        if all(t in text for t in terms):
            eid = item.get("id")
            if eid and eid not in ids:
                ids.append(eid)
        if len(ids) >= limit:
            break
    if not ids:
        for item in (rag_bundle or {}).get("evidence_pack", []) or []:
            text = str(item.get("text") or item.get("evidence") or "").lower()
            if any(t in text for t in terms):
                eid = item.get("id")
                if eid and eid not in ids:
                    ids.append(eid)
            if len(ids) >= limit:
                break
    return ids[:limit]


def _is_positive_comparison_mislabeled(text):
    low = str(text or "").lower()
    if not any(bad in low for bad in ("pressure", "issue", "decline", "weak", "leak")):
        return False
    m = re.search(r"was\s+([0-9]+(?:\.[0-9]+)?)%\s+compared\s+to\s+([0-9]+(?:\.[0-9]+)?)%", low)
    if not m:
        return False
    try:
        return float(m.group(1)) >= float(m.group(2))
    except Exception:
        return False


def _unsupported_retail_or_operating_terms(text, evidence_text):
    text_low = str(text or "").lower()
    ev_low = str(evidence_text or "").lower()
    unsupported_terms = [
        "freight", "markdown", "promotion", "promotional", "overtime",
        "labor", "churn", "returns", "inventory aging", "demand forecasting",
    ]
    return any(term in text_low and term not in ev_low for term in unsupported_terms)





def _tokens_for_similarity(text):
    return set(re.findall(r"[a-z0-9]+", str(text or "").lower()))


def _similar_text(a, b):
    aw, bw = _tokens_for_similarity(a), _tokens_for_similarity(b)
    if not aw or not bw:
        return False
    return len(aw & bw) / max(1, min(len(aw), len(bw))) >= 0.68


def _main_item_text(item, keys):
    if isinstance(item, dict):
        return " ".join(str(item.get(k, "")) for k in keys if item.get(k))
    return str(item or "")

def _finance_narrative_fix(analysis, metric_cards=None, rag_bundle=None):
    """Generic finance/performance cleanup used for any financial document.

    It keeps a separate core message, prevents positive margin movement from
    being treated as pressure, and avoids company-specific logic. It uses only
    extracted metric labels and retrieved evidence from the current document.
    """
    if not isinstance(analysis, dict):
        return analysis
    domain = analysis.get("domain") or analysis.get("detected_domain") or {}
    domain_key = (domain.get("key") or domain.get("domain") or "") if isinstance(domain, dict) else str(domain)
    text_blob = " ".join(str((item.get("text") if isinstance(item, dict) else item) or "") for item in (rag_bundle or {}).get("evidence_pack", []) or [])
    text_blob += " " + " ".join(str(x) for x in analysis.get("key_findings", []) or [])
    finance_like = "finance" in str(domain_key).lower() or any(t in text_blob.lower() for t in ("revenue", "bookings", "operating margin", "cash flow", "eps", "ebitda"))
    if not finance_like:
        return _ensure_distinct_core_message(analysis) if '_ensure_distinct_core_message' in globals() else analysis

    revenue = _metric_value(metric_cards, analysis, "revenue")
    bookings = _metric_value(metric_cards, analysis, "bookings")
    op_margin = _metric_value(metric_cards, analysis, ["operating margin", "margin"])
    fcf = _metric_value(metric_cards, analysis, ["free cash flow", "cash flow"])
    eps = _metric_value(metric_cards, analysis, "eps")
    ebitda = _metric_value(metric_cards, analysis, "ebitda")

    parts = []
    if revenue:
        parts.append(f"revenue reached {revenue}")
    if bookings:
        parts.append(f"new bookings reached {bookings}")
    if op_margin:
        label = "operating margin"
        # Use adjusted wording only if the document evidence explicitly uses it.
        if "adjusted operating margin" in text_blob.lower():
            label = "adjusted operating margin"
        parts.append(f"{label} was {op_margin}")
    if ebitda and "margin" not in str(ebitda).lower():
        parts.append(f"EBITDA was {ebitda}")
    if eps:
        parts.append(f"EPS was {eps}")
    if fcf:
        parts.append(f"free cash flow was {fcf}")

    # Remove positive-comparison statements mislabeled as pressure/issue.
    existing = []
    for item in analysis.get("explainable_insights", []) or []:
        claim = item.get("claim") if isinstance(item, dict) else str(item)
        if _is_positive_comparison_mislabeled(claim):
            continue
        existing.append(item)

    if len(parts) >= 2:
        summary = "; ".join(parts[:5]) + ", indicating that leadership should evaluate demand, profitability, and cash generation together rather than relying on one isolated metric."
        summary = summary[:1].upper() + summary[1:]
        core = "Core message: assess demand, profitability, and cash generation together rather than treating any single financial metric in isolation."
        ev_ids = list(dict.fromkeys(
            _find_evidence_ids(rag_bundle, "revenue")
            + _find_evidence_ids(rag_bundle, "bookings")
            + _find_evidence_ids(rag_bundle, "operating margin")
            + _find_evidence_ids(rag_bundle, "free cash flow")
            + _find_evidence_ids(rag_bundle, "eps")
        ))[:4]
        first_insight = {
            "claim": summary,
            "evidence_ids": ev_ids,
            "reasoning": "The cited metrics combine demand, profit-quality, and cash-generation evidence, so management should judge the performance story through conversion quality rather than a single metric.",
            "business_implication": "Prioritize actions that sustain demand while protecting profit quality and cash conversion.",
            "confidence": "high" if ev_ids else "medium",
        }
        deduped_existing = []
        for item in existing:
            claim = item.get("claim") if isinstance(item, dict) else str(item)
            if not claim or _similar_text(summary, claim):
                continue
            deduped_existing.append(item)
        analysis["explainable_insights"] = [first_insight] + deduped_existing[:5]
        analysis["insights"] = [first_insight["claim"]] + [str(i.get("claim") if isinstance(i, dict) else i) for i in deduped_existing[:5] if str(i.get("claim") if isinstance(i, dict) else i).strip()]
        analysis["key_findings"] = analysis["insights"][:5]
        analysis["executive_summary"] = summary
        analysis["core_message"] = core
    else:
        analysis["explainable_insights"] = existing[:6]
        analysis = _ensure_distinct_core_message(analysis)

    # Remove unsupported recommendations and generic admin actions.
    cleaned_recs = []
    for rec in analysis.get("recommendations", []) or []:
        rec_text = rec.get("recommendation", "") if isinstance(rec, dict) else str(rec)
        impact_text = rec.get("business_impact", "") if isinstance(rec, dict) else ""
        low_rec = (rec_text + " " + impact_text).lower()
        if any(bad in low_rec for bad in ("assign an owner to validate", "validate the cited evidence", "define a targeted action plan")):
            continue
        if _unsupported_retail_or_operating_terms(rec_text + " " + impact_text, text_blob):
            continue
        cleaned_recs.append(rec)

    generic_finance_recs = []
    if revenue or bookings:
        generic_finance_recs.append({
            "priority": "High",
            "recommendation": "Prioritize growth investments where the document shows the strongest demand evidence, while tracking conversion into operating income and cash flow.",
            "business_impact": "Keeps demand momentum tied to profitable growth rather than volume alone.",
            "evidence_ids": _find_evidence_ids(rag_bundle, "revenue")[:2] + _find_evidence_ids(rag_bundle, "bookings")[:2],
            "reasoning": "Demand evidence supports investment, but management should pair it with profit and cash conversion measures.",
        })
    if op_margin or eps or ebitda:
        generic_finance_recs.append({
            "priority": "High",
            "recommendation": "Protect profitability by reviewing the cited margin, EPS, EBITDA, SG&A, tax, or optimization-cost drivers together.",
            "business_impact": "Improves profit-quality visibility and avoids overreacting to one isolated margin line.",
            "evidence_ids": _find_evidence_ids(rag_bundle, "operating margin")[:2] + _find_evidence_ids(rag_bundle, "eps")[:2],
            "reasoning": "Profitability evidence shows conversion quality, so the action should focus on the actual cited drivers.",
        })
    if fcf:
        generic_finance_recs.append({
            "priority": "Medium",
            "recommendation": "Maintain cash discipline by monitoring free cash flow, working capital, DSO, cash balance, and capital return against the outlook.",
            "business_impact": "Supports shareholder returns and flexibility while growth continues.",
            "evidence_ids": _find_evidence_ids(rag_bundle, "free cash flow")[:2],
            "reasoning": "Cash-flow evidence should be linked to liquidity, capital allocation, and working-capital discipline.",
        })
    seen = {str(r.get("recommendation") if isinstance(r, dict) else r).lower()[:120] for r in cleaned_recs}
    for rec in generic_finance_recs:
        key = rec["recommendation"].lower()[:120]
        if key not in seen:
            cleaned_recs.append(rec)
            seen.add(key)
    analysis["recommendations"] = cleaned_recs[:5]
    return analysis



def _domain_core_message(analysis):
    domain = analysis.get("domain") or analysis.get("detected_domain") or {}
    domain_key = (domain.get("key") or domain.get("domain") or "") if isinstance(domain, dict) else str(domain)
    low = str(domain_key).lower()
    if "legal" in low or "contract" in low:
        return "Core message: prioritize the documented clauses, obligations, and accounts that can change exposure, compliance posture, or renewal control."
    if "medical" in low or "health" in low:
        return "Core message: separate documented clinical signals from interpretation, and route decision-sensitive findings to qualified review before action."
    if "sales" in low:
        return "Core message: evaluate pipeline quality, conversion, retention, and revenue impact together rather than treating volume alone as success."
    if "research" in low:
        return "Core message: judge findings by evidence strength, limitations, effect size, and decision relevance before translating them into recommendations."
    if "finance" in low or any(any(tok in str(m).lower() for tok in ("revenue", "margin", "cash", "eps", "bookings", "ebitda")) for m in analysis.get("metrics", []) or []):
        return "Core message: assess demand, profitability, and cash generation together rather than treating any single financial metric in isolation."
    return "Core message: use the strongest documented evidence to separate what happened, why it matters, and what leadership should do next."


def _ensure_distinct_core_message(analysis):
    """Keep core message visible without forcing it to be different from the summary."""
    core = str(analysis.get("core_message") or "").strip()
    if not core:
        # User preference: restore the previous behavior where the core message
        # can mirror the strongest summary/first insight instead of being forced
        # into a generic distinct statement.
        summary = str(analysis.get("executive_summary") or "").strip()
        insights = analysis.get("explainable_insights") or analysis.get("insights") or analysis.get("key_findings") or []
        first = _main_item_text(insights[0], ("claim", "insight", "text")) if insights else ""
        core = summary or first or _domain_core_message(analysis)
    if core and not core.lower().startswith("core message"):
        core = "Core message: " + core
    analysis["core_message"] = core
    return analysis



def _cleanup_cross_section_duplicates(analysis):
    def dedupe(items, keys):
        out, seen = [], []
        for item in items or []:
            text = _main_item_text(item, keys).strip()
            if not text:
                continue
            if any(_similar_text(text, s) for s in seen):
                continue
            out.append(item)
            seen.append(text)
        return out

    # Insight de-duplication is stricter against the executive summary so the
    # dashboard does not show the same story twice.
    summary_text = str(analysis.get("executive_summary") or "")
    insight_out, seen_insight = [], []
    for item in analysis.get("explainable_insights", []) or []:
        text = _main_item_text(item, ("claim", "reasoning"))
        claim = _main_item_text(item, ("claim",))
        low_claim = re.sub(r"^[\s\u2022•\-–—]+", "", claim.lower())
        if any(bad in low_claim for bad in ("capital return at least", "updated from outlook", "pdf page", "table row")):
            continue
        if insight_out and low_claim.startswith("the document shows") and any(tok in low_claim for tok in ("revenue", "bookings", "cash")):
            continue
        if insight_out and low_claim.startswith(("company continues to expect", "revenue growth (local currency)", "business outlook", "gaap operating margin")):
            continue
        # Keep the first summary insight, but drop later items that are just
        # alternate wording of the same summary.
        if insight_out and (_similar_text(claim, summary_text) or any(_similar_text(text, s) for s in seen_insight)):
            continue
        insight_out.append(item)
        seen_insight.append(text)
        if len(insight_out) >= 6:
            break
    analysis["explainable_insights"] = insight_out[:6]
    if analysis.get("explainable_insights"):
        analysis["insights"] = [str(i.get("claim") if isinstance(i, dict) else i) for i in analysis.get("explainable_insights", [])][:6]
    else:
        analysis["insights"] = dedupe(analysis.get("insights", []), ("",))[:6]
    analysis["key_findings"] = analysis.get("insights", [])[:5]

    risks = dedupe(analysis.get("risks", []), ("risk", "description"))
    risk_texts = [_main_item_text(r, ("risk", "description", "mitigation")) for r in risks]
    opps = []
    for item in dedupe(analysis.get("opportunities", []), ("opportunity", "description")):
        text = _main_item_text(item, ("opportunity", "description"))
        if any(_similar_text(text, r) for r in risk_texts):
            continue
        opps.append(item)
    recs = []
    for item in dedupe(analysis.get("recommendations", []), ("recommendation", "business_impact")):
        text = _main_item_text(item, ("recommendation", "business_impact"))
        if any(bad in text.lower() for bad in ("validate the cited evidence", "assign an owner to validate", "targeted action plan")):
            continue
        recs.append(item)
    analysis["risks"] = risks[:5]
    analysis["opportunities"] = opps[:5]
    analysis["recommendations"] = recs[:5]
    return _ensure_distinct_core_message(analysis)

def synthesize_results(
    chunk_results, original_text, tables, chart_candidates, numbers, metric_cards, sections, rag_bundle=None, domain_result=None
):
    rag_bundle = rag_bundle or {}
    evidence_pack = rag_bundle.get("evidence_pack", [])
    theme_evidence = rag_bundle.get("theme_evidence", {})
    retrieval_stats = rag_bundle.get("retrieval_stats", {})
    domain_result = domain_result or rag_bundle.get("domain") or {"domain": "general", "label": "General Executive Document", "confidence": "low"}
    domain_context = build_domain_prompt_context(domain_result)

    prompt = f"""
You are an executive presentation strategist.

Create a visual-first executive presentation plan from the document.

Return valid JSON only.

SOURCE PRIORITY:
1. DOMAIN-AWARE RAG CONTEXT. Use the detected document domain to reason with the right lens.
2. RETRIEVED EVIDENCE PACK and RAG CONTEXT BY THEME. These are the evidence snippets retrieved from the same uploaded document.
3. EXTRACTED TABLES and DETERMINISTIC CHART CANDIDATES.
4. ORIGINAL DOCUMENT TEXT only for title/context; do not create unsupported claims from it.

STRICT RAG / EXPLAINABILITY RULES:
{domain_context}

- Use only provided source facts.
- Do not invent data, drivers, risks, or recommendations.
- Every insight, risk, opportunity, and recommendation MUST cite at least one evidence ID such as E004.
- Insight claim text MUST be one complete executive sentence that blends fact + driver + implication. Do not output separate phrases beginning with "Implication:" or "Reasoning:".
- Recommendation and risk reasoning may exist in the JSON fields for explainability, but visible claim/description text must read as a blended business conclusion.
- Every recommendation MUST include a reasoning chain internally: evidence → interpretation → action → business impact.
- Every risk MUST include a reasoning chain internally: evidence → why this is a risk → likely business implication.
- If the evidence is weak, mark confidence as "low" and explain what is missing.
- Avoid generic phrases such as "requires attention", "growth opportunity", or "operational challenges" unless backed by a specific document fact.
- Use this insight pattern when possible: metric/change → driver → business implication.
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
  "domain": {{
    "key": "finance/sales/medical/legal/research/general",
    "label": "",
    "confidence": "high/medium/low",
    "why": ""
  }},
  "domain_reasoning_summary": "How the domain lens changed the analysis.",

  "metrics": [
    {{
      "name": "",
      "value": "",
      "interpretation": ""
    }}
  ],

  "key_findings": [],
  "insights": [],
  "explainable_insights": [
    {{
      "claim": "",
      "evidence_ids": ["E001"],
      "reasoning": "Internal evidence-to-implication rationale; do not prefix with Reasoning:",
      "business_implication": "",
      "confidence": "high/medium/low"
    }}
  ],
  "risks": [
    {{
      "risk": "",
      "severity": "High/Medium/Low",
      "description": "",
      "evidence_ids": ["E001"],
      "reasoning": "Evidence → why this is a risk → business implication.",
      "mitigation": ""
    }}
  ],
  "opportunities": [
    {{
      "opportunity": "",
      "description": "",
      "evidence_ids": ["E001"],
      "reasoning": "Evidence → why this is an opportunity → business implication."
    }}
  ],
  "recommendations": [
    {{
      "priority": "High/Medium/Low",
      "recommendation": "",
      "business_impact": "",
      "evidence_ids": ["E001"],
      "reasoning": "Evidence → interpretation → action → expected impact."
    }}
  ],
  "limitations": [],
  "evidence": [
    {{
      "id": "E001",
      "claim": "",
      "supporting_fact": ""
    }}
  ],

  "storyline": [
    {{
      "slide_title": "",
      "layout": "summary_dashboard/kpi_dashboard/performance_dashboard/insight_dashboard/risk_dashboard/opportunity_dashboard/action_tracker/closing_slide",
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
- summary_dashboard: one strong message + 3 short evidence-backed blocks.
- kpi_dashboard: 4 to 6 KPI cards.
- performance_dashboard: one to four charts with an executive interpretation.
- insight_dashboard: 3 to 4 evidence-backed insight cards.
- risk_dashboard: risks with evidence and mitigation.
- opportunity_dashboard: upside levers with evidence.
- action_tracker: recommendations with priority, evidence, reasoning, and impact.
- closing_slide: short final executive message.

TITLE GUIDANCE:
Bad: Revenue by Month
Good: Growth accelerated, but profitability pressure increased

Bad: Risks
Good: Margin, cash, and execution signals require management attention

LIMITS:
- Maximum 10 storyline slides.
- Maximum 8 metrics.
- Maximum 5 bullets per slide.
- Maximum 6 KPI cards.
- Use visual_title only if it exactly matches a chart candidate title.

DOMAIN CLASSIFICATION:
{json.dumps(domain_result, indent=2)}

RAG RETRIEVAL STATS:
{json.dumps(retrieval_stats, indent=2)}

RAG CONTEXT BY THEME:
{json.dumps(theme_evidence, indent=2)}

RETRIEVED EVIDENCE PACK:
{json.dumps(evidence_pack, indent=2)}

ORIGINAL DOCUMENT TEXT FOR CONTEXT ONLY:
{original_text[:8000]}

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

    try:
        output = call_llm(prompt, max_tokens=4500)
        parsed = extract_json(output)
    except Exception as exc:
        print(f"[ai_analyzer] synthesis failed: {exc}")
        parsed = None

    if not parsed:
        fallback = analysis_error(
            tables=tables,
            chart_candidates=chart_candidates,
            metric_cards=metric_cards,
            sections=sections
        )
        fallback = validate_explainable_analysis(fallback, rag_bundle)
        fallback = apply_domain_reasoning_layer(fallback, rag_bundle)
        fallback = _finance_narrative_fix(fallback, metric_cards=metric_cards, rag_bundle=rag_bundle)
        # Do not expose implementation failure language to executives. If the LLM
        # endpoint is unavailable, present the deterministic RAG output as a
        # normal evidence-backed executive summary.
        summary_items = fallback.get("insights") or fallback.get("key_findings") or []
        if summary_items:
            first_summary = str(summary_items[0])
            if not fallback.get("executive_summary") or "converted into an evidence-backed" in str(fallback.get("executive_summary", "")).lower():
                if len(first_summary.split()) >= 28:
                    fallback["executive_summary"] = first_summary[:900]
                else:
                    fallback["executive_summary"] = " ".join(str(x) for x in summary_items[:2])[:900]
            existing_core = str(fallback.get("core_message") or "").strip()
            if not existing_core or existing_core == first_summary[:420]:
                fallback["core_message"] = "Use the evidence-backed signals to prioritize management action without relying on one isolated metric."
        else:
            fallback["executive_summary"] = "The uploaded document was converted into an evidence-backed executive view using extracted metrics, trends, risks, and recommended actions."
            fallback["core_message"] = "Review the evidence-backed signals below."
        fallback = _cleanup_cross_section_duplicates(fallback)
        fallback["visuals"] = build_visuals_from_storyline(fallback.get("storyline", []), chart_candidates)
        return fallback

    analysis = validate_analysis(parsed)
    # Full RAG explainability gate: verifies evidence IDs, attaches evidence text,
    # and replaces unsupported generic claims with deterministic evidence-backed claims.
    analysis = validate_explainable_analysis(analysis, rag_bundle)
    analysis = apply_domain_reasoning_layer(analysis, rag_bundle)
    analysis = _finance_narrative_fix(analysis, metric_cards=metric_cards, rag_bundle=rag_bundle)
    analysis = _cleanup_cross_section_duplicates(analysis)
    analysis.setdefault("storyline", [])

    # FIX: include ALL chart candidates, not just storyline-matched ones
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
    tables           = tables           or []
    chart_candidates = chart_candidates or []
    numbers          = numbers          or []
    metric_cards     = metric_cards     or []
    sections         = sections         or []

    chunk_results = []
    # For large docs, sample evenly across all chunks (not just first 8)
    total = len(chunks)
    if total <= 12:
        selected_chunks = chunks
    else:
        # Sample: first 4, last 4, and middle samples
        step = max(1, total // 6)
        mid_indices = list(range(4, total - 4, step))[:4]
        indices = sorted(set([0, 1, 2, 3] + mid_indices + [total-4, total-3, total-2, total-1]))
        selected_chunks = [chunks[i] for i in indices if i < total]

    for chunk in selected_chunks:
        chunk_results.append(analyze_single_chunk(chunk))

    original_text = "\n\n".join(selected_chunks)

    # Domain-aware layer: classify the uploaded document first, then use that
    # profile to retrieve evidence and reason differently for finance, sales,
    # medical/health, legal, research, or general documents.
    domain_result = classify_document_domain(
        chunks=chunks,
        tables=tables,
        chart_candidates=chart_candidates,
        numbers=numbers,
        metric_cards=metric_cards,
        sections=sections,
    )

    # Full document-local RAG uses ALL chunks and all extracted structured data,
    # not only the sampled chunks used for lightweight chunk summaries. Retrieval
    # lenses are now domain-aware.
    rag_bundle = build_rag_bundle(
        chunks=chunks,
        tables=tables,
        chart_candidates=chart_candidates,
        numbers=numbers,
        metric_cards=metric_cards,
        sections=sections,
        domain_result=domain_result,
    )

    analysis = synthesize_results(
        chunk_results,
        original_text,
        tables,
        chart_candidates,
        numbers,
        metric_cards,
        sections,
        rag_bundle=rag_bundle,
        domain_result=domain_result
    )

    analysis["tables"]           = tables
    analysis["chart_candidates"] = chart_candidates
    analysis["numbers"]          = numbers
    analysis["metric_cards"]     = metric_cards
    analysis["sections"]         = sections
    analysis["detected_domain"]  = domain_result

    return analysis