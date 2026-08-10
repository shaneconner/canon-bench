#!/usr/bin/env python3
"""Surfacing observability: mine canon-condition transcripts for the funnel.

Per session: what pi-canon delivered (orientation / capsule flush / settle nudge, with
article paths), what the agent did with it (pi_canon map/read/write calls, ordering vs the
first file edit), joined with the cell's trap outcome. The funnel we care about:
surfaced -> read -> heeded, and its complement: never-surfaced -> never-read -> failed.

  surface_audit.py [--tag study] [--runs-root ~/canon-bench-runs]
"""

import argparse
import json
import re
from pathlib import Path

from run_suite import Chain

EDIT_TOOLS = {"write", "edit", "apply_patch", "str_replace"}
CAPSULE_LINE = re.compile(r"^(\S+?)(?: \(updated [^)]*\))?: ", re.M)


def classify(text: str) -> str:
    if "articles govern this project" in text or "No articles yet" in text:
        return "orientation"
    if "Touched but not updated" in text:
        return "settle"
    if "Governing article" in text:
        return "capsule"
    return "other"


def mine_session(session_file: Path) -> dict:
    delivered = {"orientation": 0, "capsule": 0, "settle": 0, "other": 0}
    surfaced_paths, canon_calls, sequence = [], [], []
    for line in session_file.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        message = event.get("message") or {}
        if kind == "message_end" and message.get("customType") == "pi-canon":
            content = message.get("content")
            text = content if isinstance(content, str) else json.dumps(content)
            label = classify(text)
            delivered[label] += 1
            if label == "capsule":
                body = text.split("\n", 1)[1] if "\n" in text else ""
                surfaced_paths += [m.group(1) for m in CAPSULE_LINE.finditer(body)]
        elif kind == "tool_execution_start":
            name = event.get("toolName") or ""
            args = event.get("args") or {}
            if name == "pi_canon":
                action = str(args.get("action", "?"))
                canon_calls.append(f"{action}:{args.get('path', '')}" if action != "map" else "map")
                sequence.append(f"canon-{action}")
            elif name in EDIT_TOOLS:
                sequence.append("edit")
    first_edit = sequence.index("edit") if "edit" in sequence else None
    reads_before_edit = sum(1 for s in sequence[:first_edit] if s == "canon-read") if first_edit is not None else sum(1 for s in sequence if s == "canon-read")
    return {
        "delivered": {k: v for k, v in delivered.items() if v},
        "surfaced": surfaced_paths,
        "canonCalls": canon_calls,
        "readBeforeFirstEdit": reads_before_edit,
        "edits": sequence.count("edit"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="study")
    ap.add_argument("--runs-root", default=str(Path.home() / "canon-bench-runs"))
    ap.add_argument("--condition", default="canon")
    args = ap.parse_args()

    root = Path(args.runs_root)
    for chain_dir in sorted((root / args.tag).glob("0*")):
        chain = Chain(chain_dir.name)
        grades = json.loads((chain_dir / "grades.json").read_text())
        cold = json.loads((root / "cold" / chain_dir.name / "grades.json").read_text())["cold"]
        traps = [c for c, r in cold["outcome"].items() if r != "pass"]
        print(f"\n### {chain_dir.name}  (traps: {', '.join(traps)})")
        for cell_dir in sorted(chain_dir.glob(f"rep*/{args.condition}")):
            cell = f"{cell_dir.parent.name}/{cell_dir.name}"
            outcome = grades[cell]["outcome"]
            trap_ok = all(outcome.get(c) == "pass" for c in traps)
            probe = f"s{len(chain.prompts)}"
            for session in [f"s{i}" for i in range(1, len(chain.prompts) + 1)] + ["recall"]:
                m = mine_session(cell_dir / session / "session.jsonl")
                marker = " <-- PROBE" + ("  [trap PASS]" if trap_ok else "  [trap FAIL]") if session == probe else ""
                print(f"  {cell} {session:<7} delivered={m['delivered']} surfaced={m['surfaced']} "
                      f"canon={m['canonCalls']} readsPreEdit={m['readBeforeFirstEdit']} edits={m['edits']}{marker}")


if __name__ == "__main__":
    main()
