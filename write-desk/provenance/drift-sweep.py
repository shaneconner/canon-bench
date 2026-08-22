#!/usr/bin/env python3
"""Reproduce the drift audit for the first controlled capture.

A concurrent commit edited two contract-pinned package files while that capture
was running, so ordinals 35 through 160 of 160 ran against bytes that differ
from the pins. The audit's claim is that the drift is inert: the changed code
emits schema, refs, and relations output, and none of it reached any model.

This script tests that claim. It reads every `tool_execution_end` event in every
session log, takes the text blocks the tool actually returned, and searches only
those. Model thinking, model prose, and prompt text are not searched, because a
model writing the word "relationships" is not the tool emitting a relations
warning, and an earlier version of this script conflated the two.

It needs the capture tree, which is too large for git and ships with the Zenodo
deposit. Point it at the unpacked run root:

    python3 drift-sweep.py /path/to/20260820-w4-model-001

`drift-sweep.txt` beside this file is the output of the run reported in the
paper.

The last pattern is a positive control and the reason to believe the others.
`Body grew` is output the growth-line arm certainly did produce, and the graded
report says how much of it: `per_arm.G.total_growth_lines`. If the control count
does not match that number, the extractor is not reading what it claims to read
and every zero above it is worthless. The script fails loudly in that case.
"""

import json
import re
import sys
from pathlib import Path

PROBES = {
    "schema: line": (r"(?m)^schema: ", "a schema verdict line in a write response"),
    "refs: line": (r"(?m)^refs: ", "a refs line in a write response"),
    "relations": (r"\brelations\b", "the word relations, whole word, not relationships"),
    "schema.json": (r"schema\.json", "the schema file named in a response"),
}
CONTROL = (r"Body grew \d+ -> \d+ bytes\.", "growth lines, the positive control")


def tool_texts(root: Path):
    """Every text block a tool returned, tagged with its session directory."""
    for session in sorted(p for p in (root / "sessions").iterdir() if p.is_dir()):
        log = session / "session.jsonl"
        if not log.exists():
            continue
        for line in log.open():
            if '"tool_execution_end"' not in line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "tool_execution_end":
                continue
            for block in event.get("result", {}).get("content", []):
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    yield session.name, block["text"]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1])
    if not (root / "sessions").is_dir():
        print(f"no sessions directory under {root}")
        return 2

    texts = list(tool_texts(root))
    sessions = len({name for name, _ in texts})
    print(f"swept {sessions} sessions, {len(texts)} tool result texts, under {root}")
    print()

    found = 0
    for name, (pattern, description) in PROBES.items():
        hits = [s for s, text in texts if re.search(pattern, text)]
        found += len(hits)
        print(f"{name:14s} {len(hits):4d} hits in {len(set(hits)):3d} sessions   {description}")
        for session in sorted(set(hits))[:5]:
            print(f"               {session}")

    pattern, description = CONTROL
    control = [s for s, text in texts if re.search(pattern, text)]
    print(f"{'Body grew':14s} {len(control):4d} hits in {len(set(control)):3d} sessions   {description}")

    expected = None
    report = root / "graded-report.json"
    if report.exists():
        per_arm = json.loads(report.read_text()).get("per_arm", {})
        expected = per_arm.get("G", {}).get("total_growth_lines")

    print()
    if expected is None:
        print("CONTROL: no graded report beside the run, so the control is unchecked.")
    elif len(control) != expected:
        print(f"CONTROL FAILED: {len(control)} growth lines found, report says {expected}.")
        print("The extractor is not reading the tool output it claims to read.")
        print("Every zero above is uninformative. Do not treat the drift as inert.")
        return 1
    else:
        print(f"CONTROL PASSED: {len(control)} growth lines found, matching the report.")

    if found:
        print("VERDICT: changed-code output reached a model. The drift is NOT inert.")
        return 1
    print("VERDICT: no changed-code output reached any model in this capture.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
