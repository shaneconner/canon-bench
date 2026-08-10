#!/usr/bin/env python3
"""Aggregate a study tag into CSVs and a summary table.

Discriminating outcome checks are defined empirically, not by hand: for each chain, the
checks that FAILed in its certified cold control (the trap a competent no-memory agent
falls into). Condition scores on those checks are the study's primary outcome metric.
Recall splits into plantOnly (headline: only the plant could furnish it) and secondary.

  analyze.py [--tag study] [--cold-tag cold] [--runs-root ~/canon-bench-runs]
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from run_suite import Chain


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="study")
    ap.add_argument("--cold-tag", default="cold")
    ap.add_argument("--runs-root", default=str(Path.home() / "canon-bench-runs"))
    args = ap.parse_args()

    root = Path(args.runs_root)
    study = root / args.tag
    out_dir = study / "results"
    out_dir.mkdir(exist_ok=True)

    sessions_rows, outcome_rows, recall_rows = [], [], []
    trap_checks = {}
    agg = defaultdict(lambda: defaultdict(list))

    for grades_file in sorted(study.glob("*/grades.json")):
        chain_id = grades_file.parent.name
        chain = Chain(chain_id)
        cold = json.loads((root / args.cold_tag / chain_id / "grades.json").read_text())["cold"]
        traps = [c for c, r in cold["outcome"].items() if r != "pass"]
        trap_checks[chain_id] = traps

        report = json.loads(grades_file.read_text())
        for cell, data in report.items():
            rep, condition = cell.split("/")
            for check, result in data["outcome"].items():
                outcome_rows.append([chain_id, rep, condition, check,
                                     check in traps, result == "pass", result])
            if traps:
                agg[condition]["trap"].append(all(data["outcome"].get(c) == "pass" for c in traps))

            for fact, verdict in data["recall"].items():
                plant_only = fact in chain.plant_only
                recall_rows.append([chain_id, rep, condition, fact, plant_only, verdict])
                agg[condition]["plantOnly" if plant_only else "secondary"].append(verdict)

            for session, u in data["sessions"].items():
                sessions_rows.append([chain_id, rep, condition, session, u["tokens"],
                                      u["output"], u["cost"], u["wallSeconds"], u["toolCalls"]])
                agg[condition]["cost"].append(u["cost"])
                if session == "recall":
                    agg[condition]["recallTokens"].append(u["tokens"])
                    agg[condition]["recallCost"].append(u["cost"])

    for name, header, rows in (
        ("sessions.csv", ["chain", "rep", "condition", "session", "tokens", "output", "cost", "wallSeconds", "toolCalls"], sessions_rows),
        ("outcomes.csv", ["chain", "rep", "condition", "check", "isTrap", "pass", "result"], outcome_rows),
        ("recall.csv", ["chain", "rep", "condition", "fact", "plantOnly", "asserted"], recall_rows),
    ):
        with open(out_dir / name, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

    print(f"trap checks (from cold): {json.dumps(trap_checks, indent=1)}\n")
    print(f"{'condition':<10} {'trap cells':>10} {'plantOnly':>10} {'secondary':>10} "
          f"{'recall tok (med)':>17} {'recall $ (med)':>15} {'chain $ (total)':>16}")
    for condition in agg:
        a = agg[condition]
        med = lambda xs: sorted(xs)[len(xs) // 2] if xs else 0
        frac = lambda xs: f"{sum(xs)}/{len(xs)}"
        print(f"{condition:<10} {frac(a['trap']):>10} {frac(a['plantOnly']):>10} "
              f"{frac(a['secondary']):>10} {med(a['recallTokens']):>17} "
              f"{med(a['recallCost']):>15.4f} {sum(a['cost']):>16.4f}")
    print(f"\nCSVs: {out_dir}")


if __name__ == "__main__":
    main()
