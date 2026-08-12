"""Append-only ledger. One JSON object per line in ledger.jsonl.

record() is deliberately schema free: it writes whatever fields the caller hands it
alongside the kind and the subject. What a given kind of entry is expected to carry
is the caller's business, not this module's.
"""
import json
from pathlib import Path

LEDGER = "ledger.jsonl"


def record(workdir, kind, subject, fields=None):
    row = {"kind": kind, "subject": subject}
    if fields:
        row.update(fields)
    with (Path(workdir) / LEDGER).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def read(workdir):
    path = Path(workdir) / LEDGER
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
