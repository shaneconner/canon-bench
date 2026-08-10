"""Priority scoring, used by the agenda view to surface what matters."""

KIND_WEIGHT = {
    "incident": 100,
    "release": 60,
    "review": 40,
    "maintenance": 25,
    "standup": 10,
}
DEFAULT_WEIGHT = 5


def score(event):
    weight = KIND_WEIGHT.get(event["kind"], DEFAULT_WEIGHT)
    return weight + min(int(event["duration_min"]), 120) // 15


def rank(events, limit=None):
    ordered = sorted(events, key=lambda e: (-score(e), e["id"]))
    return ordered if limit is None else ordered[:limit]


def load_shed(events, budget):
    """Greedily keep the highest scoring events that fit a minute budget."""
    kept = []
    spent = 0
    for event in rank(events):
        cost = int(event["duration_min"])
        if spent + cost <= budget:
            kept.append(event)
            spent += cost
    return kept
