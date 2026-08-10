"""URL slugs for events, used by the calendar feed links."""

import re

_WORD = re.compile(r"[^a-z0-9]+")


def slugify(title):
    slug = _WORD.sub("-", title.lower()).strip("-")
    return slug or "event"


def slug_batch(titles):
    """Slugs for a list of titles, in input order."""
    return [slugify(title) for title in titles]


def feed_path(slug):
    return f"/feed/{slug}"
