# W4C-DESIGN-001: breaking the order confound (registered mid-capture, before grading)

Status: DESIGN, registered 2026-08-22 while capture `20260822-w4c-model-001` was
running and before any grading was performed or any result inspected. That is
weaker than W3's and W4's pre-build registration and the record should say so
plainly: the instrument was built and launched first, and this document was
written during the run. What it does still buy is that the predictions below are
committed before any outcome is known, because the grader had not been pointed at
the run when this was written and the harness is grade-blind by construction.

## Why this capture exists

An outside adversarial review of the write-desk paper (round five, 2026-08-22)
raised a defect neither W4 nor W4R can answer from their own data.

`w4_build_instrument.py` iterates `for arm in ("A", "G")` for every lineage. So
inside every lineage the untreated arm's eight writer sessions and two readers ran
to completion before the treated arm started. Condition is therefore perfectly
confounded with execution order in W4. W4R reused the identical builder, so its
"replication" repeated the contrast on a second model WITHOUT breaking the
confound: it varied the writer and held the order.

Nothing in either capture separates "the growth line changed writer behaviour"
from "the arm that ran second behaved differently". Deleting the paper's p-values
addressed invalid inference and did not touch identification. One realisation per
cell and no exposed decoding seed leave no variance estimate to lean on either.

The first capture makes this concrete rather than theoretical. W4's contract pinned
`extensions/lib/schema.ts` and `extensions/lib/tool.ts` at their pre-`b6dc366`
bytes, and that concurrent commit changed both partway through the run, at ordinals
35 to 160 of 160. With A always before G, execution time and package state were not
balanced across the two conditions. The drift audit concluded the change was inert,
and that conclusion is not disputed here, but "inert" is a finding about one
specific diff, not a general reason to accept an unbalanced design.

## The variant

Exactly one thing changes from W4: the per-lineage arm order.

`w4c_build_instrument.py` is a new file rather than an edit to W4's builder, so
W4's contract pins stay valid and reproducible. It reuses `w4_lineage.build_all()`,
`w3_contract`'s prompts and submit tools, and the same two pinned arm tools under
`arms/`. Lineages are taken in the order `w4_lineage` emits; even indices run A
before G, odd indices run G before A.

- A first: `funicular_brakes_w4k8`, `observatory_chiller_w4k8`,
  `regatta_timing_w4k8`, `vineyard_netting_w4k8`
- G first: `foundry_ladle_w4k8`, `gravel_washplant_w4k8`, `mushroom_tunnel_w4k8`,
  `salt_pan_rakes_w4k8`

The schedule is deterministic and declared rather than sampled. A seeded shuffle of
eight items is not meaningfully more random than a declared alternation, and a
declared schedule is auditable. It is recorded in the instrument and the contract as
`arm_order_by_lineage`, so no reader has to infer it from ordinals.

Two invariants are asserted in the builder, not hoped for: exactly four lineages
each way, and within every lineage the first arm's writer block completes before the
second arm's begins.

## What is held

Verified equal to W4 before launch: the hidden fixture hash, the writer system
prompt hash, the reader system prompt hash, and both arm tool hashes. The 160
`assignment_id` values are identical to W4's, because the identifier hashes role,
arm, lineage, and session index and not the ordinal. 80 of the 160 ordinals moved,
which is exactly the four G-first lineages swapping their two blocks.

Package pins match W4R's rather than W4's, which is the correct precedent: W4R ran
after the launch-snapshot fix, and the harness now copies the seven pinned package
files once at launch and builds every kit from that copy, so nothing can move
mid-run. Recorded package commit is `4770088`; the seven pinned files are
byte-identical to the state W4R ran against.

Model is `gpt-5.6-luna`, matching W4 rather than W4R, because the question is about
order and not about the writer, and luna is the cheaper meter. Cost ceiling
`1.50000000`, exact and not relaxable mid-run; W4 spent 0.705 on the same shape.
Retries, replacements, and selective reruns are zero, as in every capture in this
programme.

## Validation performed before the paid run

- `--validate-only`: contract ok, 160 assignments.
- `--fake` over all 160 assignments through the real role extensions and Pi's exact
  schema validator, reusing W4's `fake-injections.json` unchanged, which is sound
  because injections are keyed by `assignment_id` and those are identical. Result:
  160 attempted, 160 protocol valid, cost 0.
- Grading the fake run with `--expect-perfect`: 32/32 readers exact, 0/96 standing
  values in both arms, both arms at median store 2,750.5 bytes and pile 7,881.5
  bytes, 136 writes each, arm G 38 growth lines and arm A zero. Arm purity and
  byte-comparability both hold under the reversed order.

## Predictions registered before grading

1. **The staleness contrast survives order reversal.** Arm G ends below arm A in
   both the four A-first lineages and the four G-first lineages, considered
   separately. This is the prediction the capture exists to test. A null here is a
   real and publishable result: it would mean W4 and W4R measured an order effect,
   or a mixture, and the paper's central claim would have to be withdrawn to a
   description of two fixed-order conditions permanently.
2. **The G-first subset shows a contrast of the same sign and roughly the same
   size as the A-first subset.** If the A-first subset reproduces W4's gap while
   the G-first subset shrinks it or reverses it, order is carrying part of the
   effect and the honest reading is a mixture rather than a clean identification.
3. **Pooled staleness lands near W4's.** W4 on this model and fixture was 88/96
   untreated against 51/96 treated. W4C pools four lineages of each order, so a
   pooled result far from that, in either arm, is evidence that something other
   than order differs between the captures and needs finding before the result is
   used.
4. **Reader exactness does not regress.** W4 was 15/16 untreated and 16/16 treated;
   W4R was 16/16 and 16/16. No mechanism here should hurt readers.
5. **Store bytes stay directionally inconsistent.** W4 and W4R already dissociated
   on size, and the paper reports the size effect as inconsistent across lineages.
   Order reversal is not expected to rescue it, and if it suddenly becomes clean
   that is itself a signal worth chasing rather than a win to bank.

## Reading rule, fixed before the numbers

If prediction 1 holds in both subsets, the paper may describe the growth line as
reducing standing superseded values rather than merely as a condition that ended
with fewer, and it must still say the identification rests on eight lineages in one
counterbalanced capture on one model.

If prediction 1 fails in the G-first subset, the paper keeps the demoted
fixed-order language it currently carries, reports W4C as a negative result in full,
and the honest headline becomes that the effect could not be separated from order.

Either way W4C is reported. This document is the commitment not to leave it out if
it comes back the wrong way.

## Artifacts

Instrument `build/instrument/instrument-w4c.json`, contracts
`build/instrument/contract-w4c-validate-only.json` and `contract-w4c-one-run.json`,
fake run `runs/20260822-w4c-fake-001/`, paid run `runs/20260822-w4c-model-001/`.
Builder `w4c_build_instrument.py`. The capture harness `w4_model_capture.py` gained
one entry in `CONTRACT_IDS` and nothing else.
