# The write desk

The second instrument family in this repo, and the continuation of an argument
the first one left open.

The chains study (see the repo root) measured whether an agent respects a
constraint it was told once, sessions ago. Its forensic pass classified 14
recall misses by where each first went wrong and found 13 of them at the write
desk: 8 facts never captured into any tier, 5 captured and then overwritten by
a later rewrite, 1 judge error, and 0 lost at retrieval or surfacing. A store
that surfaces perfectly cannot surface what was never written down. That
result pointed somewhere specific and this programme went there.

Where the chains ask "does the agent honor what it learned", the write desk
asks "what does the agent leave behind, and is it still true later". The unit
is not a repository and a planted trap; it is a lineage of session records
whose facts are revised, reversed, and retired across sessions, written into a
real store by a real agent through the shipped tool, then read back by a fresh
agent whose answers are graded per slot against a hidden oracle.

## The arc

| stage | question | answer |
|---|---|---|
| W1 | can a rule be enforced at the tool boundary rather than judged by the model? | tool-enforced rules err at zero across five captures; model-judged rules err at 10 to 20 percent on near-rank precedence |
| W2 | do writers select the right facts and file them at the right address? | yes, 94/94 governing; but they narrate superseded values into articles in 63 of 64 stores, and prompt-side guidance moves noise without moving that habit |
| W3 | does the store's economy improve as history accumulates? | no. under shipped doctrine the store grows faster than the raw transcripts it distills (18.5KB against a 7.9KB pile at eight sessions) and staleness compounds linearly |
| W4 | can the tool's own voice at the write boundary change the habit the prompt could not? | yes. one sentence naming body growth cut standing superseded values by 42 percent, 88/96 against 51/96, and shrank the median store by a fifth with no reader regression |
| W4R | does that hold on a second model? | the staleness effect replicates almost exactly (87/96 against 45/96) and the byte savings do not, which separates the mechanism from its side effect: narration and verbosity are independent |

W4's intervention shipped in the package as a result of this measurement
(pi-canon commit `e1312e6`), and W4's baseline arm produced the programme's
first observed staleness harm: a reader that pulled a reversed policy out of a
narrated store and made the wrong decision.

## What is here

Each stage carries its design document, written and frozen before the build,
and its results document. W3 and W4 registered predictions in those documents
before any model ran, including the ones that turned out wrong: W3's central
prediction (that accumulation would favor the store on cost) is refuted in
W3's own results. W1J and W2 froze their metrics but not their predictions,
and W4R reused W4's predictions without a design document of its own. Read
the preregistration claim as covering two of the five stages, not all of
them.

- `W1-RESULTS.md`, the consolidated W1e through W1j record
- `W2-DESIGN-001.md` and `W2-RESULTS-001.md`, write selection and placement
- `W3-DESIGN-001.md` and `W3-RESULTS-001.md`, accumulation
- `W4-DESIGN-001.md` and `W4-RESULTS-001.md`, the growth line
- `W4R-RESULTS-001.md`, the growth line replicated on the second subject model
  over a byte-identical instrument

## Protocol

Every capture ran sequentially in a bubblewrap sandbox with a fresh home,
temp, and work tree per session, against a digest-pinned contract naming the
package bytes, the harness sources, the Pi executable, the model, the
timeouts, and an exact decimal cost ceiling. Runs are one-run-only: no
retries, no replacements, no selective reruns, no resume. Grading is a
separate step that opens the hidden fixture only after the structural capture
closes, so the harness itself never sees an answer. Before any paid capture,
the full assignment set runs through a no-model fake driver with perfect-actor
answers injected on stdin, exercising the real shipped tool and Pi's real
schema validator, and that preflight must grade perfect.

Captures that produce no data are recorded rather than deleted, and do not
count as retries of anything: two predecessors of the replication were stopped
early, one once the second model's metering was measured and one after a
transient provider stall, and both carry an ABORTED.md stating why.

Two disclosures are carried in the results documents rather than buried: the
W4 capture ran while a concurrent commit touched two contract-pinned files
(the drift is demonstrated inert, and the harness now snapshots the package at
launch so it cannot recur), and a false-positive in the staleness metric,
where the store's own `updated:` date could be read as a value token, was
found by a later preflight and fixed. The published W3 and W4 numbers were
re-graded with the corrected metric and are unchanged.

## Artifacts

Per-session transcripts, per-rung store snapshots, and session manifests run
to roughly 220MB across the captures and are too large for git. They follow
the pattern the chains study set and ship with a Zenodo deposit; the results
documents carry the numbers, the manifests carry the provenance.
