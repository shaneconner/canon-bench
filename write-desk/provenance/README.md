# Provenance bundle

Everything here exists to answer one question a reviewer asked and we could not
answer: can someone outside the project check that the paper's figures and
tables come from the runs, without taking our word for it?

They could not, and the reason that mattered is on the record. Two figures in an
earlier draft of the paper carried captions saying they quoted a real store and
quoted the tool word for word. The template was real. The byte counts and the
records were invented. The paper now says so in its back matter. After that, a
path printed in a caption is not evidence, and this bundle is the repair.

## Check it yourself

```
python3 regenerate.py
```

No arguments, no network, no dependencies beyond the standard library. It reads
only what ships here, covers all three controlled captures and the accumulation
study, rebuilds `../data/per-lineage-endpoints.csv` and the
plotted series in `../data/figure-data.js` from the graded reports and the
fixture generators, compares them against the published copies, and prints one
line per check. It exits non-zero if anything disagrees.

```
python3 drift-sweep.py /path/to/20260820-w4-model-001
```

Reproduces the drift audit against an unpacked capture tree from the Zenodo
deposit. `drift-sweep.txt` is our run of it.

```
python3 verify-session-counts.py /path/to/runs
```

Recounts every capture against the numbers the paper prints. Also needs the
deposit. `session-counts.txt` is our run of it.

```
node retrieval/r1_freeze.mjs 400 && node retrieval/r1_frozen_score.mjs
```

Rebuilds the frozen retrieval corpus from two live project stores and scores it.
Needs those stores and a local Ollama, and it will produce different numbers as
the stores grow, which is the point `retrieval/README.md` makes.

```
sha256sum -c MANIFEST.sha256
```

Regenerate the manifest with the same command that built it. Running the Python
scripts leaves a `__pycache__` beside the fixtures, and it is excluded here
because compiled bytecode is not an artifact anyone should be asked to check.

```
find . -type f ! -name MANIFEST.sha256 -not -path '*/__pycache__/*' \
  | sed 's|^\./||' | sort | xargs sha256sum > MANIFEST.sha256
```

## What each file authenticates

| file | the claim it lets you check |
|---|---|
| `figures/figure-2-record.md` | the narration figure quotes a real control-arm record from the selection capture, markdown emphasis stripped and nothing else changed |
| `figures/figure-4-session.jsonl` | the growth-line figure quotes a real tool response with its real byte counts, `75 -> 960`, from ordinal 32 of the first controlled capture |
| `captures/graded-report-w4.json` | the first capture's endpoints: 88 and 51 of 96 standing, the per-session trajectories, the 117 growth lines |
| `captures/graded-report-w4r.json` | the same for the second model: 87 and 45 of 96, 99 growth lines |
| `captures/graded-report-w4c.json`, `captures/contract-w4c.json` | the counterbalanced capture: 85 and 71 of 96, 126 growth lines, and the contract carrying `arm_order_by_lineage` and the pinned digests it was verified against |
| `fixtures/w4c_build_instrument.py` | the counterbalance is asserted in the builder, four lineages each way, with each lineage's two writer blocks kept from interleaving |
| `captures/graded-report-w3.json` | the accumulation study's per-depth stores and piles |
| `captures/graded-report-w2.json` | the selection study's 32 stores, their staleness, and the arm medians |
| `captures/contract-w4.json`, `contract-w4r.json` | what each capture pinned: model, thinking setting, timeouts, exact decimal cost ceiling, zero retries, and the SHA-256 of every source, package file, and arm tool |
| `arms/tool-A.ts`, `arms/tool-G.ts` | the two arm tools as pinned, hashed in the contracts under `arm_tool_sha256` |
| `arms/tool-A-vs-G.diff` | the arms differ by one added block and the single line that splices its output into the response, and by nothing else |
| `fixtures/w4_lineage.py`, `fixtures/w3_lineage.py` | the histories are generated, byte-identical across arms, and the availability denominators are a property of the fixture rather than of any run |
| `drift-sweep.py`, `drift-sweep.txt` | no output from the mid-capture package drift reached any model |
| `rehearsal-growth-lines.py`, `rehearsal-growth-lines.txt` | the no-model rehearsal fires the line 38 times in all four runs, 8 of them the fixture's own exercise sentence and 30 incidental, and none of the 30 from a replacement number carrying more digits. This is the recount behind the W4 erratum |
| `regenerate.py` | the published CSV and plotted series are derived from the reports above and were not hand-edited |
| `growth-line-gate.mjs` | the line shipped with a test asserting it stays quiet on creation, shrinking, capsule-only edits, and no-op writes, and matching the same message text Figure 4 quotes. Its header names the pi-canon commit it was copied from and the SHA-256 of the copied block, so the copy can be checked against the package rather than assumed current |
| `retrieval/` | the frozen ranking harness and what freezing it revealed: BM25 fell in eight cells of eight as the two live stores grew, by 2.2 to 13.3 points, while the embedding ranker did not move consistently, and the ordering held in all eight. Start at `retrieval/README.md` |
| `verify-session-counts.py`, `session-counts.txt` | the eleven captures' run and protocol-valid counts, recounted from the capture trees rather than restated |

## What this does not establish

The bundle proves the paper agrees with the graded reports. It does not prove
the graded reports describe the runs. That chain runs through the capture
manifests and the per-session transcripts, which come to roughly 220MB and ship
with the Zenodo deposit rather than with git. `drift-sweep.py` is written to run
against that deposit, and its positive control is the pattern to copy: it counts
something the reports say is there, and refuses to report the interesting zeroes
unless that count matches.

One limit is permanent: the Codex runtime exposes no decoding seed, so the
captures are auditable but not exactly rerunnable.

A second was permanent and is now bounded. The retrieval benchmark in the paper
cannot be rerun against the corpus it plotted, because both real stores have
grown since. `retrieval/` freezes the harness so that stops being true going
forward, and measures what the old defect cost: scored against the plotted run,
BM25 fell in eight cells of eight while the embedding ranker did not move
consistently, and the ordering held in all eight.

## An audit script needs a control

The first version of `drift-sweep.py` searched every string in every session
event and reported five hits on the word "relations", concluding the drift was
not inert. All five were the model thinking about "article relationships", and
the substring matched inside that word. It had no control, so there was nothing
to tell it that it was reading model prose rather than tool output.

The version here searches only the text blocks a tool returned, matches
`relations` as a whole word, and counts growth lines as a control. The control
comes back at 117, exactly what `per_arm.G.total_growth_lines` reports, so the
extractor is reading the right stream. The zeroes above it mean something only
because of that number.
