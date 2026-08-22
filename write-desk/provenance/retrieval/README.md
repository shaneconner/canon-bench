# The retrieval benchmark, frozen

The offline known-item benchmark in this programme measured two real project
stores. It read them at their paths and derived its query set when it ran, so
both the corpus and the query population moved as the projects were used. That
is a reproducibility defect and it was found by external review rather than by
us. This directory is the repair and the measurement of what the defect cost.

## The first repair had a defect of its own

The first version of `r1_freeze.mjs` wrote one string per document and
`r1_frozen_score.mjs` handed that string to both rankers. The live harness never
did that. It truncates at 3,500 characters only the text it sends to the
embedding model, whose context is short, and it indexes the lexical ranker on
whole documents. Since 46.7 percent of `quorum` documents and 38.4 percent of
`pi-fold` documents exceed the cap, the first frozen run scored BM25 over a
corpus missing 34.2 and 30.6 percent of its characters.

That is worse than the drift the freezing was built to remove. It was found by
external review, as the original defect was. The export now carries `text` and
`embed_text` per document, the scorer indexes lexical on the first and embeds the
second, and it refuses to run against an export that lacks `embed_text`.

Pricing the defect takes ONE corpus, not two. Re-freezing also added two
documents, so differencing the old export against the new one mixes the
truncation with the corpus change, and the first version of this section did
exactly that. The scorer now emits a third arm: BM25 over the truncated strings,
scored on the same export and in the same execution as BM25 over whole
documents. The embedding arm cannot move between the two, because the change is
confined to the lexical index.

| store / variant / surface | BM25 truncated | BM25 corrected | change |
|---|---|---|---|
| quorum full art-only | 0.593 | 0.690 | +9.7 |
| quorum full mixed | 0.425 | 0.565 | +14.0 |
| quorum terse art-only | 0.378 | 0.443 | +6.5 |
| quorum terse mixed | 0.243 | 0.300 | +5.7 |
| pi-fold full art-only | 0.797 | 0.842 | +4.5 |
| pi-fold full mixed | 0.481 | 0.564 | +8.3 |
| pi-fold terse art-only | 0.564 | 0.677 | +11.3 |
| pi-fold terse mixed | 0.233 | 0.308 | +7.5 |

That ablation reproduces the cross-export figure exactly, cell for cell, which
also says the two added documents changed nothing measurable here. The numbers
stand; what changed is that they are now one controlled difference.

## What the drift cost, measured against the corrected run

Only one of the two stores supports the comparison. `quorum` is sampled as a
chronological prefix, the first 400 eligible entries, and the last of them is
dated 2026-08-05, two weeks before the earliest of the three runs. Two freezes
taken three days apart produced a byte-identical query list, which is evidence
that the prefix holds still rather than a guarantee: the live runs did not record
their query sets, so no digest match is possible against them. `pi-fold` is not
capped and takes every eligible entry, so its query population grew from 104 to
106 to 133 across the three runs and its four cells compare different
populations of queries. They are not differenced here.

| store / variant / surface | BM25 live rerun | BM25 frozen | change | embed live | embed frozen | change |
|---|---|---|---|---|---|---|
| quorum full art-only | 0.688 | 0.690 | +0.2 | 0.413 | 0.415 | +0.2 |
| quorum full mixed | 0.558 | 0.565 | +0.7 | 0.203 | 0.195 | -0.8 |
| quorum terse art-only | 0.440 | 0.443 | +0.3 | 0.233 | 0.245 | +1.2 |
| quorum terse mixed | 0.280 | 0.300 | +2.0 | 0.118 | 0.118 | 0.0 |

Across the store whose query set holds still, freezing moved lexical recall by
at most 2.0 points and embedding recall by at most 1.2. The earlier measurement
reproduced. An earlier version of this file reported BM25 falling in eight of
eight cells by 2.2 to 13.3 points; that fall was the truncation defect above and
the claim is withdrawn.

The stores did grow between the decomposition run and the frozen one, `quorum`
from 742 articles and 1,402 journal entries to 745 and 1,412 and `pi-fold` from
56 and 136 to 58 and 166. The growth is mostly journal entries sharing
vocabulary with the articles they concern, and the decomposition in
`../../RANKING-RESULTS.md` found journal crowding to be the largest recoverable
loss for the lexical ranker. On the store we can measure, that growth did not
move the result.

**The ordering held in eight of eight cells.** BM25 beats cosine over local
embeddings everywhere, by 15.8 to 37.0 points.

## Positive control

`r1_frozen_score.mjs` also scores an oracle ranker that puts each query's own
targets first, and refuses to print anything unless the oracle reaches 1.0 in
every cell. A ranking bug that returned nothing would otherwise print zeroes,
and zeroes would read as a finding. The oracle is at 1.0 in all eight.

## What is frozen and what is not

The corpus and the query set are frozen. The execution is not hermetic. The
scorer imports the retriever from the working tree and calls whichever local
model answers to `nomic-embed-text`, cached by model name rather than by digest.
Pinning the retriever commit and the model digest is remaining work.

## Files

| file | what it is |
|---|---|
| `r1_freeze.mjs` | writes the immutable artifact from the two live stores |
| `r1_frozen_score.mjs` | scores that artifact and no project store, with the oracle control |
| `r1_embed.mjs` | the original live-store harness, kept so the two can be compared |
| `frozen-scores.json` | the frozen run's output, all three arms, the source of the tables above |
| `live-reference.json` | the two live runs' cells and denominators, so the frozen-against-live movements are computed by a gate rather than kept in prose |
| `frozen-corpus.sha256` | the artifact's digest, so the scores above are pinned to one corpus |

## The corpus itself is not published here

`frozen-corpus.json` is 17 MB and contains the full text of two real, private
project-memory stores. Publishing it would publish their contents, which is a
disclosure decision separate from anything this benchmark needs, and it has not
been made. The digest is published so the scores are pinned, and the artifact
can be regenerated by anyone with the stores using the command below. Whether it
ships with the Zenodo deposit is open.

```
node lab/ranking/r1_freeze.mjs 400
node lab/ranking/r1_frozen_score.mjs
```
