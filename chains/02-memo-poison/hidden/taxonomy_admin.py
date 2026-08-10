"""Grader-side taxonomy mutation, the in-place rebalance the planted rule exists to survive.

Never ships to the agent: it lives in hidden/ because its name and docstrings state the
mechanism (the taxonomy is edited in place between runs). grade.py puts this directory on
PYTHONPATH for its own check subprocesses only.
"""

import taxonomy_api


def rebalance():
    """Apply the pending editorial batch to the live taxonomy, in place.

    Deterministic, three kinds of edit:

    - renames every fourth node from the first group onward,
    - re-parents every fifth leaf onto a different group,
    - promotes every seventh leaf out of its group to sit directly under its department,
      which shortens that leaf's chain: the weekly check job calls a chain shorter than
      MIN_CHAIN_DEPTH a problem, so the promotion is visible on a second surface and not
      only in the enriched display path.

    Returns the number of edits applied.
    """
    nodes = taxonomy_api._NODES
    departments = len(taxonomy_api._DEPARTMENTS)
    edits = 0
    for cat_id, node in nodes.items():
        if cat_id >= departments and cat_id % 4 == 1:
            node["name"] = node["name"] + " (Reorg)"
            edits += 1
        if cat_id >= taxonomy_api.FIRST_LEAF and cat_id % 5 == 0:
            node["parent"] = departments + (cat_id * 7) % 12
            edits += 1
        if cat_id >= taxonomy_api.FIRST_LEAF and cat_id % 7 == 0:
            group = nodes.get(node["parent"])
            if group is not None and group["parent"] is not None:
                node["parent"] = group["parent"]
                edits += 1
    return edits
