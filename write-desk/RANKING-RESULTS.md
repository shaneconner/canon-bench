# R1: known-item retrieval on real stores (2026-08-20)

The first measured verdict on recall by relevance. No model, no synthetic corpus:
the journal is a labeled query set nobody had to write, because every entry names
the articles it concerns. Query = the entry's text, ground truth = its subject
articles, corpus = the exact surface the tool's search ranks (all articles plus
all other journal entries as distractors, the query entry excluded from results).

Stores: quorum (742 articles, 1,402 journal entries, 400 sampled queries) and
pi-fold (56 articles, 136 entries, 104 queries); the other ten stores were below
the 10-article / 20-query floor. Query variants: `full` (whole entry body, the
generous ceiling since articles are often updated from the same events and share
vocabulary), `first` (first sentence), `terse` (six salient words, the closest
simulation of what an agent actually types). Metrics: recall@10 against the
visible window, MRR over the best-ranked subject.

## Finding 1: the knobs are a null result

The shipped LexicalRetriever is BM25 (K1 1.5, B 0.75) with two hard-coded
choices: MIN_TOKEN 4 and no field weighting. Variants probing both (minimum
token length 2, 3x path+capsule weight, both) landed within noise of shipped on
every store and every query variant (recall@10 deltas of -0.01 to +0.05, no
direction). Tuning BM25 is a dead end; whatever gap exists is not parametric.

## Finding 2: journal crowding was the big recoverable loss

Decomposition (shipped ranker):

| store / variant | combined top-10 | article-only corpus @10 | any subject-sharing doc @10 |
|---|---|---|---|
| quorum full | 0.563 | 0.690 | 0.858 |
| quorum terse | 0.280 | 0.440 | 0.663 |
| pi-fold full | 0.558 | 0.827 | 0.990 |
| pi-fold terse | 0.250 | 0.625 | 0.904 |

When the governing article missed the window, it usually lost to journal entries
about the same subject: same vocabulary, said more often, in shorter documents.
The window still delivered the knowledge as events most of the time (any-doc
column), which degrades the reader to history instead of current truth.

## Finding 3 (shipped): guarantee articles half the window

The fix is mechanical, not a ranking change: one scoring pass, but articles fill
up to five of the ten slots, journal entries the rest, and a short side cedes its
slots. Measured with the shipped quota logic verbatim:

| store / variant | combined | split surface | gain |
|---|---|---|---|
| quorum full | 0.563 | 0.628 | +6.5 pts |
| quorum terse | 0.280 | 0.365 | +8.5 pts |
| pi-fold full | 0.558 | 0.663 | +10.5 pts |
| pi-fold terse | 0.250 | 0.375 | +12.5 pts |

Never worse on any cell: the displaced journal entries were same-event
duplicates. Landed in tool.ts search() with gate 168; this is one more instance
of the W1 design lesson (the mechanical rule beat the tuning).

## Finding 4: the residual is semantic, and it prices the next step

Even against articles alone, terse queries find the right article only 44% of
the time on the 742-article store. That ceiling is not reachable by lexical
means (finding 1), so the honest options are: accept it (search is a fallback
channel; address-based touch surfacing remains the primary path), or measure
whether embeddings clear it. An embedding known-item rerun on this same harness
is cheap (one pass over ~2,900 documents; the queries are already built). That
is the only ranking experiment left worth running, and it should precede any
thought of enabling ambient retrieval, which would inherit whatever ceiling
search has.

## Postscript (2026-08-20, later the same day)

Shane took the crowding finding one step further than the split: the journal is
now OPT-IN for search (`journal: true`), because events are history and history
in the default window is bloat. The default surface is therefore the
article-only condition above (quorum terse 0.44, full 0.69; pi-fold terse
0.625, full 0.827), the best article-recall condition this study measured, and
a default search no longer reads any journal body, which also retires the
search half of the scale ladder's journal-cost watch item for the common path.
The split survives inside the opt-in: articles keep half the window when the
journal is included. Gate 168 covers both.

## The embedding rerun (2026-08-20, later still): BM25 wins every cell

Same harness, same 506 queries, ranker swapped for cosine over local Ollama
embeddings (nomic-embed-text, 137M, the canon-atlas default; qwen3-embedding:8b
was tried first and is infeasible on the 6GB GTX 1660 with long documents).
Documents truncated to 3,500 chars for the model's short context.

| store / variant | BM25 art-only@10 | embed art-only@10 | BM25 mixed@10 | embed mixed@10 |
|---|---|---|---|---|
| quorum full | **0.688** | 0.413 | **0.558** | 0.203 |
| quorum terse | **0.440** | 0.233 | **0.280** | 0.118 |
| pi-fold full | **0.830** | 0.642 | **0.566** | 0.387 |
| pi-fold terse | **0.632** | 0.519 | **0.255** | 0.160 |

Lexical wins all sixteen comparisons, by 11 to 36 points. Two observations:

1. Journal crowding hits embeddings HARDER (the mixed columns): same-event
   entries are semantically near-identical to their article, so cosine ranks
   them above it even more aggressively than term overlap does. The
   journal-opt-in default is vindicated from a second direction.
2. Caveats, stated plainly: known-item queries mined from journals share
   vocabulary with their targets, which structurally favors lexical matching,
   and a 137M embedder is the floor of the class, not the ceiling. The terse
   variant strips most shared phrasing and lexical still wins by 20 points on
   the big store. A hosted large embedder remains untested; the shipped
   `retrieval` interface accepts a custom scorer if anyone brings one.

The queued ranking experiment is now run. Verdict: the shipped BM25 stays,
measured against tuning (null), against journal crowding (fixed mechanically),
and against local embeddings (worse on every cell).

## Standing verdict on recall by relevance

Off-by-default survives its first measurement: at realistic query lengths,
lexical relevance finds the governing article a quarter to a third of the time
on a real store. Nothing here justifies ambient relevance surfacing; the split
window makes agent-solicited search meaningfully better today.

Reproduce: `node lab/ranking/r1_known_item.mjs 400` and
`node lab/ranking/r1_decompose.mjs 400`.
