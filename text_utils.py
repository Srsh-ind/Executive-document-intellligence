import re


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def truncate_text(text, limit=30000):
    if not text:
        return ""

    return text[:limit]


def count_words(text):
    if not text:
        return 0

    return len(text.split())