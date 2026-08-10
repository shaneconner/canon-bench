#!/usr/bin/env python3
"""Empirical validation of the recall judge before any study run.

For every chain shipping hidden/recall_fixtures.json ({"gold": [...], "zero": [...]}):
every gold answer must judge YES on every fact; every zero-knowledge answer must judge
NO on every plantOnly fact. Prints a table, exits nonzero on any violation. Judge
transcripts are archived beside the fixtures for audit.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_suite import Chain

BENCH = Path(__file__).resolve().parent


def main() -> None:
    chains = sys.argv[1:] or sorted(
        p.parent.parent.name for p in (BENCH / "chains").glob("*/hidden/recall_fixtures.json"))
    failures = 0
    for chain_id in chains:
        chain = Chain(chain_id)
        fixtures = json.loads((chain.dir / "hidden" / "recall_fixtures.json").read_text())
        archive_dir = chain.dir / "hidden" / "judge-validation"
        archive_dir.mkdir(exist_ok=True)
        for kind, answers in (("gold", fixtures["gold"]), ("zero", fixtures["zero"])):
            for index, answer in enumerate(answers, 1):
                verdicts = chain.grade_recall(answer, archive_dir / f"{kind}{index}.json")
                if kind == "gold":
                    bad = [f for f, v in verdicts.items() if not v]
                    label = f"missed {bad}" if bad else "all facts"
                else:
                    bad = [f for f in chain.plant_only if verdicts.get(f)]
                    label = f"LEAKED {bad}" if bad else "plantOnly clean"
                failures += bool(bad)
                print(f"{'ok ' if not bad else 'BAD'} {chain_id} {kind}{index}: {label}")
    sys.exit(1 if failures else 0)


main()
