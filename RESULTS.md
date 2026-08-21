# The chains study: results

The full results writeup for the five-chain trap-avoidance study, relocated
here from the pi-canon package README on 2026-08-21. It lives in this repo
because it is bench content: methodology, arm tables, and limitations that
belong beside the instrument that produced them rather than in a package
README that has to be re-edited every time a capture lands. The package keeps
a short pointer to it.

The instrument is described in this repo's README. The write-side programme
that continues from Finding "the result that changed the roadmap" below lives
in `write-desk/`.

## The run

The population comes before the numbers: five author-built chains, development-exposed and reused by the confirmatory run, four eligible trap designs, each repeated five times, one worker model, under a protocol frozen with a hash manifest before that run.

The unit is a cell: a fresh worktree holding a small fictional repository, run through four sessions that share it. A plant session does ordinary work whose natural course surfaces a constraint, never phrased as an instruction to remember. A distractor session comes in between. A probe session then gets a task whose obvious solution violates that constraint in a way that compiles, runs, and fails a grader the agent never sees. A recall session answers an auditor afterwards, one judge call per fact.

Four arms run every cell. `canon` is stock Pi plus this package at 0.1.0, the build the study measured. `canondoc` is canon plus a static doctrine file beside it. `agents.md` is a self-maintained convention file preloaded with 99 lines of mature-project noise. `bare` loads no memory extension, and it is a stronger floor than the name suggests: prior-session transcripts land in its worktree before the recall session and its agent is on record reading them, so it is a no-extension floor at probe time and a transcript baseline at recall.

| arm | trap cells (of 20) | all checks (of 110) | plant-only recall (of 45) | median recall tokens | total chain cost |
|---|---|---|---|---|---|
| canon | 19 | 109 | 41 | 20,775 | $0.5454 |
| agents.md | 18 | 107 | 42 | 64,568 | $0.6227 |
| canondoc | 16 | 105 | 40 | 13,991 | $0.4639 |
| bare | 8 | 85 | 40 | 61,006 | $0.5345 |

![Every eligible probe cell as a square, four trap designs by five repetitions, per arm](https://raw.githubusercontent.com/shaneconner/canon-bench/main/assets/fig-trap.png)

*One square per eligible probe cell: four trap designs across, five repetitions within each, one row per arm. Every consumer-contract cell is a loss for bare. canon loses one cell in the whole grid, chain 04 repetition 1, which is the design that costs every arm at least one.*

Read the unconditioned column beside the headline one. The trap metric is conditioned on the floor arm's cold failures, which is the strongest objection to it, so the unconditioned count scores all 110 intended checks whether or not a cold worker had already failed them, and the ordering survives. That count is check-level rather than an unconditioned version of the cell metric, and it was computed after the run rather than frozen with the protocol. Read the 18 before the 8: a self-maintained convention file, deliberately burdened with 99 lines of noise, finished one repeated cell behind the package, and quoting the gap against the floor without that number would be managing the reader rather than informing them.

Recall is a wash and has to be reported as one. Plant-only recall, 45 judged facts per arm: agents.md 42, canon 41, canondoc 40, bare 40. One fact flagged as paraphrase-sensitive before the freeze carries 9 of the 17 misses across arms, and striking it leaves canon level with bare. An ordering that moves when one judged item is removed is not an ordering.

Where the arms separate is the price of the answer. Median recall session tokens ran canondoc 13,991, canon 20,775, bare 61,006, agents.md 64,568, so canon answers at 0.34x bare's median. That does not make it the cheapest arm end to end. Total chain cost ran canondoc $0.4639, bare $0.5345, canon $0.5454, agents.md $0.6227, so canon is not the cheapest arm overall, and canondoc is lowest on both metered measures while passing three fewer trap cells. Every dollar figure is metered worker-session cost at that day's rates; the judge calls sit outside all of them, in equal number per arm. A package-level study offers no account of why.

The result that changed the roadmap is not in that run at all. A forensic pass over a development run classified 14 recall misses by where each first went wrong.

![Fourteen misses classified by first failure point, thirteen of them at the write desk](https://raw.githubusercontent.com/shaneconner/canon-bench/main/assets/fig-writedesk.png)

*The 14 recall misses from a development run, each placed at the point it first went wrong: 8 never captured into any tier, 5 captured and then overwritten by a later rewrite, 1 judge error, and 0 lost at retrieval or surfacing.*

That is development evidence over two arms of one run and it carries no confirmatory weight, but 13 of 14 is not a close call and it points somewhere specific. None of the misses was a fact sitting in the store that recall failed to reach, which is the failure a retrieval-shaped design would predict. A store that surfaces perfectly cannot surface what was never written down, so on this evidence the open problem is write-side fidelity rather than recall coverage: the hard moment is when an agent has just learned something, is mid-task, and has a live prompt in front of it asking for something else. The constraint guard is a first answer to the rewrite half of that, and an incomplete one.

### What the run does not establish

- The five chains are development-exposed. The product changed in response to failures on these same chains, and the confirmatory run reuses them, so the freeze confirms disciplined execution rather than generalization to unseen tasks.
- The result is package-level. It attributes nothing to the journal, the spine, or surfacing separately. A later development probe tried to: a sham arm carrying this package's exact tool schema and orientation line with an inert implementation, so the surface is present and no memory work happens behind it. On one chain at 15 repetitions, first-pass correctness ran bare 12/15, canon 8/15, sham 7/15. canon and sham are indistinguishable (Fisher exact, p=1.0000) and neither separates from bare at that size (p=0.25 and p=0.13). Fifteen repetitions cannot establish equivalence, so read it as the absence of a signal rather than the presence of a null. What it does say is that any account of this package's costs has to start with the tool surface, because nothing behind the surface has yet been shown to contribute to them.
- No evaluated arm is a search-driven LLM wiki, so nothing here is a comparison against one.
- The `agents.md` arm is one construct, a self-maintained file under author-designed preload noise, with no clean-file or human-maintained counterpart run beside it.
- Eligibility is model-relative. A check counts as a trap only where a cold run of the worker failed it, so every number built on it moves when the worker does.
- One author wrote the package, the chains, the traps, and the graders.
- Five repetitions of one trap design are five looks at one design, so no uncertainty interval is attached to any pooled count.
