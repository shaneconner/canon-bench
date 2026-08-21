# W3-DESIGN-001: accumulation, where the store earns its keep (sketch)

Status: SKETCH. Nothing built, no fixture, no run scheduled.

## Why this is next

W2 priced the left end of the history curve: at ONE session of history, the raw
transcript matched the store on accuracy at a third of the read cost, because
store recall spends turns and every turn re-pays context. Canon's actual claim
lives further right: history grows linearly with sessions, the current-truth
article does not, and somewhere the transcript channel stops fitting and stops
being cheap. W3 measures the crossover and what accuracy does on each side of
it.

## Shape

Extend the W2 machinery from one session to a LINEAGE of K sessions per domain
(K in {1, 2, 4, 8}), each session's transcript evolving the same facts the W2
generator already produces: values revised across sessions (the staleness
pressure now compounds), facts introduced late, facts retired mid-lineage.
Writers run sequentially per lineage through the SHIPPED tool, each inheriting
the store its predecessor actually left (the W1j inheritance discipline,
applied to real stores). Readers at the end of each lineage answer tasks whose
facts span sessions: the current value of a thrice-revised limit, a fact from
session 1 untouched since, a fact retired in session K-1 that must NOT be
reported as current.

Arms: A store-recall (the shipped tool over the accumulated store), C
transcript-recall (ALL K transcripts inline, however large that gets). Arm B
(guidance) is dropped: W2 measured its effect and the question here is channel
economics, not prompting. 8 domains x the four K rungs, writers 8x(1+2+4+8)=120,
readers 2 per lineage per arm = 128, total 248 sessions; estimated under 0.90
at W2 prices; ceiling 1.50000000.

## Frozen metrics

Reader exactness per arm per K; reader input tokens per arm per K (the
crossover curve, the headline); staleness of the FINAL store per K (does the
W2 narration habit compound or saturate as writers inherit narrated articles);
retired-fact contamination in reader answers (does arm C start reporting old
values as current when K transcripts pile up, which is the transcript
channel's predicted failure mode); store size vs transcript-pile size per K.

## Predictions registered before any build

1. Arm C input grows roughly linearly in K; arm A stays near-flat.
2. Arm C accuracy degrades with K on revised and retired facts (the pile
   carries every old value with equal typographic authority); arm A holds if
   and only if writers keep articles current, which W2 says they mostly do,
   staleness residue aside.
3. The staleness residue compounds in arm A stores across K: inherited
   narration invites more narration. If it instead saturates, that weakens the
   typed-state urgency; either answer is worth having.

## Open before build

Whether K=8 transcripts still fit the reader context comfortably (they should:
8 x ~750 tokens), and whether writer session count per lineage needs a
turn-budget bump beyond 14. Build follows the W2 pattern: lineage generator,
instrument, fake preflight to perfection, then capture under the standing
no-per-run-gate rule.
