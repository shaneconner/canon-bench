"""W4 lineages: the W3 generator at K=8 only, under a fresh seed.

W4 measures writer behavior (staleness, store growth) under two tool voices,
so it needs only the deepest rung: the per-session store snapshots inside a
K=8 lineage carry the whole growth trajectory. Both arms run the SAME eight
lineages; the arms differ only in the kit's tool.ts. Fresh seed so no fixture
is reused across captures.
"""

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "w3"))

import w3_lineage as base  # noqa: E402

DEV_SEED = hashlib.sha256(b"w4-dev-seed-v1").digest()

state_at = base.state_at
DOMAINS = base.DOMAINS


def build_all() -> list[dict]:
    # The generator reads its module-level seed; W4 swaps it for its own and
    # restores it, so an interleaved W3 import cannot be poisoned.
    saved = base.DEV_SEED
    base.DEV_SEED = DEV_SEED
    try:
        lineages = [base.build_lineage(domain, 8) for domain in DOMAINS]
    finally:
        base.DEV_SEED = saved
    assert len(lineages) == 8
    for entry in lineages:
        entry["lineage_key"] = f"{entry['domain']}_w4k8"
        assert entry["k"] == 8
        assert entry["retire_at"] == 7 and entry["flip_at"] == 5
        assert len(entry["superseded"]["capacity_limit"]) == 7
    decisions = [t["expected"]["decision"] for e in lineages for t in e["tasks"]]
    # Both outcomes of both derivations must occur.
    assert 1 <= decisions.count("proceed") <= 7, decisions.count("proceed")
    assert 1 <= decisions.count("notify") <= 7, decisions.count("notify")
    return lineages


if __name__ == "__main__":
    built = build_all()
    for entry in built:
        print(entry["lineage_key"], entry["facts_final"]["consumer_status"],
              [t["expected"]["decision"] for t in entry["tasks"]])
