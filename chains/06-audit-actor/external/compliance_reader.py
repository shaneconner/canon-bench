"""Compliance reader. Lives OUTSIDE the checkout; the agent never sees this file.

It builds the quarterly human-attribution report from an audit sink. Every actor
string that is not prefixed `system:` is taken to be a named person, and every
action under that actor is attributed to them personally.

The prefix is the only signal. There is no allowlist of job names, no heuristic
on hyphens or the word "bot", and no way to mark a row automated after the fact,
because the reader is downstream of a dozen services and the sink is append only.
This is the whole reason the house rule exists: a nightly job once ran as
`ops-bot`, which is also a real staff account, and 40,000 automated deletions
were attributed to a person for eleven weeks.
"""
import json
import sys
from pathlib import Path

SYSTEM_PREFIX = "system:"


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
    return isinstance(actor, str) and actor.startswith(SYSTEM_PREFIX) and len(actor) > len(SYSTEM_PREFIX)


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
