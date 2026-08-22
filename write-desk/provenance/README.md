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
only what ships here, rebuilds `../data/per-lineage-endpoints.csv` and the
plotted series in `../data/figure-data.js` from the graded reports and the
fixture generators, compares them against the published copies, and prints one
line per check. It exits non-zero if anything disagrees.

```
python3 drift-sweep.py /path/to/20260820-w4-model-001
```

Reproduces the drift audit against an unpacked capture tree from the Zenodo
deposit. `drift-sweep.txt` is our run of it.

```
sha256sum -c MANIFEST.sha256
```

## What each file authenticates

| file | the claim it lets you check |
|---|---|
| `figures/figure-2-record.md` | the narration figure quotes a real control-arm record from the selection capture, markdown emphasis stripped and nothing else changed |
| `figures/figure-4-session.jsonl` | the growth-line figure quotes a real tool response with its real byte counts, `75 -> 960`, from ordinal 32 of the first controlled capture |
| `captures/graded-report-w4.json` | the first capture's endpoints: 88 and 51 of 96 standing, the per-session trajectories, the 117 growth lines |
| `captures/graded-report-w4r.json` | the same for the second model: 87 and 45 of 96, 99 growth lines |
| `captures/graded-report-w3.json` | the accumulation study's per-depth stores and piles |
| `captures/graded-report-w2.json` | the selection study's 32 stores, their staleness, and the arm medians |
| `captures/contract-w4.json`, `contract-w4r.json` | what each capture pinned: model, thinking setting, timeouts, exact decimal cost ceiling, zero retries, and the SHA-256 of every source, package file, and arm tool |
| `arms/tool-A.ts`, `arms/tool-G.ts` | the two arm tools as pinned, hashed in the contracts under `arm_tool_sha256` |
| `arms/tool-A-vs-G.diff` | the arms differ by one added block and the single line that splices its output into the response, and by nothing else |
| `fixtures/w4_lineage.py`, `fixtures/w3_lineage.py` | the histories are generated, byte-identical across arms, and the availability denominators are a property of the fixture rather than of any run |
| `drift-sweep.py`, `drift-sweep.txt` | no output from the mid-capture package drift reached any model |
| `regenerate.py` | the published CSV and plotted series are derived from the reports above and were not hand-edited |

## What this does not establish

The bundle proves the paper agrees with the graded reports. It does not prove
the graded reports describe the runs. That chain runs through the capture
manifests and the per-session transcripts, which come to roughly 220MB and ship
with the Zenodo deposit rather than with git. `drift-sweep.py` is written to run
against that deposit, and its positive control is the pattern to copy: it counts
something the reports say is there, and refuses to report the interesting zeroes
unless that count matches.

Two limits are permanent. The Codex runtime exposes no decoding seed, so the
captures are auditable but not exactly rerunnable. And the retrieval benchmark
in the paper cannot be rerun against the same corpus at all, because both real
stores have grown since it ran.

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
