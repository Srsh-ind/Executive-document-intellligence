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
            or ""
        )

    return str(value)


def normalize_card(card):
    if isinstance(card, dict):

        # Metric-specific formats
        if "metric" in card:
            return {
                "label": str(card.get("metric", "")).strip(),
                "value": str(card.get("value", "")).strip(),
                "note": str(
                    card.get("note", "")
                    or card.get("interpretation", "")
                    or card.get("context", "")
                ).strip()
            }

        # Recommendation / action formats
        if "recommendation" in card:
            return {
                "label": str(card.get("priority", "Action")).strip(),
                "value": str(card.get("recommendation", "")).strip(),
                "note": str(
                    card.get("business_impact", "")
                    or card.get("impact", "")
                    or card.get("note", "")
                ).strip()
            }

        if "action" in card:
            return {
                "label": str(card.get("priority", "Action")).strip(),
                "value": str(card.get("action", "")).strip(),
                "note": str(
                    card.get("impact", "")
                    or card.get("business_impact", "")
                    or card.get("note", "")
                ).strip()
            }

        # Risk formats
        if "risk" in card:
            return {
                "label": "Risk",
                "value": str(card.get("risk", "")).strip(),
                "note": str(
                    card.get("description", "")
                    or card.get("impact", "")
                    or card.get("note", "")
                ).strip()
            }

        # Opportunity formats
        if "opportunity" in card:
            return {
                "label": "Opportunity",
                "value": str(card.get("opportunity", "")).strip(),
                "note": str(
                    card.get("description", "")
                    or card.get("impact", "")
                    or card.get("note", "")
                ).strip()
            }

        # Title + description formats
        if "title" in card and "description" in card:
            return {
                "label": str(card.get("title", "")).strip(),
                "value": str(card.get("description", "")).strip(),
                "note": str(
                    card.get("impact", "")
                    or card.get("business_impact", "")
                    or card.get("note", "")
                ).strip()
            }

        # Generic item format
        if "item" in card:
            text = str(card.get("item", "")).strip()

            if ":" in text:
                label, value = text.split(":", 1)
                return {
                    "label": label.strip(),
                    "value": value.strip(),
                    "note": ""
                }

            return {
                "label": "Insight",
                "value": text,
                "note": ""
            }

        # Generic fallback
        return {
            "label": str(
                card.get("label")
                or card.get("name")
                or card.get("priority")
                or card.get("title")
                or "Insight"
            ).strip(),
            "value": str(
                card.get("value")
                or card.get("status")
                or card.get("summary")
                or card.get("text")
                or ""
            ).strip(),
            "note": str(
                card.get("note")
                or card.get("interpretation")
                or card.get("description")
                or card.get("business_impact")
                or card.get("impact")
                or ""
            ).strip()
        }

    text = str(card).strip()

    if ":" in text:
        label, value = text.split(":", 1)
        return {
            "label": label.strip(),
            "value": value.strip(),
            "note": ""
        }

    return {
        "label": "Insight",
        "value": text,
        "note": ""
    }

def normalize_cards(cards):
    normalized = []

    for card in cards or []:
        clean = normalize_card(card)

        has_content = (
            clean.get("label")
            and clean.get("label") != "Item"
        ) or clean.get("value") or clean.get("note")

        if has_content:
            normalized.append(clean)

    return normalized


def normalize_bullets(bullets):
    cleaned = []

    for item in bullets or []:
        text = safe_text(item)

        if text:
            cleaned.append(text)

    return cleaned


def normalize_blocks(blocks):
    cleaned = []

    for block in blocks or []:
        if not isinstance(block, dict):
            continue

        label = block.get("label", "Section")
        items = normalize_bullets(block.get("items", []))

        if label and items:
            cleaned.append({
                "label": label,
                "items": items
            })

    return cleaned


def normalize_storyboard(storyboard):
    normalized = []

    for slide in storyboard:
        slide = dict(slide)

        slide["cards"] = normalize_cards(slide.get("cards", []))
        slide["bullets"] = normalize_bullets(slide.get("bullets", []))
        slide["blocks"] = normalize_blocks(slide.get("blocks", []))

        has_content = (
            slide.get("message")
            or slide.get("headline")
            or slide.get("so_what")
            or slide["cards"]
            or slide["bullets"]
            or slide["blocks"]
        )

        if has_content:
            normalized.append(slide)

    return normalized