# canon-bench pre-registration freeze

Frozen 2026-08-10, before the headline run. Aggregate manifest hash 32820fccc3c96717
(sha256 of FREEZE-manifest.txt, which lists sha256 per suite-defining file: the five
chains complete with graders and fixtures, SPEC.md, run_suite.py, run_session.py,
analyze.py, assets/agents-preload.md). Product under test: pi-canon at commit b95c680.
Nothing listed here changes between this freeze and the published numbers; anything
that must change voids the run and is disclosed.

## Suite

canon-bench is built by this project, not derived from any external benchmark. Five
chains: 01-vendor-feed, 02-memo-poison, 03-consumer-contract, 04-tz-convention,
05-import-lazy. Each chain: plant, distract, probe work sessions, then a recall
session; hidden graders score a post-probe snapshot against the pristine external
package; recall facts are graded per-fact by the pinned LLM judge.

## Pre-registered protocol

- Conditions, 4 arms: canon (stock pi + pi-canon), canondoc (canon + static doctrine
  AGENTS.md), bare (nothing persists; transcripts at .sessions/ for recall), agentsmd
  (self-maintained AGENTS.md preloaded with assets/agents-preload.md noise, prompted
  each work session to keep it updated).
- Reps: 5 per chain per condition (100 cells). Cells run to completion; a cell lost
  to infrastructure (nonzero pi exit, timeout) is rerun once and disclosed, never
  silently dropped.
- Worker model pinned: gpt-5.6-luna, thinking low, via openai-codex provider.
- Judge pinned: gpt-5.6-luna, thinking low, JUDGE_PROMPT as frozen in run_suite.py;
  judge validated 24/24 on per-chain gold/zero fixtures (validate_judge.py).
- Trap checks are defined empirically as the checks that FAILED in the certified cold
  controls (tag: cold), already run on fresh seeds under bare. Chain 05 has no
  cold-failing check and is pre-excluded from the trap aggregate (it still counts for
  recall and cost). Recall-cold certified plantOnly facts unanswerable without the plant.

## Pre-registered metrics, in rank order

1. Trap cells: fraction of cells where every cold-failing check passes.
2. plantOnly recall: facts only the plant could furnish, judge-graded.
3. Recall session tokens and cost (median): the price of the answer.
4. Secondary recall; total chain cost.

## Pre-registered hypotheses

H1: canon beats bare on trap cells by a wide margin (run 2: 6/8 vs 3/8; run 3: 8/8).
H2: canon matches bare on plantOnly recall within 2 facts while spending under half
    bare's median recall tokens (run 3: 17/18 vs 17/18 at 29k vs 64k).
H3: canondoc adds nothing over canon now the doctrine ships in the product (run 3
    direction: canondoc scored below canon).
H4: agentsmd pays the preload tax: highest total cost, no metric lead (run 2: most
    expensive arm, dropped a trap cell and recall facts vs its unloaded run-1 self).

Runs 1-3 were development runs and are reported as such; the headline numbers come
only from the run executed after this freeze (tag: headline).
