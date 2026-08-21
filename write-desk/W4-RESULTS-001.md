# W4-RESULTS-001: the tool's voice halves narration (2026-08-20)

One capture, 20260820-w4-model-001: 160 sessions (128 writers, 32 readers),
sequential, grade-blind, gpt-5.6-luna thinking high, bwrap strict sandbox,
contract w4-one-model-run-001, ceiling 1.50000000, one run only. Reported
cost $0.70484515999999999977. 160/160 attempted, 160/160 protocol-valid: the
programme's first capture with zero invalid and zero recovery sessions. Fake
preflight before the run: 160/160, graded perfect, arm purity asserted from
inside the sessions (the shipped kit must never speak the growth line).

## Design in one paragraph

The W3 finding priced narration; W4 tested the cheapest structural pressure
against it. Two arms over the SAME eight fresh K=8 lineages, differing in
exactly one file: arm A ran the shipped tool verbatim, arm G ran a lab-patched
tool.ts whose write path appends, whenever a rewrite grows the trimmed body,
one sentence naming the growth in bytes and restating the split (article
carries current state, narrated history belongs in the journal). Writers
inherit predecessor stores within their arm; two readers per lineage per arm
answer from the final store as the regression check. Predictions and the ship
rule were frozen in W4-DESIGN-001.md before the build.

## Results: the first intervention that moved the habit

| metric (8 lineages each) | arm A (shipped) | arm G (growth voice) |
|---|---|---|
| superseded values standing in final articles | 88/96 | 51/96 |
| median final store bytes (pile = 7,882) | 15,905 | 12,708 |
| median writer output tokens | 2,894 | 2,384 |
| median reader input tokens | 4,330 | 3,951 |
| readers exact | 15/16 | 16/16 |

Arm A replicated W3's baseline on a fresh fixture (92% of superseded values
standing, against 86% in W3). The growth voice cut that to 53%, shrank final
stores by a fifth, and spent 18% fewer writer output tokens, with readers at
16/16. The staleness trajectory tells it as a slope: arm A accumulated about
11 standing stale values per session all the way to s8, arm G about 6, with
no saturation in either. Journal counts were equal across arms (65 vs 64
entries), so the voice did not relocate history into the journal; it
suppressed the narration itself. Prompting the same doctrine moved staleness
by one cell in W2. The tool saying it, at the moment of the write, moved 37.

The growth line fired 117 times across arm G's 198 writes. Fire count is not
a pure narration proxy: the perfect-actor preflight fired 30 times from
digit-length variance alone. The named byte sizes carry the signal.

## The baseline arm delivered W3's missing observation: staleness harm

W3 closed with "debris grows linearly, harm holds at zero through K=8." W4's
fresh baseline arm found the harm: the foundry arm A watch reader reported
the pre-flip confirmation policy out of the narrated store and made a wrong
DECISION, the same contamination class that hit arm C's transcript pile in
W3 (its reader waded through 6,503 input tokens of fattened articles). The
transcript channel's failure mode infects the store exactly insofar as the
store becomes a transcript. Harm at the K=8 baseline is now 1/16, not zero,
and arm G's 16/16 sits beside it.

## Ship

The frozen ship rule was met on all three predictions (staleness margin
material, store bytes down, no reader regression; the regression appeared in
the baseline instead). The growth line shipped the same evening, verbatim as
measured, zero constants: commit e1312e6, gate "a growing rewrite names its
growth; creation, shrinking, capsule-only, and no-op stay silent," README
paragraph included, 173 gates green. The residual matters: arm G still left
53% of superseded values standing, so the voice halves the habit rather than
curing it, and the typed current-state arc remains the cure candidate, now
with its mitigation shipped and its remaining gap measured.

## Integrity disclosure: concurrent commit mid-capture

While the capture ran, a concurrent session committed b6dc366 ("Relations
rules join the contract") to main at 19:10, editing two contract-pinned
package files (schema.ts, tool.ts) in the working tree the harness copies
kits from. Sessions at ordinals 35 through 160 (126 of 160) therefore ran
with package bytes that differ from the contract pins; the launch-time digest
check passed and nothing re-verified per session. The drift is inert for this
capture, by construction and by evidence: the relations defaults enforce
nothing (required false, no min_count, warn false), schema.json sits at the
store root outside every graded surface, arm G's tool.ts came from the
unchanged lab patch throughout, and a sweep of all 160 transcripts found zero
schema, refs, or relations output reaching any model (the five "relations"
hits are model prose). The comparison stands, disclosed.

Instrument rule from this, binding on every future capture: the harness must
snapshot the pinned package files into the run root at launch and build every
kit from that snapshot, so a moving working tree cannot reach a running
capture. Per-session digest re-verification would only detect the drift;
the snapshot prevents it.

## Predictions scored

1. Arm G staleness below arm A: CONFIRMED, 51 vs 88 of 96.
2. Arm G store bytes below arm A: CONFIRMED, 12,708 vs 15,905 median.
3. No reader regression in arm G: CONFIRMED, 16/16; the baseline arm lost
   one to stale-store contamination instead.
4. Growth line fires in most arm G sessions: CONFIRMED (117 fires), with the
   preflight-measured caveat that count includes benign digit variance.

Artifacts: lab/evolving-canon/w4/ (patched/tool.ts, generator, instrument,
harness, injections, grader, run 20260820-w4-model-001 with per-session
manifests and stores at every rung). Day's paid research spend across W1j,
W2, W3, W4: about $2.81.
