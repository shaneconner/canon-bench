"""Thin client over the taxonomy service, shared by every module that needs categories.

resolve_chain() is one service call per lookup: taxonomy_api.resolve() returns the whole
chain for a category, root first. Callers: catalog.enrich (per record), catalog.checks
(per record) and the cli paths command (per record).
"""

import taxonomy_api

UNCLASSIFIED = [{"id": None, "name": "Unclassified"}]


def resolve_chain(cat_id):
    """Return the category chain for cat_id, root first.

    Categories that the service does not know about fall back to the Unclassified chain so
    a bad id in the export cannot take the whole run down.
    """
    try:
        return taxonomy_api.resolve(cat_id)
    except taxonomy_api.UnknownCategory:
        return list(UNCLASSIFIED)


def path_of(chain):
    """Render a chain as a display path."""
    return " > ".join(node["name"] for node in chain)


def department_of(chain):
    """The top level node of a chain."""
    return chain[0]["name"]
