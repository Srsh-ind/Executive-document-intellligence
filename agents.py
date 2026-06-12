from json_utils import validate_analysis


def remove_empty_sections(analysis):
    """
    Removes empty sections from generated analysis.
    """
    cleaned_sections = []

    for section in analysis.get("sections", []):
        if not isinstance(section, dict):
            continue

        heading = section.get("heading", "")
        bullets = section.get("bullets", [])

        if heading and bullets:
            cleaned_sections.append(section)

    analysis["sections"] = cleaned_sections
    return analysis


def add_default_conclusion(analysis):
    """
    Adds a conclusion only if the model did not provide one.
    """
    if not analysis.get("conclusion"):
        analysis["conclusion"] = (
            "The document has been condensed into key themes, findings, and implications. "
            "The next step is to validate the extracted insights with subject matter experts."
        )

    return analysis


def enrich_analysis(analysis):
    """
    Main post-processing function.
    Makes the model output safer and presentation-ready.
    """
    analysis = validate_analysis(analysis)
    analysis = remove_empty_sections(analysis)
    analysis = add_default_conclusion(analysis)

    if not analysis.get("core_message") and analysis.get("executive_summary"):
        analysis["core_message"] = analysis["executive_summary"][:250]

    return analysis