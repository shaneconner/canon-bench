# W2 results: selection quality upstream of recall (2026-08-20)

Run 20260820-w2-model-002, openai-codex / gpt-5.6-luna / high: 128/128 sessions
attempted, 127 protocol valid, cost 0.27602940000000000069 of the 1.50000000
ceiling. First experiment through the SHIPPED pi_canon tool (package commit
93172bb) rather than a lab protocol: writers persisted real session records
into real .canon stores; readers answered typed tasks from whatever store
their arm's writer actually left.

The predecessor capture 20260820-w2-model-001 was aborted at 10 sessions
(0.053 spent) for an instrument defect: the reader prompts never stated the
task_id the submit schema requires. Preserved with its ABORTED.md; excluded
from analysis.

## Headline

| Arm | Readers exact | Median reader input | Writer stores |
|---|---|---|---|
| A shipped doctrine | 31/32 | 3,310 tok | median 4,913 bytes, 5/12 decoys absorbed |
| B + selection guidance | 32/32 | 3,025 tok | median 2,904 bytes, 2/12 decoys absorbed |
| C no canon (raw transcript) | 32/32 | 909 tok | none |

Readers 95/96 overall. The one miss is not a knowledge failure: the arm A
quarry capacity reader established every slot correctly (its final prose shows
the right limit, mode, rule, and decision) but submitted the task_id with the
last character dropped, was softly refused TASK_ID_MISMATCH, and never
retried, because Pi 0.84.2 presents an extension tool's soft error with the
turn-level error flag FALSE, so the model read the refusal as a normal result.
The frozen grade stands as a miss; conditionally the cell was exact.

## Findings

1. **Selection and placement worked.** All six needed facts reached the store
   in every lineage and arm (the four raw retention misses, all on
   confirmation_required, are containment conservatism: the stores carry the
   fact in paraphrase, e.g. "requires confirmation from two people", and every
   corresponding reader answered it correctly). Every retained fact sat in the
   article at its GOVERNING address: 94/94 placed in each arm. The placement
   traps caught nobody; the doctrine's file-at-the-governing-address rule was
   followed even for facts discovered while working elsewhere. The two
   explicitly-undecided red herrings were never recorded as decided.

2. **Staleness is the universal writer failure: 63/64.** Both superseded facts
   entered the articles WITH their old values in 16/16 arm A writers (32/32
   fact-cells) and 15/16 + 16/16 in arm B (31/32): the writers narrate the
   change ("raised from 36 to 69") into current-truth articles instead of
   leaving the transition to the journal. Arm B's guidance said, verbatim,
   "the article carries only the current value and the journal carries the
   event", and moved the rate from 32/32 to 31/32. This replicates the
   programme's core asymmetry on the selection side: prompting does not fix a
   habit. Decision-level harm today was zero (readers extract the current
   value), but this is W1b's retained-revoked-values defect measured in the
   wild at near-100%, and it accumulates. The lint closure was BUILT AND
   REJECTED the same day: a change-narration phrase lint detected only 2 of 32
   narrating W2 stores (the retirement vocabulary is endlessly varied: "is
   retired", "superseded", "reversed", "invalidated", "prior value of") while
   tripping 3 of 4 articles in pi-canon's own store on legitimate prose.
   String matching cannot distinguish a current value from a retired one; that
   distinction requires provenance, which is exactly what the typed-state
   research core carries (W1e graded retired-value hits mechanically at zero)
   and markdown articles do not. Staleness closure is a typed-state question,
   the programme's long arc, not a lint question.

3. **Guidance DID move selection hygiene, the first positive prompt effect the
   programme has measured.** Decoy absorption into articles: arm A 82/192
   (median 5 of 12 per writer), arm B 33/192 (median 2). Median store: A 4,913
   bytes, B 2,904. Median journal entries: A 1, B 2 (guidance shifted events
   to the journal). Leaner stores read cheaper: median reader input 3,310 vs
   3,025. So prompt guidance separates on WHAT gets written and WHERE, while
   failing entirely on the staleness habit; the boundary between the two is
   the finding.

4. **At one session of history, the raw transcript beats the store on cost at
   equal accuracy.** Arm C readers: 32/32 exact at a median 909 input tokens
   against A's 3,310 and B's 3,025. Store recall costs turns, and every turn
   re-pays the conversation. This is the honest left end of the curve: W2's
   history is ONE ~750-token session, which fits in a prompt trivially. The
   product's case is accumulation (the transcript channel grows linearly with
   sessions and stops fitting; the store does not), so this number prices the
   crossover's origin rather than refuting the design. What it does establish:
   for short histories, canon's value is durability and addressability, not
   token economy, and nobody should claim otherwise.

5. **Pi soft-error invisibility is now a measured model-facing hazard, not
   just a classifier artifact.** The one reader loss happened because the
   refusal did not look like an error to the model. Instrument rule going
   forward, and a design echo of W1j's deterrence finding: terminal-tool
   refusals must be loud and instructive in their TEXT ("NOT RECORDED:
   task_id differs; resend with task_id X"), because the error channel cannot
   be relied on to carry the signal.

## Protocol notes

Writers 32/32 persisted (median output: A 2,913 tokens, B 3,168). Readers
95/96 first_pass, zero validation rejections, zero recoveries needed; the one
invalid is the task_id cell above. The harness's result.isError join (added
after the aborted run) classified the soft refusal correctly. Total W2 spend
including the aborted predecessor: 0.32917880.

## What W2 does not claim

Development evidence, one model, synthetic single-session transcripts, 16
lineages. No confirmatory, domain-general, scale, or shipping claim. The arm C
economy comparison is bound to one-session histories by construction.

Artifacts: runs/20260820-w2-model-002/ (capture-manifest.json,
grade-blind-report.json, graded-report.json, per-session trees, per-arm
stores), runs/20260820-w2-model-001/ABORTED.md.
