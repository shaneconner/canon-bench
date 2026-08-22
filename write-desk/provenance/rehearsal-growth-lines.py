#!/usr/bin/env python3
"""Recount the growth lines in the no-model rehearsals, and say what caused each.

Two documents in this programme reported that the perfect-actor preflight fired
the growth line "from digit-length variance alone". The count they reported was
right and the cause was wrong, and neither had a script behind it. This is the
script.

It answers three questions:

  1. How many growth lines does the rehearsal fire, and is it the same number
     every time? The paper calls the floor deterministic, so four rehearsals
     have to agree.
  2. How many of those are the fixture firing the line on purpose? The injected
     bodies carry a sentence that exists to exercise the growth voice, and a
     rehearsal that counts its own test cases as incidental firings overstates
     the floor.
  3. What actually grew in the rest? The claim under repair was a claim about
     cause, so the byte delta is not enough; the script prints the text.

It needs the rehearsal trees and the injection file, which are too large for git
and ship with the Zenodo deposit:

    python3 rehearsal-growth-lines.py /path/to/runs /path/to/fake-injections.json

Reading rule, learned the hard way in this bundle. `drift-sweep.py` searched every
string in every session event and matched the model's own thinking text, which
made it report a conclusion that was false. Here the message is echoed twice per
write, once in `tool_execution_end` and once in `turn_end`, so a naive scan
returns exactly double and looks plausible. This script reads the text blocks a
tool returned and nothing else.

Positive control. The interesting answers here are counts that should match a
figure computed elsewhere, so the script refuses to report them unless its own
recount of each rehearsal agrees with that rehearsal's graded report
(`per_arm.G.total_growth_lines`). Without that check a bug that returned zero
would read as a clean result.
"""

import itertools
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

GROWTH = re.compile(r"Body grew (\d+) -> (\d+) bytes")

# The sentence the rehearsal fixture appends to make the line fire. Writes that
# grow only because of this are test cases, not incidental firings.
PLANTED = "Rehearsal note, deliberately grown"


def growth_lines(capture: Path) -> list[int]:
    """Byte deltas of every growth line a tool actually returned, in this capture."""
    deltas = []
    for log in sorted((capture / "sessions").rglob("*.jsonl")):
        for line in log.read_text().splitlines():
            if "Body grew" not in line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "tool_execution_end":
                continue
            blocks = (event.get("result") or {}).get("content") or []
            for block in blocks:
                for m in GROWTH.finditer(block.get("text") or ""):
                    deltas.append(int(m.group(2)) - int(m.group(1)))
    return deltas


def planted_deltas(injections: Path) -> set[int]:
    """Byte deltas reachable only by appending the fixture's exercise sentence."""
    bodies = defaultdict(set)
    for entry in json.loads(injections.read_text()).values():
        for call in entry.get("calls", []):
            if call.get("action") == "write" and call.get("body"):
                bodies[call["path"]].add(call["body"].rstrip())

    by_delta = defaultdict(set)
    for versions in bodies.values():
        for before, after in itertools.permutations(versions, 2):
            delta = len(after) - len(before)
            if delta > 0:
                by_delta[delta].add(PLANTED in after and PLANTED not in before)
    return {d for d, causes in by_delta.items() if causes == {True}}


def examples(injections: Path, deltas: set[int]) -> dict[int, tuple[str, str, str]]:
    """One before/after pair per byte delta, so the cause can be read rather than inferred."""
    bodies = defaultdict(set)
    for entry in json.loads(injections.read_text()).values():
        for call in entry.get("calls", []):
            if call.get("action") == "write" and call.get("body"):
                bodies[call["path"]].add(call["body"].rstrip())

    out = {}
    for path, versions in bodies.items():
        for before, after in itertools.permutations(versions, 2):
            delta = len(after) - len(before)
            if delta not in deltas or delta in out or PLANTED in after:
                continue
            old = [ln for ln in before.split("\n") if ln not in after.split("\n")]
            new = [ln for ln in after.split("\n") if ln not in before.split("\n")]
            out[delta] = (path, " / ".join(old), " / ".join(new))
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    root, injections = Path(sys.argv[1]), Path(sys.argv[2])

    rehearsals = sorted(p for p in root.rglob("*fake*") if p.is_dir() and (p / "sessions").is_dir())
    if not rehearsals:
        print(f"no rehearsal trees under {root}; nothing is concluded.")
        return 2

    planted = planted_deltas(injections)
    totals, disagreed = [], 0

    print(f"{'rehearsal':34s} {'recount':>8s} {'report':>7s} {'planted':>8s} {'incidental':>11s}")
    for capture in rehearsals:
        deltas = growth_lines(capture)
        report = json.loads((capture / "graded-report.json").read_text())
        stated = ((report.get("per_arm") or {}).get("G") or {}).get("total_growth_lines")
        # Positive control: the recount has to reproduce the graded figure.
        if stated != len(deltas):
            disagreed += 1
        planted_n = sum(1 for d in deltas if d in planted)
        print(f"{capture.name:34s} {len(deltas):>8d} {str(stated):>7s} {planted_n:>8d} "
              f"{len(deltas) - planted_n:>11d}"
              f"{'  MISMATCH' if stated != len(deltas) else ''}")
        totals.append((len(deltas), planted_n, Counter(deltas)))

    if disagreed:
        print(f"\n{disagreed} rehearsal(s) disagree with their own graded report. "
              f"The recount is not trustworthy and nothing is concluded.")
        return 1

    counts = {t for t, _, _ in totals}
    print(f"\nall {len(totals)} rehearsals fired "
          f"{'the same ' + str(counts.pop()) if len(counts) == 1 else 'differing counts, ' + str(sorted(counts))}"
          f" growth lines" + (", so the floor is deterministic" if len(totals) > 1 else ""))

    _, planted_n, dist = totals[0]
    print(f"of those, {planted_n} are the fixture's own exercise sentence and "
          f"{sum(dist.values()) - planted_n} are incidental")
    print("\nwhat grew, by byte delta:")
    shown = examples(injections, {d for d in dist if d not in planted})
    for delta in sorted(dist):
        if delta in planted:
            print(f"  +{delta:<3d} x{dist[delta]:<3d} the fixture's exercise sentence")
            continue
        path, old, new = shown.get(delta, ("?", "?", "?"))
        print(f"  +{delta:<3d} x{dist[delta]:<3d} {path}")
        print(f"           - {old}")
        print(f"           + {new}")
    digits = [d for d in dist if d not in planted and shown.get(d, ("", "", ""))[1].strip().isdigit()]
    print(f"\ndeltas explained by a replacement number carrying more digits: {len(digits)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
