#!/usr/bin/env python3
"""Recount the sessions in every capture, from the capture trees.

The paper prints eleven captures with a run count and a protocol-valid count
each, and says the run counts were read off each capture's own directory. An
earlier version said that and was wrong by 232 sessions, because one capture's
count was never actually read off anything. So the recount is a script now.

It needs the capture trees, which are too large for git and ship with the Zenodo
deposit. Point it at the directory holding the unpacked runs:

    python3 verify-session-counts.py /path/to/runs

Each capture is counted two ways where the layout allows: by listing the session
or assignment directories, and by reading the count out of the capture's own
report. Both are printed. They should agree, and the script says so or does not.

Ten of the eleven captures list one directory per session. The other, W1e, uses
a checkpoint-pair layout with no such directory, which is exactly the one the
earlier count got wrong; for that capture the report's own
`unique_transcript_session_id_count` is the authority and the script says so
rather than quietly substituting it.

Three totals are printed and they are not the same claim. The paper total sums the
figures the paper prints. The verified total sums only what this script actually
read out of a report. The declared total is the remainder, the figures the paper
supplied because no field carries them, and W1h's protocol-valid count is the only
one of those. Counting a supplied figure inside a total labelled "recounted" would
be the object under test confirming itself, which an earlier version of this script
did.
"""

import json
import sys
from pathlib import Path

# capture directory, session-listing subdirectory or None, report file,
# the key holding the run count, the key holding the protocol-valid count
CAPTURES = [
    ("20260816-w1e-state-only-model-001", None, "grade-blind-report.json",
     "unique_transcript_session_id_count",
     ("writer_terminal_protocol_valid_count", "probe_protocol_valid_count")),
    ("20260817-w1f-model-001", "assignments", "grade-blind-report.json",
     "assigned_session_count", "protocol_valid_session_count"),
    ("20260817-w1g-model-001", "assignments", "grade-blind-report.json",
     "assigned_session_count", "protocol_valid_session_count"),
    ("20260817-w1h-model-001", "assignments", "grade-blind-report.json",
     "assigned_session_count", None),
    ("20260819-w1i-lean-model-001", "assignments", "protocol-corrected-report.json",
     "session_count", "corrected_protocol_valid_count"),
    ("20260820-w1j-model-001", "assignments", "grade-blind-report.json",
     "assigned_session_count", "protocol_valid_session_count"),
    ("20260820-w2-model-002", "sessions", "graded-report.json",
     None, "protocol_valid_sessions"),
    ("20260820-w3-model-001", "sessions", "graded-report.json",
     None, "protocol_valid_sessions"),
    ("20260820-w4-model-001", "sessions", "graded-report.json",
     None, "protocol_valid_sessions"),
    ("20260821-w4r-model-003", "sessions", "graded-report.json",
     None, "protocol_valid_sessions"),
    ("20260822-w4c-model-001", "sessions", "graded-report.json",
     None, "protocol_valid_sessions"),
]

# W1e and W1h were each scored at zero protocol-valid sessions by a classifier
# that required a field Pi omits from its summarised tool results. Both are
# corrected, and both corrections are frozen beside the original grading.
NOTES = {
    "20260816-w1e-state-only-model-001":
        "no per-session directory; report is the authority. Valid 320 of 320: "
        "writer_terminal_protocol_valid_count 160 plus probe_protocol_valid_count 160.",
    "20260817-w1h-model-001":
        "valid 512 of 512 under analyses/20260817-w1h-model-001-protocol-corrected.json; "
        "the grade-blind report says 0, which is the classifier bug, not the result.",
    "20260819-w1i-lean-model-001":
        "valid 320 of 320 under protocol-corrected-report.json; graded-report.json "
        "says 0, which is the same classifier bug.",
}

PAPER = {
    "20260816-w1e-state-only-model-001": (320, 320),
    "20260817-w1f-model-001": (512, 511),
    "20260817-w1g-model-001": (640, 636),
    "20260817-w1h-model-001": (512, 512),
    "20260819-w1i-lean-model-001": (320, 320),
    "20260820-w1j-model-001": (576, 572),
    "20260820-w2-model-002": (128, 127),
    "20260820-w3-model-001": (248, 247),
    "20260820-w4-model-001": (160, 160),
    "20260821-w4r-model-003": (160, 160),
    "20260822-w4c-model-001": (160, 160),
}


def find(root: Path, name: str) -> Path | None:
    if (root / name).is_dir():
        return root / name
    matches = [p for p in root.rglob(name) if p.is_dir()]
    return matches[0] if len(matches) == 1 else None


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1])

    print(f"{'capture':38s} {'listed':>7s} {'report':>7s} {'valid':>6s}  paper")
    run_total = valid_total = 0
    verified_run = verified_valid = verified_captures = 0
    declared_valid = []
    missing = mismatched = 0

    for name, listing, report_name, run_key, valid_key in CAPTURES:
        capture = find(root, name)
        if capture is None:
            print(f"{name:38s} {'-':>7s} {'-':>7s} {'-':>6s}  not found")
            missing += 1
            continue

        listed = len(list((capture / listing).iterdir())) if listing and \
            (capture / listing).is_dir() else None

        report_path = capture / report_name
        if not report_path.exists():
            candidates = list(capture.rglob(report_name))
            report_path = candidates[0] if candidates else None
        report = json.loads(report_path.read_text()) if report_path else {}

        run = report.get(run_key) if run_key else listed
        # W1e splits its protocol-valid count across a writer key and a probe key,
        # so the tuple form sums them rather than substituting the paper's figure.
        if isinstance(valid_key, tuple):
            parts = [report.get(k) for k in valid_key]
            valid = sum(parts) if all(p is not None for p in parts) else None
        else:
            valid = report.get(valid_key) if valid_key else None
        # W1h's corrected analysis records the decision that the classifier bug
        # caused its zero, but carries no protocol-valid field to read. That
        # figure is the paper's, not a recount, and the totals below say so.
        substituted = valid is None
        if substituted and name in PAPER:
            valid = PAPER[name][1]

        paper_run, paper_valid = PAPER[name]
        ok = (run == paper_run) and (valid == paper_valid) and \
             (listed is None or listed == paper_run)
        if not ok:
            mismatched += 1
        else:
            verified_run += run
            verified_captures += 1
            if substituted:
                declared_valid.append((name, valid))
            else:
                verified_valid += valid
        run_total += paper_run
        valid_total += paper_valid

        print(f"{name:38s} {str(listed):>7s} {str(run):>7s} {str(valid):>6s}  "
              f"{paper_run}/{paper_valid} {'ok' if ok else 'MISMATCH'}")
        if name in NOTES:
            print(f"{'':38s} {NOTES[name]}")

    print()
    declared_total = sum(v for _, v in declared_valid)
    print(f"as printed in the paper:  {run_total} run, {valid_total} protocol-valid "
          f"over {len(CAPTURES)} captures")
    print(f"verified from the trees:  {verified_run} run, {verified_valid} protocol-valid "
          f"over {verified_captures} captures, protocol-valid read for "
          f"{verified_captures - len(declared_valid)}")
    if declared_valid:
        print(f"declared, not verified:   {declared_total} protocol-valid from "
              + ", ".join(name for name, _ in declared_valid)
              + ". No field in those reports carries the figure, so this script takes it from"
                " the paper and does not count it as checked.")
    if verified_captures != len(CAPTURES):
        print("some capture was not found; the verified total is the only one that was checked.")
    if missing:
        print(f"{missing} capture(s) not found under {root}; nothing is concluded about those.")
    if mismatched:
        print(f"{mismatched} capture(s) disagree with the paper.")
        return 1
    if missing:
        return 2
    if declared_valid:
        print(f"every capture found agrees with the paper, with {len(declared_valid)} "
              f"protocol-valid figure(s) declared rather than verified, named above.")
    else:
        print("every capture found agrees with the paper, and every figure was read off a report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
