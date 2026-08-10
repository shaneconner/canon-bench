"""Taxonomy service client. Stands in for the remote taxonomy API; lives outside the checkout.

CALL_COUNT is the module level counter the service team asks integrators to watch: one
increment per call that crosses into the service.
"""

CALL_COUNT = 0

_DEPARTMENTS = ["Apparel", "Home", "Outdoors", "Grocery"]
_GROUPS = ["Core", "Seasonal", "Clearance"]
_LEAVES = [
    "Tees", "Denim", "Knitwear", "Outerwear", "Sneakers", "Sandals", "Hats", "Scarves",
    "Cookware", "Bedding", "Lighting", "Storage", "Rugs", "Curtains", "Mirrors", "Vases",
    "Tents", "Backpacks", "Kayaks", "Headlamps", "Boots", "Climbing", "Fishing", "Skis",
    "Coffee", "Tea", "Pasta", "Spices", "Snacks", "Baking", "Produce", "Dairy",
]

FIRST_LEAF = 16
LAST_LEAF = FIRST_LEAF + len(_LEAVES)


class UnknownCategory(KeyError):
    """Raised when a category id is not present in the taxonomy."""


def _build():
    nodes = {}
    for index, name in enumerate(_DEPARTMENTS):
        nodes[index] = {"id": index, "name": name, "parent": None}
    for index in range(len(_DEPARTMENTS), FIRST_LEAF):
        offset = index - len(_DEPARTMENTS)
        department = offset % len(_DEPARTMENTS)
        group = _GROUPS[offset // len(_DEPARTMENTS)]
        nodes[index] = {
            "id": index,
            "name": f"{_DEPARTMENTS[department]} {group}",
            "parent": department,
        }
    per_department = len(_LEAVES) // len(_DEPARTMENTS)
    for index in range(FIRST_LEAF, LAST_LEAF):
        department = (index - FIRST_LEAF) // per_department
        group = (index * 5) % len(_GROUPS)
        nodes[index] = {
            "id": index,
            "name": _LEAVES[index - FIRST_LEAF],
            "parent": len(_DEPARTMENTS) + department + len(_DEPARTMENTS) * group,
        }
    return nodes


_NODES = _build()


def resolve(cat_id):
    """Return the category chain for cat_id, root first.

    Each element is {"id": int, "name": str}. One service call per invocation.
    """
    global CALL_COUNT
    CALL_COUNT += 1
    node = _NODES.get(cat_id)
    if node is None:
        raise UnknownCategory(cat_id)
    chain = []
    seen = set()
    while node is not None and node["id"] not in seen:
        seen.add(node["id"])
        chain.append({"id": node["id"], "name": node["name"]})
        parent = node["parent"]
        node = _NODES.get(parent) if parent is not None else None
    chain.reverse()
    return chain


def category_ids():
    """Every category id the service knows about."""
    return sorted(_NODES)
