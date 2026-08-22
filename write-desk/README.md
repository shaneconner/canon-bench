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
| W4 | can the tool's own voice at the write boundary change the habit the prompt could not? | yes on this capture. a recurring line naming body growth, which fired after 117 of the 198 treated writes, went with standing superseded values 42 percent lower, 88/96 against 51/96, and a median store a fifth smaller. Read the size against W4C below, which did not reproduce it |
| W4R | does that hold on a second model? | the staleness contrast recurs at almost the same size (87/96 against 45/96) and the byte savings do not. Read that as the two outcomes coming apart, not as independence: verbosity is confounded with model identity here, so the two captures cannot separate either one from the other |
| W4C | does it survive reversing the arm order? | the direction does and the size does not. Counterbalanced on the first model, 85/96 against 71/96, where the same model in fixed order gave 88/96 against 51/96. One lineage supplies 10 of the 14. Four of five registered predictions failed. With one run per cell nothing here can rank the sources of variation; what it shows is that a partially matched repeat moved enough to remove most of the original size |

W4's intervention shipped in the package as a result of this measurement
(pi-canon commit `e1312e6`), and W4's baseline arm produced the programme's
first observed staleness harm: a reader that pulled a reversed policy out of a
narrated store and made the wrong decision. W4C produced the second, from a
TREATED store, on the same lineage and the same task. Two harms in 96 reader
sessions, one from each arm. Nothing here supports "no reader regression" as a
statement about the intervention, and that phrase has been removed from the
package and the paper.

## What is here

Each stage carries its design document and its results document. W3 and W4
registered predictions before any model ran, including the ones that turned out
wrong: W3's central prediction (that accumulation would favor the store on cost)
is refuted in W3's own results. W4C registered five predictions and a reading
rule after its capture had launched but before any grading, which is weaker and
is recorded as weaker in its own design document; four of the five failed and
all four are reported. W1J and W2 froze their metrics but not their predictions,
and W4R reused W4's predictions without a design document of its own. Read the
preregistration claim as covering three of the six stages at two different
strengths, not all of them.

- `W1-RESULTS.md`, the consolidated W1e through W1j record
- `W2-DESIGN-001.md` and `W2-RESULTS-001.md`, write selection and placement
- `W3-DESIGN-001.md` and `W3-RESULTS-001.md`, accumulation
- `W4-DESIGN-001.md` and `W4-RESULTS-001.md`, the growth line
- `W4R-RESULTS-001.md`, the growth line repeated on the second subject model
  over a byte-identical instrument
- `W4C-DESIGN-001.md` and `W4C-RESULTS-001.md`, the counterbalanced capture that
  took the magnitude back. The design document says plainly that its predictions
  were registered after launch and before grading, which is weaker than W3's and
  W4's pre-build registration, and it committed in advance to reporting the
  capture whichever way it came back. It came back the wrong way and is reported
- `RANKING-RESULTS.md`, the offline retrieval benchmark on two real stores that
  tested the retrieval explanation directly
- `data/per-lineage-endpoints.csv`, 80 rows covering all three controlled
  captures and the accumulation study: capture, model, arm, lineage, depth,
  superseded values standing, superseded values available, store bytes,
  transcript pile bytes, article count, journal count. Every per-lineage figure
  and every direction count in the paper recomputes from this file.
- `data/figure-data.js`, every plotted series in the paper, including the six
  staleness trajectories and the eight paired endpoints per capture, so a reader
  can check the charts against the numbers without reading dots off an axis
- `provenance/`, the artifacts every source-level claim in the paper rests on,
  with a SHA-256 manifest and scripts that check the claims rather than restate
  them. `regenerate.py` rebuilds the two data files above from the graded
  reports, the fixture generators, and the frozen retrieval scores, and diffs
  them against the published copies; all twenty-six of its checks pass.
  `drift-sweep.py` reproduces the drift audit. `verify-session-counts.py`
  recounts every capture and separates what it verified from what it could only
  take on the paper's word. `rehearsal-growth-lines.py` resolves every rehearsal
  firing to the write that produced it. `retrieval/` freezes the ranking harness,
  which used to read live stores. Start at `provenance/README.md`.

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

## Errata

The results documents are frozen at the moment they were written and are not
edited after the fact, because they are the record. Corrections are noted here
instead.

**W4R-RESULTS-001.md, "the only variable against W4 is the model".** That sentence
is false, and W4-RESULTS-001.md's own integrity disclosure is what disproves it.
The first capture ran 126 of its 160 sessions against package files a concurrent
commit had changed, and the second ran under the launch-snapshot discipline that
was introduced afterwards. Model is the only variable the two captures were
*designed* to differ on. It is not the only one they did differ on. The drift is
demonstrably inert for what was measured, and `provenance/drift-sweep.py`
reproduces that audit with a positive control, but inert is not identical. The
paper drawn from this programme says the two contrasts came from the same
generated histories and the same nominal arm definitions, and that the executions
were not byte-identical.

**Claims in the frozen documents that the final synthesis supersedes.** The
results documents are the record and are not edited, so the superseded claims
are listed here rather than removed there. Read the paper's wording as current
wherever the two differ.

- W4 and W4R describe the staleness contrast as an effect and as halving, and
  W4R adds "narration and verbosity are independent". The counterbalanced
  capture did not reproduce the size, so the direction stands and the magnitude
  does not, and the two outcomes come apart differently in each of the three
  captures rather than being shown independent.
- W4's "the tool's voice suppressed the narration itself" reads equal journal
  counts as evidence of mechanism. Equal journal counts rule out one relocation
  route. The paper does not identify the mechanism and says so.
- W4C's "the largest source of variation is between captures, not between arms"
  is withdrawn. One realization per cell estimates no variance, and the
  comparison is not even uniformly in that direction: W4's own arm contrast of
  37 counts exceeds the 20-count movement of the treated arm between captures.
- W4C's dose paragraph concludes that "the difference is in response, not in
  exposure". Firing count is post-treatment, not an assigned dose: the line
  appears only after a writer chooses a growing rewrite, and it may change how
  often and how large those rewrites are. Similar firing proportions rule out
  the treated arm simply not seeing the line, and establish nothing about
  equivalent timing or informational content.
- W4C's two-by-two decomposition over arm and position is cut from the paper.
  Every lineage takes both arms and four fixed lineages take each sequence, so
  it is a two-period crossover whose terms separate only under a no-carryover
  assumption that one run per cell cannot check, and sequence was assigned by
  lineage order rather than at random.

**RANKING-RESULTS.md, "Same harness, same 506 queries".** The harness is the
same and the stores and queries are not. `r1_embed.mjs` reads two live project
stores at their paths rather than a frozen corpus, and it derives the eligible
query set when it runs, so both the corpus and the query population move as the
projects are used. They did move: six of the eight BM25 cells differ between the
decomposition run and the embedding rerun, by up to 0.008, and the query totals
differ by two, 400 plus 104 against the 506 the later section quotes. Both stores
have grown again since, `quorum` from 742 articles and 1,402 journal entries to
744 and 1,411, and `pi-fold` from 56 and 136 to 58 and 166, so neither run
reproduces today. What the embedding result rests on is unaffected, because both
rankers scored one corpus state inside a single execution; what does not survive
is reading the two runs as a replication of each other. The script's header
carried the same error and also named the wrong embedding model, and both are
corrected in place because it is code rather than a frozen record. The paper
drawn from this programme states the mutability, the observed spread, and that
freezing an immutable export is the fix and is not done.

**W4-RESULTS-001.md, "the perfect-actor preflight fired 30 times from
digit-length variance alone".** The count is right and the cause is wrong. The
preflight fires the growth line 38 times across arm G's 136 writes, identically
in all four rehearsals. Eight of those are the fixture exercising the line on
purpose: the injected body appends "Rehearsal note, deliberately grown: this
sentence exists to exercise the growth voice", worth 87 bytes each. The
remaining 30 are the number this sentence means. None of them is a digit-length
change. They are correct rewrites whose replacement wording is longer than what
it replaced: "standard" becoming "aggressive" for two bytes, "standard"
becoming "conservative" for four, a two-person confirmation rule replaced by a
single-operator rule for fourteen, and a consumer statement replaced by a
decommissioning statement for twenty-seven. The point the sentence was making
survives, and is if anything stronger: fire count is not a narration proxy,
because the writes that fired here were correct. Recount with
`provenance/rehearsal-growth-lines.py`. The paper drawn from this programme
carries the corrected breakdown and cause.

**W1-RESULTS.md, the 67-cell count.** Finding 3 reads "The tiebreak variants
R3/R4 were flawless in every arm (0 misses in 67 conditional cells)". The count
is wrong, and the document's own table disproves it. R3 plus R4 gives 15+12=27
in arm A and 13+12=25 in arm B, so 52 across the two model-judged arms, and
another 16+15=31 in the guarded arm C for 83 across all three. No scope in the
table produces 67. The finding itself stands: zero misses on those variants,
whichever denominator you take. Only the count is wrong. The paper drawn from
this programme reports 52, scoped to the two model-judged arms.

## Artifacts

Per-session transcripts, per-rung store snapshots, and session manifests run
to roughly 220MB across the captures and are too large for git. They follow
the pattern the chains study set and ship with a Zenodo deposit; the results
documents carry the numbers, the manifests carry the provenance.
