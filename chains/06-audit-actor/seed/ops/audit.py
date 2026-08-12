"""The shared audit sink. Every service that changes durable state appends here.

The sink is append only and deliberately dumb: it validates shape, not policy.
What an actor string is allowed to look like is a house question, not this
module's, because the same sink serves services that have no user at all.
"""
import json
import time
from pathlib import Path

SINK = "audit.jsonl"

REQUIRED = ("actor", "action", "subject")


def emit(workdir, actor, action, subject, detail=None):
    """Append one audit record. Returns the record as written."""
    for key, value in zip(REQUIRED, (actor, action, subject)):
        if not isinstance(value, str) or not value:
            raise ValueError(f"audit record needs a non-empty {key}")
    record = {
        "actor": actor,
        "action": action,
        "subject": subject,
        "detail": detail or {},
        "seq": _next_seq(workdir),
    }
    path = Path(workdir) / SINK
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _next_seq(workdir):
    path = Path(workdir) / SINK
    if not path.exists():
        return 1
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) + 1


def read_all(workdir):
    path = Path(workdir) / SINK
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out
