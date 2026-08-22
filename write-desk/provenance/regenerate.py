#!/usr/bin/env python3
"""Rebuild the published data files from the capture reports and check them.

Run it from this directory with no arguments:

    python3 regenerate.py

It reads only what ships in this bundle: the four graded reports under
`captures/` and the two fixture generators under `fixtures/`. It rebuilds
`../data/per-lineage-endpoints.csv` and the two data blocks of
`../data/figure-data.js` from those, compares the result against the published
copies byte for byte where the format allows and value for value where it does
not, and prints one line per check. Exit status is 0 only if every check passes.

Pass `--write` to overwrite the published copies instead of comparing.

What this does and does not establish. It establishes that the published CSV and
the plotted series are derived from the graded reports and the fixture
generators, and that nobody hand-edited a number between them. It does not
establish that the graded reports describe the runs, which is what the capture
manifests, the contracts, and the per-session transcripts are for. Those are
listed in MANIFEST.sha256 and the large ones ship with the Zenodo deposit.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
sys.path.insert(0, str(HERE / "fixtures"))

import w3_lineage  # noqa: E402
import w4_lineage  # noqa: E402

CAPTURES = {
    "w4": ("first", HERE / "captures/graded-report-w4.json"),
    "w4r": ("second", HERE / "captures/graded-report-w4r.json"),
    "w3": ("first", HERE / "captures/graded-report-w3.json"),
}

failures = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        failures.append(name)


def endpoint_rows() -> list[dict]:
    """One row per lineage per arm per capture, as the CSV carries them."""
    rows = []
    for capture in ("w4", "w4r"):
        model, path = CAPTURES[capture]
        grades = json.loads(path.read_text())["store_grades"]
        for key in sorted(grades):
            arm, lineage = key.split(":", 1)
            g = grades[key]
            last = g["trajectory"][-1]
            rows.append({
                "capture": capture, "model": model, "arm": arm, "lineage": lineage,
                "depth": 8, "stale": g["stale_final"],
                "superseded_total": g["superseded_total"],
                "store_bytes": last["store_bytes"],
                "pile_bytes": last["transcript_pile_bytes"],
                "articles": last["article_count"], "journal": last["journal_count"],
            })

    # The accumulation study has one store per lineage per depth and no arms, and
    # its availability denominator is a property of the fixture rather than the
    # run, so it comes from the generator the way the paper says it does.
    available = {}
    for entry in w3_lineage.build_all():
        base = entry["lineage_key"].rsplit("_k", 1)[0]
        state = w3_lineage.state_at(entry, entry["k"])["superseded_as_of"]
        available[(base, entry["k"])] = sum(len(v) for v in state.values())

    grades = json.loads(CAPTURES["w3"][1].read_text())["store_grades"]
    for key in sorted(grades):
        base, depth = key.rsplit("_k", 1)
        depth = int(depth)
        g = grades[key]
        last = g["trajectory"][-1]
        rows.append({
            "capture": "w3", "model": "first", "arm": "store", "lineage": base,
            "depth": depth, "stale": g["stale_final"],
            "superseded_total": available[(base, depth)],
            "store_bytes": last["store_bytes"],
            "pile_bytes": last["transcript_pile_bytes"],
            "articles": last["article_count"], "journal": last["journal_count"],
        })
    return rows


def trajectory_series() -> dict:
    """The four cumulative staleness series plotted against session depth."""
    out = {}
    for capture in ("w4", "w4r"):
        model, path = CAPTURES[capture]
        grades = json.loads(path.read_text())["store_grades"]
        for arm in ("A", "G"):
            totals = [0] * 8
            for key, g in grades.items():
                if not key.startswith(arm + ":"):
                    continue
                for point in g["trajectory"]:
                    totals[point["session"] - 1] += point["stale_in_articles"]
            out[(model, arm)] = totals
    return out


def availability_schedule() -> list[int]:
    """How many superseded values the eight K=8 lineages expose by each session."""
    entries = w4_lineage.build_all()
    schedule = []
    for session in range(1, 9):
        total = 0
        for entry in entries:
            state = w3_lineage.state_at(entry, session)["superseded_as_of"]
            total += sum(len(v) for v in state.values())
        schedule.append(total)
    return schedule


def paired(rows: list[dict], model: str, metric: str) -> list[list[int]]:
    key = "store_bytes" if metric == "store" else "stale"
    capture = "w4" if model == "first" else "w4r"
    by_lineage = {}
    for r in rows:
        if r["capture"] != capture:
            continue
        by_lineage.setdefault(r["lineage"], {})[r["arm"]] = int(r[key])
    return [[by_lineage[k]["A"], by_lineage[k]["G"]] for k in sorted(by_lineage)]


def js_array(source: str, name: str) -> list:
    """Pull one array literal out of figure-data.js without executing it."""
    match = re.search(rf"\b{re.escape(name)}\s*:\s*(\[[^\]]*\])", source)
    if not match:
        raise SystemExit(f"could not find {name} in figure-data.js")
    return json.loads(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true",
                        help="overwrite the published CSV instead of comparing")
    args = parser.parse_args()

    rows = endpoint_rows()
    fields = ["capture", "model", "arm", "lineage", "depth", "stale",
              "superseded_total", "store_bytes", "pile_bytes", "articles", "journal"]
    order = {"w4": 0, "w4r": 1, "w3": 2}
    rows.sort(key=lambda r: (order[r["capture"]], r["lineage"], r["depth"], r["arm"]))

    csv_path = DATA / "per-lineage-endpoints.csv"
    if args.write:
        with csv_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {csv_path} with {len(rows)} rows")
        return 0

    published = list(csv.DictReader(csv_path.open()))
    check("CSV row count", len(published) == len(rows),
          f"{len(published)} published, {len(rows)} regenerated")

    def norm(r):
        return tuple(str(r[f]) for f in fields)

    pub = sorted(norm(r) for r in published)
    reg = sorted(norm(r) for r in rows)
    if pub == reg:
        check("CSV values", True, f"all {len(reg)} rows match")
    else:
        differing = [a for a, b in zip(pub, reg) if a != b][:3]
        check("CSV values", False, f"first differences: {differing}")

    source = (DATA / "figure-data.js").read_text()

    schedule = availability_schedule()
    check("availability schedule", js_array(source, "available") == schedule,
          str(schedule))

    series = trajectory_series()
    plotted = re.findall(
        r'\{\s*model:\s*"(\w+)",\s*arm:\s*"(\w+)",\s*values:\s*(\[[^\]]*\])',
        source)
    arm_of = {"control": "A", "line": "G"}
    for model, arm, values in plotted:
        want = series[(model, arm_of[arm])]
        check(f"trajectory {model}/{arm}", json.loads(values) == want, str(want))

    for model in ("first", "second"):
        for metric in ("store", "stale"):
            want = paired(rows, model, metric)
            got = re.search(rf'"{model}:{metric}":\s*(\[\[.*?\]\])', source, re.S)
            if not got:
                check(f"paired {model}:{metric}", False, "not found in figure-data.js")
                continue
            check(f"paired {model}:{metric}",
                  json.loads(re.sub(r"\s+", "", got.group(1))) == want,
                  f"{len(want)} pairs")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("every check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
