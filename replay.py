#!/usr/bin/env python3
"""Probe-only replay: freeze everything except the article, run the last session.

    python3 replay.py --chain 06-audit-actor --reps 4 --tag cap1

A full chain run lets the plant session decide what gets written, where it gets
filed, and what the checkout looks like, all at once. When the probe then fails,
the run cannot say which of those caused it. This runs only the probe, against a
deterministic checkout and a store written directly from a variant spec, so the
article is the only thing that differs between cells.

Each chain that supports replay ships hidden/replay_spec.py exporting:

    VARIANTS    name -> {address: (capsule, body)}; an empty dict is the floor
    post_plant  (work) -> None, mutating the seed into its post-plant state

Writes grades.json under <runs-root>/<tag>/<chain>/ and checkpoints it after every
cell, so a crash costs one cell rather than the run.
"""

import argparse
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_suite import BENCH, CellFailed, Chain, RUNS_ROOT, WORKER, run_session, usage_of


def load_spec(chain: Chain):
    path = chain.dir / "hidden" / "replay_spec.py"
    if not path.exists():
        raise SystemExit(f"{chain.name} ships no hidden/replay_spec.py, so it cannot be replayed")
    spec = importlib.util.spec_from_file_location(f"{chain.name}_replay_spec", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_store(work: Path, articles: dict) -> None:
    """Write the article store directly, in the package's own on-disk format.

    Writing the store rather than driving the tool is the point: the bytes under test
    are the bytes named in the spec, with no distillation step in between."""
    if not articles:
        return
    stamp = time.strftime("%Y-%m-%d")
    for address, (capsule, body) in articles.items():
        path = work / ".canon" / "articles" / f"{address}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        escaped = capsule.replace("\\", "\\\\").replace('"', '\\"')
        path.write_text(f'---\ncapsule: "{escaped}"\nupdated: {stamp}\n---\n{body}\n',
                        encoding="utf-8")


def run_variant(chain: Chain, spec, base: Path, name: str, condition: str, rep: int) -> dict:
    cell = base / f"rep{rep}" / name
    work = chain.seed_cell(cell)
    spec.post_plant(work)
    write_store(work, spec.VARIANTS[name])

    out = cell / "probe"
    run_session(condition, work, out, chain.prompts[-1])

    graded = cell / "work-graded"
    shutil.copytree(work, graded)
    return {"outcome": chain.grade(graded), "probe": usage_of(out)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--condition", default="canonret",
                    help="held constant across variants; canonret so an off-path "
                         "address is rankable at all and the config never varies")
    ap.add_argument("--variants", default="", help="comma separated; default all")
    ap.add_argument("--tag", default="replay")
    ap.add_argument("--runs-root", default=str(RUNS_ROOT))
    ap.add_argument("--model", default=WORKER["model"])
    ap.add_argument("--provider", default=WORKER["provider"])
    args = ap.parse_args()
    WORKER.update(model=args.model, provider=args.provider)

    chain = Chain(args.chain)
    spec = load_spec(chain)
    names = args.variants.split(",") if args.variants else list(spec.VARIANTS)
    unknown = [n for n in names if n not in spec.VARIANTS]
    if unknown:
        raise SystemExit(f"unknown variants: {unknown}; have {list(spec.VARIANTS)}")

    base = Path(args.runs_root) / args.tag / chain.name
    if base.exists():
        base.rename(base.with_name(f"{chain.name}-{time.strftime('%Y%m%d-%H%M%S')}"))
    base.mkdir(parents=True)

    report = {}
    for rep in range(1, args.reps + 1):
        for name in names:
            key = f"rep{rep}/{name}"
            try:
                report[key] = run_variant(chain, spec, base, name, args.condition, rep)
            except CellFailed as exc:
                report[key] = {"cell": f"FAILED: {exc}"}
                print(f"!! {key} failed: {exc}", flush=True)
            (base / "grades.json").write_text(json.dumps(report, indent=1) + "\n")
            outcome = report[key].get("outcome")
            if outcome:
                print(f"{key}: " + "/".join("P" if v == "pass" else "F" for v in outcome.values()),
                      flush=True)

    rule = json.loads((chain.dir / "chain.json").read_text())["ruleCheck"]
    print("\nvariant                 kept the rule")
    for name in names:
        cells = [report.get(f"rep{r}/{name}", {}).get("outcome") for r in range(1, args.reps + 1)]
        kept = sum(1 for c in cells if c and c.get(rule) == "pass")
        done = sum(1 for c in cells if c)
        print(f"  {name:22} {kept}/{done}")


if __name__ == "__main__":
    main()
