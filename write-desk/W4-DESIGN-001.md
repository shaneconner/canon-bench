# W4-DESIGN-001: the tool's own voice against narration (pre-build)

Status: DESIGN, registered before any build. Follows Shane's go on the
W4-shaped question (2026-08-20): move forward with structural pressure for
current-only articles. The lighter candidate is tried first, and it is NOT
shipped first: W4 measures a lab-patched tool variant against the shipped
baseline in one capture, and the winner ships with its gate afterward or the
route is closed like prompting (W2) and phrase-lint (built and rejected).

## The question

W3 priced narration: ~2.2KB of permanent store growth and ~11 standing stale
values per session, compounding linearly, because writers rewrite articles
LARGER every session. W2 showed the system prompt's voice does not change
this habit. W1 showed the tool's enforced rules err at zero and W1j showed
mere presence of a tool-side check deters. The open question is the middle
ground: does the TOOL'S OWN VOICE at the write boundary, informational and
mechanical, change the rewrite habit where the prompt's voice did not?

## The variant

One patched block in tool.ts (lab kit only): when a write REPLACES an
existing article and the new body is larger than the prior body, the success
text carries one extra sentence naming the growth in bytes and restating the
doctrine split: body grew from X to Y bytes; keep the article current-state,
the journal carries history. No option, no threshold, no phrase detection;
fires on any rewrite growth. Calibration constants, if the effect is real,
are a shipping decision made after measurement, with the gate.

## Shape

Fresh fixture, new seed, K=8 only: W3 already measured the reader crossover
and the K ladder; W4's question is writer behavior, and the per-session store
snapshots inside a K=8 lineage carry the whole growth trajectory. 8 domains x
1 lineage x 2 arms, both arms in ONE capture (no cross-capture baselines):

- Arm A: shipped tool verbatim at the pinned package commit.
- Arm G: identical except the patched tool.ts in the kit; writers and readers
  both get the patched kit for arm purity (the growth line fires only on
  writes, so readers are unaffected by construction).

Writers 8 sessions x 8 lineages x 2 arms = 128; readers 2 per lineage per arm
on the final store = 32; total 160 sessions. Estimated ~0.85 at W3 prices
(writers dominated W3 at $0.0059 median). Ceiling 1.50000000, one run, zero
retries, grade-blind, bwrap strict, same model and thinking as W1-W3.

## Frozen metrics

Per arm: staleness trajectory across s=1..8 (superseded-as-of-s tokens
standing in store-s articles) and final staleness; final store bytes vs the
7.9KB-median transcript pile; writer output tokens by session index; write
counts; reader exactness as the regression check; growth-line fire count per
arm G session (from transcripts).

## Predictions registered before the build

1. Arm G final staleness lands below arm A's (W3 arm A measured 82/95 at
   K=8). Direction predicted, magnitude honestly unknown; the W2 guidance
   analogue moved staleness by one cell only, and this is the same
   intervention in a different voice. A null here is a real result: it kills
   the nudge route entirely and leaves typed state as the only standing
   candidate.
2. Arm G final store bytes land below arm A's (W3: 18.5KB median).
3. Reader exactness does not regress in arm G (16/16 both arms expected;
   W3 arm A readers were 64/64 against heavily narrated stores, so tighter
   articles have no mechanism to hurt at this scale).
4. The growth line fires in most arm G writer sessions s>=2 (the fixture
   revises values every session; a perfect current-state writer would fire
   it rarely, so fire rate is itself a narration proxy).

## Ship rule

If predictions 1 and 2 hold with any material margin and 3 holds, the growth
line ships in the package with calibration constants and its gate, and the
W4 results record the measured justification. If 1 fails, the route closes
and the typed current-state arc is the remaining candidate, now with two
dead ends (prompt voice, tool voice) priced behind it.

Build follows the W3 pattern: generator, instrument, fake preflight to
perfection (including a rehearsal asserting the growth line's exact text),
then the one capture under the standing rule.
