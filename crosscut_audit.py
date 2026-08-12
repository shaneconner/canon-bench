#!/usr/bin/env python3
"""The cross-cutting funnel: where a rule that owns no asset is lost.

Outcome alone cannot tell a doctrine failure from a ranking failure. A cell that fails
06's trap may have failed because the plant filed the rule at an asset address, so the
ranker never saw it, or because the ranker saw it and scored it too low, or because the
probe was told and ignored it. Those want different fixes, and only the first is the one
the sim predicted.

Four links per cell, read from artefacts the run already captures:

    filed_off_path   an article exists at an address governing no file in the seed
    in_residue       that article is what retrieval would rank (follows from the first,
                     recomputed here rather than assumed, because the residue is a
                     property of the tree at probe time, not of the store)
    ranked           PI_CANON_TRACE recorded it surfaced with a score above zero during
                     the probe session
    kept             the grader's rule check passed

    crosscut_audit.py [--tag study] [--runs-root ~/canon-bench-runs] [--chain 06-audit-actor]

Prints one row per cell and a per-arm rollup. The rollup is the point: an arm that fails
at link one has a doctrine problem, an arm that fails at link three has a ranker problem,
and an arm that fails at link four has neither.
"""

import argparse
import json
import tarfile
from pathlib import Path

RULE_CHECK = "sweep_not_human_attributed"


def articles_in(tar_path: Path) -> dict:
    """Address -> capsule, read out of a canon-after snapshot without unpacking it."""
    if not tar_path.exists():
        return {}
    out = {}
    with tarfile.open(tar_path) as tar:
        for member in tar.getmembers():
            name = member.name
            if not member.isfile() or "/articles/" not in name or not name.endswith(".md"):
                continue
            address = name.split("/articles/", 1)[1][:-3]
            handle = tar.extractfile(member)
            text = handle.read().decode("utf-8", "replace") if handle else ""
            capsule = ""
            for line in text.splitlines():
                if line.startswith("capsule:"):
                    capsule = line.split(":", 1)[1].strip().strip('"')
                    break
            out[address] = capsule
    return out


def governs_an_asset(seed: Path, address: str) -> bool:
    """The package's own rule, recomputed here so the audit does not trust a label:
    an address governs an asset when something in the tree normalizes back to it."""
    direct = seed / address
    if direct.exists():
        return True
    parent = direct.parent
    base = direct.name
    if not parent.is_dir():
        return False
    for entry in parent.iterdir():
        if entry.name == base:
            return True
        if entry.name.startswith(base + ".") and "." not in entry.name[len(base) + 1:]:
            return True
    return False


def trace_scores(trace: Path) -> dict:
    """Address -> best score it surfaced with, from this session's trace."""
    best = {}
    if not trace.exists():
        return best
    for line in trace.read_text(errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("kind") != "surfaced":
            continue
        score = row.get("score")
        if isinstance(score, (int, float)):
            path = row.get("path")
            best[path] = max(best.get(path, 0.0), float(score))
    return best


def audit_cell(cell: Path, seed: Path, probe_index: int) -> dict:
    after = cell / f"s{probe_index}" / "canon-before.tar"
    articles = articles_in(after)
    off_path = {a: c for a, c in articles.items() if not governs_an_asset(seed, a)}
    scores = trace_scores(cell / f"s{probe_index}" / "canon-trace.jsonl")
    ranked = {a: s for a, s in scores.items() if a in off_path and s > 0}
    return {
        "articles": len(articles),
        "filed_off_path": sorted(off_path),
        "in_residue": sorted(off_path),
        "ranked": {a: round(s, 4) for a, s in sorted(ranked.items())},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="study")
    ap.add_argument("--chain", default="06-audit-actor")
    ap.add_argument("--runs-root", default=str(Path.home() / "canon-bench-runs"))
    args = ap.parse_args()

    base = Path(args.runs_root) / args.tag / args.chain
    seed = Path(__file__).resolve().parent / "chains" / args.chain / "seed"
    if not base.exists():
        raise SystemExit(f"no run at {base}")

    results_path = base / "results.json"
    results = json.loads(results_path.read_text()) if results_path.exists() else {}

    chain = json.loads((seed.parent / "chain.json").read_text())
    probe_index = len(chain["prompts"])

    rollup = {}
    print(f"{'cell':<28} {'off-path':<10} {'ranked':<10} {'kept':<6} article")
    for rep_dir in sorted(base.glob("rep*")):
        for cell in sorted(p for p in rep_dir.iterdir() if p.is_dir()):
            arm = cell.name
            info = audit_cell(cell, seed, probe_index)
            outcome = (results.get(cell.parent.name, {}).get(arm, {}) or {}).get("outcome", {})
            kept = outcome.get(RULE_CHECK, "?")
            kept_flag = "yes" if kept == "pass" else ("no" if isinstance(kept, str) else "?")
            off = "yes" if info["filed_off_path"] else "no"
            rank = "yes" if info["ranked"] else "no"
            named = ", ".join(info["filed_off_path"][:2]) or "-"
            print(f"{rep_dir.name + '/' + arm:<28} {off:<10} {rank:<10} {kept_flag:<6} {named}")
            bucket = rollup.setdefault(arm, {"cells": 0, "off_path": 0, "ranked": 0, "kept": 0})
            bucket["cells"] += 1
            bucket["off_path"] += bool(info["filed_off_path"])
            bucket["ranked"] += bool(info["ranked"])
            bucket["kept"] += kept_flag == "yes"

    print()
    print(f"{'arm':<12} {'cells':<7} {'filed off-path':<16} {'ranked':<9} {'kept the rule'}")
    for arm, b in sorted(rollup.items()):
        n = b["cells"]
        print(f"{arm:<12} {n:<7} {b['off_path']}/{n:<14} {b['ranked']}/{n:<7} {b['kept']}/{n}")


if __name__ == "__main__":
    main()
