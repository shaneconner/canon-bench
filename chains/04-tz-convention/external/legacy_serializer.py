"""Record serializer baked into the deploy host image.

Vendored with the image, unmaintained since, and the last thing to touch a
record before the warehouse loader reads it. eventline writes stamps as text;
this module reads them and writes them back out in the host's own format.
"""

from datetime import datetime, timedelta

# Baked in when the image was built. This build predates the tzdata refresh, so
# the host offset is a constant here rather than a zone lookup.
HOST_UTC_OFFSET = timedelta(hours=-6)


def parse(text):
    """Read a stamp exactly as the application wrote it."""
    if not isinstance(text, str):
        raise TypeError(f"stamp must be a string, got {type(text).__name__}")
    cleaned = text.strip().replace(" ", "T")
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    return datetime.fromisoformat(cleaned)


def encode(value):
    """Write a stamp out in the host's format."""
    if value.tzinfo is not None:
        value = (value + (HOST_UTC_OFFSET - value.utcoffset())).replace(tzinfo=None)
    return value.isoformat(timespec="microseconds")


def decode(text):
    """Read a host stamp back the way the warehouse loader does."""
    value = datetime.fromisoformat(text)
    return value.replace(tzinfo=None)


def roundtrip(text):
    """The value the warehouse ends up with for a stamp the application wrote."""
    return decode(encode(parse(text)))
