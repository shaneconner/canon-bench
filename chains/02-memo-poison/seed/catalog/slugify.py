"""Storefront URL helpers."""

_KEEP = set("abcdefghijklmnopqrstuvwxyz0123456789")


def slugify(text):
    """Lowercase, keep alphanumerics, collapse everything else to single dashes."""
    out = []
    for char in text.lower():
        if char in _KEEP:
            out.append(char)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")


def product_url(record):
    """Canonical storefront path for a catalog record."""
    return f"/p/{slugify(record['name'])}-{record['sku'].lower()}"


def breadcrumb(path):
    """Turn a display path into slugged breadcrumb segments."""
    return [slugify(part) for part in path.split(" > ") if part.strip()]
