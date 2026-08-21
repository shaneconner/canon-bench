# W4R-RESULTS-001: the growth line replicates on a second model (2026-08-21)

One capture, 20260821-w4r-model-003: 160 sessions (128 writers, 32 readers),
sequential, grade-blind, **gpt-5.6-sol** thinking high, bwrap strict sandbox,
contract w4r-one-model-run-001, ceiling 15.00000000, one run only. Reported
cost $10.19082600000000039200. 160/160 attempted, 160/160 protocol-valid, the
second consecutive capture with zero invalid and zero recovery sessions.

The instrument is byte-identical to W4's (instrument sha
66832125d366f1b32a76ec6f5e9ed6d2bf16e639226937b8ee88f0c300d203e2, asserted at
build time): the same eight lineages, the same eight-session histories, the
same tasks and task ids. The two arms are the same two explicit pinned files,
the shipped tool at `e1312e6` and its parent `b6dc366`, differing only in the
growth-line block. The only variable against W4 is the model.

## Predictions, registered in W4-DESIGN-001 before the result

1. The direction reproduces. **CONFIRMED.**
2. The baseline arm narrates heavily, above 70 percent standing. **CONFIRMED**
   at 91 percent.
3. No reader regression in the growth-line arm. **CONFIRMED**, 32 of 32 both
   arms.

## The headline replicates almost exactly

| metric | luna baseline | luna growth line | sol baseline | sol growth line |
|---|---|---|---|---|
| standing superseded values | 88/96 | 51/96 | 87/96 | 45/96 |
| readers exact | 15/16 | 16/16 | 16/16 | 16/16 |
| journal entries | 65 | 64 | 64 | 64 |

Two different models, run a day apart on identical histories, land within one
value of each other on both arms: 92 percent standing versus 91 percent
without the line, 53 percent versus 47 percent with it. The staleness
trajectory replicates as a slope too, roughly eleven new standing stale values
per session in the baseline arm against roughly six with the line, in both
models, with no saturation in either:

```
sol baseline   0  11  25  36  52  63  79  87
sol growth     0   8  18  19  23  32  42  45
```

Journal counts stay equal across arms in both models, so the finding that the
voice suppresses narration rather than relocating it into the journal
replicates as well.

## What did NOT replicate, and why it matters

The size and token savings did not carry over:

| metric | luna baseline | luna growth line | sol baseline | sol growth line |
|---|---|---|---|---|
| median final store bytes | 15,905 | 12,708 (-20%) | 10,575 | 10,261 (-3%) |
| median writer output tokens | 2,894 | 2,384 (-18%) | 1,199 | 1,225 (+2%) |
| total writes | 194 | 198 | 148 | 184 |

Sol is a far terser writer: half the output tokens and a third smaller stores
before any intervention. Its baseline store sits at 1.34x the transcript pile
where luna's sat at 2.0x, so there was much less bloat available to remove.

That difference is the most useful thing this capture produced, because it
separates two effects that were confounded in W4:

**Narration and verbosity are independent.** Sol writes half as much prose as
luna and carries the same proportion of superseded values into its articles
(91 percent against 92 percent). A terse writer is not a current-state writer.
The growth line then halves staleness in both, while shrinking bytes only in
the model that had bytes to spare.

So the size reduction reported in W4 was a side effect, and the staleness
reduction is the effect. That is a stronger claim than the one W4 could make
alone: the mechanism is not "the tool nags and the model writes less", it is
"the tool names growth and the model stops smuggling history into current
state". Under sol the line fired 99 times across 184 writes and produced MORE
writes than the baseline arm, not fewer, which fits that reading: writers
respond with more targeted rewrites rather than with restraint.

## Other observations

- The W3 finding that the store outgrows the transcript pile it distills
  holds in direction under sol but is much weaker in magnitude, 1.34x against
  luna's 2.0x at eight sessions. Store bloat is model-dependent; narration is
  not.
- Reader input fell from luna's ~4,300 to sol's ~2,460 median tokens, tracking
  the smaller stores, with identical accuracy.
- Zero contaminated reader misses in either sol arm. W4's single baseline-arm
  harm (a reversed policy read out of a narrated store) did not recur here,
  so that remains one observed harm in 32 luna reader cells and none in 32 sol
  cells. Narrated stores are demonstrably hazardous, but the hazard rate at
  eight sessions is low and this capture does not pin it down.

## Cost and discipline

$10.19 of a 15.00000000 ceiling. Sol meters roughly 15x luna for identical
work while using fewer tokens, which is a price difference and not a behavior
difference; the ceiling was sized to sol rather than the experiment shrunk to
fit a luna-sized ceiling, at Shane's direction.

Two aborted predecessors are preserved beside this run and entered no result:
20260821-w4r-model-001, stopped at two sessions once sol's metering was
measured, and 20260821-w4r-model-002, stopped at one session after a transient
provider stall produced an empty session. Both carry ABORTED.md.

The staleness metric used here carries the fix found by this capture's own
preflight: the store's `updated:` date could previously be read as a value
token by bounded containment, which would have false-positived on any run
whose date fragment matched a superseded value. W3 and W4 were re-graded with
the corrected metric and every published number reproduced exactly.

## Standing conclusion

The growth line is now measured on two models over identical histories. Its
staleness effect replicates closely and its economy effect does not, and the
honest statement of what shipped is: a mechanical observation at the write
boundary halves the narration habit across both subject models, and may or may
not shrink the store depending on how verbose the writer was to begin with.
