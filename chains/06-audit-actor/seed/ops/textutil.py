"""Small text helpers. Unrelated to the audit sink."""


def truncate(value, limit):
    if limit < 1:
        raise ValueError("limit must be positive")
    return value if len(value) <= limit else value[: limit - 1] + "…"


def slug(value):
    out = []
    for char in value.lower():
        out.append(char if char.isalnum() else "-")
    return "-".join(part for part in "".join(out).split("-") if part)
