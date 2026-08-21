# W3-RESULTS-001: accumulation, measured (2026-08-20)

One capture, 20260820-w3-model-001: 248 sessions (120 writers, 128 readers),
sequential, grade-blind, gpt-5.6-luna thinking high through the SHIPPED
pi_canon tool at package commit 93172bb, bwrap strict sandbox, contract
w3-one-model-run-001, ceiling 1.50000000, one run only. Reported cost
$0.81108520000000000252, of which writers $0.7046, arm A readers $0.0804, arm
C readers $0.0261. 248/248 attempted, 247/248 protocol-valid (one writer
timeout, below). Fake preflight before the run: 248/248 protocol-valid,
graded perfect, sixteen no-op rehearsals, sixteen loud-mismatch rehearsals.

## Design in one paragraph

32 lineages (8 domains x K in {1, 2, 4, 8}) of evolving session records:
capacity revised EVERY session, operating mode on even sessions, alert
threshold on odd sessions from 3, confirmation policy flipped once
mid-lineage, a sequence rule set in session 1 and never touched, a consumer
retired near the end of every K >= 2 lineage. Arm A writers run sequentially
through the shipped tool, each inheriting the store its predecessor actually
left; arm A readers answer from the final store, arm C readers from all K raw
records inline. Two typed reviews per lineage per arm, graded exactly per
slot, with every miss checked against superseded values (contamination). New
instrument discipline from W2: terminal refusals are loud and instructive in
their text, and the watch review carries a consumer_status slot so a reader
must say "retired" rather than parrot the stale active state.

## Readers: 127/128, and the store side was perfect

| K | A exact | A median input tok | C exact | C median input tok |
|---|---|---|---|---|
| 1 | 16/16 | 4,301 | 16/16 | 623 |
| 2 | 16/16 | 3,304 | 16/16 | 892 |
| 4 | 16/16 | 3,990 | 15/16 | 1,308 |
| 8 | 16/16 | 4,781 | 16/16 | 2,144 |

Decisions 128/128. All 32 arm C watch readers reported the consumer status
correctly, including the 24 retired cases. The single miss in the whole
capture: the vineyard K=4 arm C watch reader reported the session 1
confirmation policy despite session 3's reversal sitting in its own prompt
pile, the exact contamination class registered as prediction 2 (flagged
confirmation_pre_flip_value; its decision still came out right through the
threshold branch). Arm A went 64/64 against stores that were, as measured
below, heavily narrated.

## The headline: the store LOST the size race

Prediction 1 said arm C input grows linearly and arm A stays near-flat. Both
halves held (C 623 to 2,144 tokens, slope about 215 per session; A within
+11% of flat). The expected conclusion, a crossover where the store becomes
the cheap channel, did NOT arrive, and the reason is the finding:

| K | median final store bytes | median transcript pile bytes |
|---|---|---|
| 1 | 3,199 | 1,432 |
| 2 | 4,614 | 2,603 |
| 4 | 9,844 | 4,359 |
| 8 | 18,511 | 7,880 |

Under the shipped doctrine, writers narrate history into articles, and the
store grows FASTER than the raw record it distills: 2.3x the pile at K=8.
Arm A reader input therefore stayed 2x to 7x above arm C at every rung, and
extrapolating the measured slopes the crossover sits near K=20 even if
articles stopped fattening today. The premise "history grows linearly, the
current-truth article does not" is false as a statement about what writers DO;
it is only true of what articles COULD be. The store's economy case is not a
property of the architecture, it is a property of write discipline that the
current doctrine does not enforce.

## Staleness compounds, and does not yet harm

Prediction 3 asked whether inherited narration compounds or saturates.
Compounds, linearly, without a hint of saturation: superseded values standing
in final-store articles were 16/16 at K=2, 37/45 at K=4, 82/95 at K=8 (by
family: capacity 71, mode 34, threshold 30). The K=8 trajectory is a straight
line, about 11 new standing stale tokens and 2.2KB of store growth per
session, and writer output tokens grow with session index (median 2,595 at
s1 to 4,390 at s8) even though later sessions carry fewer changes: fat
inherited articles invite fatter rewrites. Retention stayed perfect through
all of it (all five mechanical facts in the governing article in 32/32 final
stores), and arm A readers went 64/64, so at this scale the debris is not yet
costing correctness, only tokens. The two curves now on record: debris grows
linearly, harm holds at zero through K=8. Whatever K breaks arm A first was
not reached.

## Session-scale events worth the record

- The vineyard K=8 session 7 writer (the retirement session) hit the 300s
  timeout after 9 writes and a journal entry; the retirement had already
  landed, session 8 inherited the partial store, and the lineage's readers
  went 4/4. Inheritance of whatever the predecessor ACTUALLY left absorbed a
  killed session with zero downstream loss.
- The W2 instrument rule paid off in one session: a foundry K=4 arm A reader
  dropped one character from its task_id, the same digit-drop that caused
  W2's only miss, and this time the loud TASK_ID_MISMATCH text named the
  expected id and the reader resubmitted correctly (protocol class recovery).
  Two id mis-copies in ~224 typed submissions across W2 and W3 is the
  measured rate for this model; loud refusals are the mitigation.
- The shipped no-op write rule fired once on real traffic (vineyard K=1
  writer re-sent an identical article; the store reported "already current"
  and the freshness stamp survived).

## Predictions scored

1. C linear, A near-flat: CONFIRMED, but the inference drawn from it in the
   design (a crossover in the store's favor) is refuted by the store-growth
   finding above.
2. C degrades on revised and retired facts: barely present. 1/64 exact-miss
   contamination at K <= 8 on clean, well-ordered records; retired facts
   24/24. The transcript pile is more reliable under revision at this depth
   than predicted; its failure mode is real but rare while the pile fits.
3. A staleness compounds or saturates: COMPOUNDS, linearly, harm-free so far.

## What W3 changes

The store's measured wins are correctness under revision at zero marginal
input growth, selection and placement (still solved: 40/40 placed at every
rung), surviving killed sessions through inheritance, and the W1-proven touch
channel. Its measured loss is bulk-recall economics under the current write
doctrine, because articles accrete narrated history. The design pressure this
creates is specific: current-only articles need enforcement, not invitation.
W2 showed prompting halves noise but does not change revision habits, and the
phrase-lint route was built and rejected the same day (vocabulary too
varied). What remains is structural: either a typed current-state arc
(provenance, not prose) or a mechanical pressure against article growth,
e.g. surfacing article byte growth across writes at the tool boundary. That
is a W4-shaped question, and it now has a number attached: every session of
narration costs about 2.2KB of permanent store growth and 11 standing stale
values, paid by every future reader of those articles.

Artifacts: lab/evolving-canon/w3/ (generator, contracts, harness, injections,
grader, run 20260820-w3-model-001 with per-session manifests, stores at every
rung, and graded-report.json). Predictions were registered in
W3-DESIGN-001.md before the build.
