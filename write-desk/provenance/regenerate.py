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

Pass `--write` to overwrite the published CSV. It writes only that file, then runs
every check as usual: `figure-data.js` is always compared and never written, so a
series that has drifted still fails after a --write.

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
    "w4c": ("counter", HERE / "captures/graded-report-w4c.json"),
    "w3": ("first", HERE / "captures/graded-report-w3.json"),
}
CONTROLLED = ("w4", "w4r", "w4c")

failures = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        failures.append(name)


def endpoint_rows() -> list[dict]:
    """One row per lineage per arm per capture, as the CSV carries them."""
    rows = []
    for capture in CONTROLLED:
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
    for capture in CONTROLLED:
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
    capture = {"first": "w4", "second": "w4r", "counter": "w4c"}[model]
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
                        help="overwrite the published CSV, then run every check as usual")
    args = parser.parse_args()

    rows = endpoint_rows()
    fields = ["capture", "model", "arm", "lineage", "depth", "stale",
              "superseded_total", "store_bytes", "pile_bytes", "articles", "journal"]
    order = {"w4": 0, "w4r": 1, "w4c": 2, "w3": 3}
    rows.sort(key=lambda r: (order[r["capture"]], r["lineage"], r["depth"], r["arm"]))

    csv_path = DATA / "per-lineage-endpoints.csv"
    if args.write:
        with csv_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {csv_path} with {len(rows)} rows")
        # Fall through rather than returning. Writing and then not checking is how
        # a regeneration script comes to certify nothing: the CSV comparison below
        # becomes trivial, but the series checks against figure-data.js still run,
        # and those are the ones --write cannot repair, because this script does
        # not write that file.

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
    # Equality of the KEY SETS, not just of the series that happen to be present.
    # Every loop above iterates what the file contains, so deleting a series from
    # figure-data.js removes its check along with it and the gate still reports
    # green over a figure that lost a line.
    check("trajectory series set",
          {(m, arm_of[a]) for m, a, _ in plotted} == set(series),
          f"{len(series)} series: {sorted(series)}")

    want_paired = {f"{m}:{k}" for m in ("first", "second", "counter")
                   for k in ("store", "stale")}
    check("paired series set",
          set(re.findall(r'"(\w+:\w+)":\s*\[\[', source)) == want_paired,
          f"{len(want_paired)} keys: {sorted(want_paired)}")

    for model in ("first", "second", "counter"):
        for metric in ("store", "stale"):
            want = paired(rows, model, metric)
            got = re.search(rf'"{model}:{metric}":\s*(\[\[.*?\]\])', source, re.S)
            if not got:
                check(f"paired {model}:{metric}", False, "not found in figure-data.js")
                continue
            check(f"paired {model}:{metric}",
                  json.loads(re.sub(r"\s+", "", got.group(1))) == want,
                  f"{len(want)} pairs")

    # ---- Figure 1, against the frozen retrieval run rather than against prose.
    # Round seven noted this figure was not regenerated by anything, and round
    # eight then found it carrying one run's rates beside another run's query
    # count. Both are closed here: the plotted values now have to equal the
    # frozen scorer's output, and the store metadata has to equal the frozen
    # corpus it was scored against.
    scores = json.loads((HERE / "retrieval" / "frozen-scores.json").read_text())
    proj_of = {"pifold": "pi-fold", "quorum": "quorum"}
    # The corpus identity. This was a substring-presence test, and it passed while
    # the file carried TWO digests: the corrected one in the block below and the
    # defective export's still sitting in the header. Presence of the right value
    # says nothing about the absence of a wrong one. So: exactly one 64-hex string
    # may appear in the whole file, it has to be the declared field, and it has to
    # equal the published digest.
    digest = (HERE / "retrieval" / "frozen-corpus.sha256").read_text().split()[0]
    hexes = set(re.findall(r"\b[0-9a-f]{64}\b", source))
    check("figure data states exactly one corpus digest", len(hexes) == 1,
          f"{len(hexes)} distinct 64-hex strings: {sorted(hexes)}")
    declared = re.findall(r'frozenCorpusSha256:\s*"([0-9a-f]{64})"', source)
    check("the declared corpus digest equals the published one",
          declared == [digest], f"declared {declared or 'nothing'}, published {digest}")
    check("frozen store set", set(scores) == set(proj_of.values()),
          f"{sorted(proj_of.values())}")
    # splitGain is the one block in figure-data.js that no figure renders: it is
    # the source for a sentence in Figure 1's caption, and it comes from the
    # earlier decomposition run rather than from the frozen one. Nothing checked
    # it, which is how a number from a different run sits in a caption unnoticed.
    ranking = (HERE.parent / "RANKING-RESULTS.md").read_text()
    want_gain = {}
    for store, variant, combined, split, gain in re.findall(
            r"^\|\s*(quorum|pi-fold)\s+(full|terse)\s*\|\s*([\d.]+)\s*\|"
            r"\s*([\d.]+)\s*\|\s*\+([\d.]+) pts\s*\|", ranking, re.M):
        key = f"{store.replace('pi-fold', 'pifold')}:{variant}"
        want_gain[key] = float(gain)
        # The document's own gain column has to equal its own two rate columns.
        check(f"ranking split gain arithmetic {key}",
              abs((float(split) - float(combined)) * 100 - float(gain)) < 0.051,
              f"{combined} to {split} is +{gain}")
    got_gain = {f"{s}:{v}": float(g) for s, v, g in re.findall(
        r'"(\w+):(\w+)":\s*([\d.]+)',
        re.search(r"splitGain:\s*\{(.*?)\}", source, re.S).group(1))}
    check("split gains match the decomposition run", got_gain == want_gain,
          ", ".join(f"{k} {v}" for k, v in sorted(want_gain.items())))

    # ---- the frozen-against-live deltas. The sentence these support replaced a
    # claim that survived several review rounds while being wrong, and it lived
    # only in a hand-maintained Markdown table. Compute it.
    live = json.loads((HERE / "retrieval" / "live-reference.json").read_text())
    lex_deltas, emb_deltas = [], []
    for run_name, run in live["runs"].items():
        # quorum only: pi-fold's query population moved between every run.
        if run["denominators"]["quorum"] != scores["quorum"]["full"]["n"]:
            check(f"{run_name} quorum denominator matches the frozen run", False,
                  f"{run['denominators']['quorum']} against "
                  f"{scores['quorum']['full']['n']}")
            continue
        check(f"{run_name} quorum denominator matches the frozen run", True,
              f"{run['denominators']['quorum']} queries in both")
        for variant in ("full", "terse"):
            cell = run["cells"][f"quorum/{variant}"]
            frozen_cell = scores["quorum"][variant]
            for surface in ("art", "mixed"):
                lex_deltas.append(abs(
                    frozen_cell[f"lex_{surface}_recall_at_10"] - cell[f"lex_{surface}"]) * 100)
                if f"emb_{surface}" in cell:
                    emb_deltas.append(abs(
                        frozen_cell[f"emb_{surface}_recall_at_10"] - cell[f"emb_{surface}"]) * 100)
    worst_lex = round(max(lex_deltas), 1)
    worst_emb = round(max(emb_deltas), 1)
    check("frozen-against-live lexical movement on the mature store",
          worst_lex == 2.0, f"at most {worst_lex} points over {len(lex_deltas)} cells")
    check("frozen-against-live embedding movement on the mature store",
          worst_emb == 1.2, f"at most {worst_emb} points over {len(emb_deltas)} cells")
    # The published live cells must be the ones the frozen results document states.
    # Both tables carry a "| quorum full |" row, so each is parsed by its own shape
    # rather than by a line search, which would validate one run's cell against the
    # other run's row: the very substitution this artifact exists to prevent.
    dec_rows = {f"{s}/{v}": {"lex_art": float(a_), "lex_mixed": float(c)}
                for s, v, c, a_, _x in re.findall(
                    r"^\|\s*(quorum|pi-fold)\s+(full|terse)\s*\|\s*([\d.]+)\s*\|"
                    r"\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", ranking, re.M)}
    rer_rows = {f"{s}/{v}": {"lex_art": float(la), "emb_art": float(ea),
                             "lex_mixed": float(lm), "emb_mixed": float(em)}
                for s, v, la, ea, lm, em in re.findall(
                    r"^\|\s*(quorum|pi-fold)\s+(full|terse)\s*\|\s*\*\*([\d.]+)\*\*\s*\|"
                    r"\s*([\d.]+)\s*\|\s*\*\*([\d.]+)\*\*\s*\|\s*([\d.]+)\s*\|",
                    ranking, re.M)}
    for run_name, parsed in (("decomposition", dec_rows), ("embedding_rerun", rer_rows)):
        check(f"{run_name} cells transcribe RANKING-RESULTS.md",
              live["runs"][run_name]["cells"] == parsed,
              f"{len(parsed)} rows match the frozen document")

    # No hand-written check count anywhere in the published prose. The README
    # carried "all twenty-six of its checks pass" while the script ran thirty-
    # seven, and the paper carried the same number one revision later. A count of
    # a growing thing, written by hand, goes stale by default.
    readme = (HERE.parent / "README.md").read_text()
    stale = re.findall(
        r"(?:twent|thirt|fort|fift)[a-z-]*\s+(?:of\s+its\s+)?checks?|"
        r"all\s+[a-z-]+\s+of\s+its\s+checks", readme, re.I)
    check("the README states no hand-written check count", not stale,
          f"found: {stale}" if stale else "none, so it cannot go stale")

    stores_block = re.search(r'stores:\s*\[(.*?)\]', source, re.S)
    check("figure plots exactly the frozen stores",
          bool(stores_block)
          and set(re.findall(r'key:\s*"(\w+)"', stores_block.group(1))) == set(proj_of),
          f"{sorted(proj_of)}")
    groups = re.findall(r'corpus:\s*"([^"]+)",\s*rows:\s*\[(.*?)\]', source, re.S)
    surface_of = {"records only": "art", "records and journal entries competing": "mixed"}
    seen = 0
    for corpus, block in groups:
        surface = surface_of.get(corpus)
        if surface is None:
            continue
        for store, variant, lex, emb in re.findall(
                r'store:\s*"(\w+)",\s*query:\s*"(\w+)",\s*lexical:\s*([0-9.]+),\s*embed:\s*([0-9.]+)',
                block):
            cell = scores[proj_of[store]][variant]
            want = (cell[f"lex_{surface}_recall_at_10"], cell[f"emb_{surface}_recall_at_10"])
            got = (float(lex), float(emb))
            check(f"retrieval {store}/{variant}/{surface}", got == want,
                  f"lexical {want[0]}, embed {want[1]}")
            seen += 1
    check("retrieval cell count", seen == 8, f"{seen} of 8 plotted cells checked")

    for store, proj in proj_of.items():
        corpus = scores[proj]["corpus"]
        variants = {k: v["n"] for k, v in scores[proj].items() if k != "corpus"}
        # Both query variants score the same sample, so a split between them would
        # mean the two halves of one figure row came from different populations.
        check(f"retrieval {store} variant denominators agree",
              len(set(variants.values())) == 1,
              ", ".join(f"{k}={v}" for k, v in sorted(variants.items())))
        want_n = min(variants.values())
        got = re.search(rf'key:\s*"{store}".*?queries:\s*(\d+)', source, re.S)
        check(f"retrieval {store} query count",
              bool(got) and int(got.group(1)) == want_n,
              f"n={want_n} in the frozen run")
        # The record count is printed on every row label of the figure, and the
        # journal and candidate counts are quoted in the caption. Round nine found
        # all of them taken from a different run than the rates beside them, so
        # each one is checked against the run the rates came from.
        got = re.search(rf'key:\s*"{store}".*?records:\s*(\d+)', source, re.S)
        check(f"retrieval {store} record count",
              bool(got) and int(got.group(1)) == corpus["articles"],
              f"{corpus['articles']} in the frozen run")
        check(f"retrieval {store} candidate arithmetic",
              corpus["articles"] + corpus["journal"] - 1 == corpus["mixed_candidates"],
              f"{corpus['articles']} + {corpus['journal']} - 1 = {corpus['mixed_candidates']}")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("every check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
