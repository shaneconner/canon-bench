"""Config loading. Unrelated to the audit sink."""
import json
from pathlib import Path

DEFAULTS = {"carrier": "acme-freight", "batch": 25}


def load(workdir):
    path = Path(workdir) / "ops.json"
    values = dict(DEFAULTS)
    if path.exists():
        values.update(json.loads(path.read_text(encoding="utf-8")))
    return values
