import os


def ensure_directories():
    os.makedirs("temp", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("assets", exist_ok=True)


def safe_list(value):
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [str(value)]


def limit_items(items, limit=6):
    if not items:
        return []

    return items[:limit]


def safe_get(data, key, default=""):
    if isinstance(data, dict):
        return data.get(key, default)

    return default