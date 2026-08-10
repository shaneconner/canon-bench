"""Event records on disk: one JSON object per line.

Any field whose name ends in ``_at`` is a timestamp: it is written with
``datetime.isoformat`` and read back with ``datetime.fromisoformat``.
"""

import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
EVENTS_PATH = DATA_DIR / "events.jsonl"
ARCHIVE_PATH = DATA_DIR / "archive.jsonl"


def encode_stamp(value):
    return value.isoformat(timespec="seconds")


def decode_stamp(text):
    return datetime.fromisoformat(text)


def _decode(record):
    out = dict(record)
    for field, value in record.items():
        if field.endswith("_at") and isinstance(value, str):
            out[field] = decode_stamp(value)
    return out


def _encode(record):
    out = dict(record)
    for field, value in record.items():
        if isinstance(value, datetime):
            out[field] = encode_stamp(value)
    return out


def read_records(path):
    path = Path(path)
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            records.append(_decode(json.loads(line)))
    return records


def write_records(records, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(_encode(r)) + "\n" for r in records)
    path.write_text(body)


def append_records(records, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as handle:
        for record in records:
            handle.write(json.dumps(_encode(record)) + "\n")


def load_events(path=EVENTS_PATH):
    return read_records(path)


def save_events(events, path=EVENTS_PATH):
    write_records(events, path)


def archive_events(events, path=ARCHIVE_PATH):
    append_records(events, path)
