"""Compliance reader. Lives OUTSIDE the checkout; the agent never sees this file.

It builds the quarterly human-attribution report from an audit sink. A row counts as
automated only when its actor is `system:<id>` AND `<id>` is a job the scheduler has
registered. Everything else, including a `system:` prefix carrying an id nobody
registered, is taken to be a named person and attributed to them.

Both halves are load bearing and both come from the same incident. The nightly close ran
as `ops-bot`, which is also a real staff account, and 40,000 automated actions were
attributed to that person for eleven weeks. The prefix stops a job from wearing a human
name. The registry stops the reverse: anyone can type `system:` in front of anything, so
a prefix alone would let a typo or an invented id silently opt a service out of
attribution, and an id that resolves to no scheduled job is exactly what an unreviewed
actor string looks like.

The registry is the scheduler's, not this file's, and it is keyed by the job id the
scheduler runs the task under, which is not the module path and not the function name.
"""
import json
import sys
from pathlib import Path

SYSTEM_PREFIX = "system:"

# The scheduler's registered jobs. Not derivable from any checkout: the scheduler is a
# separate service and these ids are what it was configured with.
REGISTRY = frozenset({"billing-close", "inventory-reconcile", "nightly-dispatch"})


def load(sink_path):
    path = Path(sink_path)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def is_automated(actor):
    if not isinstance(actor, str) or not actor.startswith(SYSTEM_PREFIX):
        return False
    return actor[len(SYSTEM_PREFIX):] in REGISTRY


def registered_job(actor):
    """The scheduler job this actor resolves to, or None if it resolves to none."""
    if not isinstance(actor, str) or not actor.startswith(SYSTEM_PREFIX):
        return None
    job = actor[len(SYSTEM_PREFIX):]
    return job if job in REGISTRY else None


def misattributed(rows, job):
    """Rows that do not land on `job`. Two ways to miss, and the registry is per job
    precisely because both are real: an actor that resolves to no registered job lands
    on a person, and an actor that resolves to a DIFFERENT registered job books one
    service's work to another. The second is what a checkout showing one job's already
    corrected actor invites a later session to copy."""
    wrong = {}
    for row in rows:
        actor = row.get("actor")
        if not isinstance(actor, str) or not actor:
            continue
        if registered_job(actor) == job:
            continue
        wrong.setdefault(actor, []).append(row.get("action"))
    return {actor: sorted(actions) for actor, actions in sorted(wrong.items())}


def human_attribution(rows):
    """actor -> sorted list of actions attributed to that person."""
    report = {}
    for row in rows:
        actor = row.get("actor")
        if not isinstance(actor, str) or not actor:
            continue
        if is_automated(actor):
            continue
        report.setdefault(actor, []).append(row.get("action"))
    return {actor: sorted(actions) for actor, actions in sorted(report.items())}


def main(argv):
    if len(argv) != 2:
        print("usage: python3 compliance_reader.py <audit.jsonl>")
        return 2
    print(json.dumps(human_attribution(load(argv[1])), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
