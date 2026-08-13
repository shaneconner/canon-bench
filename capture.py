#!/usr/bin/env python3
"""Plant-only capture audit: does the article keep the values the journal recorded?

    python3 capture.py --chain 06-audit-actor --reps 8 --tag cap-base

cap1 established that an article stating a rule's shape without its values is worth
exactly what no article is worth. The loss happens at distillation: the journal keeps
the original, the article summarises, and the values go. This measures that step
directly and deterministically.

It runs only the plant session, then greps the resulting store for literal strings the
chain declares under `captureValues`. No probe, no judge, no grader. The number that
matters is the GAP: values the journal kept minus values the article kept. That gap is
what a doctrine change has to close, and it is measurable in one session per cell.

This exists because replay.py cannot test a write-side intervention. Replay writes the
store directly, which is exactly the step a capture fix changes, so it would measure a
fix by bypassing it. The two instruments compose: capture.py says whether the article
retains the values, replay.py says whether an article that retains them changes the
outcome. cap1 already answered the second.
"""

import argparse
import json
import shutil
import sys
import tarfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_suite import CellFailed, Chain, RUNS_ROOT, WORKER, run_session


def store_text(tar_path: Path) -> tuple[str, str]:
    """(articles text, journal text) from a canon snapshot, without unpacking it."""
    articles, journal = [], []
    if not tar_path.exists():
        return "", ""
    with tarfile.open(tar_path) as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith(".md"):
                continue
            handle = tar.extractfile(member)
            if not handle:
                continue
            text = handle.read().decode("utf-8", "replace")
            if "/articles/" in member.name:
                articles.append(text)
            elif "/journal/" in member.name:
                journal.append(text)
    return "\n".join(articles), "\n".join(journal)


def retained(text: str, values: list[str]) -> list[str]:
    lowered = text.lower()
    return [v for v in values if v.lower() in lowered]


def run_cell(chain: Chain, values: list[str], base: Path, condition: str, rep: int,
             validity: str | None = None) -> dict:
    cell = base / f"rep{rep}" / condition
    work = chain.seed_cell(cell)
    out = cell / "plant"
    run_session(condition, work, out, chain.prompts[0])

    # The plant's own task, graded on a snapshot. Only the check the chain declares under
    # cellValidity is meaningful here: every other check asks about the probe's work, and
    # the probe has not run. Cheap because the plant session is the only one paid for, and
    # it is the whole measurement when the question is what the memory tool costs the
    # session that writes rather than what it buys the one that reads.
    plant = "n/a"
    if validity:
        graded = cell / "plant-graded"
        shutil.copytree(work, graded)
        plant = chain.grade(graded).get(validity, "FAIL: check not reported")

    articles, journal = store_text(out / "canon-after.tar")
    in_article = retained(articles, values)
    in_journal = retained(journal, values)
    # A value the journal never held is a recording failure, not a distillation one, and
    # the two want different fixes. Kept separate rather than summed.
    return {
        "plantTask": plant,
        "article": in_article,
        "journal": in_journal,
        "articleKept": f"{len(in_article)}/{len(values)}",
        "journalKept": f"{len(in_journal)}/{len(values)}",
        "droppedInDistillation": sorted(set(in_journal) - set(in_article)),
        "neverRecorded": sorted(set(values) - set(in_journal) - set(in_article)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reps", type=int, default=8)
    ap.add_argument("--conditions", default="canon")
    ap.add_argument("--tag", default="capture")
    ap.add_argument("--runs-root", default=str(RUNS_ROOT))
    ap.add_argument("--model", default=WORKER["model"])
    ap.add_argument("--provider", default=WORKER["provider"])
    args = ap.parse_args()
    WORKER.update(model=args.model, provider=args.provider)

    chain = Chain(args.chain)
    manifest = json.loads((chain.dir / "chain.json").read_text())
    values = manifest.get("captureValues")
    if not values:
        raise SystemExit(f"{chain.name} declares no captureValues, so capture cannot be scored")
    validity = manifest.get("cellValidity")

    base = Path(args.runs_root) / args.tag / chain.name
    if base.exists():
        base.rename(base.with_name(f"{chain.name}-{time.strftime('%Y%m%d-%H%M%S')}"))
    base.mkdir(parents=True)

    report = {}
    for rep in range(1, args.reps + 1):
        for condition in args.conditions.split(","):
            key = f"rep{rep}/{condition}"
            try:
                report[key] = run_cell(chain, values, base, condition, rep, validity)
                r = report[key]
                print(f"{key}: article {r['articleKept']}  journal {r['journalKept']}"
                      f"  plant {'pass' if r['plantTask'] == 'pass' else 'FAIL'}"
                      f"  dropped {r['droppedInDistillation']}", flush=True)
            except CellFailed as exc:
                report[key] = {"cell": f"FAILED: {exc}"}
                print(f"!! {key} failed: {exc}", flush=True)
            (base / "capture.json").write_text(json.dumps(report, indent=1) + "\n")

    print(f"\nvalues under audit: {values}\n")
    for condition in args.conditions.split(","):
        cells = [report.get(f"rep{r}/{condition}") for r in range(1, args.reps + 1)]
        cells = [c for c in cells if c and "article" in c]
        if not cells:
            continue
        n = len(cells) * len(values)
        art = sum(len(c["article"]) for c in cells)
        jou = sum(len(c["journal"]) for c in cells)
        done = sum(1 for c in cells if c.get("plantTask") == "pass")
        print(f"  {condition:10} journal kept {jou}/{n}   article kept {art}/{n}   "
              f"lost at distillation {jou - art}/{n}   plant task {done}/{len(cells)}")


if __name__ == "__main__":
    main()
