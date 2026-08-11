# canon-bench

The benchmark behind *pi-canon: Mutable Canonical Memory over an Immutable
Journal, with Recall by Surfacing* (Conner, 2026). Five multi-session chains
that measure whether a coding agent respects a constraint it was told about in
an earlier session and never told again.

The package under test is [pi-canon](https://github.com/shaneconner/pi-canon).
The per-cell artifact trail (transcripts, store snapshots, judge verdicts) is
too large for git and ships with the Zenodo deposit.

## What it measures

A chain is a small fictional repository and a four-session story, all four
sessions sharing one persistent worktree:

1. **plant**: a task whose natural course surfaces a constraint, never phrased
   as an instruction to remember.
2. **distractor**: unrelated work.
3. **probe**: a task whose obvious solution violates the planted constraint in
   a way that compiles, runs, and passes the visible tests, but fails a hidden
   grader.
4. **recall**: an auditor's questions, graded per fact by a pinned LLM judge.

**Trap avoidance** is the primary metric: the fraction of probe cells where
every cold-failing grader check passes. **Plant-only recall** is secondary.

Both metrics are model-relative and fixed by executed cold controls, but by
different mechanisms, and the difference matters when reading the numbers:

- The **trap set is derived**. A probe-cold run attempts the probe with nothing
  planted; every check it fails becomes trap-eligible. No check is trap-eligible
  by authorial declaration.
- The **plant-only set is declared, then certified**. Each chain names its
  plant-only facts in `chain.json`; a recall-cold run answers the questions with
  nothing planted, and demotes any declared fact it recovers. The cold control
  can remove facts from the set but never add them, so a fact the author did not
  declare stays secondary even if no cold run recovered it. Five of the twenty
  facts are in that position under the headline worker.

`analyze.py` is where both rules live: line 41 derives traps from the cold
outcome, line 54 reads plant-only membership from the chain manifest.

## The five chains

| chain | knowledge class | the planted constraint |
| --- | --- | --- |
| `01-vendor-feed` | operational constraint | list endpoints silently cap pages at 50; stock 999 is an uncounted sentinel |
| `02-memo-poison` | rejected alternative | resolve results must never be cached; a nightly rebalancer mutates records in place |
| `03-consumer-contract` | invisible downstream consumer | a finance parser in another repository needs integer cents in `report.txt` |
| `04-tz-convention` | cross-asset convention | datetimes stay naive UTC; the deploy host's serializer double-converts aware values |
| `05-import-lazy` | environment quirk | the cron host has no network at import time, so client construction stays lazy |

Chain 05 carries no trap endpoint: a cold worker passes its probe unaided, so
100 cells yield 80 trap-eligible probe outcomes.

## Verifying the published numbers

    python3 tests/verify_claims.py    # 92 of 92 checks pass
    python3 tests/verify_freeze.py    # 113 of 115 at HEAD, see below

`verify_claims.py` recomputes every quantitative claim in the paper from
`results/` and `chains/`, printing the paper section, the expected value, the
recomputed value, and the source field for each. Standard library only.

`verify_freeze.py` checks the working tree against `FREEZE-manifest.txt`. It
reports 115 of 115 at the freeze commit `a1bf589` and 113 of 115 at HEAD: one
disclosed post-freeze commit (`ad6aa45`) added a worker-model passthrough to
`run_suite.py` and `run_session.py` so the robustness pass could swap the worker,
with defaults untouched and the judge pinned regardless. Any other difference
fails the script.

## Layout

    chains/<id>/chain.json     the manifest: prompts, recall questions, facts,
                               and the declared plantOnly list
    chains/<id>/seed/          the starting repository
    chains/<id>/external/      the enforcement package, copied into each cell as
                               a worktree sibling so relative paths resolve
    chains/<id>/hidden/        the grader, never placed in the cell
    chains/<id>/validate.py    asserts a reference solution passes and the naive
                               solution fails with the expected signature
    chains/SPEC.md             the contract the five chains implement
    run_suite.py               the driver: one chain, all reps, all arms
    run_session.py             one session
    analyze.py                 grades to CSVs; where the two metric rules live
    results/<tag>/             outcomes.csv, recall.csv, sessions.csv,
                               ledger.csv, and per-chain grades.json
    FREEZE.md                  the pre-specified protocol, metrics, hypotheses
    FREEZE-manifest.txt        a SHA-256 per suite-defining file

Run tags: `cold` and `spot-sol-cold` are cold controls, `headline` is the
confirmatory run, `spot-sol` is the post-freeze robustness pass, and `study2`
and `study3` are development runs reported as development evidence only.

`sessions.csv` rounds cost to five decimals; `ledger.csv` carries the same
values at full precision. Dollar figures in the paper are computed from the
ledger, so summing the `sessions.csv` column can differ in the fourth decimal.

## Reading the results honestly

The five chains are development-exposed: the product changed in response to
failures on these same chains, and the confirmatory run reuses them. The freeze
constrains execution after it; it does not make the chains unseen. The same
author wrote the package, the chains, the traps, and the graders, and the
plant-only set is declared by that author, which is the most direct route for
task-selection bias into a headline number.

The generalization unit is five chains, and on the trap metric four eligible
trap designs, not 100 cells. Repetitions repeat the same traps, so no binomial
uncertainty attaches to any pooled count. Judge calls are archived but never
metered, so every dollar figure is metered worker-session cost only.

This is a package-level result on these chains. It does not estimate a general
effect and does not attribute results to components; no component ablations
exist.

## License

MIT.
