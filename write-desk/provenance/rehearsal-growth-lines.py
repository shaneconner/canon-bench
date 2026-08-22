#!/usr/bin/env python3
"""Recount the growth lines in the no-model rehearsals, and say what caused each one.

Two documents in this programme reported that the perfect-actor preflight fired
the growth line "from digit-length variance alone". The count they reported was
right and the cause was invented. Neither had a script behind it. This is the
script.

It answers four questions:

  1. How many growth lines does the rehearsal fire, and is it the same number
     every time? The paper calls the floor deterministic, so four rehearsals
     have to agree.
  2. How many are the fixture firing the line on purpose? The injected bodies
     carry a sentence that exists to exercise the growth voice, and a rehearsal
     that counts its own test cases as incidental firings overstates the floor.
  3. For each remaining firing, which write produced it? Not which write could
     have. An earlier version of this script kept only the byte delta and then
     matched deltas against every permutation of injected bodies, so it could
     say "some transition of this size exists" and not "this event was that
     transition". It now joins each event to the write arguments carried under
     the same toolCallId, and accepts a predecessor only when exactly one body
     written to that path has the reported size.
  4. Was any of them a digit-length change? That was the claim under repair, so
     it is tested directly, by comparing the numeric tokens of the exact before
     and after strings rather than by asking whether a whole line is a number.

It needs the rehearsal trees, which are too large for git and ship with the Zenodo
deposit. It reads nothing else: the write bodies are in the session logs beside
the tool results they produced, so the injected fixture file is not consulted and
cannot disagree with what actually ran.

    python3 rehearsal-growth-lines.py /path/to/runs

Add --rows to print one machine-readable row per firing.

Reading rule, learned the hard way in this bundle. `drift-sweep.py` searched
every string in every session event and matched the model's own thinking text,
which made it report a conclusion that was false. Here the message is echoed
twice per write, once in `tool_execution_end` and once in `turn_end`, so a naive
scan returns exactly double and looks plausible. This script reads the text
blocks a tool returned and nothing else.

Positive control. The interesting answers are counts that should match a figure
computed elsewhere, so the script refuses to report unless its own recount of
each rehearsal agrees with that rehearsal's graded report
(`per_arm.G.total_growth_lines`), and unless every firing resolves to a write it
can name. Without those checks a bug that returned zero would read as a result.
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

GROWTH = re.compile(r"Body grew (\d+) -> (\d+) bytes")
WROTE = re.compile(r"Wrote (\S+?)\.")

# The sentence the rehearsal fixture appends to make the line fire. Writes that
# grow only because of this are test cases, not incidental firings.
PLANTED = "Rehearsal note, deliberately grown"


def events(capture: Path):
    """Every growth line a tool returned, with the exact body it replaced.

    Counting reads `tool_execution_end` only, because the same message is echoed
    in `turn_end` and a scan of both returns exactly double. The write arguments
    live in `turn_end` under the same toolCallId, so the after body is the literal
    string the tool was handed.

    The before body is not guessed either. Each session manifest names its arm,
    its `lineage_key`, and its `session_index`, so the sessions of one lineage can
    be walked in order while carrying the last body written to each path. A
    lineage's store persists across its sessions, which is what makes the
    predecessor of the first write in a session the last write of the one before.
    """
    sessions = []
    for manifest_path in sorted((capture / "sessions").rglob("session-manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        sessions.append((manifest.get("arm"), manifest.get("lineage_key"),
                         manifest.get("session_index") or 0,
                         manifest.get("growth_line_count"), manifest_path.parent))

    fired, declared = [], 0
    for _, group in sorted(_by_lineage(sessions).items()):
        state = {}
        for arm, lineage, index, stated, directory in group:
            declared += stated or 0
            writes, firings = _session(directory)
            for call_id, path, body in writes:
                before = state.get(path)
                if call_id in firings:
                    grew = firings[call_id]
                    fired.append({
                        "session": directory.name, "arm": arm, "lineage": lineage,
                        "index": index, "path": path,
                        "before": before, "after": body,
                        "before_bytes": grew[0], "after_bytes": grew[1],
                        "delta": grew[1] - grew[0],
                    })
                state[path] = body
    return fired, declared


def _by_lineage(sessions):
    grouped = defaultdict(list)
    for row in sessions:
        grouped[(row[0], row[1])].append(row)
    for key in grouped:
        grouped[key].sort(key=lambda r: r[2])
    return grouped


def _session(directory: Path):
    """One session's ordered writes, and the tool calls whose result grew a body."""
    writes, firings = [], {}
    log = directory / "session.jsonl"
    if not log.exists():
        return writes, firings
    for line in log.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "tool_execution_end":
            blocks = (event.get("result") or {}).get("content") or []
            text = "\n".join(b.get("text") or "" for b in blocks)
            grew = GROWTH.search(text)
            if grew and WROTE.search(text):
                firings[event.get("toolCallId")] = (int(grew.group(1)), int(grew.group(2)))
        elif event.get("type") == "turn_end":
            for block in ((event.get("message") or {}).get("content") or []):
                call = block.get("toolCall") or block
                args = call.get("arguments") or {}
                if call.get("name") == "pi_canon" and args.get("body"):
                    writes.append((call.get("id"), args.get("path"), args["body"].rstrip()))
    return writes, firings


def numeric_tokens(text: str) -> list[str]:
    return re.findall(r"\d+", text)


def classify(event: dict) -> dict | None:
    """Label one firing by what actually changed, or None if it has no predecessor."""
    before, after = event.get("before"), event.get("after")
    if before is None or after is None:
        return None
    if len(before) != event["before_bytes"] or len(after) != event["after_bytes"]:
        return None
    planted = PLANTED in after and PLANTED not in before
    before_nums, after_nums = numeric_tokens(before), numeric_tokens(after)
    # A digit-length change means the growth is explained by numbers getting
    # longer: the same count of numeric tokens, and the extra bytes exactly the
    # extra digits. "limit 9" to "limit 100" counts. A new sentence does not.
    digit_growth = (
        event["delta"] > 0
        and len(before_nums) == len(after_nums)
        and sum(len(n) for n in after_nums) - sum(len(n) for n in before_nums) == event["delta"])
    removed = [ln for ln in before.split("\n") if ln not in after.split("\n")]
    added = [ln for ln in after.split("\n") if ln not in before.split("\n")]
    return {**event, "planted": planted, "digit_growth": digit_growth,
            "removed": " / ".join(removed), "added": " / ".join(added)}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    root = Path(args[0])
    want_rows = "--rows" in sys.argv

    # The paper says "all four rehearsals". Globbing and accepting whatever turns
    # up would report determinism from ONE tree, and would also pass silently if a
    # fifth appeared. Name them, and require exactly this set.
    EXPECTED = {
        "20260820-w4-fake-001",
        "20260821-w4r-fake-001",
        "20260821-w4r-fake-002",
        "20260822-w4c-fake-001",
    }
    rehearsals = sorted(p for p in root.rglob("*fake*")
                        if p.is_dir() and (p / "sessions").is_dir())
    found_names = {p.name for p in rehearsals}
    if found_names != EXPECTED:
        print(f"expected exactly {len(EXPECTED)} rehearsal trees under {root}.")
        for missing in sorted(EXPECTED - found_names):
            print(f"  missing: {missing}")
        for extra in sorted(found_names - EXPECTED):
            print(f"  unexpected: {extra}")
        print("nothing is concluded.")
        return 2

    totals, write_totals, problems = [], [], 0

    print(f"{'rehearsal':34s} {'recount':>8s} {'report':>7s} {'resolved':>9s} "
          f"{'planted':>8s} {'incidental':>11s} {'digit':>6s}")
    for capture in rehearsals:
        found, declared = events(capture)
        report = json.loads((capture / "graded-report.json").read_text())
        stated = ((report.get("per_arm") or {}).get("G") or {}).get("total_growth_lines")
        writes = ((report.get("per_arm") or {}).get("G") or {}).get("total_write_count")

        resolved = [r for r in (classify(e) for e in found) if r]

        # The growth line is an arm-G behaviour and the untreated arm must never
        # fire it. Comparing only the TOTAL against per_arm.G.total_growth_lines
        # would pass if one firing moved from G to A, so the arms are separated
        # here and the untreated count has to be zero.
        off_arm = [r for r in resolved if r["arm"] != "G"]
        if off_arm:
            problems += 1
            print(f"{capture.name:34s} {len(off_arm)} firing(s) outside arm G: "
                  f"{sorted({r['arm'] for r in off_arm})}")
            continue

        planted = sum(1 for r in resolved if r["planted"])
        digits = sum(1 for r in resolved if r["digit_growth"] and not r["planted"])
        # Three ways to count the same thing: the graded report, the sum of the
        # per-session manifest counts, and this walk. All three have to agree.
        ok = stated == len(found) == declared and len(resolved) == len(found)
        if not ok:
            problems += 1
        print(f"{capture.name:34s} {len(found):>8d} {str(stated):>7s} "
              f"{len(resolved):>9d} {planted:>8d} {len(resolved) - planted:>11d} "
              f"{digits:>6d}{'  UNRESOLVED' if not ok else ''}")
        totals.append((len(found), planted, digits, resolved))
        write_totals.append(writes)

    if problems:
        print(f"\n{problems} rehearsal(s) either disagree with their own graded report or "
              f"carry a firing this script could not resolve to a write. Nothing is concluded.")
        return 1

    # Determinism is a claim about WHICH writes fire, not just how many. Comparing
    # totals alone would pass four rehearsals that agreed on 38 while disagreeing
    # about how many were the fixture's own exercise sentence, and the breakdown
    # below is then read off the first rehearsal as if it spoke for all of them.
    # So compare the breakdown, and compare the firing sites themselves.
    counts = {t for t, _, _, _ in totals}
    breakdowns = {(t, p_, d) for t, p_, d, _ in totals}
    def signature(resolved):
        return tuple(sorted(
            (r["arm"], r["lineage"], r["index"], r["path"],
             r["planted"], r["digit_growth"])
            for r in resolved))
    signatures = {signature(r) for _, _, _, r in totals}

    print(f"\nall {len(totals)} rehearsals fired "
          + (f"the same {sorted(counts)[0]}" if len(counts) == 1
             else f"differing counts, {sorted(counts)}")
          + " growth lines")
    if len(counts) > 1 or len(breakdowns) > 1 or len(signatures) > 1:
        print("the rehearsals do NOT agree, so the floor is not deterministic:")
        if len(counts) > 1:
            print(f"  totals differ: {sorted(counts)}")
        if len(breakdowns) > 1:
            print("  (total, planted, digit-explained) differ: "
                  f"{sorted(breakdowns)}")
        if len(signatures) > 1:
            print(f"  the same count fires at different writes across rehearsals; "
                  f"{len(signatures)} distinct firing sets")
        return 1
    if len(totals) > 1:
        sites = len(next(iter(signatures)))
        print(f"identical in all {len(totals)}: same count, same split, and the same "
              f"{sites} firing sites, so the floor is deterministic")

    # The denominator the paper prints beside the firing count. It was written by
    # hand into the fact gate; printing it here lets that gate derive it.
    if len(set(write_totals)) != 1:
        print(f"the rehearsals disagree on treated writes: {sorted(set(write_totals))}")
        return 1
    print(f"each rehearsal ran {write_totals[0]} treated writes")

    total, planted, digits, resolved = totals[0]
    # The --rows output reads fields the grouped output does not, so it used to
    # raise a KeyError that only a --rows run would find. Check the field set on
    # every run instead of leaving one output mode unexercised.
    ROW_FIELDS = ("session", "arm", "lineage", "index", "path",
                  "before_bytes", "after_bytes", "delta", "planted", "digit_growth")
    missing = {f for r in resolved for f in ROW_FIELDS if f not in r}
    if missing:
        print(f"\nrow output would fail on missing field(s): {sorted(missing)}")
        return 1
    print(f"of those, {planted} are the fixture's own exercise sentence and "
          f"{total - planted} are incidental")
    print(f"incidental firings explained by a replacement number carrying more digits: {digits}")

    print("\nevery incidental firing, grouped by the transition that produced it:")
    grouped = defaultdict(list)
    for r in resolved:
        if not r["planted"]:
            grouped[(r["delta"], r["path"], r["removed"], r["added"])].append(r)
    for (delta, path, removed, added), rows in sorted(grouped.items()):
        print(f"  +{delta:<3d} x{len(rows):<3d} {path}")
        print(f"           - {removed}")
        print(f"           + {added}")
    planted_rows = [r for r in resolved if r["planted"]]
    if planted_rows:
        d = Counter(r["delta"] for r in planted_rows)
        print(f"  planted: {len(planted_rows)} firings, deltas "
              + ", ".join(f"+{k} x{v}" for k, v in sorted(d.items())))

    if want_rows:
        print("\nsession\tarm\tlineage\tsession_index\tpath\tbefore\tafter\tdelta"
              "\tplanted\tdigit_growth")
        for r in resolved:
            print(f"{r['session']}\t{r['arm']}\t{r['lineage']}\t{r['index']}\t{r['path']}\t"
                  f"{r['before_bytes']}\t{r['after_bytes']}\t{r['delta']}\t{r['planted']}\t"
                  f"{r['digit_growth']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
