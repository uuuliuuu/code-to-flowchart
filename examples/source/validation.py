def normalize(raw):
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value:
        return None
    return value.lower()
