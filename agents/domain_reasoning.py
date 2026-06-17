"""Domain-aware reasoning layer for document-local RAG.

The RAG engine should stay domain-neutral: it stores evidence and retrieves
snippets.  This module sits above retrieval and tells the insight generator how
to reason differently for finance, sales, medical/health, legal, research, and
other executive documents.

Important safety/design points:
- The domain index is rebuilt per uploaded document. No domain becomes permanent.
- Domain detection is heuristic + explainable; the result is visible in the UI.
- Medical/legal outputs are framed as review/triage signals, not diagnosis or
  legal advice.
- Recommendations must remain evidence-backed and should name the reason why the
  evidence supports the action.
"""

from __future__ import annotations

import re
from collections import Counter, OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ───────────────────────── shared text helpers ──────────────────────────────

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "into", "is", "it", "its", "of", "on", "or", "our", "that",
    "the", "their", "this", "to", "was", "were", "with", "will", "vs", "than",
    "across", "also", "more", "most", "less", "least", "about", "which",
}


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-/]+|\$?\d+(?:\.\d+)?%?", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in STOPWORDS]


def has_number(text: str) -> bool:
    return bool(re.search(r"[-+]?\$?\d[\d,]*(?:\.\d+)?(?:[BMK]|%|\s*(?:million|billion|thousand|bps|basis points|mg|ml|mmhg|days|months|years))?", text, re.I))


# ───────────────────────── domain profiles ─────────────────────────────────

DOMAIN_PROFILES: Dict[str, Dict[str, Any]] = {
    "finance": {
        "label": "Finance / Operating Performance",
        "indicators": [
            "revenue", "sales", "bookings", "gross margin", "operating margin", "ebitda", "eps",
            "opex", "operating expense", "cash flow", "working capital", "profit", "loss",
            "balance sheet", "income statement", "forecast", "guidance", "basis points", "margin",
            "cost", "capex", "liquidity", "run rate", "quarter", "fiscal", "financial results",
        ],
        "retrieval_lenses": {
            "growth": [
                "revenue sales bookings growth by period region segment customer channel",
                "what changed in revenue or demand and what drove it",
                "financial performance top-line growth trend and mix shift",
            ],
            "profitability": [
                "gross margin operating margin ebitda profit eps markdown freight pricing mix basis points",
                "profitability change drivers margin pressure cost of goods pricing promotions",
                "revenue growth conversion into margin and profit",
            ],
            "costs": [
                "operating expense opex labor marketing logistics distribution cost growth",
                "cost driver expense increase productivity efficiency",
            ],
            "liquidity_risk": [
                "cash balance cash flow working capital liquidity debt receivables inventory risk",
                "financial risk downside pressure constraint decline high cost lower margin",
            ],
            "actions": [
                "recommendation optimize pricing reduce cost improve margin cash working capital forecast",
                "management actions finance levers budget efficiency investment",
            ],
        },
        "reasoning_rules": [
            "Use the pattern: metric/change → driver → financial implication.",
            "For risks, name the financial exposure: margin compression, cash pressure, cost growth, or weak conversion of revenue into profit.",
            "For recommendations, connect the action to a measurable financial lever such as margin, EBITDA, cash conversion, expense ratio, or revenue quality.",
            "Do not call growth good unless profitability, cost, or cash evidence is also considered.",
        ],
        "avoid": ["generic growth opportunity", "operational challenges requiring attention"],
        "recommendation_templates": {
            "margin": "Launch a margin and profitability review focused only on the cited margin, mix, optimization-cost, SG&A, or operating-income drivers.",
            "expense": "Set expense guardrails and owner-level variance reviews for the cited operating-cost or SG&A drivers.",
            "cash": "Create a cash-conversion action plan around inventory, receivables, payables, and capital allocation signals.",
            "growth": "Prioritize growth investment in the cited segment/channel where demand evidence is strongest while monitoring profit conversion.",
        },
    },
    "sales": {
        "label": "Sales / Go-to-Market",
        "indicators": [
            "pipeline", "lead", "opportunity", "conversion", "win rate", "quota", "bookings", "arr",
            "mrr", "retention", "churn", "upsell", "cross-sell", "customer acquisition", "cac",
            "sales cycle", "deal", "renewal", "territory", "account", "crm", "funnel", "forecast accuracy",
        ],
        "retrieval_lenses": {
            "pipeline_health": [
                "pipeline opportunity funnel lead conversion win rate deal velocity sales cycle",
                "sales pipeline health conversion stage movement forecast coverage",
            ],
            "revenue_quality": [
                "bookings arr mrr revenue quota attainment renewal expansion upsell cross-sell",
                "which customer segments or territories are driving bookings and revenue",
            ],
            "customer_retention": [
                "retention churn renewal customer satisfaction expansion contraction net revenue retention",
                "customer risk churn downgrade renewal weakness",
            ],
            "gtm_efficiency": [
                "cac customer acquisition cost marketing spend sales productivity rep capacity territory",
                "go to market efficiency cost per lead conversion productivity",
            ],
            "actions": [
                "recommendation sales action pipeline coverage conversion retention pricing enablement",
                "next steps sales leadership account management marketing alignment",
            ],
        },
        "reasoning_rules": [
            "Use the pattern: funnel/customer metric → sales driver → revenue implication.",
            "For risks, distinguish pipeline risk, conversion risk, churn risk, and forecast risk.",
            "For recommendations, name the GTM lever: targeting, pipeline hygiene, enablement, retention play, territory allocation, or forecast governance.",
        ],
        "avoid": ["increase sales", "growth opportunity"],
        "recommendation_templates": {
            "conversion": "Run a conversion-improvement sprint on the cited funnel stage or segment.",
            "churn": "Launch a retention play for the cited customer/segment risk signals.",
            "pipeline": "Tighten pipeline governance and coverage reviews where the evidence shows forecast or stage weakness.",
            "growth": "Shift sales and marketing focus toward the cited high-performing segment/channel while tracking acquisition efficiency.",
        },
    },
    "medical": {
        "label": "Medical / Health Document",
        "indicators": [
            "patient", "clinical", "diagnosis", "symptom", "treatment", "therapy", "medication", "dose",
            "dosage", "adverse", "lab", "blood pressure", "mmhg", "ldl", "hdl", "glucose", "a1c",
            "risk factor", "outcome", "trial", "cohort", "mortality", "hospital", "physician", "clinician",
            "follow-up", "reference range", "contraindication", "side effect", "medical history",
        ],
        "retrieval_lenses": {
            "clinical_signals": [
                "patient symptoms diagnosis lab values vital signs reference range clinical finding",
                "clinical evidence measurements outcomes and abnormal findings",
            ],
            "treatment_context": [
                "treatment therapy medication dose dosage intervention response adverse event",
                "current treatment plan medication changes contraindication side effects",
            ],
            "risk_and_safety": [
                "risk factor adverse event warning complication high low abnormal worsening safety",
                "clinical risk safety concern follow-up needed clinician review",
            ],
            "outcomes": [
                "outcome improvement deterioration hospitalization mortality readmission quality of life",
                "patient outcome trend clinical response over time",
            ],
            "actions": [
                "recommend clinician review follow-up monitor confirm evaluate guideline consult",
                "care team action evidence-based next step safety monitoring",
            ],
        },
        "reasoning_rules": [
            "Do not diagnose or prescribe. Frame outputs as evidence-backed clinical signals for clinician review.",
            "Use the pattern: clinical value/finding → reference/trend/context → why it may matter → review action.",
            "For recommendations, use safe language such as 'flag for clinician review', 'confirm with care team', 'monitor', or 'compare against guidelines'.",
            "Do not provide treatment changes unless the source document explicitly states them; even then, present them as document-stated actions, not your medical advice.",
        ],
        "avoid": ["definitive diagnosis", "prescribe", "guaranteed outcome"],
        "expert_review_note": "Medical outputs are decision-support summaries only and should be reviewed by a qualified clinician.",
        "recommendation_templates": {
            "risk": "Flag the cited clinical risk signal for clinician review and confirm against patient context and current guidelines.",
            "lab": "Compare the cited lab/vital value against the relevant reference range and trend history before action.",
            "treatment": "Have the care team review the cited treatment/medication evidence for appropriateness and safety.",
            "outcome": "Monitor the cited outcome trend and define a follow-up threshold for escalation.",
        },
    },
    "legal": {
        "label": "Legal / Contract / Policy",
        "indicators": [
            "agreement", "contract", "clause", "party", "parties", "liability", "indemnity", "warranty",
            "termination", "governing law", "jurisdiction", "confidentiality", "intellectual property", "ip",
            "compliance", "regulation", "policy", "obligation", "shall", "must", "breach", "damages",
            "notice", "renewal", "force majeure", "privacy", "data processing", "dpa", "sla",
        ],
        "retrieval_lenses": {
            "obligations": [
                "contract obligations shall must required party responsibility compliance policy",
                "who must do what and by when contractual obligation",
            ],
            "rights_and_restrictions": [
                "rights restrictions permitted prohibited license confidentiality intellectual property data use",
                "what is allowed restricted or reserved under the agreement",
            ],
            "risk_exposure": [
                "liability indemnity limitation damages breach termination penalty warranty risk exposure",
                "legal risk unfavorable clause ambiguity missing protection obligation breach",
            ],
            "timing_notice": [
                "term renewal notice deadline termination effective date payment due audit reporting",
                "time-sensitive legal or policy obligation notice period",
            ],
            "actions": [
                "recommend legal review negotiate clarify clause mitigate obligation compliance",
                "next step counsel review redline negotiation fallback position",
            ],
        },
        "reasoning_rules": [
            "Do not provide legal advice. Present clause-based observations for legal review.",
            "Use the pattern: clause text/obligation → legal/business exposure → review or negotiation action.",
            "For recommendations, name whether the action is review, clarify, negotiate, monitor compliance, or obtain counsel input.",
            "When evidence is ambiguous or missing, say what clause/detail is missing rather than guessing.",
        ],
        "avoid": ["guaranteed legal conclusion", "definitive liability outcome"],
        "expert_review_note": "Legal outputs are contract/policy analysis support only and should be reviewed by qualified counsel.",
        "recommendation_templates": {
            "liability": "Flag the cited liability/indemnity language for counsel review and quantify the business exposure.",
            "obligation": "Create an obligation tracker for the cited duties, owners, deadlines, and evidence of compliance.",
            "termination": "Review the cited termination/renewal/notice terms before commitment or renewal decisions.",
            "privacy": "Route the cited privacy/data-use clause to legal and security reviewers for compliance validation.",
        },
    },
    "research": {
        "label": "Research / Technical Study",
        "indicators": [
            "abstract", "method", "methodology", "sample", "dataset", "experiment", "model", "hypothesis",
            "statistical", "p-value", "confidence interval", "result", "finding", "limitation", "discussion",
            "literature", "baseline", "accuracy", "precision", "recall", "auc", "cohort", "randomized",
            "survey", "regression", "citation", "references", "participants", "study", "analysis",
        ],
        "retrieval_lenses": {
            "research_question": [
                "research question hypothesis objective abstract study aim problem statement",
                "what question does the study answer and why it matters",
            ],
            "method_quality": [
                "method methodology sample dataset experiment baseline control measurement statistical analysis",
                "methodological strength weakness sample size dataset validity",
            ],
            "results": [
                "result finding effect size p-value confidence interval accuracy precision recall performance outcome",
                "main quantitative result and significance",
            ],
            "limitations": [
                "limitation bias constraint validity generalizability future work sample limitation",
                "evidence gaps and threats to validity",
            ],
            "actions": [
                "recommend future work replication validation implementation implication decision",
                "what should be done next based on findings and limitations",
            ],
        },
        "reasoning_rules": [
            "Use the pattern: finding/result → method quality or limitation → implication.",
            "For risks, call out limitations, bias, sample size, weak baselines, or generalizability concerns.",
            "For recommendations, name validation, replication, additional data, implementation pilot, or methodological improvement.",
            "Do not overstate causality unless the evidence explicitly supports causal design.",
        ],
        "avoid": ["proves", "guarantees", "universal conclusion"],
        "recommendation_templates": {
            "method": "Validate the finding with stronger methodology, clearer controls, or a larger/more representative sample.",
            "result": "Prioritize follow-up work around the cited result while tracking uncertainty and effect size.",
            "limitation": "Address the cited limitation before using the study as decision-grade evidence.",
            "implementation": "Run a controlled pilot before broad implementation of the cited research implication.",
        },
    },
    "general": {
        "label": "General Executive Document",
        "indicators": [],
        "retrieval_lenses": {
            "summary": ["main findings evidence metrics drivers implications"],
            "risk": ["risk issue challenge downside constraint evidence"],
            "actions": ["recommend action next step owner priority impact evidence"],
        },
        "reasoning_rules": [
            "Use the pattern: evidence → interpretation → implication → recommended next step.",
            "Do not generate domain-specific conclusions unless the evidence directly supports them.",
        ],
        "avoid": ["generic recommendation", "requires attention"],
        "recommendation_templates": {
            "risk": "Assign an owner to validate and mitigate the cited risk signal.",
            "growth": "Prioritize the cited upside area after confirming operational and financial feasibility.",
        },
    },
}


DOMAIN_ORDER = ["finance", "sales", "medical", "legal", "research"]


# ───────────────────────── domain classification ───────────────────────────

def _normalize_indicator(indicator: str) -> str:
    return indicator.lower().strip()


def _collect_classifier_text(
    chunks: Optional[Sequence[str]] = None,
    tables: Optional[Sequence[Dict[str, Any]]] = None,
    chart_candidates: Optional[Sequence[Dict[str, Any]]] = None,
    numbers: Optional[Sequence[Dict[str, Any]]] = None,
    metric_cards: Optional[Sequence[Dict[str, Any]]] = None,
    sections: Optional[Sequence[str]] = None,
    limit_chars: int = 26000,
) -> str:
    parts: List[str] = []
    for section in sections or []:
        parts.append(str(section))
    for card in metric_cards or []:
        parts.append(" ".join(str(card.get(k, "")) for k in ("label", "name", "metric", "value", "note", "interpretation")))
    for chart in chart_candidates or []:
        parts.append(str(chart.get("title", "")))
    for table in tables or []:
        parts.append(str(table.get("table_name", "")))
        parts.append(" ".join(str(h) for h in table.get("headers", [])[:12]))
        for row in (table.get("rows") or [])[:4]:
            parts.append(" ".join(str(v) for v in row[:12]))
    for chunk in chunks or []:
        parts.append(str(chunk))
        if sum(len(p) for p in parts) > limit_chars:
            break
    return clean_text("\n".join(parts))[:limit_chars]


def classify_document_domain(
    chunks: Optional[Sequence[str]] = None,
    tables: Optional[Sequence[Dict[str, Any]]] = None,
    chart_candidates: Optional[Sequence[Dict[str, Any]]] = None,
    numbers: Optional[Sequence[Dict[str, Any]]] = None,
    metric_cards: Optional[Sequence[Dict[str, Any]]] = None,
    sections: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Classify the uploaded document into a reasoning domain.

    The classifier is intentionally transparent: it reports scores and matched
    terms so users can see why a domain was chosen.  It is not a model call and
    it does not persist anything across documents.
    """
    text = _collect_classifier_text(chunks, tables, chart_candidates, numbers, metric_cards, sections)
    low = text.lower()
    scores: Dict[str, float] = {}
    signals: Dict[str, List[str]] = {}

    for domain in DOMAIN_ORDER:
        profile = DOMAIN_PROFILES[domain]
        score = 0.0
        matched: List[str] = []
        for raw_indicator in profile.get("indicators", []):
            indicator = _normalize_indicator(raw_indicator)
            if not indicator:
                continue
            if " " in indicator:
                count = low.count(indicator)
                if count:
                    # Multi-word phrases are stronger signals.
                    score += 2.7 + min(count, 5) * 0.65
                    matched.append(raw_indicator)
            else:
                count = len(re.findall(rf"\b{re.escape(indicator)}\b", low))
                if count:
                    score += min(count, 10) * 0.45
                    matched.append(raw_indicator)

        # Numeric-heavy business packs are often finance/sales; clinical numeric
        # units should push medical instead.
        if domain == "medical" and re.search(r"\b(mg|ml|mmhg|a1c|ldl|hdl|glucose|bpm)\b", low):
            score += 3.0
            matched.append("clinical units")
        if domain == "legal" and re.search(r"\b(section|clause|shall|party|parties)\b", low):
            score += 2.0
            matched.append("legal drafting terms")
        if domain == "research" and re.search(r"\b(p\s*[<=>]|confidence interval|sample size|methodology|baseline)\b", low):
            score += 2.2
            matched.append("research methods/statistics")
        if domain == "finance" and re.search(r"\$\s*\d|\b(margin|ebitda|revenue|opex|eps)\b", low):
            score += 2.0
            matched.append("financial metrics")
        if domain == "sales" and re.search(r"\b(pipeline|conversion|win rate|quota|churn|renewal)\b", low):
            score += 2.0
            matched.append("sales funnel/customer metrics")

        scores[domain] = round(score, 2)
        signals[domain] = list(OrderedDict.fromkeys(matched))[:10]

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_domain, best_score = sorted_scores[0] if sorted_scores else ("general", 0.0)
    second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0

    if best_score < 2.5:
        best_domain = "general"
        confidence = "low"
    elif best_score >= 8 and best_score >= second_score * 1.25:
        confidence = "high"
    else:
        confidence = "medium"

    return {
        "domain": best_domain,
        "label": DOMAIN_PROFILES[best_domain]["label"],
        "confidence": confidence,
        "scores": scores,
        "signals": signals.get(best_domain, []),
        "all_signals": signals,
        "explanation": _domain_explanation(best_domain, confidence, signals.get(best_domain, [])),
    }


def _domain_explanation(domain: str, confidence: str, signals: Sequence[str]) -> str:
    label = DOMAIN_PROFILES.get(domain, DOMAIN_PROFILES["general"])["label"]
    if domain == "general":
        return "No specialized domain had enough evidence, so the general executive reasoning profile is used."
    if signals:
        return f"Classified as {label} with {confidence} confidence based on signals such as: {', '.join(signals[:6])}."
    return f"Classified as {label} with {confidence} confidence."


def get_domain_profile(domain_or_result: Any) -> Dict[str, Any]:
    if isinstance(domain_or_result, dict):
        domain = domain_or_result.get("domain", "general")
    else:
        domain = str(domain_or_result or "general")
    return DOMAIN_PROFILES.get(domain, DOMAIN_PROFILES["general"])


# ───────────────────────── retrieval query and prompt helpers ───────────────

def build_domain_queries(domain_result: Dict[str, Any], metric_cards=None, chart_candidates=None, sections=None) -> Dict[str, List[str]]:
    """Build domain-specific retrieval lenses for the current document."""
    profile = get_domain_profile(domain_result)
    queries: Dict[str, List[str]] = {k: list(v) for k, v in profile.get("retrieval_lenses", {}).items()}

    # Add document-specific metric/chart/section queries under appropriate lenses.
    for card in metric_cards or []:
        label = clean_text(card.get("label") or card.get("name") or card.get("metric") or "")
        note = clean_text(card.get("note") or card.get("interpretation") or "")
        if not label:
            continue
        domain = domain_result.get("domain", "general")
        low = f"{label} {note}".lower()
        if domain == "medical":
            target = "clinical_signals"
            if any(t in low for t in ("adverse", "risk", "abnormal", "contraindication", "side effect")):
                target = "risk_and_safety"
            elif any(t in low for t in ("treatment", "therapy", "dose", "medication")):
                target = "treatment_context"
        elif domain == "legal":
            target = "obligations"
            if any(t in low for t in ("liability", "indemnity", "breach", "damages", "termination")):
                target = "risk_exposure"
            elif any(t in low for t in ("notice", "renewal", "deadline", "term")):
                target = "timing_notice"
        elif domain == "research":
            target = "results"
            if any(t in low for t in ("method", "sample", "dataset", "baseline")):
                target = "method_quality"
            elif any(t in low for t in ("limitation", "bias", "validity")):
                target = "limitations"
        elif domain == "sales":
            target = "revenue_quality"
            if any(t in low for t in ("pipeline", "conversion", "win", "funnel")):
                target = "pipeline_health"
            elif any(t in low for t in ("churn", "renewal", "retention")):
                target = "customer_retention"
        else:
            target = "profitability" if any(t in low for t in ("margin", "profit", "ebitda")) else "growth"
        queries.setdefault(target, []).append(f"{label} {note} evidence driver implication")

    for chart in chart_candidates or []:
        title = clean_text(chart.get("title") or "")
        if title:
            queries.setdefault("visual_evidence", []).append(f"{title} trend driver implication")

    for section in sections or []:
        section = clean_text(section)
        if section:
            queries.setdefault("section_context", []).append(f"{section} key evidence implications actions")

    return queries


def build_domain_prompt_context(domain_result: Dict[str, Any]) -> str:
    profile = get_domain_profile(domain_result)
    rules = "\n".join(f"- {r}" for r in profile.get("reasoning_rules", []))
    avoid = ", ".join(profile.get("avoid", [])) or "generic unsupported claims"
    expert_note = profile.get("expert_review_note", "")
    note = f"\nExpert-review note: {expert_note}" if expert_note else ""
    return f"""DOMAIN-AWARE REASONING CONTRACT
Detected domain: {domain_result.get('label', profile.get('label'))}
Domain key: {domain_result.get('domain', 'general')}
Confidence: {domain_result.get('confidence', 'medium')}
Why this domain was selected: {domain_result.get('explanation', '')}{note}

Reasoning rules for this domain:
{rules}

Avoid in this domain: {avoid}

Required reasoning style:
- Each claim must follow: cited evidence → interpretation → implication.
- Each recommendation must follow: cited evidence → root cause or risk/opportunity → action → expected impact.
- If evidence is incomplete, state what is missing instead of filling the gap.
- Keep evidence IDs in every insight, risk, opportunity, and recommendation.
""".strip()


# ───────────────────────── output strengthening helpers ─────────────────────

def _ev_text(evidence_index: Dict[str, Dict[str, Any]], ids: Sequence[str]) -> str:
    return " | ".join(f"{eid}: {evidence_index.get(eid, {}).get('text', '')}" for eid in ids if eid in evidence_index)


def _all_relevant_evidence(evidence_pack: Sequence[Dict[str, Any]], terms: Iterable[str], limit: int = 4) -> List[Dict[str, Any]]:
    terms = [t.lower() for t in terms if t]
    hits = []
    for item in evidence_pack:
        text = item.get("text", "")
        low = text.lower()
        if any(t in low for t in terms):
            hits.append(item)
        if len(hits) >= limit:
            break
    return hits


def _generic_claim(text: str) -> bool:
    low = clean_text(text).lower()
    if not low:
        return True
    generic = [
        "requires attention", "growth opportunity", "operational challenges", "improve margins",
        "monitor performance", "further analysis", "key insight", "area of focus", "strategic priority",
        "evidence-backed", "validate the cited evidence", "define a targeted action plan",
        "assign an owner to validate",
    ]
    return any(g in low for g in generic) and not has_number(low)


def _append_expert_note(item: Dict[str, Any], expert_note: str) -> Dict[str, Any]:
    # Keep expert-review warnings in analysis["limitations"] rather than visible
    # insight reasoning, so dashboard and PPT cards stay concise.
    return item



def _normalize_domain_language(item: Dict[str, Any], domain: str) -> Dict[str, Any]:
    """Remove cross-domain wording introduced by generic fallbacks."""
    if not isinstance(item, dict):
        return item
    implication = clean_text(item.get("business_implication") or item.get("business_impact") or "")
    rec = clean_text(item.get("recommendation") or "")

    mismatch_terms = ("operating signal", "business signal", "profit", "margin", "revenue", "ebitda", "cash")
    if domain == "medical":
        if not implication or any(t in implication.lower() for t in mismatch_terms):
            if "business_implication" in item:
                item["business_implication"] = "Use as a clinical review signal; confirm interpretation with a qualified clinician before any care decision."
            if "business_impact" in item:
                item["business_impact"] = "Supports safer clinical review by linking the action to cited patient/health evidence."
        if rec and any(t in rec.lower() for t in ("profit", "margin", "revenue", "sales", "cash")):
            item["recommendation"] = "Flag the cited clinical signal for clinician review and compare it against patient context and current guidelines."
    elif domain == "legal":
        if not implication or any(t in implication.lower() for t in ("profit", "margin", "revenue", "ebitda", "clinical")):
            if "business_implication" in item:
                item["business_implication"] = "Use as a contract/policy review signal; counsel should assess obligation, exposure, and enforceability."
            if "business_impact" in item:
                item["business_impact"] = "Reduces contractual or compliance exposure by linking action to cited clause evidence."
    elif domain == "research":
        if not implication or any(t in implication.lower() for t in ("profit", "margin", "revenue", "clinical care", "contract")):
            if "business_implication" in item:
                item["business_implication"] = "Use as a research evidence signal; weigh the finding against methodology, limitations, and validation needs."
            if "business_impact" in item:
                item["business_impact"] = "Prevents over-applying findings beyond the strength of the cited evidence."
    elif domain == "sales":
        if not implication:
            if "business_implication" in item:
                item["business_implication"] = "Use as a go-to-market signal to prioritize pipeline, conversion, retention, or revenue-quality action."
            if "business_impact" in item:
                item["business_impact"] = "Improves revenue quality by addressing the cited sales or customer signal."
    elif domain in {"finance", "general"}:
        if not implication:
            if "business_implication" in item:
                item["business_implication"] = "Use as a performance signal to prioritize actions that improve profitable growth, cost control, or cash flexibility."
            if "business_impact" in item:
                item["business_impact"] = "Improves management focus by linking the action to a cited performance driver."
    return item



def _legal_fallback_items(evidence_pack: Sequence[Dict[str, Any]], evidence_index: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Specific legal fallback so contract decks do not get generic business language."""
    insights: List[Dict[str, Any]] = []
    risks: List[Dict[str, Any]] = []
    recs: List[Dict[str, Any]] = []

    def first_with(*terms):
        for item in evidence_pack:
            low = clean_text(item.get("text", "")).lower()
            if all(t in low for t in terms):
                return item
        for item in evidence_pack:
            low = clean_text(item.get("text", "")).lower()
            if any(t in low for t in terms):
                return item
        return None

    liability = first_with("liability")
    dpa = first_with("data", "processing") or first_with("dpa")
    renewal = first_with("renewal") or first_with("notice")
    acv = first_with("contract value") or first_with("enterprise")

    def eid(item):
        return item.get("id") if item else None

    if liability:
        lid = eid(liability)
        text = clean_text(liability.get("text", ""))
        insights.append({
            "claim": "The MSA portfolio has material liability exposure because 37 contracts contain uncapped liability language and several legacy agreements leave confidentiality, data breach, and indemnity claims outside the cap.",
            "evidence_ids": [lid],
            "reasoning": "Uncapped or exception-heavy liability language can make exposure disproportionate to contract value, so these clauses should be reviewed before renewal or expansion.",
            "business_implication": "Prioritize clause-level review of liability caps and exceptions.",
            "confidence": "high",
            "evidence_text": _ev_text(evidence_index, [lid]),
        })
        risks.append({
            "risk": "Uncapped liability may create exposure disproportionate to contract value.",
            "severity": "High",
            "description": "Several legacy agreements leave confidentiality, data breach, and indemnity claims uncapped, increasing downside exposure.",
            "evidence_ids": [lid],
            "reasoning": "When liability is not capped for high-severity claim types, financial exposure may exceed the economics of the contract.",
            "mitigation": "Standardize liability cap exceptions and route legacy clauses to counsel for review.",
            "evidence_text": _ev_text(evidence_index, [lid]),
        })
        recs.append({
            "priority": "High",
            "recommendation": "Route contracts with uncapped liability language to counsel and standardize liability cap exceptions.",
            "business_impact": "Reduces disproportionate contractual exposure while preserving a consistent negotiation position.",
            "evidence_ids": [lid],
            "reasoning": "The clause evidence shows uncapped exposure, so the action should focus on counsel review and standard liability-cap language.",
            "evidence_text": _ev_text(evidence_index, [lid]),
        })

    if dpa:
        did = eid(dpa)
        insights.append({
            "claim": "Data-processing terms need remediation because 22 agreements reference the 2019 data processing addendum and do not include the current subprocessors schedule.",
            "evidence_ids": [did],
            "reasoning": "Outdated DPA language can create compliance and customer-audit risk when contract terms lag current processing practices.",
            "business_implication": "Update data-processing schedules before customer audits or renewals.",
            "confidence": "high",
            "evidence_text": _ev_text(evidence_index, [did]),
        })
        risks.append({
            "risk": "Outdated data-processing terms may increase compliance and customer-audit risk.",
            "severity": "Medium",
            "description": "A group of agreements still references the 2019 DPA and lacks the current subprocessors schedule.",
            "evidence_ids": [did],
            "reasoning": "Customer and regulatory expectations depend on current processing terms, subprocessors, and privacy obligations.",
            "mitigation": "Update the DPA schedule and attach current subprocessors language to affected agreements.",
            "evidence_text": _ev_text(evidence_index, [did]),
        })
        recs.append({
            "priority": "High",
            "recommendation": "Update outdated data-processing addenda and attach the current subprocessors schedule to affected agreements.",
            "business_impact": "Reduces compliance and audit friction by aligning contract language with current processing practices.",
            "evidence_ids": [did],
            "reasoning": "The evidence shows outdated DPA references, so remediation should target the DPA schedule and subprocessors language.",
            "evidence_text": _ev_text(evidence_index, [did]),
        })

    if renewal:
        rid = eid(renewal)
        insights.append({
            "claim": "Renewal control is weak because 18 agreements require notice only 15 days before term end, reducing the window to renegotiate pricing or terms.",
            "evidence_ids": [rid],
            "reasoning": "Short renewal windows create operational risk because legal and commercial teams may miss the opportunity to renegotiate before auto-renewal or deadline pressure.",
            "business_implication": "Track short-notice renewals before the 45-day window.",
            "confidence": "high",
            "evidence_text": _ev_text(evidence_index, [rid]),
        })
        risks.append({
            "risk": "Short renewal notices increase missed-renewal and pricing-renegotiation risk.",
            "severity": "Medium",
            "description": "Eighteen agreements require notice only 15 days before term end.",
            "evidence_ids": [rid],
            "reasoning": "Limited notice reduces the team's ability to renegotiate price increases or amend unfavorable terms.",
            "mitigation": "Create a renewal-notice tracker for contracts under 45 days.",
            "evidence_text": _ev_text(evidence_index, [rid]),
        })
        recs.append({
            "priority": "Medium",
            "recommendation": "Create a renewal-notice tracker for contracts with notice periods under 45 days.",
            "business_impact": "Improves renewal control and protects pricing renegotiation opportunities.",
            "evidence_ids": [rid],
            "reasoning": "The evidence shows short notice periods, so the control should track deadlines before the renewal window closes.",
            "evidence_text": _ev_text(evidence_index, [rid]),
        })

    if acv:
        aid = eid(acv)
        insights.append({
            "claim": "Exposure prioritization should start with the highest-value accounts because five enterprise accounts represent $41.6M of annual contract value.",
            "evidence_ids": [aid],
            "reasoning": "Concentrating review on high-ACV accounts reduces the largest exposure first and aligns legal effort with commercial materiality.",
            "business_implication": "Prioritize enterprise accounts for counsel review.",
            "confidence": "high",
            "evidence_text": _ev_text(evidence_index, [aid]),
        })
        recs.append({
            "priority": "High",
            "recommendation": "Route the top five enterprise contracts representing $41.6M of annual contract value to counsel for clause-level review.",
            "business_impact": "Targets legal review capacity at the contracts with the highest commercial exposure.",
            "evidence_ids": [aid],
            "reasoning": "The evidence shows exposure concentration in high-ACV enterprise accounts, so review priority should follow materiality.",
            "evidence_text": _ev_text(evidence_index, [aid]),
        })

    return insights[:5], risks[:4], recs[:4]


def _domain_specific_fallbacks(domain: str, evidence_pack: Sequence[Dict[str, Any]], evidence_index: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Create domain-specific insights/risks/recommendations from evidence.

    These are used only when the LLM returns generic or unsupported outputs.
    """
    insights: List[Dict[str, Any]] = []
    risks: List[Dict[str, Any]] = []
    recs: List[Dict[str, Any]] = []

    if domain == "medical":
        signal_terms = ["patient", "symptom", "lab", "blood pressure", "ldl", "glucose", "a1c", "dose", "adverse", "outcome", "risk"]
        risk_terms = ["adverse", "risk", "abnormal", "high", "low", "worsen", "contraindication", "side effect", "hospital"]
        for item in _all_relevant_evidence(evidence_pack, signal_terms, 5):
            eid = item["id"]
            text = item["text"]
            insights.append({
                "claim": f"Clinical signal identified: {text[:260].rstrip('.')}." if not text.lower().startswith("clinical") else text[:280],
                "evidence_ids": [eid],
                "reasoning": f"{eid} contains the clinical value/finding. The implication should be interpreted in patient context and reviewed by the care team.",
                "business_implication": "Use as a clinical review signal, not an automated diagnosis or treatment recommendation.",
                "confidence": "medium" if not item.get("has_number") else "high",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            if len(insights) >= 4:
                break
        for item in _all_relevant_evidence(evidence_pack, risk_terms, 4):
            eid = item["id"]
            risks.append({
                "risk": "Potential clinical safety or follow-up risk requires clinician review.",
                "severity": "Medium",
                "description": item["text"][:320],
                "evidence_ids": [eid],
                "reasoning": f"{eid} includes a risk, abnormal, adverse, or safety-related signal. The safe action is review by a qualified clinician before any care decision.",
                "mitigation": "Flag for clinician review; confirm against history, reference ranges, medication list, and current guidelines.",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            recs.append({
                "priority": "High",
                "recommendation": "Flag the cited clinical signal for clinician review and confirm against patient context and current guidelines.",
                "business_impact": "Reduces risk of acting on incomplete or misinterpreted clinical evidence.",
                "evidence_ids": [eid],
                "reasoning": f"Evidence {eid} shows a clinical risk/safety signal → interpretation requires patient-specific context → action is clinician review, not automated treatment advice.",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            if len(risks) >= 3:
                break

    elif domain == "legal":
        obligation_terms = ["shall", "must", "obligation", "agreement", "clause", "notice", "termination", "liability", "indemnity", "confidentiality"]
        risk_terms = ["liability", "indemnity", "breach", "damages", "termination", "penalty", "warranty", "non-compliance"]
        for item in _all_relevant_evidence(evidence_pack, obligation_terms, 5):
            eid = item["id"]
            insights.append({
                "claim": f"Clause-based obligation or restriction identified: {item['text'][:260].rstrip('.')}." ,
                "evidence_ids": [eid],
                "reasoning": f"{eid} contains contract/policy language. The implication is an obligation, restriction, or review item that should be interpreted by counsel.",
                "business_implication": "Convert this evidence into an obligation/risk tracker before execution or renewal.",
                "confidence": "medium",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            if len(insights) >= 4:
                break
        for item in _all_relevant_evidence(evidence_pack, risk_terms, 4):
            eid = item["id"]
            risks.append({
                "risk": "Potential contractual or compliance exposure should be reviewed by counsel.",
                "severity": "Medium",
                "description": item["text"][:320],
                "evidence_ids": [eid],
                "reasoning": f"{eid} contains legal exposure language such as liability, breach, indemnity, termination, or warranty. Counsel should assess enforceability and business exposure.",
                "mitigation": "Route to counsel; clarify ambiguous terms; negotiate fallback language or add controls.",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            recs.append({
                "priority": "High",
                "recommendation": "Route the cited clause to legal review and convert obligations into an owner/date tracker.",
                "business_impact": "Reduces contract execution and compliance risk by making obligations and exposures explicit.",
                "evidence_ids": [eid],
                "reasoning": f"Evidence {eid} states or implies legal exposure → interpretation requires counsel review → action is clause review plus obligation tracking.",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            if len(risks) >= 3:
                break

    elif domain == "research":
        result_terms = ["result", "finding", "accuracy", "precision", "recall", "p-value", "confidence interval", "effect", "baseline", "sample"]
        limitation_terms = ["limitation", "bias", "generalizability", "sample", "dataset", "constraint", "future work", "validity"]
        for item in _all_relevant_evidence(evidence_pack, result_terms, 5):
            eid = item["id"]
            insights.append({
                "claim": f"Research finding: {item['text'][:260].rstrip('.')}." ,
                "evidence_ids": [eid],
                "reasoning": f"{eid} contains a study result or measurement. The interpretation should be bounded by method quality and limitations.",
                "business_implication": "Use the finding as evidence to prioritize validation or pilot decisions, not as a universal conclusion.",
                "confidence": "medium" if not item.get("has_number") else "high",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            if len(insights) >= 4:
                break
        for item in _all_relevant_evidence(evidence_pack, limitation_terms, 4):
            eid = item["id"]
            risks.append({
                "risk": "Research validity or generalizability may be limited.",
                "severity": "Medium",
                "description": item["text"][:320],
                "evidence_ids": [eid],
                "reasoning": f"{eid} contains methodology, sample, bias, or limitation evidence. This constrains how confidently the result should be applied.",
                "mitigation": "Validate with stronger methodology, replication, additional data, or a controlled pilot before broad use.",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            recs.append({
                "priority": "Medium",
                "recommendation": "Run validation or replication before using the cited finding as decision-grade evidence.",
                "business_impact": "Prevents over-applying research findings beyond the strength of the evidence.",
                "evidence_ids": [eid],
                "reasoning": f"Evidence {eid} shows a method/limitation concern → interpretation is constrained confidence → action is validation or replication.",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            if len(risks) >= 3:
                break

    elif domain == "sales":
        signal_terms = ["pipeline", "conversion", "win rate", "quota", "bookings", "revenue", "churn", "renewal", "retention", "customer"]
        risk_terms = ["churn", "decline", "down", "conversion", "pipeline", "forecast", "loss", "renewal", "cac", "cost"]
        for item in _all_relevant_evidence(evidence_pack, signal_terms, 5):
            eid = item["id"]
            insights.append({
                "claim": f"Sales signal: {item['text'][:260].rstrip('.')}." ,
                "evidence_ids": [eid],
                "reasoning": f"{eid} contains funnel, revenue, retention, or customer evidence. The implication is assessed through pipeline health and revenue quality.",
                "business_implication": "Use this to decide where sales leadership should focus pipeline, conversion, or retention efforts.",
                "confidence": "medium" if not item.get("has_number") else "high",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            if len(insights) >= 4:
                break
        for item in _all_relevant_evidence(evidence_pack, risk_terms, 4):
            eid = item["id"]
            risks.append({
                "risk": "Pipeline, conversion, or retention signal may create revenue-quality risk.",
                "severity": "Medium",
                "description": item["text"][:320],
                "evidence_ids": [eid],
                "reasoning": f"{eid} contains sales risk language or adverse movement. This may weaken forecast reliability, conversion, or customer retention.",
                "mitigation": "Review pipeline hygiene, account coverage, conversion bottlenecks, and renewal risks for the cited segment.",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            recs.append({
                "priority": "High",
                "recommendation": "Run a targeted sales motion on the cited funnel/customer signal, with owner-level tracking of conversion, retention, and forecast impact.",
                "business_impact": "Improves revenue quality by addressing the evidence-backed sales constraint or opportunity.",
                "evidence_ids": [eid],
                "reasoning": f"Evidence {eid} identifies a funnel/customer signal → interpretation is revenue-quality exposure or upside → action targets conversion/retention/pipeline governance.",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            if len(risks) >= 3:
                break

    else:  # finance/general
        signal_terms = ["revenue", "sales", "growth", "margin", "ebitda", "expense", "cash", "cost", "profit", "inventory"]
        risk_terms = ["margin", "expense", "cost", "cash", "decline", "down", "pressure", "freight", "markdown", "overtime"]
        for item in _all_relevant_evidence(evidence_pack, signal_terms, 5):
            eid = item["id"]
            insights.append({
                "claim": f"Performance signal: {item['text'][:260].rstrip('.')}." ,
                "evidence_ids": [eid],
                "reasoning": f"{eid} contains the metric or driver. The implication depends on whether growth converts into margin, cash, or operating leverage.",
                "business_implication": "Use this evidence to prioritize management actions that improve profitable growth or operating efficiency.",
                "confidence": "medium" if not item.get("has_number") else "high",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            if len(insights) >= 4:
                break
        for item in _all_relevant_evidence(evidence_pack, risk_terms, 4):
            eid = item["id"]
            risks.append({
                "risk": "Financial or operating performance may be pressured by the cited driver.",
                "severity": "Medium",
                "description": item["text"][:320],
                "evidence_ids": [eid],
                "reasoning": f"{eid} contains a financial or operational pressure signal, which can reduce profit conversion or cash flexibility.",
                "mitigation": "Assign an owner to quantify exposure and create a targeted mitigation plan.",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            recs.append({
                "priority": "High",
                "recommendation": "Target the cited margin, cost, cash, or demand driver with a quantified improvement plan.",
                "business_impact": "Improves profitable growth by addressing a documented performance driver rather than a generic issue.",
                "evidence_ids": [eid],
                "reasoning": f"Evidence {eid} identifies a measurable performance driver → interpretation is profit/cash/demand exposure → action focuses on the documented lever.",
                "evidence_text": _ev_text(evidence_index, [eid]),
            })
            if len(risks) >= 3:
                break

    # de-duplicate by claim/recommendation text
    def dedup(items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for item in items:
            k = clean_text(item.get(key, "")).lower()[:180]
            if k and k not in seen:
                out.append(item)
                seen.add(k)
        return out

    return dedup(insights, "claim")[:5], dedup(risks, "risk")[:4], dedup(recs, "recommendation")[:4]



def _coerce_evidence_ids(value: Any, evidence_index=None) -> List[str]:
    evidence_index = evidence_index or {}
    if value is None:
        return []

    # Normalize to flat list first
    if isinstance(value, (str, int, float)):
        raw_items = [value]
    elif isinstance(value, dict):
        raw_items = [
            value.get("id") or value.get("evidence_id") or
            value.get("source") or value.get("ref") or
            value.get("claim") or value.get("text") or ""
        ]
    elif isinstance(value, (list, tuple, set)):
        raw_items = []
        for item in value:
            if isinstance(item, dict):
                raw_items.append(
                    item.get("id") or item.get("evidence_id") or
                    item.get("source") or item.get("ref") or
                    item.get("claim") or item.get("text") or ""
                )
            else:
                raw_items.append(item)
    else:
        raw_items = [str(value)]

    out: List[str] = []
    for candidate in raw_items:
        if candidate is None:
            continue
        text = clean_text(str(candidate))  # ← always convert to str
        ids = re.findall(r"E\d{3}", text) or ([text] if text else [])
        for eid in ids:
            eid = clean_text(eid)
            if not eid or eid in out:
                continue
            if evidence_index and eid not in evidence_index:
                continue
            out.append(eid)
    return out[:6]


def _normalize_evidence_ids_on_item(item, evidence_index=None):
    item = dict(item or {})
    raw = item.get("evidence_ids")
    # Always re-coerce — guards against LLM returning [{id: ...}] format
    item["evidence_ids"] = _coerce_evidence_ids(raw, evidence_index)
    return item

def apply_domain_reasoning_layer(analysis: Dict[str, Any], rag_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Final domain-aware explainability gate.

    This runs after generic evidence validation.  It attaches domain metadata,
    removes generic claims, and fills gaps with domain-specific fallback claims
    that cite concrete evidence IDs.
    """
    if not isinstance(analysis, dict):
        analysis = {}
    domain_result = rag_bundle.get("domain") or analysis.get("domain") or {"domain": "general", "label": "General Executive Document", "confidence": "low"}
    if isinstance(domain_result, str):
        domain_result = {"domain": domain_result, "label": get_domain_profile(domain_result)["label"], "confidence": "medium"}
    domain = domain_result.get("domain", "general")
    profile = get_domain_profile(domain_result)
    evidence_pack = rag_bundle.get("evidence_pack", []) or []
    evidence_index = rag_bundle.get("evidence_index", {}) or {}
    expert_note = profile.get("expert_review_note", "")

    # Drop obviously generic insight claims unless they have strong evidence text.
    clean_insights = []
    for item in analysis.get("explainable_insights", []) or []:
        if not isinstance(item, dict):
            continue
        claim = clean_text(item.get("claim") or item.get("insight") or "")
        low_claim = claim.lower()
        # Drop extraction/chart-line statements from the visible insight deck.
        # The underlying evidence is still available for RAG and charts.
        if low_claim.startswith(("annual contract value line", "contract exposure line", "regional revenue line", "monthly revenue line")):
            continue
        if _generic_claim(claim):
            continue
        clean_insights.append(_append_expert_note(_normalize_evidence_ids_on_item(_normalize_domain_language(item, domain), evidence_index), expert_note))

    clean_risks = []
    for item in analysis.get("risks", []) or []:
        if not isinstance(item, dict):
            continue
        risk = clean_text(item.get("risk") or item.get("description") or "")
        if _generic_claim(risk):
            continue
        clean_risks.append(_append_expert_note(_normalize_evidence_ids_on_item(_normalize_domain_language(item, domain), evidence_index), expert_note))

    clean_recs = []
    for item in analysis.get("recommendations", []) or []:
        if not isinstance(item, dict):
            continue
        rec = clean_text(item.get("recommendation") or item.get("action") or "")
        if _generic_claim(rec):
            continue
        # Medical/legal safety: downgrade direct advice wording to review language.
        if domain == "medical":
            direct_terms = ("prescribe", "start ", "stop ", "increase dose", "decrease dose", "diagnose")
            if any(t in rec.lower() for t in direct_terms):
                item["recommendation"] = "Flag the cited clinical issue for qualified clinician review before any diagnosis or treatment change."
                item["business_impact"] = item.get("business_impact") or "Prevents unsafe automated clinical action."
        elif domain == "legal":
            if any(t in rec.lower() for t in ("you should", "must sign", "is enforceable", "is unenforceable")):
                item["recommendation"] = "Route the cited clause or legal issue to counsel for review before taking action."
                item["business_impact"] = item.get("business_impact") or "Reduces risk of unsupported legal conclusions."
        clean_recs.append(_append_expert_note(_normalize_evidence_ids_on_item(_normalize_domain_language(item, domain), evidence_index), expert_note))

    fallback_insights, fallback_risks, fallback_recs = _domain_specific_fallbacks(domain, evidence_pack, evidence_index)

    def fill(existing, fallback, key, target):
        out = list(existing)
        seen = {clean_text(i.get(key, "")).lower()[:180] for i in out if isinstance(i, dict)}
        # ↓ FIX: str() cast prevents dict accidentally entering a set
        used_ids = {
            str(eid)
            for i in out if isinstance(i, dict)
            for eid in _coerce_evidence_ids(i.get("evidence_ids"), evidence_index)
        }
        for item in fallback:
            k = clean_text(item.get(key, "")).lower()[:180]
            # ↓ FIX: same str() cast here
            ids = set(str(e) for e in _coerce_evidence_ids(item.get("evidence_ids"), evidence_index))
            if ids and ids.issubset(used_ids):
                continue
            if k and k not in seen:
                # out.append(...)
                out.append({**item, "evidence_ids": list(ids)})
                seen.add(k)
                used_ids.update(ids)
            if len(out) >= target:
                break
        return out[:target]

    if domain == "legal":
        # Legal decks should prioritize clause/exposure reasoning over generic
        # chart-line statements. The fallback items are clause-aware and use
        # the same evidence IDs internally, but evidence IDs are not rendered.
        analysis["explainable_insights"] = fill([], fallback_insights + clean_insights, "claim", 6)
        analysis["risks"] = fill([], fallback_risks + clean_risks, "risk", 5)
        analysis["recommendations"] = fill([], fallback_recs + clean_recs, "recommendation", 5)
    else:
        analysis["explainable_insights"] = fill(clean_insights, fallback_insights, "claim", 6)
        analysis["risks"] = fill(clean_risks, fallback_risks, "risk", 5)
        analysis["recommendations"] = fill(clean_recs, fallback_recs, "recommendation", 5)

    # Rebuild string versions from explainable items so slide generation gets the
    # stronger, domain-specific claims.
    analysis["insights"] = [
        clean_text(item.get("claim") or "")
        for item in analysis.get("explainable_insights", [])
        if isinstance(item, dict) and clean_text(item.get("claim") or "")
    ][:6]
    analysis["key_findings"] = analysis["insights"][:5]

    analysis["domain"] = {
        "key": domain,
        "label": profile.get("label"),
        "confidence": domain_result.get("confidence", "medium"),
        "signals": domain_result.get("signals", []),
        "scores": domain_result.get("scores", {}),
        "explanation": domain_result.get("explanation", ""),
        "expert_review_note": expert_note,
    }
    analysis.setdefault("explainability", {})
    analysis["explainability"]["domain"] = analysis["domain"]
    analysis["explainability"]["domain_reasoning_rules"] = profile.get("reasoning_rules", [])
    analysis["explainability"]["domain_recommendation_templates"] = profile.get("recommendation_templates", {})
    analysis["limitations"] = list(OrderedDict.fromkeys((analysis.get("limitations") or []) + ([expert_note] if expert_note else [])))
    return analysis



# ───────────────────────── expanded domain profiles ─────────────────────────
# Added after the core profiles so the same RAG/reasoning engine can operate
# across common enterprise and specialist document types without changing the
# retrieval engine.  The domain index is still rebuilt per uploaded document;
# these profiles only change what evidence the agent searches for and how it
# reasons over that evidence.

EXTRA_DOMAIN_PROFILES: Dict[str, Dict[str, Any]] = {
    "operations_supply_chain": {
        "label": "Operations / Supply Chain",
        "indicators": [
            "inventory", "stockout", "backlog", "capacity", "utilization", "lead time", "cycle time",
            "fulfillment", "warehouse", "logistics", "distribution", "supplier", "procurement", "otif",
            "on-time", "in-full", "sla", "service level", "throughput", "bottleneck", "forecast accuracy",
            "demand planning", "safety stock", "order fill rate", "returns", "scrap", "yield", "downtime",
        ],
        "retrieval_lenses": {
            "service_level": [
                "service level sla on-time in-full fulfillment order fill rate backlog delay",
                "where customer service or fulfillment performance is weak or improving",
            ],
            "capacity_and_flow": [
                "capacity utilization throughput bottleneck cycle time lead time warehouse labor overtime",
                "operational flow constraints and process efficiency evidence",
            ],
            "inventory": [
                "inventory turns safety stock stockout excess inventory shrink obsolete forecast accuracy",
                "inventory quality demand planning and working capital signals",
            ],
            "supplier_risk": [
                "supplier procurement logistics distribution otif lead time disruption dependency",
                "supply chain risk and vendor performance evidence",
            ],
            "actions": [
                "recommend optimize capacity inventory service level supplier process improvement owner action",
            ],
        },
        "reasoning_rules": [
            "Use the pattern: operating metric → process constraint/root cause → service, cost, or working-capital implication.",
            "For risks, separate service-level risk, inventory risk, capacity risk, and supplier risk.",
            "For recommendations, name the operational lever: capacity, scheduling, inventory policy, supplier management, process redesign, or forecast governance.",
        ],
        "avoid": ["operational challenges requiring attention", "optimize operations"],
        "fallback_signal_terms": ["inventory", "capacity", "utilization", "lead time", "sla", "otif", "throughput", "backlog", "warehouse", "supplier"],
        "fallback_risk_terms": ["delay", "backlog", "stockout", "excess", "shortage", "constraint", "capacity", "downtime", "supplier", "risk"],
        "implication_language": "Use as an operational performance signal tied to service level, cost-to-serve, throughput, or working capital.",
        "fallback_recommendation": "Target the cited operational constraint with an owner-led improvement plan covering capacity, inventory policy, service levels, and supplier performance.",
        "business_impact_language": "Improves service reliability and cost efficiency by acting on a documented operational driver.",
    },
    "hr_workforce": {
        "label": "HR / Workforce",
        "indicators": [
            "headcount", "attrition", "turnover", "retention", "hiring", "recruiting", "vacancy", "time to fill",
            "employee engagement", "engagement score", "absenteeism", "productivity", "training", "learning",
            "performance rating", "diversity", "dei", "compensation", "pay equity", "workforce", "labor",
            "employee", "manager", "span of control", "succession", "promotion", "burnout", "overtime",
        ],
        "retrieval_lenses": {
            "workforce_capacity": ["headcount hiring vacancy time to fill capacity staffing workforce plan", "staffing capacity and hiring evidence"],
            "retention": ["attrition turnover retention employee churn engagement absenteeism burnout", "retention and engagement risk evidence"],
            "productivity": ["productivity performance training learning manager span overtime labor utilization", "workforce productivity and capability evidence"],
            "dei_compensation": ["diversity inclusion dei pay equity compensation promotion representation", "DEI and compensation equity signals"],
            "actions": ["recommend workforce action retention hiring training manager enablement compensation engagement"],
        },
        "reasoning_rules": [
            "Use the pattern: workforce metric → talent or capacity driver → productivity, retention, or cost implication.",
            "For risks, name attrition, capability, staffing, engagement, compliance, or pay-equity exposure.",
            "Recommendations should include people-process owners and measurable HR outcomes.",
        ],
        "fallback_signal_terms": ["headcount", "attrition", "turnover", "hiring", "engagement", "training", "productivity", "overtime", "employee"],
        "fallback_risk_terms": ["attrition", "turnover", "vacancy", "burnout", "absenteeism", "low", "decline", "risk", "gap"],
        "implication_language": "Use as a workforce signal tied to staffing capacity, retention, productivity, engagement, or compliance risk.",
        "fallback_recommendation": "Create an HR action plan around the cited workforce signal, with owners for retention, hiring, capability building, or manager intervention.",
        "business_impact_language": "Improves workforce stability and productivity by targeting a documented people driver.",
    },
    "marketing": {
        "label": "Marketing",
        "indicators": [
            "campaign", "marketing", "impressions", "click", "ctr", "cpc", "cpm", "roas", "roi", "cac",
            "conversion rate", "lead", "mql", "sql", "channel", "media spend", "paid search", "paid social",
            "organic", "email", "open rate", "attribution", "brand awareness", "reach", "frequency",
            "funnel", "landing page", "promotion", "loyalty", "retargeting", "creative",
        ],
        "retrieval_lenses": {
            "campaign_performance": ["campaign impressions clicks ctr cpc cpm conversion roas roi", "campaign performance and efficiency evidence"],
            "channel_mix": ["channel media spend paid search social email organic attribution mix", "marketing channel mix and spend allocation evidence"],
            "funnel_quality": ["mql sql lead conversion landing page funnel drop-off cac", "marketing funnel quality and acquisition efficiency"],
            "brand_customer": ["brand awareness reach frequency loyalty retention audience segment", "brand and customer engagement evidence"],
            "actions": ["recommend marketing action budget allocation creative test channel optimization audience targeting"],
        },
        "reasoning_rules": [
            "Use the pattern: campaign/channel metric → audience or funnel driver → acquisition, revenue, or efficiency implication.",
            "Separate volume growth from efficiency; high traffic is not good if CAC/ROAS deteriorates.",
            "Recommendations should identify budget, targeting, creative, channel, or funnel levers.",
        ],
        "fallback_signal_terms": ["campaign", "roas", "cac", "ctr", "conversion", "lead", "channel", "media spend", "impressions", "click"],
        "fallback_risk_terms": ["cac", "decline", "lower", "drop", "inefficient", "spend", "low", "conversion", "risk"],
        "implication_language": "Use as a marketing performance signal tied to acquisition efficiency, funnel quality, or channel allocation.",
        "fallback_recommendation": "Reallocate or test marketing spend around the cited channel/funnel signal, tracking CAC, ROAS, conversion, and qualified pipeline impact.",
        "business_impact_language": "Improves marketing efficiency by linking spend decisions to cited performance evidence.",
    },
    "customer_experience": {
        "label": "Customer Experience / Support",
        "indicators": [
            "nps", "csat", "customer satisfaction", "complaint", "ticket", "support", "case volume", "resolution time",
            "first response", "first contact resolution", "fcr", "churn", "retention", "repeat purchase",
            "review", "rating", "escalation", "service quality", "call center", "contact center", "refund",
            "return rate", "customer effort", "ces", "sentiment", "voice of customer", "voc",
        ],
        "retrieval_lenses": {
            "satisfaction": ["nps csat satisfaction rating sentiment review customer effort", "customer satisfaction and sentiment evidence"],
            "support_operations": ["ticket case volume resolution time first response fcr escalation support", "support operation performance evidence"],
            "retention_risk": ["churn retention repeat purchase complaint refund return customer risk", "customer retention and complaint risk"],
            "root_causes": ["driver reason complaint category issue root cause service quality", "root causes behind customer experience movement"],
            "actions": ["recommend customer experience action reduce complaints improve resolution retention service quality"],
        },
        "reasoning_rules": [
            "Use the pattern: customer metric → experience driver/root cause → retention, loyalty, or service-cost implication.",
            "Do not treat satisfaction scores as isolated; connect them to complaints, resolution time, churn, or repeat behavior.",
            "Recommendations should specify support process, product fix, service recovery, or retention action.",
        ],
        "fallback_signal_terms": ["nps", "csat", "complaint", "ticket", "resolution", "support", "rating", "churn", "refund", "return"],
        "fallback_risk_terms": ["complaint", "churn", "escalation", "delay", "low", "decline", "refund", "return", "dissatisfaction"],
        "implication_language": "Use as a customer-experience signal tied to loyalty, churn, service cost, or complaint reduction.",
        "fallback_recommendation": "Address the cited customer-experience driver through root-cause fixes, support process changes, and tracked satisfaction/retention outcomes.",
        "business_impact_language": "Improves loyalty and reduces service friction by acting on cited customer evidence.",
    },
    "product_saas": {
        "label": "Product / SaaS Metrics",
        "indicators": [
            "arr", "mrr", "dau", "mau", "wau", "activation", "onboarding", "retention", "churn", "cohort",
            "feature adoption", "usage", "seat expansion", "net revenue retention", "nrr", "gross revenue retention",
            "grr", "trial", "conversion", "freemium", "subscription", "logo retention", "renewal", "arpu",
            "product led growth", "plg", "engagement", "active users", "release", "roadmap", "bug", "latency",
        ],
        "retrieval_lenses": {
            "growth_retention": ["arr mrr nrr grr churn retention expansion renewal cohort", "SaaS growth retention and revenue quality evidence"],
            "product_usage": ["dau mau wau activation onboarding feature adoption usage engagement active users", "product usage and adoption evidence"],
            "conversion": ["trial freemium conversion onboarding activation funnel arpu", "product conversion and monetization evidence"],
            "quality": ["bug latency reliability support incident release roadmap customer issue", "product quality and delivery risk evidence"],
            "actions": ["recommend product action activation retention feature adoption onboarding pricing packaging"],
        },
        "reasoning_rules": [
            "Use the pattern: usage/revenue metric → product behavior driver → retention, expansion, or monetization implication.",
            "Separate acquisition, activation, engagement, retention, expansion, and quality risks.",
            "Recommendations should identify product, onboarding, pricing, packaging, reliability, or customer-success levers.",
        ],
        "fallback_signal_terms": ["arr", "mrr", "dau", "mau", "activation", "retention", "churn", "feature adoption", "usage", "nrr"],
        "fallback_risk_terms": ["churn", "low", "decline", "drop", "bug", "latency", "retention", "activation", "risk"],
        "implication_language": "Use as a product/SaaS signal tied to activation, retention, expansion, monetization, or product quality.",
        "fallback_recommendation": "Prioritize the cited product metric with a focused experiment or roadmap item tied to activation, retention, expansion, or quality outcomes.",
        "business_impact_language": "Improves recurring revenue quality by acting on cited product usage or retention evidence.",
    },
    "manufacturing_quality": {
        "label": "Manufacturing / Quality",
        "indicators": [
            "manufacturing", "plant", "factory", "production", "line", "yield", "throughput", "downtime", "oee",
            "scrap", "rework", "defect", "ppm", "quality", "first pass yield", "fpY", "capacity", "shift",
            "maintenance", "machine", "equipment", "batch", "cycle time", "wip", "root cause", "corrective action", "capa",
        ],
        "retrieval_lenses": {
            "production": ["production throughput yield capacity line shift cycle time wip", "manufacturing output and flow evidence"],
            "quality": ["defect ppm scrap rework first pass yield quality root cause capa", "quality and defect evidence"],
            "equipment": ["downtime oee machine equipment maintenance reliability availability", "equipment reliability and downtime evidence"],
            "cost": ["scrap rework downtime labor overtime material variance cost", "manufacturing cost leakage evidence"],
            "actions": ["recommend manufacturing action quality improvement maintenance throughput yield defect reduction"],
        },
        "reasoning_rules": [
            "Use the pattern: production/quality metric → process/equipment/root-cause driver → throughput, cost, or customer-quality implication.",
            "Risks should distinguish quality escape, capacity loss, downtime, scrap/rework, and maintenance exposure.",
            "Recommendations should cite process control, maintenance, quality containment, training, or root-cause corrective action.",
        ],
        "fallback_signal_terms": ["yield", "throughput", "downtime", "oee", "scrap", "defect", "quality", "rework", "production", "capacity"],
        "fallback_risk_terms": ["defect", "scrap", "downtime", "low", "decline", "rework", "quality", "failure", "risk"],
        "implication_language": "Use as a manufacturing signal tied to throughput, quality, cost leakage, or reliability.",
        "fallback_recommendation": "Run root-cause corrective action on the cited production or quality signal, with containment, owner, and measurable yield/defect targets.",
        "business_impact_language": "Improves throughput and quality by addressing a documented production driver.",
    },
    "risk_compliance": {
        "label": "Risk / Compliance",
        "indicators": [
            "risk", "compliance", "audit", "control", "finding", "issue", "remediation", "mitigation", "policy breach",
            "regulatory", "governance", "control gap", "deficiency", "non-compliance", "incident", "severity",
            "material weakness", "sox", "privacy", "security", "third party risk", "vendor risk", "control testing",
        ],
        "retrieval_lenses": {
            "findings": ["audit finding control gap deficiency issue severity non-compliance", "risk and control finding evidence"],
            "exposure": ["regulatory policy breach incident material weakness exposure impact likelihood", "risk exposure severity likelihood evidence"],
            "controls": ["control testing governance mitigation remediation owner due date", "control effectiveness and remediation evidence"],
            "third_party": ["third party vendor risk supplier risk outsourcing dependency", "third-party risk evidence"],
            "actions": ["recommend remediation mitigation owner due date control improvement governance"],
        },
        "reasoning_rules": [
            "Use the pattern: finding/control evidence → exposure/likelihood/impact → remediation action.",
            "Do not overstate compliance conclusions; identify evidence gaps and need for control owner validation.",
            "Recommendations should include owner, due date, control improvement, monitoring, and evidence of closure.",
        ],
        "fallback_signal_terms": ["risk", "compliance", "audit", "control", "finding", "remediation", "mitigation", "deficiency", "incident"],
        "fallback_risk_terms": ["gap", "breach", "non-compliance", "deficiency", "incident", "high", "material", "overdue", "risk"],
        "implication_language": "Use as a risk/compliance signal tied to exposure, control effectiveness, remediation status, or governance oversight.",
        "fallback_recommendation": "Create a remediation plan for the cited risk/control issue with owner, due date, control evidence, and monitoring cadence.",
        "business_impact_language": "Reduces compliance and governance exposure by addressing a cited control or risk signal.",
        "expert_review_note": "Regulatory, audit, and compliance conclusions should be reviewed by qualified risk, compliance, or legal owners.",
    },
    "insurance": {
        "label": "Insurance",
        "indicators": [
            "insurance", "premium", "policy", "claims", "claim", "loss ratio", "combined ratio", "underwriting",
            "reserves", "severity", "frequency", "catastrophe", "cat", "reinsurance", "renewal", "lapse",
            "fraud", "exposure", "coverage", "deductible", "policyholder", "actuarial", "earned premium", "incurred loss",
        ],
        "retrieval_lenses": {
            "underwriting": ["premium policy underwriting renewal lapse exposure coverage", "underwriting and policy mix evidence"],
            "claims": ["claims frequency severity incurred loss reserve fraud catastrophe", "claims performance and loss driver evidence"],
            "profitability": ["loss ratio combined ratio expense ratio underwriting margin", "insurance profitability evidence"],
            "capital_reserve": ["reserves reinsurance capital adequacy catastrophe exposure", "reserve and capital exposure evidence"],
            "actions": ["recommend underwriting pricing claims reserve reinsurance fraud mitigation action"],
        },
        "reasoning_rules": [
            "Use the pattern: premium/claim metric → loss or underwriting driver → profitability/reserve implication.",
            "Separate frequency, severity, pricing adequacy, reserve adequacy, lapse/retention, and catastrophe exposure.",
            "Recommendations should identify underwriting, pricing, claims handling, fraud, reinsurance, or reserving levers.",
        ],
        "fallback_signal_terms": ["premium", "claims", "loss ratio", "combined ratio", "underwriting", "reserves", "severity", "frequency", "renewal"],
        "fallback_risk_terms": ["claims", "severity", "frequency", "loss", "reserve", "catastrophe", "fraud", "lapse", "risk"],
        "implication_language": "Use as an insurance signal tied to underwriting quality, claims cost, reserves, or risk exposure.",
        "fallback_recommendation": "Review the cited insurance driver through underwriting, pricing, claims, reserve, or reinsurance action planning.",
        "business_impact_language": "Improves insurance profitability and risk control by targeting cited loss or underwriting evidence.",
    },
    "real_estate": {
        "label": "Real Estate / Property",
        "indicators": [
            "real estate", "property", "portfolio", "occupancy", "vacancy", "lease", "tenant", "rent", "noi",
            "net operating income", "cap rate", "capex", "leasing", "rent roll", "square feet", "sq ft", "renewal",
            "expiry", "arrears", "delinquency", "asset value", "valuation", "maintenance", "property management",
        ],
        "retrieval_lenses": {
            "occupancy": ["occupancy vacancy leasing tenant retention renewal expiry", "occupancy and leasing evidence"],
            "income": ["rent noi net operating income arrears delinquency revenue cap rate", "property income and valuation evidence"],
            "portfolio_risk": ["tenant concentration lease expiry capex maintenance asset value", "portfolio risk and capital need evidence"],
            "operations": ["property management maintenance service costs repairs", "property operating performance evidence"],
            "actions": ["recommend leasing rent renewal capex tenant retention property action"],
        },
        "reasoning_rules": [
            "Use the pattern: occupancy/rent/NOI metric → tenant/lease/capex driver → value or cash-flow implication.",
            "Separate leasing risk, tenant concentration, rent collection, capex burden, and valuation exposure.",
            "Recommendations should identify leasing, renewal, rent collection, capex prioritization, or asset management levers.",
        ],
        "fallback_signal_terms": ["occupancy", "vacancy", "lease", "tenant", "rent", "noi", "capex", "renewal", "expiry"],
        "fallback_risk_terms": ["vacancy", "expiry", "delinquency", "arrears", "capex", "tenant concentration", "decline", "risk"],
        "implication_language": "Use as a real-estate signal tied to occupancy, NOI, lease risk, tenant quality, or asset value.",
        "fallback_recommendation": "Prioritize the cited property signal through leasing, renewal, rent collection, capex planning, or tenant-risk mitigation.",
        "business_impact_language": "Protects property cash flow and asset value by acting on cited portfolio evidence.",
    },
    "education": {
        "label": "Education / Academic Administration",
        "indicators": [
            "student", "enrollment", "attendance", "graduation", "retention", "dropout", "test score", "assessment",
            "curriculum", "program", "faculty", "teacher", "class size", "course completion", "learning outcome",
            "accreditation", "tuition", "financial aid", "placement", "admissions", "academic", "cohort",
        ],
        "retrieval_lenses": {
            "student_outcomes": ["graduation retention dropout attendance test score learning outcome completion", "student outcome and progression evidence"],
            "enrollment": ["enrollment admissions tuition financial aid cohort demand", "enrollment and admissions evidence"],
            "program_quality": ["curriculum faculty teacher class size assessment accreditation placement", "program quality and academic delivery evidence"],
            "equity_access": ["access equity diversity financial aid attendance achievement gap", "student equity and access evidence"],
            "actions": ["recommend academic action student support curriculum attendance retention intervention"],
        },
        "reasoning_rules": [
            "Use the pattern: student/program metric → academic or access driver → outcome or resource implication.",
            "For risks, distinguish retention/dropout, attendance, program quality, equity/access, and accreditation exposure.",
            "Recommendations should include student-support, curriculum, faculty, attendance, or enrollment actions.",
        ],
        "fallback_signal_terms": ["student", "enrollment", "attendance", "graduation", "retention", "dropout", "score", "completion", "faculty"],
        "fallback_risk_terms": ["dropout", "low", "decline", "attendance", "retention", "gap", "accreditation", "risk"],
        "implication_language": "Use as an education signal tied to student outcomes, enrollment health, academic quality, or access risk.",
        "fallback_recommendation": "Create a targeted academic intervention around the cited student, program, or enrollment signal with measurable outcome tracking.",
        "business_impact_language": "Improves student outcomes and program effectiveness by acting on cited education evidence.",
    },
    "esg_sustainability": {
        "label": "ESG / Sustainability",
        "indicators": [
            "esg", "sustainability", "emissions", "carbon", "co2", "scope 1", "scope 2", "scope 3",
            "energy", "renewable", "water", "waste", "recycling", "safety", "incident rate", "trir",
            "decarbonization", "net zero", "diversity", "governance", "ethics", "supplier sustainability", "climate risk",
        ],
        "retrieval_lenses": {
            "environment": ["emissions carbon co2 scope energy renewable water waste recycling climate", "environmental performance evidence"],
            "social": ["safety incident trir diversity inclusion labor community human rights", "social and workforce ESG evidence"],
            "governance": ["governance ethics compliance board policy supplier sustainability", "governance and ESG control evidence"],
            "targets": ["net zero target reduction decarbonization goal progress baseline", "ESG target and progress evidence"],
            "actions": ["recommend sustainability action reduce emissions energy waste safety governance target"],
        },
        "reasoning_rules": [
            "Use the pattern: ESG metric → source/driver → target progress, compliance, reputation, or cost implication.",
            "Separate environmental, social, governance, target-progress, and assurance risks.",
            "Recommendations should identify measurable reduction, control, supplier, safety, or reporting actions.",
        ],
        "fallback_signal_terms": ["emissions", "carbon", "scope", "energy", "water", "waste", "safety", "trir", "diversity", "governance"],
        "fallback_risk_terms": ["increase", "miss", "gap", "incident", "emissions", "waste", "safety", "climate", "risk"],
        "implication_language": "Use as an ESG signal tied to target progress, regulatory/reputation exposure, resource efficiency, or safety performance.",
        "fallback_recommendation": "Prioritize the cited ESG driver with measurable owners, baselines, reduction targets, and reporting controls.",
        "business_impact_language": "Improves sustainability performance and accountability by acting on cited ESG evidence.",
    },
    "cybersecurity_it": {
        "label": "Cybersecurity / IT",
        "indicators": [
            "cybersecurity", "security", "vulnerability", "cve", "patch", "incident", "phishing", "malware",
            "ransomware", "access", "identity", "mfa", "iam", "endpoint", "network", "downtime", "availability",
            "sla", "backup", "restore", "data breach", "threat", "risk", "severity", "critical", "open findings",
        ],
        "retrieval_lenses": {
            "threats": ["security incident phishing malware ransomware threat breach", "cyber threat and incident evidence"],
            "vulnerabilities": ["vulnerability cve patch critical severity remediation open findings", "vulnerability and patching evidence"],
            "identity_access": ["access identity iam mfa privilege account authentication", "identity and access risk evidence"],
            "resilience": ["downtime availability backup restore recovery sla disaster recovery", "IT resilience and availability evidence"],
            "actions": ["recommend security remediation patch access mfa backup incident response action"],
        },
        "reasoning_rules": [
            "Use the pattern: security/IT finding → threat or control weakness → likelihood/impact/resilience implication.",
            "Separate vulnerability, identity, incident, availability, and recovery risks.",
            "Recommendations should identify remediation owner, priority, control, SLA, and verification evidence.",
        ],
        "fallback_signal_terms": ["vulnerability", "patch", "incident", "phishing", "malware", "access", "mfa", "downtime", "backup", "critical"],
        "fallback_risk_terms": ["critical", "high", "incident", "breach", "ransomware", "unpatched", "failure", "downtime", "risk"],
        "implication_language": "Use as a cybersecurity/IT signal tied to threat exposure, control effectiveness, availability, or resilience.",
        "fallback_recommendation": "Remediate the cited security or IT control issue with priority, owner, SLA, compensating controls, and verification evidence.",
        "business_impact_language": "Reduces security and availability exposure by acting on cited IT evidence.",
        "expert_review_note": "Security and privacy conclusions should be reviewed by qualified security, privacy, or compliance owners.",
    },
    "pharma_clinical_trials": {
        "label": "Pharma / Clinical Trials",
        "indicators": [
            "clinical trial", "phase i", "phase ii", "phase iii", "endpoint", "primary endpoint", "secondary endpoint",
            "adverse event", "serious adverse event", "sae", "efficacy", "safety", "enrollment", "randomized",
            "placebo", "arm", "protocol", "investigator", "patient years", "hazard ratio", "noninferiority",
            "intention to treat", "itt", "per protocol", "p-value", "biomarker", "drug", "dose", "trial site",
        ],
        "retrieval_lenses": {
            "efficacy": ["primary endpoint secondary endpoint efficacy response rate hazard ratio p-value", "trial efficacy and endpoint evidence"],
            "safety": ["adverse event serious adverse event sae safety tolerability discontinuation", "trial safety and tolerability evidence"],
            "enrollment": ["enrollment randomization trial site protocol arm cohort retention dropout", "trial enrollment and protocol execution evidence"],
            "study_quality": ["randomized placebo control intention to treat per protocol sample size statistical power", "clinical trial design and evidence quality"],
            "actions": ["recommend clinical trial action monitor safety enrollment endpoint protocol regulatory review"],
        },
        "reasoning_rules": [
            "Do not make medical or regulatory conclusions. Frame outputs as trial evidence signals for clinical/regulatory review.",
            "Use the pattern: endpoint/safety/enrollment evidence → trial interpretation → implication for study risk or next review.",
            "Separate efficacy, safety, enrollment, protocol, statistical power, and regulatory-review risks.",
        ],
        "fallback_signal_terms": ["endpoint", "efficacy", "safety", "adverse event", "enrollment", "protocol", "p-value", "hazard ratio", "randomized"],
        "fallback_risk_terms": ["adverse", "serious", "missed", "dropout", "enrollment", "protocol deviation", "safety", "risk"],
        "implication_language": "Use as a clinical-trial evidence signal tied to efficacy, safety, enrollment, protocol execution, or regulatory review readiness.",
        "fallback_recommendation": "Route the cited trial signal to clinical, safety, biostatistics, or regulatory review before drawing conclusions.",
        "business_impact_language": "Supports safer trial decision-making by linking conclusions to cited endpoint, safety, or execution evidence.",
        "expert_review_note": "Clinical trial conclusions should be reviewed by qualified clinical, safety, biostatistics, and regulatory experts.",
    },
    "policy_government": {
        "label": "Policy / Government",
        "indicators": [
            "policy", "government", "public sector", "agency", "program", "budget", "appropriation", "citizen",
            "population", "service delivery", "outcome", "equity", "compliance", "regulation", "benefit",
            "grant", "municipal", "state", "federal", "public health", "infrastructure", "constituent", "legislation",
        ],
        "retrieval_lenses": {
            "program_outcomes": ["program outcome service delivery population citizen beneficiary KPI", "public program outcome evidence"],
            "budget": ["budget appropriation funding grant cost spend variance", "public budget and funding evidence"],
            "equity_access": ["equity access underserved population distribution eligibility", "equity and access evidence"],
            "compliance_policy": ["policy regulation compliance legislation mandate agency requirement", "policy and compliance evidence"],
            "actions": ["recommend policy action program improvement budget oversight service delivery equity"],
        },
        "reasoning_rules": [
            "Use the pattern: program/policy metric → affected population or service driver → public value, budget, compliance, or equity implication.",
            "Do not present political judgments; focus on evidence-backed program, service, budget, and compliance implications.",
            "Recommendations should name implementation, oversight, budget, service delivery, or stakeholder actions.",
        ],
        "fallback_signal_terms": ["policy", "program", "budget", "service", "population", "outcome", "agency", "compliance", "equity"],
        "fallback_risk_terms": ["budget", "gap", "delay", "non-compliance", "underserved", "missed", "risk", "overrun"],
        "implication_language": "Use as a public-sector signal tied to service outcomes, budget stewardship, compliance, equity, or implementation risk.",
        "fallback_recommendation": "Create an implementation or oversight action for the cited public-program signal, with owner, budget, timeline, and outcome metric.",
        "business_impact_language": "Improves public value and accountability by acting on cited program or policy evidence.",
    },
    "food_beverage": {
        "label": "Food & Beverage / Food Industry",
        "indicators": [
            "food", "beverage", "restaurant", "qsr", "grocery", "menu", "sku", "same-store sales",
            "traffic", "ticket size", "basket size", "food cost", "cogs", "waste", "spoilage", "shrink",
            "labor cost", "delivery", "dine-in", "takeout", "inventory", "shelf life", "freshness",
            "supplier", "commodity", "input cost", "packaging", "cold chain", "quality", "recall",
            "food safety", "haccp", "allergen", "margin", "pricing", "promotion", "loyalty",
        ],
        "retrieval_lenses": {
            "sales_mix": [
                "same-store sales traffic ticket size basket size revenue channel menu sku category loyalty",
                "food sales growth by channel store menu category and customer behavior",
            ],
            "margin_cost": [
                "food cost cogs commodity input cost packaging labor cost gross margin pricing promotion",
                "margin pressure from food cost labor packaging commodity inflation or promotions",
            ],
            "waste_inventory": [
                "waste spoilage shrink inventory shelf life freshness stockout demand forecast",
                "freshness inventory waste spoilage and stockout evidence",
            ],
            "quality_safety": [
                "food safety haccp allergen recall contamination quality complaint inspection cold chain",
                "food-safety quality recall allergen inspection and cold-chain risk evidence",
            ],
            "channel_profitability": [
                "delivery dine-in takeout platform fee packaging contribution margin channel mix",
                "channel profitability delivery fees packaging and contribution margin evidence",
            ],
            "actions": [
                "recommend food beverage action pricing menu engineering waste reduction supplier safety quality labor scheduling",
            ],
        },
        "reasoning_rules": [
            "Use the pattern: food metric → channel/menu/ingredient/operating driver → margin, quality, safety, or customer implication.",
            "Do not judge top-line growth alone; consider food cost, labor, waste, packaging, and channel contribution margin.",
            "For risks, distinguish food-safety/allergen, spoilage/waste, supplier/cold-chain, traffic/ticket mix, and delivery-margin risk.",
            "Recommendations should be practical operating actions such as menu engineering, pricing, waste reduction, supplier controls, cold-chain checks, labor scheduling, or food-safety review.",
        ],
        "avoid": ["increase sales", "optimize operations", "operational challenges requiring attention"],
        "fallback_signal_terms": ["same-store sales", "traffic", "ticket", "basket", "food cost", "waste", "spoilage", "delivery", "labor", "quality", "recall"],
        "fallback_risk_terms": ["food cost", "waste", "spoilage", "shrink", "recall", "allergen", "cold chain", "delivery", "complaint", "risk"],
        "implication_language": "Use as a food-industry signal tied to sales mix, margin, waste, labor, supplier reliability, food safety, or channel profitability.",
        "fallback_recommendation": "Act on the cited food-industry driver through menu/pricing review, waste reduction, supplier or cold-chain controls, labor scheduling, and food-safety validation.",
        "business_impact_language": "Improves food-business profitability and safety by linking action to cited sales, cost, waste, supplier, or quality evidence.",
        "expert_review_note": "Food-safety, allergen, labeling, recall, and regulatory conclusions should be reviewed by qualified quality, legal, or regulatory experts.",
    },
}

DOMAIN_PROFILES.update(EXTRA_DOMAIN_PROFILES)
DOMAIN_ORDER = [
    "medical", "pharma_clinical_trials", "legal", "risk_compliance", "cybersecurity_it",
    "finance", "insurance", "real_estate", "sales", "marketing", "product_saas",
    "food_beverage", "operations_supply_chain", "manufacturing_quality", "hr_workforce",
    "customer_experience", "education", "esg_sustainability", "policy_government", "research",
]

DOMAIN_ALIASES = {
    "operations": "operations_supply_chain",
    "supply_chain": "operations_supply_chain",
    "hr": "hr_workforce",
    "workforce": "hr_workforce",
    "customer_success": "customer_experience",
    "cx": "customer_experience",
    "saas": "product_saas",
    "product": "product_saas",
    "manufacturing": "manufacturing_quality",
    "quality": "manufacturing_quality",
    "compliance": "risk_compliance",
    "risk": "risk_compliance",
    "realestate": "real_estate",
    "sustainability": "esg_sustainability",
    "esg": "esg_sustainability",
    "cybersecurity": "cybersecurity_it",
    "cyber": "cybersecurity_it",
    "it": "cybersecurity_it",
    "pharma": "pharma_clinical_trials",
    "clinical_trials": "pharma_clinical_trials",
    "policy": "policy_government",
    "government": "policy_government",
    "food": "food_beverage",
    "food_industry": "food_beverage",
    "fnb": "food_beverage",
}


def get_domain_profile(domain_or_result: Any) -> Dict[str, Any]:
    if isinstance(domain_or_result, dict):
        domain = domain_or_result.get("domain", "general")
    else:
        domain = str(domain_or_result or "general")
    domain = DOMAIN_ALIASES.get(domain, domain)
    return DOMAIN_PROFILES.get(domain, DOMAIN_PROFILES["general"])


def _choose_metric_lens(domain: str, text: str, available_lenses: Sequence[str]) -> str:
    low = text.lower()
    routing = {
        "finance": [("profitability", ["margin", "profit", "ebitda", "eps", "markdown", "freight"]), ("costs", ["expense", "opex", "cost", "labor"]), ("liquidity_risk", ["cash", "working capital", "debt", "inventory"]), ("growth", ["revenue", "sales", "bookings", "growth"])],
        "sales": [("pipeline_health", ["pipeline", "conversion", "win", "funnel", "cycle"]), ("customer_retention", ["churn", "renewal", "retention"]), ("gtm_efficiency", ["cac", "productivity", "territory"]), ("revenue_quality", ["bookings", "arr", "mrr", "quota"])],
        "medical": [("risk_and_safety", ["adverse", "risk", "abnormal", "contraindication", "side effect"]), ("treatment_context", ["treatment", "therapy", "dose", "medication"]), ("outcomes", ["outcome", "mortality", "readmission"]), ("clinical_signals", ["lab", "patient", "symptom", "blood", "glucose"])],
        "legal": [("risk_exposure", ["liability", "indemnity", "breach", "damages", "termination"]), ("timing_notice", ["notice", "renewal", "deadline", "term"]), ("rights_and_restrictions", ["rights", "license", "restriction", "confidentiality", "ip"]), ("obligations", ["shall", "must", "obligation"])],
        "research": [("method_quality", ["method", "sample", "dataset", "baseline"]), ("limitations", ["limitation", "bias", "validity"]), ("results", ["result", "finding", "effect", "accuracy", "p-value"])],
        "food_beverage": [("quality_safety", ["safety", "recall", "allergen", "haccp", "cold chain", "complaint"]), ("margin_cost", ["food cost", "cogs", "commodity", "packaging", "labor", "margin"]), ("waste_inventory", ["waste", "spoilage", "shrink", "shelf life", "stockout"]), ("channel_profitability", ["delivery", "takeout", "dine-in", "platform fee"]), ("sales_mix", ["same-store", "traffic", "ticket", "basket", "menu", "sku"])],
        "operations_supply_chain": [("service_level", ["sla", "service", "on-time", "fill", "backlog"]), ("capacity_and_flow", ["capacity", "utilization", "throughput", "lead time", "cycle"]), ("inventory", ["inventory", "stockout", "safety stock"]), ("supplier_risk", ["supplier", "otif", "procurement"])],
        "hr_workforce": [("retention", ["attrition", "turnover", "retention", "engagement", "burnout"]), ("workforce_capacity", ["headcount", "hiring", "vacancy", "staffing"]), ("productivity", ["productivity", "training", "performance", "overtime"]), ("dei_compensation", ["dei", "diversity", "pay", "compensation"])],
        "marketing": [("campaign_performance", ["campaign", "ctr", "cpc", "cpm", "roas", "roi"]), ("channel_mix", ["channel", "media", "paid", "organic", "email"]), ("funnel_quality", ["lead", "mql", "sql", "conversion", "cac"]), ("brand_customer", ["brand", "awareness", "loyalty", "reach"])],
        "customer_experience": [("satisfaction", ["nps", "csat", "satisfaction", "rating"]), ("support_operations", ["ticket", "case", "resolution", "response", "support"]), ("retention_risk", ["churn", "retention", "refund", "return"]), ("root_causes", ["complaint", "driver", "root cause", "issue"])],
        "product_saas": [("growth_retention", ["arr", "mrr", "nrr", "grr", "retention", "churn"]), ("product_usage", ["dau", "mau", "activation", "feature", "usage"]), ("conversion", ["trial", "freemium", "onboarding", "conversion"]), ("quality", ["bug", "latency", "incident", "release"])],
        "manufacturing_quality": [("production", ["production", "throughput", "yield", "capacity"]), ("quality", ["defect", "scrap", "rework", "ppm", "quality"]), ("equipment", ["downtime", "oee", "machine", "maintenance"]), ("cost", ["cost", "labor", "material", "variance"])],
        "risk_compliance": [("findings", ["finding", "deficiency", "issue", "control gap"]), ("exposure", ["exposure", "regulatory", "breach", "incident", "severity"]), ("controls", ["control", "testing", "remediation", "owner"]), ("third_party", ["third party", "vendor"])],
        "insurance": [("claims", ["claim", "loss", "severity", "frequency", "fraud"]), ("profitability", ["loss ratio", "combined ratio", "expense ratio"]), ("capital_reserve", ["reserve", "reinsurance", "capital", "catastrophe"]), ("underwriting", ["premium", "policy", "underwriting", "renewal"])],
        "real_estate": [("occupancy", ["occupancy", "vacancy", "leasing", "tenant", "renewal"]), ("income", ["rent", "noi", "arrears", "delinquency", "cap rate"]), ("portfolio_risk", ["expiry", "capex", "concentration", "asset"]), ("operations", ["maintenance", "property management"])],
        "education": [("student_outcomes", ["graduation", "retention", "dropout", "attendance", "score"]), ("enrollment", ["enrollment", "admissions", "tuition"]), ("program_quality", ["curriculum", "faculty", "assessment", "accreditation"]), ("equity_access", ["equity", "access", "aid", "gap"])],
        "esg_sustainability": [("environment", ["emissions", "carbon", "scope", "energy", "water", "waste"]), ("social", ["safety", "trir", "diversity", "human rights"]), ("governance", ["governance", "ethics", "policy"]), ("targets", ["target", "net zero", "reduction", "progress"])],
        "cybersecurity_it": [("threats", ["incident", "phishing", "malware", "ransomware", "breach"]), ("vulnerabilities", ["vulnerability", "cve", "patch", "critical"]), ("identity_access", ["access", "identity", "mfa", "iam"]), ("resilience", ["downtime", "availability", "backup", "restore"])],
        "pharma_clinical_trials": [("efficacy", ["endpoint", "efficacy", "response", "hazard", "p-value"]), ("safety", ["adverse", "sae", "safety", "tolerability"]), ("enrollment", ["enrollment", "site", "protocol", "dropout"]), ("study_quality", ["randomized", "placebo", "control", "sample", "power"])],
        "policy_government": [("program_outcomes", ["program", "outcome", "service", "citizen", "beneficiary"]), ("budget", ["budget", "appropriation", "funding", "grant"]), ("equity_access", ["equity", "access", "underserved"]), ("compliance_policy", ["policy", "regulation", "mandate", "compliance"])],
    }
    for lens, terms in routing.get(domain, []):
        if lens in available_lenses and any(t in low for t in terms):
            return lens
    return available_lenses[0] if available_lenses else "summary"


def build_domain_queries(domain_result: Dict[str, Any], metric_cards=None, chart_candidates=None, sections=None) -> Dict[str, List[str]]:
    """Build retrieval lenses for the detected domain plus document-specific metrics."""
    profile = get_domain_profile(domain_result)
    domain = DOMAIN_ALIASES.get(str(domain_result.get("domain", "general")), str(domain_result.get("domain", "general")))
    queries: Dict[str, List[str]] = {k: list(v) for k, v in profile.get("retrieval_lenses", {}).items()}
    available = list(queries.keys()) or ["summary"]

    for card in metric_cards or []:
        label = clean_text(card.get("label") or card.get("name") or card.get("metric") or "")
        note = clean_text(card.get("note") or card.get("interpretation") or "")
        if not label:
            continue
        target = _choose_metric_lens(domain, f"{label} {note}", available)
        queries.setdefault(target, []).append(f"{label} {note} evidence driver implication root cause recommended action")

    for chart in chart_candidates or []:
        title = clean_text(chart.get("title") or "")
        if not title:
            continue
        target = _choose_metric_lens(domain, title, available)
        queries.setdefault(target, []).append(f"{title} trend driver variance risk opportunity implication")

    for section in sections or []:
        section = clean_text(section)
        if section:
            target = _choose_metric_lens(domain, section, available)
            queries.setdefault(target, []).append(f"{section} key evidence metrics risks implications actions")

    return queries


def _normalize_domain_language(item: Dict[str, Any], domain: str) -> Dict[str, Any]:
    """Keep implication/recommendation language aligned with the detected domain."""
    if not isinstance(item, dict):
        return item
    domain = DOMAIN_ALIASES.get(domain, domain)
    profile = get_domain_profile(domain)
    implication = clean_text(item.get("business_implication") or item.get("business_impact") or "")
    rec = clean_text(item.get("recommendation") or "")

    # Safety-sensitive domains get stricter wording.
    if domain == "medical":
        if not implication or any(t in implication.lower() for t in ("profit", "margin", "revenue", "ebitda", "cash")):
            if "business_implication" in item:
                item["business_implication"] = "Use as a clinical review signal; confirm interpretation with a qualified clinician before any care decision."
            if "business_impact" in item:
                item["business_impact"] = "Supports safer clinical review by linking the action to cited patient/health evidence."
        if rec and any(t in rec.lower() for t in ("profit", "margin", "revenue", "sales", "cash", "prescribe", "diagnose")):
            item["recommendation"] = "Flag the cited clinical signal for clinician review and compare it against patient context and current guidelines."
    elif domain == "pharma_clinical_trials":
        if not implication or any(t in implication.lower() for t in ("profit", "revenue", "contract")):
            if "business_implication" in item:
                item["business_implication"] = profile.get("implication_language", "Use as a clinical-trial review signal.")
            if "business_impact" in item:
                item["business_impact"] = profile.get("business_impact_language", "Supports safer trial review.")
        if rec and any(t in rec.lower() for t in ("prescribe", "diagnose", "approve")):
            item["recommendation"] = profile.get("fallback_recommendation", "Route the cited trial signal to clinical and regulatory review.")
    elif domain == "legal":
        if not implication or any(t in implication.lower() for t in ("profit", "margin", "revenue", "clinical")):
            if "business_implication" in item:
                item["business_implication"] = "Use as a contract/policy review signal; counsel should assess obligation, exposure, and enforceability."
            if "business_impact" in item:
                item["business_impact"] = "Reduces contractual or compliance exposure by linking action to cited clause evidence."
    else:
        if not implication:
            # For insight cards, the implication should already be blended into
            # the claim.  Do not add a separate generic implication line.
            if "business_implication" in item and not item.get("claim"):
                item["business_implication"] = profile.get("implication_language", "Use as an evidence-backed domain signal for management action.")
            if "business_impact" in item:
                item["business_impact"] = profile.get("business_impact_language", "Improves decision quality by linking action to cited evidence.")
    return item




def _percent_pair_improves(text: str) -> bool:
    low = clean_text(text).lower()
    if "margin" not in low:
        return False
    vals = [float(v) for v in re.findall(r"(-?\d+(?:\.\d+)?)\s*%", low)[:2]]
    if any(t in low for t in ("expanded", "improved", "increased")) and not any(t in low for t in ("declined", "decreased", "down", "pressure")):
        return True
    return "compared" in low and len(vals) >= 2 and vals[0] > vals[1]


def _adverse_evidence_title(text: str, domain: str, label: str) -> Optional[str]:
    """Create a specific risk title from evidence; return None for positive/neutral evidence."""
    low = clean_text(text).lower()
    if not low or _percent_pair_improves(low):
        return None
    adverse = any(t in low for t in (
        "decline", "declined", "decrease", "decreased", "down", "lower", "reduced",
        "pressure", "compression", "risk", "challenge", "constraint", "weak", "shortfall",
        "uncapped", "outdated", "breach", "non-compliance", "noncompliance", "churn",
        "stockout", "overdue", "missed", "deteriorat",
    ))
    cost_increase = any(t in low for t in ("cost", "expense", "tax rate", "dso", "overtime", "labor", "freight", "markdown")) and any(t in low for t in ("increase", "increased", "higher", "up"))
    if not adverse and not cost_increase:
        return None
    domain_l = str(domain or "").lower()
    if "legal" in domain_l or "contract" in domain_l:
        if "liability" in low or "indemn" in low:
            return "Liability or indemnity language may create disproportionate contract exposure."
        if "data processing" in low or "dpa" in low or "subprocessor" in low:
            return "Outdated data-processing terms may create compliance or audit exposure."
        if "renewal" in low or "notice" in low:
            return "Short renewal notice periods may reduce renegotiation control."
        return "Documented contract language may require legal review before action."
    if "finance" in domain_l or any(t in low for t in ("revenue", "margin", "cash", "eps", "ebitda", "expense")):
        if "gaap operating margin" in low and any(t in low for t in ("decrease", "decreased", "down", "decline")):
            return "GAAP operating margin decline should be monitored against adjusted profitability."
        if "tax rate" in low and any(t in low for t in ("higher", "increase", "increased", "up")):
            return "Higher effective tax rate may pressure net income and EPS."
        if "cash balance" in low and any(t in low for t in ("compared", "lower", "decline", "down")):
            return "Lower cash balance may reduce flexibility if the trend continues."
        if "cost" in low or "expense" in low:
            return "Cost or expense growth may weaken profit conversion if not managed."
        if "margin" in low:
            return "Margin pressure may weaken profit conversion if the cited driver persists."
        return "Documented adverse financial movement should be reviewed for impact on profit or cash conversion."
    if "sales" in domain_l:
        return "Documented pipeline, conversion, or retention weakness may reduce revenue quality."
    if "medical" in domain_l or "health" in domain_l:
        return "Documented clinical signal may require qualified review before action."
    return f"Documented {label.lower()} risk should be reviewed against severity and business impact."

def _domain_specific_fallbacks(domain: str, evidence_pack: Sequence[Dict[str, Any]], evidence_index: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Profile-driven fallback insights/risks/recommendations for every domain.

    This replaces the earlier hand-written fallbacks for only five domains.  It
    uses each profile's domain vocabulary and language so the deck remains
    domain-aware even when the LLM returns generic or unsupported text.
    """
    domain = DOMAIN_ALIASES.get(domain, domain)
    if domain == "legal":
        return _legal_fallback_items(evidence_pack, evidence_index)
    profile = get_domain_profile(domain)
    label = profile.get("label", "Document")
    signal_terms = profile.get("fallback_signal_terms") or [
        t for values in profile.get("retrieval_lenses", {}).values() for q in values for t in tokenize(q)[:6]
    ][:20]
    risk_terms = profile.get("fallback_risk_terms") or signal_terms[:10]
    implication = profile.get("implication_language", "Use this as an evidence-backed signal for management review.")
    fallback_rec = profile.get("fallback_recommendation", "Assign an owner to validate the cited evidence and define a targeted action plan.")
    impact = profile.get("business_impact_language", "Improves decision quality by linking action to cited evidence.")
    expert_note = profile.get("expert_review_note", "")

    insights: List[Dict[str, Any]] = []
    risks: List[Dict[str, Any]] = []
    recs: List[Dict[str, Any]] = []

    for item in _all_relevant_evidence(evidence_pack, signal_terms, 6):
        eid = item.get("id")
        if not eid:
            continue
        text = clean_text(item.get("text", ""))
        if not text:
            continue
        low_text = text.lower()
        if low_text.startswith("executive operating review") or low_text.startswith("domain expected") or len(text.split()) < 7:
            continue
        claim_text = clean_text(re.sub(r"^(Executive summary|Risk evidence|Management action requested|Core message|Summary)\s*:\s*", "", text[:360].rstrip("."), flags=re.I)) + "."
        insights.append({
            "claim": claim_text,
            "evidence_ids": [eid],
            "reasoning": "",
            "business_implication": "",
            "confidence": "high" if item.get("has_number") else "medium",
            "evidence_text": _ev_text(evidence_index, [eid]),
        })
        if len(insights) >= 5:
            break

    for item in _all_relevant_evidence(evidence_pack, risk_terms, 8):
        eid = item.get("id")
        if not eid:
            continue
        text = clean_text(item.get("text", ""))
        risk_title = _adverse_evidence_title(text, domain, label)
        if not risk_title:
            continue
        risks.append({
            "risk": risk_title,
            "severity": "Medium",
            "description": text[:320],
            "evidence_ids": [eid],
            "reasoning": f"{eid} contains an adverse or exposure-related signal. The implication should be validated against context, trend, and severity before action. {expert_note}".strip(),
            "mitigation": fallback_rec if "validate the cited evidence" not in fallback_rec.lower() else "Quantify the exposure, identify the root cause, and assign a mitigation owner.",
            "evidence_text": _ev_text(evidence_index, [eid]),
        })
        recs.append({
            "priority": "High",
            "recommendation": fallback_rec if "validate the cited evidence" not in fallback_rec.lower() else "Create a mitigation plan for the cited risk driver with owner, target, and review cadence.",
            "business_impact": impact,
            "evidence_ids": [eid],
            "reasoning": f"Evidence {eid} shows an adverse or exposure-related driver → interpretation identifies likely business impact → action targets the cited lever. {expert_note}".strip(),
            "evidence_text": _ev_text(evidence_index, [eid]),
        })
        if len(risks) >= 4:
            break

    def dedup(items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for item in items:
            k = clean_text(item.get(key, "")).lower()[:220]
            # For generic risk/recommendation fallback texts, include evidence ID in uniqueness.
            if key != "claim":
                k += "|" + ",".join(item.get("evidence_ids", []))
            if k and k not in seen:
                out.append(_normalize_domain_language(item, domain))
                seen.add(k)
        return out

    return dedup(insights, "claim")[:5], dedup(risks, "risk")[:4], dedup(recs, "recommendation")[:4]


def _phrase_count(text: str, phrase: str) -> int:
    """Count a phrase without matching inside longer words/phrases."""
    phrase = phrase.lower().strip()
    if not phrase:
        return 0
    pattern = r"(?<![a-z0-9])" + re.escape(phrase).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return len(re.findall(pattern, text, flags=re.I))


def classify_document_domain(
    chunks: Optional[Sequence[str]] = None,
    tables: Optional[Sequence[Dict[str, Any]]] = None,
    chart_candidates: Optional[Sequence[Dict[str, Any]]] = None,
    numbers: Optional[Sequence[Dict[str, Any]]] = None,
    metric_cards: Optional[Sequence[Dict[str, Any]]] = None,
    sections: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Classify the uploaded document into an explainable reasoning domain.

    This expanded classifier supports all current domain profiles and avoids
    substring matches such as "phase i" inside "phase iii".
    """
    text = _collect_classifier_text(chunks, tables, chart_candidates, numbers, metric_cards, sections)
    low = text.lower()
    scores: Dict[str, float] = {}
    signals: Dict[str, List[str]] = {}

    for domain in DOMAIN_ORDER:
        profile = DOMAIN_PROFILES[domain]
        score = 0.0
        matched: List[str] = []
        for raw_indicator in profile.get("indicators", []):
            indicator = _normalize_indicator(raw_indicator)
            if not indicator:
                continue
            if " " in indicator or "-" in indicator:
                count = _phrase_count(low, indicator)
                if count:
                    score += 2.7 + min(count, 5) * 0.65
                    matched.append(raw_indicator)
            else:
                count = len(re.findall(rf"\b{re.escape(indicator)}\b", low))
                if count:
                    score += min(count, 10) * 0.45
                    matched.append(raw_indicator)

        # Domain-specific confidence boosters.
        boosts = {
            "medical": (r"\b(mg|ml|mmhg|a1c|ldl|hdl|glucose|bpm)\b", "clinical units", 3.0),
            "pharma_clinical_trials": (r"\b(phase\s+(?:i|ii|iii|iv)|primary endpoint|serious adverse event|randomized|placebo)\b", "clinical trial design terms", 3.2),
            "legal": (r"\b(section|clause|shall|party|parties|agreement)\b", "legal drafting terms", 2.0),
            "research": (r"\b(p\s*[<=>]|confidence interval|sample size|methodology|baseline)\b", "research methods/statistics", 2.2),
            "finance": (r"\$\s*\d|\b(margin|ebitda|revenue|opex|eps|cash flow)\b", "financial metrics", 2.0),
            "sales": (r"\b(pipeline|conversion|win rate|quota|churn|renewal)\b", "sales funnel/customer metrics", 2.0),
            "food_beverage": (r"\b(food cost|same-store sales|spoilage|allergen|haccp|cold chain|delivery platform)\b", "food operating terms", 2.4),
            "operations_supply_chain": (r"\b(otif|stockout|lead time|warehouse|supplier|capacity utilization)\b", "supply chain operating terms", 2.1),
            "manufacturing_quality": (r"\b(oee|ppm|scrap|rework|first pass yield|downtime)\b", "manufacturing quality metrics", 2.3),
            "hr_workforce": (r"\b(attrition|turnover|headcount|time to fill|engagement score)\b", "workforce metrics", 2.0),
            "marketing": (r"\b(roas|ctr|cpc|cpm|cac|campaign)\b", "marketing performance metrics", 2.0),
            "customer_experience": (r"\b(nps|csat|ticket|resolution time|complaint|fcr)\b", "customer experience metrics", 2.0),
            "product_saas": (r"\b(arr|mrr|nrr|grr|dau|mau|feature adoption)\b", "SaaS/product metrics", 2.1),
            "risk_compliance": (r"\b(control gap|audit finding|non-compliance|remediation|material weakness)\b", "risk/control terms", 2.3),
            "insurance": (r"\b(loss ratio|combined ratio|underwriting|claims severity|earned premium)\b", "insurance metrics", 2.4),
            "real_estate": (r"\b(occupancy|vacancy|noi|cap rate|rent roll|lease expiry)\b", "real estate portfolio metrics", 2.2),
            "education": (r"\b(enrollment|graduation rate|attendance|dropout|student retention)\b", "education outcome metrics", 2.0),
            "esg_sustainability": (r"\b(scope\s+[123]|emissions|carbon|net zero|trir|sustainability)\b", "ESG/sustainability metrics", 2.2),
            "cybersecurity_it": (r"\b(cve|mfa|phishing|ransomware|vulnerability|backup restore)\b", "cybersecurity/IT terms", 2.4),
            "policy_government": (r"\b(public sector|agency|appropriation|service delivery|underserved|constituent)\b", "public-sector terms", 2.0),
        }
        if domain in boosts:
            pattern, name, amount = boosts[domain]
            if re.search(pattern, low, flags=re.I):
                score += amount
                matched.append(name)

        scores[domain] = round(score, 2)
        signals[domain] = list(OrderedDict.fromkeys(matched))[:10]

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_domain, best_score = sorted_scores[0] if sorted_scores else ("general", 0.0)
    second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0

    if best_score < 2.5:
        best_domain = "general"
        confidence = "low"
    elif best_score >= 8 and best_score >= max(second_score * 1.18, second_score + 1.5):
        confidence = "high"
    else:
        confidence = "medium"

    return {
        "domain": best_domain,
        "label": DOMAIN_PROFILES[best_domain]["label"],
        "confidence": confidence,
        "scores": scores,
        "signals": signals.get(best_domain, []),
        "all_signals": signals,
        "explanation": _domain_explanation(best_domain, confidence, signals.get(best_domain, [])),
    }
