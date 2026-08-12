# canon-bench chain suite specification

Five engineered chains, each a plant / distract / probe / recall sequence run across three
conditions (canon, bare, agentsmd) by run_suite.py. The proto (01-vendor-feed) validated the
doctrine; chains 02-05 extend it across knowledge classes. Design invariants, learned the hard
way in runs 1-4:

- The planted fact must be non-guessable from the checkout AND non-derivable by common sense.
  Test: would a competent agent with no memory plausibly do the right thing anyway? If yes,
  redesign (we rejected a retired-SKU rule for exactly this; nobody guesses 999-means-zero).
- Enforcement lives OUTSIDE the checkout: an external sim/consumer the agent cannot read, or a
  hidden test. Code comments are the null memory system; the plant session's own fix will leak
  whatever a comment can naturally hold. That leakage is legitimate (measure it), but the
  probe's key fact must not be recoverable that way.
- Failure signatures must be distinct and deterministic: correct, task-done-but-rule-missed,
  and task-failed must each produce a different gradeable result (proto: 4573 / 45532 / 6679).
- Recall facts are ground-truth STATEMENTS graded by a pinned LLM judge (one yes/no assertion
  check per fact over the whole answer; hedged speculation and "not recorded" grade no). Regex
  fact-matching was tried and provably misgrades both directions: paraphrase false-negatives on
  fully-correct answers, hedged-speculation false-positives on zero-knowledge ones. Outcome
  grading, the study's primary metric, stays 100% deterministic; the judge touches only recall,
  every judge transcript is archived, and validate_judge.py must pass the chain's
  hidden/recall_fixtures.json (gold answers all-yes, zero-knowledge answers no on every
  plantOnly fact) before any study run.
- A plant session that REMEDIATES leaks its own answer into the checkout, and validating
  against the pristine seed cannot see it. Chain 06's first cut passed a real probe cell
  on exactly this: the plant had to fix ops/billing.py, so by probe time the tree showed
  the convention, and the probe read that file six times and copied it. The secret must
  sit somewhere the remediation cannot carry, and validate.py must grade the naive
  implementation against a checkout where the plant's own fix is ALREADY APPLIED, not
  only against the seed.
- Grading runs against a post-probe snapshot and the chain's PRISTINE external/ (never the cell
  copy: a session told the external is broken may try to fix it in place).
- No timing assertions anywhere; determinism only (call counters, not wall clocks).

## Chain contract (directory layout)

    chains/<id>/
      chain.json        driver manifest, see below
      seed/             the checkout the agent works in (8-15 files; include modules
                        unrelated to the tasks so exploration cost is real)
      external/         code outside the checkout (sim, consumer, serializer); the driver
                        copies it beside the work tree under externalName
      hidden/grade.py   grades a workdir: python3 grade.py <workdir> <externaldir>
                        prints JSON {check: "pass" | "FAIL: <reason>"}, always exit 0
      validate.py       offline self-check, no LLM: writes a reference implementation into a
                        temp copy of seed and asserts every check passes; writes the naive
                        implementation and asserts the exact expected FAIL signature; exits
                        nonzero on any mismatch

chain.json:

    {
      "name": "02-memo-poison",
      "externalName": "taxonomy",            directory name the prompts reference (../taxonomy)
      "prompts": ["...", "...", "..."],      work sessions in order; plant is first, probe last
      "recall": "...",                       the recall prompt, neutral auditor framing,
                                             never names .sessions/
      "facts": {"why_no_memo": "Resolved category chains must never be cached across runs
                               because a background rebalancer mutates records in place."},
                                             ground-truth statements for the LLM judge
      "plantOnly": ["why_no_memo"]           facts only the plant can furnish: the recall-cold
                                             control must judge them no, and they are the
                                             headline recall metric
    }

## 01-vendor-feed (operational constraint) - built, validated, n=2

The proto. Silent 50-cap + stock-999 sentinel. Signatures 4573 / 45532 / 6679. Converted to
the contract unchanged.

## 02-memo-poison (rejected alternative)

Seed: a catalog service. catalog/enrich.py enriches product records by resolving category
chains through catalog/categories.py, which calls the external taxonomy package per lookup.
Plant (support/postmortem framing in session 1's task prompt): resolve results must NEVER be
cached or memoized across records or runs; the nightly rebalancer mutates category records in
place and we shipped stale-alias corruption last quarter. The sanctioned speedup is batching:
resolve each distinct category once per enrichment run via a per-run precomputed index.
Distractor: unrelated task (e.g., CSV export module).
Probe: "enrich_all is too slow on large catalogs; speed it up." The natural fix is
functools.lru_cache on the resolver: the trap.
External: taxonomy package exposes resolve(cat_id) with a module-level CALL_COUNT and a
rebalance() that mutates the taxonomy. Hidden grade: (a) efficiency check, CALL_COUNT for a
large catalog stays at or below distinct-categories (proves the speedup happened); (b)
freshness check, enrich, rebalance(), enrich again, second result must reflect the mutation
(cross-run cache fails it). Signatures: pass+pass correct; pass+FAIL memoized (the trap);
FAIL+pass no speedup.
Recall facts: why memoization is forbidden (rebalancer mutates in place), what happened last
quarter (stale-alias corruption), the sanctioned alternative (per-run batch/precompute).

## 03-consumer-contract (invisible downstream consumer)

Seed: a reporting tool that writes report.txt daily. Plant: finance's ingest parser (separate
repo, not in the checkout) reads report.txt and is brittle: amounts must be integer cents, and
any comma or dollar sign inside an amount field marks the line corrupt. Dollars are for humans:
display surfaces only, never the file.
Distractor: unrelated task.
Probe: "amounts in the report are hard to read; show them as dollars." Conflicting-pressures
probe: correct behavior prettifies stdout/summary output while report.txt keeps integer cents;
naive behavior rewrites report.txt with $1,234.56.
External: finance_parser.py, the actual consumer. Hidden grade: (a) run the parser on the
generated report.txt, must parse clean; (b) parsed totals equal ground truth; (c) the dollars
ask actually happened somewhere (a display surface emits formatted dollars) so "ignored the
task" cannot pass as "preserved the contract".
Recall facts: who reads report.txt (finance ingest), the format law (integer cents, no
commas/$ in amounts), where dollars are allowed (display only).

## 04-tz-convention (cross-asset convention; stresses project-wide articles)

Seed: an event/scheduling service, several modules all using naive-UTC datetimes. Plant
(postmortem framing): ALL datetimes stay naive UTC by convention; the legacy serializer on the
deploy host (TZ=America/Chicago) double-converts aware datetimes, and we lost six hours of
events in March. utcnow() style everywhere; never timezone-aware objects.
Distractor: unrelated task.
Probe: "add a retention module that removes events older than N days." The modern reflex is
datetime.now(timezone.utc), an aware object: comparisons against stored naive datetimes raise,
and the legacy serializer shifts aware values.
External: legacy_serializer.py that faithfully double-converts aware datetimes (the bug the
convention exists to dodge). Hidden grade: (a) retention works on naive-UTC fixture data; (b)
serializer round-trip of everything the new module stores matches ground truth (aware objects
come back shifted). Interesting side-measurement: where canon files a project-wide convention
(root article vs per-asset).
Recall facts: the convention and why (legacy serializer double-converts), deploy host timezone
(America/Chicago), the March incident (lost six hours of events).

## 05-import-lazy (environment/ops quirk)

Seed: a metrics collector with a vendor client used from several modules. Plant (ops framing):
the prod cron host has no network until the VPN sidecar is up; ANY vendor call at import time
crashes the entire crontab, so client construction and fetches must be lazy, inside functions,
never at module level.
Distractor: unrelated task.
Probe: "config is duplicated everywhere; centralize the vendor client setup in one shared
module." The natural refactor is a module-level singleton client = vendor.Client(cfg): the trap.
External: vendor package whose Client.__init__ contacts the network, honoring NETWORK_UP env
(0 raises). Hidden grade: (a) subprocess-import every seed module with NETWORK_UP=0, all must
import clean; (b) with NETWORK_UP=1, the collector actually works (laziness did not become
never-connect). Signatures: import-crash the trap; both-pass correct.
Recall facts: why lazy (no network at import on the cron host), the blast radius (whole
crontab dies), the trigger (VPN sidecar comes up late).

## Study grid

5 chains x 3 conditions x 2 reps, sessions per chain = prompts + recall (4-5). ~130 Luna
sessions. Plus one cold control per chain before the study: bare condition, probe prompt only
on a fresh seed; if it passes the hidden grade without the plant, the chain leaks and goes
back to design. Cold controls are the empirical guessability test; opinions do not count.

## Knowledge classes, and the class the suite was missing (2026-08-12)

Chains 01-05 are all **asset-scoped**: the planted constraint belongs to a file, the
plant session works on that file, and the probe session works on that file or a
descendant of it. That is a deliberate design, because it is the shape pi-canon's
address spine is built for, and the headline run measures it.

It is also why the 1.0 forensic could not see a retrieval failure. All 14 missed facts
were classified as write-desk failures (8 never captured, 5 overwritten, 1 judge error,
0 lost at retrieval), and the natural reading is that retrieval is not the problem. The
survivorship structure has to be read beside it: in a suite where every planted fact has
an owning asset, a retrieval miss is not a failure the population contains. The chains
cannot fail the way retrieval would fix. A null result from these five arms would
therefore say nothing about a ranker, in either direction.

**A cross-cutting chain** closes that. Its planted constraint governs many assets and
owns none, so the address that would carry it does not exist:

- The plant session learns the rule while working on one asset.
- The probe session needs the rule while working on an asset with **no shared ancestor
  short of the root**. pi-canon resolves by exact address then by ancestor walk, so this
  is the precise condition under which the spine provably cannot carry the rule across.
  A root article would reach it, and surfaces on every touch of anything, which is the
  degenerate case rather than a filing.
- Every other invariant above still holds: non-guessable, enforcement outside the
  checkout, distinct deterministic signatures, ground-truth statements for the judge.

A chain declares its class in chain.json as `"class": "asset-scoped" | "cross-cutting"`,
so an analysis can split the two rather than pooling them. Chains 01-05 are asset-scoped
by construction and are not being relabelled by hand: the field is read as asset-scoped
when absent.

The scoping property is not a comment. `validate.py` asserts it, by computing the
ancestor sets of the plant and probe addresses and requiring the intersection to be
empty, and by requiring that no plant prompt touches the probe's package.

## 06-audit-actor (cross-cutting) - built, validated offline, not yet run

Seed: a small ops repo. `ops/audit.py` is a shared append-only sink; `ops/billing.py`
and `ops/inventory.py` emit to it; `dispatch/sweep.py` is a separate top-level package
that predates the sink and emits nothing. Unrelated modules (`ops/pricing.py`,
`ops/textutil.py`, `ops/config.py`) carry real exploration cost.

Plant (compliance write-up framing, session 1 works on `ops/billing.py`): the quarterly
human-attribution report treats every actor string not prefixed `system:` as a named
person, so a scheduled job must write `system:<job-name>`. The prefix is the reader's
only signal: no allowlist, no way to mark a row automated afterwards, because the sink
is append only and the reader is downstream of every service. It exists because the
nightly close once ran as `ops-bot`, also a real staff account, and about 40,000
automated actions were attributed to that employee for eleven weeks.

Distract: a `--format` flag on `cli.py`.

Probe: wire `dispatch/sweep.py` into the sink. The obvious actor is a descriptive job
name with no prefix, and nothing in the checkout says otherwise: `ops/audit.py`
validates shape and never policy, and the seed never mentions the reader, the incident,
or attribution. The external `compliance_reader.py` then attributes the automated
dispatches to a person.

Signatures (`sweep_runs_clean` / `dispatch_audited` / `sweep_not_human_attributed` /
`suite_still_passes`):

    correct        pass / pass / pass / pass
    trap           pass / pass / FAIL / pass
    probe ignored  pass / FAIL / pass / pass
    entry broken   FAIL / *    / *    / *

`dispatch_audited` is blind to the actor and `sweep_not_human_attributed` is evaluated
only against rows the sweep itself produced, so a seed row can neither rescue nor
condemn the probe. Three near misses are validated as traps rather than passes: a bare
`system` with no job name, a `-bot` suffix, and a short human-shaped name.

Still owed before this chain can run: `hidden/recall_fixtures.json` and
`hidden/judge-validation/` gold and zero-knowledge answers, and a pass through
`validate_judge.py`.
