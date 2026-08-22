# W4C-RESULTS-001: the counterbalanced capture, and what it took back

Status: frozen result. Capture `20260822-w4c-model-001`, graded 2026-08-22 against
`W4C-DESIGN-001.md`, whose predictions and reading rule were written before grading
and are scored below without amendment.

Headline: the direction survived order reversal and the magnitude did not. Four of
the five registered predictions failed. The paper's central magnitude claim, that
the growth line takes standing superseded values from roughly nine in ten down to
roughly one in two, is not reproducible on the same model and must be withdrawn as
an estimate. What survives is a direction, now over three captures, with a much
smaller and much less stable size.

## The capture

160 attempted, 160 protocol valid, zero failed, zero timed out, zero retries,
replacements, or reruns. Reported model cost `0.79075743999999999731` against the
exact `1.50000000` ceiling; `ceiling_exceeded` false. Model `gpt-5.6-luna` at
thinking high, matching W4. Instrument sha256
`8ba9fd2d9b13fc5ac4e7f6a8e98aa6ab753898887c3445bd10e5e1e51f1f95f7`.

Held equal to W4 and verified from the contracts before launch: hidden fixture
`68cea033`, writer system prompt `15eecf86`, reader system prompt `8b8fe349`, and
both arm tool digests. Five of the seven pinned package files are identical across
W4, W4R, and W4C. Two are not: `extensions/lib/schema.ts` and `extensions/lib/tool.ts`
sit at `c4abd9a2` and `c4299092` here, which is W4R's state, not W4's `e28704dd` and
`5002b0a4`. That is the post-`b6dc366` state W4 itself drifted into partway through,
so W4C ran uniformly on bytes W4 ran on for 126 of its 160 sessions. This is a real
difference between W4 and W4C and it is not the arm order.

Arm order by lineage, declared in the instrument and asserted in the builder:
untreated first for `funicular_brakes`, `observatory_chiller`, `regatta_timing`,
`vineyard_netting`; treated first for `foundry_ladle`, `gravel_washplant`,
`mushroom_tunnel`, `salt_pan_rakes`.

## Endpoints

| arm | standing of 96 | median store bytes | writes | growth lines | median writer output | readers exact |
|---|---|---|---|---|---|---|
| A untreated | 85 | 22,086.0 | 206 | 0 | 3,442.0 | 16/16 |
| G treated | 71 | 12,455.5 | 207 | 126 | 2,468.0 | 15/16 |

Transcript pile median 7,881.5 in both arms, as in every capture on this fixture.
Both arms placed 40 of 40 governing and retained 40 of 40. Arm A made 2 no-op writes,
arm G none.

## Predictions scored

**1. The staleness contrast survives order reversal, in both subsets considered
separately. CONFIRMED, and the confirmation is thin.**

Untreated-first subset: 45/48 untreated against 33/48 treated, a gap of 12.
Treated-first subset: 40/48 untreated against 38/48 treated, a gap of 2.

The treated arm ends below the untreated arm in both subsets, which is what the
prediction asked. It is worth saying plainly that a gap of 2 of 48, in a subset that
contains one lineage moving the wrong way by 2, is not much of a survival.

**2. The two subsets show contrasts of roughly the same size. REFUTED.**

Minus 26.7 percent against minus 5.0 percent. Six-fold apart, same sign. The design
document's rule for this case was written in advance and is quoted here rather than
paraphrased: "If the A-first subset reproduces W4's gap while the G-first subset
shrinks it or reverses it, order is carrying part of the effect and the honest reading
is a mixture rather than a clean identification." That is the finding.

**3. Pooled staleness lands near W4's 88 and 51 of 96. REFUTED on the treated arm.**

Untreated 85 against W4's 88, which reproduces. Treated 71 against W4's 51, which does
not. The registered rule: a pooled result far from W4's in either arm "is evidence that
something other than order differs between the captures and needs finding before the
result is used." The section below is that search, and it does not find a sufficient
cause.

**4. Reader exactness does not regress. REFUTED, narrowly but in the direction that
matters.**

31 of 32 overall, the same total as W4, but the miss moved arms. W4 was 15/16 untreated
and 16/16 treated. W4C is 16/16 untreated and 15/16 treated. The treated miss is
`foundry_ladle`, ordinal 30, task kind `watch`, contamination tag
`confirmation_pre_flip_value`: the reader took the pre-flip confirmation value out of
the store and got both that slot and the decision wrong.

This is the programme's first reader harm from a treated store. Until now every
observed staleness harm came from a baseline arm, and "no reader regression" was a
line in the results documents, in the shipped package comment, and in the paper. It
is no longer true and must come out of all three.

**5. Store bytes stay directionally inconsistent. REFUTED, in the flattering
direction, which is the reason to distrust it.**

All 8 lineages ended smaller in the treated arm, against 6 of 8 in W4 and 5 of 8 in
W4R. Median 22,086.0 against 12,455.5, a fall of 43.6 percent, far larger than W4's
20 percent.

But the movement is in the untreated arm. Treated medians across the two captures on
this model are 12,707.5 and 12,455.5, two percent apart. Untreated medians are
15,905.0 and 22,086.0, thirty-nine percent apart. The byte contrast widened because
the baseline grew, not because the treatment did more. A result that improves because
the control moved is not an improvement.

## Where the difference from W4 actually sits

Per lineage, standing superseded values of 12, untreated then treated:

| lineage | W4C order | W4 | W4 delta | W4C | W4C delta |
|---|---|---|---|---|---|
| foundry_ladle | treated first | 11, 7 | -4 | 9, 8 | -1 |
| funicular_brakes | untreated first | 11, 9 | -2 | 10, 11 | +1 |
| gravel_washplant | treated first | 11, 9 | -2 | 12, 10 | -2 |
| mushroom_tunnel | treated first | 11, 4 | -7 | 12, 11 | -1 |
| observatory_chiller | untreated first | 12, 2 | -10 | 11, 1 | -10 |
| regatta_timing | untreated first | 11, 4 | -7 | 12, 10 | -2 |
| salt_pan_rakes | treated first | 10, 8 | -2 | 7, 9 | +2 |
| vineyard_netting | untreated first | 11, 8 | -3 | 12, 11 | -1 |
| pooled | | 88, 51 | -37 | 85, 71 | -14 |

W4: 8 of 8 lineages improved, deltas -10 to -2, median -3.5.
W4C: 6 of 8 improved, 2 worse, deltas -10 to +2, median -1.

The decisive comparison is the four lineages that ran in W4's own order. If the
shrinkage were an order effect it should not touch them. It does. Their deltas sum to
-22 in W4 and -12 in W4C, so the effect roughly halved with order held constant. The
four order-reversed lineages fell further, -15 to -2. Both subsets shrank; only part of
the shrinkage can be order.

One lineage reproduced exactly. `observatory_chiller` went -10 in W4 and -10 in W4C.
Every other lineage's response shrank or reversed. Removing that one lineage leaves
W4C's pooled contrast at -4 over seven lineages.

Decomposed as a 2x2 over arm and run position, four lineages per cell:

| | position 1 | position 2 | arm total |
|---|---|---|---|
| untreated | 45/48 | 40/48 | 85/96 |
| treated | 38/48 | 33/48 | 71/96 |
| position total | 83/96 | 73/96 | |

Arm accounts for -14, position for -10, interaction exactly 0. Read with care. Four
lineages per cell and one realization each cannot separate these with confidence, the
arm column is carried by a single lineage, and no monotone trend with ordinal supports
a wall-clock story. What the table does show is that a position term of the same order
of magnitude as the arm term is consistent with this capture, and that W4 and W4R,
which confounded the two, measured whatever sum they make.

## What this capture actually established

The largest source of variation on this instrument is between captures, not between
arms. Same model, same fixture, same prompts, same arm tools, two runs two days apart:
the untreated arm's median store moved 39 percent and the treated arm's standing count
moved from 51 to 71 of 96. That is larger than several of the per-lineage arm contrasts
the programme has reported as findings.

The programme has run one realization per cell with no exposed decoding seed since W1.
Every magnitude it has published rests on that. W4C is the first matched re-run of an
existing cell, and it says the design is under-powered for the magnitudes it reported.

Two things survive and should be stated as the result:

1. Direction. Across three captures on two models and 24 lineage pairs, the treated
   arm ended below the untreated arm in 20, tied in 2, and above in 2. That is a
   direction, and order reversal did not remove it.
2. Dose stability. The line fired after 126 of 207 treated writes here against 117 of
   198 in W4, 60.9 percent against 59.1 percent. The treatment was delivered at the
   same rate and produced a much weaker outcome, so the difference is in response, not
   in exposure.

What does not survive is the size. "From roughly nine in ten down to roughly one in
two" is a description of W4 and W4R. On the same model in a counterbalanced capture it
is nine in ten down to seven in ten.

## Consequences, and they are not optional

- The paper withdraws the pooled magnitude as an estimate and reports all three
  captures with their spread. The demoted fixed-order language stays; nothing here
  licenses promoting it.
- "No reader regression" comes out of the paper, the shipped package comment in
  `extensions/lib/tool.ts`, the gate comment in `tests/verify.mjs`, and the
  canon-bench arc table.
- The shipped behavior does not change. The direction is unchanged, the line costs one
  response line, and nothing here argues for removing it. What changes is what we claim
  for it.
- Any further magnitude claim from this programme needs replicate cells, which means a
  design change, not another single capture.

## Artifacts

`runs/20260822-w4c-model-001/` with `capture-manifest.json`, `grade-blind-report.json`,
`graded-report.json`, 160 session trees, and both arms' per-session stores.
`build/instrument/instrument-w4c.json` and `contract-w4c-one-run.json`.
Builder `w4c_build_instrument.py`. Fake preflight `runs/20260822-w4c-fake-001/`,
160 of 160 protocol valid at zero cost, graded perfect with `--expect-perfect`.
