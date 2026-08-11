#!/usr/bin/env python3
"""Recompute every quantitative claim in the pi-canon paper from this repository.

    python3 tests/verify_claims.py

Every check names the paper section and the claimed value, recomputes it from
the files in results/ and chains/, and reports PASS or FAIL with its source
field. Standard library only; nothing outside this repository is read.

The paper is the Zenodo record; this is the harness that produced its numbers.
If a check fails, the paper and these artifacts disagree, and the artifacts win.
"""

import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARMS = ["canon", "canondoc", "agentsmd", "bare"]

results = []


def check(section, claim, expected, actual, source):
    ok = expected == actual
    results.append((ok, section, claim, expected, actual, source))
    return ok


def load_csv(tag, name):
    with open(ROOT / "results" / tag / name, newline="") as fh:
        return list(csv.DictReader(fh))


def cold_grades(tag, chain):
    """The live cold grades for a chain (the file without a timestamp suffix)."""
    path = ROOT / "results" / tag / f"{chain}-grades.json"
    return json.loads(path.read_text())["cold"]


def chain_ids():
    return sorted(p.name for p in (ROOT / "chains").iterdir() if p.is_dir())


def declared_plant_only(chain):
    path = ROOT / "chains" / chain / "chain.json"
    return set(json.loads(path.read_text()).get("plantOnly", []))


# ---------------------------------------------------------------- eligibility

def trap_checks(cold_tag):
    """Section 4.2: trap checks are DERIVED, the cold checks that failed."""
    out = {}
    for chain in chain_ids():
        cold = cold_grades(cold_tag, chain)
        out[chain] = [c for c, r in cold["outcome"].items() if r != "pass"]
    return out


traps_luna = trap_checks("cold")

check("4.2", "chain 05 contributes no trap endpoint",
      True, traps_luna["05-import-lazy"] == [],
      "results/cold/05-import-lazy-grades.json : cold.outcome (all pass)")

check("4.2", "chains with at least one trap endpoint",
      4, sum(1 for v in traps_luna.values() if v),
      "results/cold/*-grades.json : cold.outcome")

# The declare-then-certify asymmetry disclosed in Section 4.2.
declared = {c: declared_plant_only(c) for c in chain_ids()}
cold_unrecovered = {}
for chain in chain_ids():
    facts = cold_grades("cold", chain)["recallFacts"]
    cold_unrecovered[chain] = {f for f, recovered in facts.items() if not recovered}

total_facts = sum(len(cold_grades("cold", c)["recallFacts"]) for c in chain_ids())
total_declared = sum(len(v) for v in declared.values())
total_unrec = sum(len(v) for v in cold_unrecovered.values())
undeclared_but_cold_unrecovered = sum(
    len(cold_unrecovered[c] - declared[c]) for c in chain_ids())
demoted_luna = sum(len(declared[c] - cold_unrecovered[c]) for c in chain_ids())

check("4.2", "recall facts across the chains", 20, total_facts,
      "results/cold/*-grades.json : cold.recallFacts (keys)")
check("4.2", "facts declared plant-only", 9, total_declared,
      "chains/*/chain.json : plantOnly")
check("4.2", "declared facts demoted by the headline cold run", 0, demoted_luna,
      "chain.json plantOnly minus cold.recallFacts==false")
check("4.2", "cold-unrecovered facts that stay secondary (undeclared)",
      5, undeclared_but_cold_unrecovered,
      "cold.recallFacts==false minus chain.json plantOnly")
check("4.2", "facts the stated-empirical rule would have selected",
      14, total_unrec,
      "results/cold/*-grades.json : cold.recallFacts==false")
check("4.2", "secondary facts", 11, total_facts - total_declared,
      "20 facts minus 9 declared")

# Chain 05's three cold executions (Section 4.2, Section 8).
c05 = sorted((ROOT / "results" / "cold").glob("05-import-lazy*-grades.json"))
c05_probe = [json.loads(p.read_text())["cold"]["outcome"] for p in c05]
c05_recall = [json.loads(p.read_text())["cold"]["recallFacts"] for p in c05]
check("4.2", "chain 05 cold executions", 3, len(c05),
      "results/cold/05-import-lazy*-grades.json")
check("4.2", "chain 05 probe-cold executions that failed at least one check",
      1, sum(1 for o in c05_probe if any(r != "pass" for r in o.values())),
      "cold.outcome across the three chain-05 files")
check("4.2", "chain 05 recall-cold verdicts identical across executions",
      True, all(r == c05_recall[0] for r in c05_recall),
      "cold.recallFacts across the three chain-05 files")


# ------------------------------------------------------------------- headline

def trap_cells(tag, cold_tag="cold"):
    """A cell passes if every trap check in its chain passes. Chains with no
    trap endpoint contribute no cells, which is why 100 cells yield 80 probes."""
    traps = trap_checks(cold_tag)
    rows = load_csv(tag, "outcomes.csv")
    cells = defaultdict(dict)
    for r in rows:
        cells[(r["chain"], r["rep"], r["condition"])][r["check"]] = r["pass"]
    tally = defaultdict(lambda: [0, 0])
    for (chain, _rep, cond), checks in cells.items():
        if not traps[chain]:
            continue
        tally[cond][1] += 1
        if all(checks.get(c) == "True" for c in traps[chain]):
            tally[cond][0] += 1
    return tally


headline_traps = trap_cells("headline")
check("4.6/5.1", "trap-eligible probe outcomes", 80,
      sum(v[1] for v in headline_traps.values()),
      "results/headline/outcomes.csv joined to cold-derived trap checks")

for arm, expected in [("canon", 19), ("canondoc", 16), ("agentsmd", 18), ("bare", 8)]:
    check("5.1", f"{arm} trap cells (of 20)", expected, headline_traps[arm][0],
          "results/headline/outcomes.csv : passed, over cold-derived traps")


def recall_counts(tag, plant_only_by_chain=None):
    rows = load_csv(tag, "recall.csv")
    tally = defaultdict(lambda: {"po": [0, 0], "sec": [0, 0]})
    for r in rows:
        if plant_only_by_chain is not None:
            is_po = r["fact"] in plant_only_by_chain.get(r["chain"], set())
        else:
            is_po = r["plantOnly"] == "True"
        key = "po" if is_po else "sec"
        tally[r["condition"]][key][1] += 1
        if r["asserted"] == "True":
            tally[r["condition"]][key][0] += 1
    return tally


hr = recall_counts("headline")
for arm, po, sec in [("canon", 41, 54), ("canondoc", 40, 53),
                     ("agentsmd", 42, 52), ("bare", 40, 49)]:
    check("5.2", f"{arm} plant-only recall (of 45)", po, hr[arm]["po"][0],
          "results/headline/recall.csv : asserted where plantOnly")
    check("5.2", f"{arm} secondary recall (of 55)", sec, hr[arm]["sec"][0],
          "results/headline/recall.csv : asserted where not plantOnly")

# The judge-sensitive item carrying most of the spread (Section 5.2).
rows = load_csv("headline", "recall.csv")
FLAGGED = "violation_dropped_silently"
misses = [r for r in rows if r["plantOnly"] == "True" and r["asserted"] != "True"]
check("5.2", "total plant-only misses across arms", 17, len(misses),
      "results/headline/recall.csv : plantOnly and not asserted")
check("5.2", f"misses carried by {FLAGGED}", 9,
      sum(1 for r in misses if r["fact"] == FLAGGED),
      "results/headline/recall.csv : fact column")
for arm, n in [("canon", 1), ("canondoc", 3), ("bare", 2), ("agentsmd", 3)]:
    check("5.2", f"{FLAGGED} misses in {arm}", n,
          sum(1 for r in misses if r["fact"] == FLAGGED and r["condition"] == arm),
          "results/headline/recall.csv")

loo = defaultdict(lambda: [0, 0])
for r in rows:
    if r["plantOnly"] == "True" and r["fact"] != FLAGGED:
        loo[r["condition"]][1] += 1
        if r["asserted"] == "True":
            loo[r["condition"]][0] += 1
for arm, n in [("agentsmd", 40), ("canondoc", 38), ("canon", 37), ("bare", 37)]:
    check("5.2", f"{arm} plant-only excluding the flagged item (of 40)", n,
          loo[arm][0], "results/headline/recall.csv minus the flagged fact")


def ledger_sessions(tag):
    """Per-session ledger records at full precision.

    Section 4.6 of the paper defines a session's dollar cost as the figure Pi's
    ledger reports, so dollar claims are computed from results/<tag>/ledger.csv.
    sessions.csv carries a five-decimal export of the same values, which is why
    summing that column can differ from a printed figure in the fourth decimal.
    """
    out = []
    for r in load_csv(tag, "ledger.csv"):
        out.append({"chain": r["chain"], "rep": r["rep"],
                    "condition": r["condition"], "session": r["session"],
                    "cost": float(r["cost"])})
    return out


def token_stats(tag):
    rows = load_csv(tag, "sessions.csv")
    ledger = ledger_sessions(tag)
    med_tok, med_cost, total = {}, {}, {}
    for cond in {r["condition"] for r in rows}:
        rec = [r for r in rows if r["condition"] == cond and r["session"] == "recall"]
        med_tok[cond] = statistics.median(int(r["tokens"]) for r in rec)
        lrec = [r["cost"] for r in ledger
                if r["condition"] == cond and r["session"] == "recall"]
        med_cost[cond] = statistics.median(lrec)
        total[cond] = sum(r["cost"] for r in ledger if r["condition"] == cond)
    return med_tok, med_cost, total


med_tok, med_cost, chain_total = token_stats("headline")
for arm, tok in [("canon", 20775), ("canondoc", 13991),
                 ("agentsmd", 64568), ("bare", 61006)]:
    check("5.3", f"{arm} median recall tokens", tok, int(med_tok[arm]),
          "results/headline/sessions.csv : tokens where session=recall")
for arm, cost in [("canon", 0.0033), ("canondoc", 0.0022),
                  ("agentsmd", 0.0120), ("bare", 0.0123)]:
    check("5.3", f"{arm} median recall cost", cost, round(med_cost[arm], 4),
          "results/headline/ledger.csv : usage.cost where session=recall")
for arm, tot in [("canon", 0.5453), ("canondoc", 0.4639),
                 ("agentsmd", 0.6227), ("bare", 0.5346)]:
    check("5.3", f"{arm} total chain cost", tot, round(chain_total[arm], 4),
          "results/headline/ledger.csv : usage.cost summed over the arm")

check("5.3", "total chain cost ordering: canondoc < bare < canon < agentsmd",
      ["canondoc", "bare", "canon", "agentsmd"],
      sorted(ARMS, key=lambda a: chain_total[a]),
      "results/headline/ledger.csv : usage.cost")

check("4.6", "confirmatory run metered worker-session total", 2.17,
      round(sum(chain_total[a] for a in ARMS), 2),
      "results/headline/ledger.csv : usage.cost summed over all arms")
check("5.3", "canon median recall tokens as a ratio of bare", 0.34,
      round(med_tok["canon"] / med_tok["bare"], 2),
      "results/headline/sessions.csv")
check("5.3", "canon median recall cost as a ratio of bare", 0.27,
      round(med_cost["canon"] / med_cost["bare"], 2),
      "results/headline/sessions.csv")

check("4.6", "confirmatory cells", 100,
      len({(r["chain"], r["rep"], r["condition"])
           for r in load_csv("headline", "outcomes.csv")}),
      "results/headline/outcomes.csv : distinct chain/rep/condition")


def judge_calls(tag):
    total = 0
    for path in sorted((ROOT / "results" / tag).glob("*-grades.json")):
        doc = json.loads(path.read_text())
        if "cold" in doc:
            total += len(doc["cold"].get("recallFacts", {}))
        else:
            total += sum(len(cell.get("recall", {})) for cell in doc.values())
    return total


check("4.6/8", "judge calls in the confirmatory run", 400, judge_calls("headline"),
      "results/headline/*-grades.json : recall verdicts, one call per fact")
check("8", "judge calls in the Sol spot check", 80, judge_calls("spot-sol"),
      "results/spot-sol/*-grades.json : recall verdicts")
check("8", "judge calls in the headline cold controls", 26, judge_calls("cold"),
      "results/cold/*-grades.json : cold.recallFacts, all three chain-05 runs")

# Unconditioned check-level sensitivity (Section 4.2, Figure 4 caption).
unc = defaultdict(lambda: [0, 0])
for r in load_csv("headline", "outcomes.csv"):
    unc[r["condition"]][1] += 1
    if r["pass"] == "True":
        unc[r["condition"]][0] += 1
for arm, n in [("canon", 109), ("agentsmd", 107), ("canondoc", 105), ("bare", 85)]:
    check("4.2", f"{arm} intended checks passed (of 110)", n, unc[arm][0],
          "results/headline/outcomes.csv : passed, no cold filter")

cold_metrics = ledger_sessions("cold")
cold_cost = sum(r["cost"] for r in cold_metrics)
check("4.2", "cold-control sessions executed", 14, len(cold_metrics),
      "results/cold/ledger.csv (5 chains x 2 controls, plus chain 05 twice more)")
check("4.2", "cold-control cost", 0.083, round(cold_cost, 3),
      "results/cold/ledger.csv : usage.cost")


# ----------------------------------------------------------------- Sol check

sol_traps = trap_cells("spot-sol", cold_tag="spot-sol-cold")
for arm, n, d in [("canon", 6, 6), ("bare", 2, 6)]:
    check("7", f"Sol {arm} trap cells under Sol eligibility",
          (n, d), tuple(sol_traps[arm]),
          "results/spot-sol/outcomes.csv joined to spot-sol-cold traps")

sol_r = recall_counts("spot-sol")
for arm, po, sec in [("canon", 17, 22), ("bare", 15, 20)]:
    check("7", f"Sol {arm} plant-only, headline eligibility (of 18)", po,
          sol_r[arm]["po"][0], "results/spot-sol/recall.csv : asserted")
    check("7", f"Sol {arm} secondary (of 22)", sec, sol_r[arm]["sec"][0],
          "results/spot-sol/recall.csv : asserted where not plantOnly")

# Facts a cold Sol recovered unaided are demoted; they do not become secondary.
sol_leaked = set()
for chain in chain_ids():
    facts = cold_grades("spot-sol-cold", chain)["recallFacts"]
    sol_leaked |= {f for f, rec in facts.items() if rec and f in declared[chain]}
check("7", "facts demoted from plant-only under a cold Sol", 2, len(sol_leaked),
      "results/spot-sol-cold/*-grades.json : cold.recallFacts true and declared")
check("7", "the demoted facts",
      {"docs_1000", "consumer_repo_fin_ledger_intake"}, sol_leaked,
      "results/spot-sol-cold/*-grades.json")

sol_excl = defaultdict(lambda: [0, 0])
for r in load_csv("spot-sol", "recall.csv"):
    if r["plantOnly"] == "True" and r["fact"] not in sol_leaked:
        sol_excl[r["condition"]][1] += 1
        if r["asserted"] == "True":
            sol_excl[r["condition"]][0] += 1
for arm, n in [("canon", 13), ("bare", 11)]:
    check("7", f"Sol {arm} demotion-excluded plant-only (of 14)", n,
          sol_excl[arm][0], "results/spot-sol/recall.csv minus demoted facts")

sol_tok, sol_cost, sol_total = token_stats("spot-sol")
for arm, tok in [("canon", 11228), ("bare", 46911)]:
    check("7", f"Sol {arm} median recall tokens", tok, int(sol_tok[arm]),
          "results/spot-sol/sessions.csv : tokens where session=recall")
for arm, cost in [("canon", 0.0499), ("bare", 0.1701)]:
    check("7", f"Sol {arm} median recall cost", cost, round(sol_cost[arm], 4),
          "results/spot-sol/ledger.csv : usage.cost where session=recall")
check("7", "Sol spot-check arm totals", 9.63,
      round(sol_total["canon"] + sol_total["bare"], 2),
      "results/spot-sol/ledger.csv : usage.cost summed over both arms")


# ------------------------------------------------- development runs (Sec. 6)

for tag, arm, po, sec in [("study2", "canon", 10, 17), ("study2", "canondoc", 12, 20),
                          ("study2", "bare", 17, 22), ("study2", "agentsmd", 14, 21),
                          ("study3", "canon", 17, 22), ("study3", "canondoc", 15, 21)]:
    t = recall_counts(tag)
    check("6", f"{tag} {arm} plant-only (of 18)", po, t[arm]["po"][0],
          f"results/{tag}/recall.csv : asserted where plantOnly")
    check("6", f"{tag} {arm} secondary (of 22)", sec, t[arm]["sec"][0],
          f"results/{tag}/recall.csv : asserted where not plantOnly")

s2_tok, _, _ = token_stats("study2")
s3_tok, _, _ = token_stats("study3")
# Ten recall sessions give an even-sized sample, so this median is the mean of
# the 5th and 6th values and lands on an exact half token. The paper displays
# 43,587. See PROVENANCE.md, "Rounding".
check("6", "canon run-2 median recall tokens", 43587.5, s2_tok["canon"],
      "results/study2/sessions.csv")
check("6", "canon run-3 median recall tokens", 24151, int(s3_tok["canon"]),
      "results/study3/sessions.csv")
check("6", "canon run-2 to run-3 recall-token reduction", 1.80,
      round(s2_tok["canon"] / s3_tok["canon"], 2),
      "results/study2 and study3 sessions.csv")
check("4.5", "bare median recall tokens in run 2, the freeze's 64k prior",
      64034, int(s2_tok["bare"]), "results/study2/sessions.csv")
check("4.5", "no run-3 canon median reproduces the freeze's 29k",
      True, int(s3_tok["canon"]) != 29000,
      "results/study3/sessions.csv : median is 24,151")


# ----------------------------------------------------------------- reporting

width = max(len(c) for _, _, c, _, _, _ in results)
failed = 0
for ok, section, claim, expected, actual, source in results:
    tag = "PASS" if ok else "FAIL"
    if not ok:
        failed += 1
    print(f"[{tag}] {section:8s} {claim:<{width}}  expected={expected!r} "
          f"got={actual!r}\n         source: {source}")

print(f"\n{len(results) - failed} of {len(results)} checks passed.")
if failed:
    print(f"{failed} FAILED. The artifacts are the arbiter: a failure here means "
          f"the paper and these artifacts disagree.")
sys.exit(1 if failed else 0)
