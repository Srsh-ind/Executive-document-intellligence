
"""Storyboard normalization and quality gating.

The LLM can occasionally return visually valid but content-empty slides such as
cards with only labels ("Revenue Breakdown") and no value/body.  This module
turns those into useful fallback slides or drops them before the PPT builder runs.
"""

import re

CHART_LAYOUTS = {
    "performance_dashboard",
    "split_metrics_chart",
    "comparison_dashboard",
    "donut_insights",
    "dashboard_grid",
    "before_after",
}

ROADMAP_LAYOUTS = {"roadmap", "timeline", "recommendation_roadmap"}


def safe_text(value):
    if value is None:
        return ""

    if isinstance(value, dict):
        return (
            value.get("item")
            or value.get("text")
            or value.get("description")
            or value.get("recommendation")
            or value.get("risk")
            or value.get("opportunity")
            or value.get("title")
            or value.get("value")
            or ""
        )

    return str(value)


def _clean(value):
    return str(value or "").strip()


def _evidence_suffix(card):
    # Evidence IDs are retained in analysis metadata, but are no longer rendered
    # on dashboard tabs or PPT slides.
    return ""


def _join_note(*parts):
    cleaned = [_clean(p) for p in parts if _clean(p)]
    return " | ".join(cleaned)


def _display_clean(value):
    text = _clean(value)
    lines = []
    for line in text.splitlines():
        low = line.strip().lower()
        if low.startswith(("audience:", "domain expected:", "prepared for:", "reporting period:", "source profile:")):
            continue
        lines.append(line)
    text = "\n".join(lines).strip()
    text = re.sub(r"\s*\|?\s*Evidence\s*(?:IDs?|references?)?\s*[:：]\s*(?:E\d{3}(?:\s*[,;]\s*)?)+", "", text, flags=re.I)
    text = re.sub(r"\s*\(?\bE\d{3}(?:\s*[,;]\s*E\d{3})*\)?", "", text, flags=re.I)
    text = re.sub(r"^(Implication|Reasoning|Business implication)\s*[:：]\s*", "", text, flags=re.I)
    text = text.replace("Evidence → interpretation → implication:", "")
    text = text.replace("Evidence -> interpretation -> implication:", "")
    text = text.replace("Evidence → interpretation → action → expected impact:", "")
    text = text.replace("Evidence -> interpretation -> action -> expected impact:", "")
    text = re.sub(r"\bStrategies should focus on\s*$", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()




def _visible_reasoning(value):
    text = _display_clean(value)
    low = text.lower()
    if not text or any(bad in low for bad in (
        "retrieved supporting evidence",
        "cited evidence",
        "evidence item",
        "directly derived",
        "contains a numeric document fact",
        "reasoning path is",
    )):
        return ""
    return text[:360].rstrip()


def _is_generic_action(text):
    low = _display_clean(text).lower()
    return (
        low.startswith("assign an owner to validate")
        or "validate the cited evidence" in low
        or low.startswith("define a targeted action plan")
    )


def _is_generic_review_item(text):
    low = _display_clean(text).lower()
    return low.startswith("evidence-backed ") and (" risk or review item" in low or " signal" in low)

def _card_body_strength(card):
    value = _display_clean(card.get("value", ""))
    note = _display_clean(card.get("note", ""))
    text = f"{value} {note}".strip()
    numeric_only = bool(re.fullmatch(r"[-+]?\$?\d+(?:\.\d+)?\s*(?:%|bps|M|B)?", text or "", flags=re.I))
    has_sentence = len(text.split()) >= 8 or any(p in text for p in (".", ";"))
    return 0 if numeric_only else (2 if has_sentence else 1 if text else 0)


def _weak_insight_cards(cards):
    cards = cards or []
    if not cards:
        return False
    labels = [_display_clean(c.get("label", "")).lower() for c in cards if isinstance(c, dict)]
    duplicate_labels = len(labels) >= 3 and len(set(labels)) <= max(1, len(labels) // 2)
    weak_bodies = sum(1 for c in cards if isinstance(c, dict) and _card_body_strength(c) <= 1)
    return duplicate_labels or weak_bodies >= max(2, len(cards) // 2)


def _meaningful(text):
    text = _clean(text)
    if not text:
        return False
    generic = {
        "insight", "section", "item", "risk", "opportunity", "action", "metric",
        "priority", "high", "medium", "low", "status", "recommendation",
    }
    return text.lower() not in generic


def _dashboard_section_ok(text):
    text = _clean(text)
    low = text.lower()
    if not _meaningful(text):
        return False
    # Avoid surfacing source-control/debug/audience metadata in slide boxes.
    bad_prefixes = (
        "audience", "prepared for", "domain expected", "reporting period", "source profile"
    )
    return not any(low.startswith(p) for p in bad_prefixes)


def normalize_card(card):
    if isinstance(card, dict):

        # Metric-specific formats
        if "metric" in card or "name" in card:
            return {
                "label": _display_clean(card.get("metric") or card.get("name") or card.get("label") or "Metric"),
                "value": _display_clean(card.get("value") or card.get("amount") or card.get("number") or ""),
                "note":  _display_clean(card.get("note") or card.get("interpretation") or card.get("context") or "")
            }

        # Recommendation / action formats
        if "recommendation" in card:
            return {
                "label": _display_clean(card.get("priority") or card.get("label") or "Action"),
                "value": _display_clean(card.get("recommendation") or card.get("value") or ""),
                "note":  _join_note(card.get("business_impact") or card.get("impact") or card.get("note") or "", _evidence_suffix(card))
            }

        if "action" in card:
            return {
                "label": _display_clean(card.get("priority") or card.get("label") or "Action"),
                "value": _display_clean(card.get("action") or card.get("value") or ""),
                "note":  _join_note(card.get("impact") or card.get("business_impact") or card.get("note") or "", _evidence_suffix(card))
            }

        # Risk formats
        if "risk" in card:
            return {
                "label": _display_clean(card.get("label") or "Risk"),
                "value": _display_clean(card.get("risk") or card.get("value") or ""),
                "note":  _join_note(card.get("description") or card.get("impact") or card.get("note") or "", _evidence_suffix(card))
            }

        # Opportunity formats
        if "opportunity" in card:
            return {
                "label": _display_clean(card.get("label") or "Opportunity"),
                "value": _display_clean(card.get("opportunity") or card.get("value") or ""),
                "note":  _join_note(card.get("description") or card.get("impact") or card.get("note") or "", _evidence_suffix(card))
            }

        # Explainable insight format. Keep the visible card as one blended
        # executive statement; evidence details remain available in the Evidence tab.
        if "claim" in card:
            return {
                "label": _display_clean(card.get("label") or "Insight"),
                "value": _display_clean(card.get("claim") or ""),
                "note": _visible_reasoning(card.get("reasoning") or card.get("business_implication") or card.get("implication") or "")
            }

        # Title + description formats
        if "title" in card and "description" in card:
            return {
                "label": _display_clean(card.get("title") or "Insight"),
                "value": _display_clean(card.get("description") or ""),
                "note":  _join_note(card.get("impact") or card.get("business_impact") or card.get("note") or "", _evidence_suffix(card))
            }

        # Generic item format
        if "item" in card:
            text = _clean(card.get("item"))
            if ":" in text:
                label, value = text.split(":", 1)
                return {"label": _clean(label), "value": _clean(value), "note": ""}
            return {"label": "Insight", "value": text, "note": ""}

        # Generic fallback
        return {
            "label": _clean(
                card.get("label") or card.get("name") or card.get("priority")
                or card.get("title") or "Insight"
            ),
            "value": _clean(
                card.get("value") or card.get("status") or card.get("summary")
                or card.get("text") or card.get("body") or ""
            ),
            "note": _join_note(
                card.get("note") or card.get("interpretation") or card.get("description")
                or card.get("business_impact") or card.get("impact") or "",
                _evidence_suffix(card)
            )
        }

    text = _clean(card)
    if ":" in text:
        label, value = text.split(":", 1)
        return {"label": _clean(label), "value": _clean(value), "note": ""}
    return {"label": "Insight", "value": text, "note": ""}


def _card_has_body(card):
    return _meaningful(card.get("value")) or _meaningful(card.get("note"))


def normalize_cards(cards):
    normalized = []

    for card in cards or []:
        clean = normalize_card(card)

        # Drop label-only cards.  These caused the "nothing came" blank boxes.
        # If the label itself is a full sentence, preserve it as a body insight.
        if not _card_has_body(clean):
            label = _clean(clean.get("label"))
            if len(label.split()) >= 5:
                clean = {"label": "Insight", "value": label, "note": ""}
            else:
                continue

        if _is_generic_action(clean.get("value", "")) or _is_generic_review_item(clean.get("value", "")):
            continue
        normalized.append(clean)

    return normalized


def normalize_bullets(bullets):
    cleaned = []
    for item in bullets or []:
        text = _display_clean(safe_text(item))
        if _meaningful(text) and not _is_generic_action(text) and not _is_generic_review_item(text):
            cleaned.append(text)
    return cleaned


def normalize_blocks(blocks):
    cleaned = []
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        label = _clean(block.get("label") or "Section")
        items = normalize_bullets(block.get("items", []))
        if _meaningful(label) and items:
            cleaned.append({"label": label, "items": items})
    return cleaned


def _recommendation_text(item):
    if isinstance(item, dict):
        text = _display_clean(item.get("recommendation") or item.get("action") or item.get("value") or item.get("title") or "")
    else:
        text = _display_clean(item)
    return "" if _is_generic_action(text) else text


def _as_cards(items, default_label="Insight", limit=6):
    cards = []
    for item in (items or [])[:limit]:
        if isinstance(item, dict):
            cards.append(normalize_card(item))
        else:
            cards.append({"label": default_label, "value": _clean(item), "note": ""})
    return normalize_cards(cards)


def _summary_blocks(analysis):
    blocks = []
    sections = [s for s in (analysis.get("sections") or []) if _dashboard_section_ok(s)]
    findings = [s for s in (analysis.get("key_findings") or analysis.get("insights") or []) if _meaningful(s)]
    actions = [_recommendation_text(r) for r in (analysis.get("recommendations") or [])]
    actions = [a for a in actions if _meaningful(a)]

    if sections:
        blocks.append({"label": "Focus Areas", "items": sections[:4]})
    if findings:
        blocks.append({"label": "Key Findings", "items": findings[:5]})
    if actions:
        blocks.append({"label": "Next Steps", "items": actions[:4]})
    if len(blocks) < 3 and analysis.get("opportunities"):
        blocks.append({"label": "Opportunities", "items": normalize_bullets(analysis.get("opportunities"))[:4]})
    return blocks[:3]


def _layout_fallback_cards(layout, role, analysis):
    role = (role or "").lower()
    if layout in {"kpi_dashboard", "dashboard_grid", "split_metrics_chart", "comparison_dashboard", "donut_insights"}:
        return _as_cards(analysis.get("metrics") or analysis.get("metric_cards"), "Metric", 6)
    if layout == "risk_dashboard" or "risk" in role:
        return _as_cards((analysis.get("risks") or [])[:3] + (analysis.get("opportunities") or [])[:3], "Watch Area", 6)
    if layout == "opportunity_dashboard" or "opportun" in role:
        return _as_cards(analysis.get("opportunities"), "Opportunity", 6)
    if layout == "action_tracker" or "action" in role or "recommend" in role or "future" in role:
        return _as_cards(analysis.get("recommendations"), "Action", 5)
    return []


def _layout_fallback_bullets(layout, role, analysis):
    role = (role or "").lower()
    if layout == "risk_dashboard" or "risk" in role:
        return normalize_bullets(analysis.get("risks") or analysis.get("limitations") or analysis.get("key_findings"))[:6]
    if layout == "opportunity_dashboard" or "opportun" in role:
        return normalize_bullets(analysis.get("opportunities") or analysis.get("key_findings"))[:6]
    if layout == "action_tracker" or "action" in role or "future" in role:
        return [_recommendation_text(r) for r in (analysis.get("recommendations") or [])[:5] if _recommendation_text(r)]
    return normalize_bullets(analysis.get("insights") or analysis.get("key_findings") or analysis.get("sections"))[:6]


def _rewrite_roadmap_title(title):
    title = _clean(title)
    if "roadmap" in title.lower() or "timeline" in title.lower():
        return "Implementation Priorities"
    return title


def enrich_slide(slide, analysis):
    layout = slide.get("layout", "insight_dashboard")
    role = slide.get("story_role", "")

    if layout in ROADMAP_LAYOUTS:
        slide["layout"] = "action_tracker"
        layout = "action_tracker"
        slide["title"] = _rewrite_roadmap_title(slide.get("title", "Implementation Priorities"))
        slide["visual_style"] = "cards"

    # Normalize title too, so a converted roadmap does not still look like one.
    slide["title"] = _rewrite_roadmap_title(slide.get("title", "Insight"))

    if layout == "summary_dashboard":
        if len(slide.get("blocks", [])) < 2:
            slide["blocks"] = _summary_blocks(analysis)
        if not slide.get("cards"):
            slide["cards"] = _as_cards(analysis.get("metrics") or analysis.get("metric_cards"), "Metric", 4)

    elif layout == "kpi_dashboard":
        if not slide.get("cards"):
            slide["cards"] = _as_cards(analysis.get("metrics") or analysis.get("metric_cards"), "Metric", 6)
        # Long single metric values (for example a segment ACV list) make a KPI slide
        # look broken. Let the summary and chart slides carry that evidence instead.
        if len(slide.get("cards") or []) < 2:
            slide["cards"] = []

    elif layout in CHART_LAYOUTS:
        # Chart layouts may legitimately have no cards/bullets if chart_paths exists.
        if not analysis.get("chart_paths") and not slide.get("cards") and not slide.get("bullets") and not slide.get("blocks"):
            slide["bullets"] = _layout_fallback_bullets(layout, role, analysis)

    elif layout == "insight_dashboard":
        # Keep PPT insight content aligned with the dashboard: use explainable
        # insight cards with concise reasoning, not raw LLM bullets.  Limit to
        # three cards so reasoning stays inside each box.
        preferred = analysis.get("explainable_insights") or analysis.get("insights") or analysis.get("key_findings")
        if preferred:
            slide["cards"] = _as_cards(preferred, "Insight", 3)
            slide["bullets"] = []
        elif _weak_insight_cards(slide.get("cards") or []):
            slide["cards"] = _as_cards(preferred, "Insight", 3)
        elif not slide.get("cards") and not slide.get("bullets"):
            slide["cards"] = _as_cards(preferred, "Insight", 3)

    elif layout in {"risk_dashboard", "opportunity_dashboard", "action_tracker"}:
        if not slide.get("cards"):
            slide["cards"] = _layout_fallback_cards(layout, role, analysis)
        if not slide.get("cards") and not slide.get("bullets"):
            slide["bullets"] = _layout_fallback_bullets(layout, role, analysis)

    else:
        if not slide.get("cards") and not slide.get("bullets") and not slide.get("blocks"):
            slide["bullets"] = _layout_fallback_bullets(layout, role, analysis)

    # Add a usable headline if the LLM left only a label/title.
    if not _meaningful(slide.get("headline")):
        slide["headline"] = _clean(slide.get("message") or slide.get("so_what") or analysis.get("core_message") or "")

    return slide


def _slide_has_renderable_content(slide, analysis):
    layout = slide.get("layout", "")
    if layout in CHART_LAYOUTS and analysis.get("chart_paths"):
        return True
    if slide.get("cards") or slide.get("bullets") or slide.get("blocks"):
        return True
    # Allow a summary/conclusion-like text slide, but do not allow label-only blank boxes.
    return _meaningful(slide.get("message")) or _meaningful(slide.get("headline")) or _meaningful(slide.get("so_what"))


def _make_cover(analysis):
    return {
        "story_role":   "cover",
        "layout":       "hero_cover",
        "title":        analysis.get("title", "Executive Insight Report"),
        "headline":     analysis.get("core_message", ""),
        "message":      analysis.get("executive_summary", ""),
        "so_what":      analysis.get("core_message", ""),
        "cards":        [],
        "bullets":      [],
        "blocks":       [],
        "visual_title": "",
        "visual_style": "cover",
        "density":      "low",
    }


def _make_closing(analysis):
    return {
        "story_role":   "closing",
        "layout":       "closing_slide",
        "title":        "Closing",
        "headline":     analysis.get("conclusion", analysis.get("core_message", "")),
        "message":      analysis.get("conclusion", ""),
        "so_what":      analysis.get("conclusion", ""),
        "cards":        [],
        "bullets":      [],
        "blocks":       [],
        "visual_title": "",
        "visual_style": "minimal",
        "density":      "low",
    }


def normalize_storyboard(storyboard, analysis=None):
    """
    Normalize cards/bullets/blocks on each slide, enrich weak slides with
    deterministic fallbacks from analysis, and drop empty slides before render.
    Also ensures hero_cover is slide 1 and closing_slide is last.
    """
    analysis = analysis or {}
    normalized = []
    seen = set()

    for slide in storyboard or []:
        if not isinstance(slide, dict):
            continue
        slide = dict(slide)
        layout = slide.get("layout", "") or "insight_dashboard"

        # Skip cover/closing from original list — we'll add them ourselves.
        if layout in ("hero_cover", "closing_slide"):
            continue

        slide["cards"] = normalize_cards(slide.get("cards", []))
        slide["bullets"] = normalize_bullets(slide.get("bullets", []))
        slide["blocks"] = normalize_blocks(slide.get("blocks", []))
        slide = enrich_slide(slide, analysis)

        # A KPI slide with one tiny card looks empty in the deck. Drop it and
        # let the summary/insight slides carry the available metric.
        if slide.get("layout") == "kpi_dashboard" and len(slide.get("cards") or []) < 2:
            continue

        if not _slide_has_renderable_content(slide, analysis):
            continue

        # Deduplicate low-value repeated slide shells.
        sig = (
            slide.get("layout", ""),
            _clean(slide.get("title", "")).lower(),
            tuple(c.get("value", "") for c in slide.get("cards", [])[:3]),
            tuple(slide.get("bullets", [])[:3]),
        )
        if sig in seen:
            continue
        seen.add(sig)
        normalized.append(slide)

    orig_cover = next((dict(s) for s in (storyboard or []) if isinstance(s, dict) and s.get("layout") == "hero_cover"), None)
    orig_closing = next((dict(s) for s in (storyboard or []) if isinstance(s, dict) and s.get("layout") == "closing_slide"), None)

    cover = orig_cover or _make_cover(analysis)
    closing = orig_closing or _make_closing(analysis)

    for s in (cover, closing):
        s["cards"] = normalize_cards(s.get("cards", []))
        s["bullets"] = normalize_bullets(s.get("bullets", []))
        s["blocks"] = normalize_blocks(s.get("blocks", []))

    return [cover] + normalized + [closing]
