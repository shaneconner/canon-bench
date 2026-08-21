# W2-DESIGN-001: selection quality upstream of recall (sketch for review)

Status: SKETCH. Nothing is built, no fixture exists, no run is authorized.

## The question W1 could not ask

Every W1 experiment handed the writer an oracle packet and asked whether it was
transcribed exactly. Real sessions hand the agent a mess and ask it to decide
what deserves to become durable at all. W2 measures that decision: given a
realistic working session, does the agent write the right things, at the right
addresses, in the right tier (article vs journal), and do those choices pay off
in a later session's task decisions?

This is the first experiment where the write surface is the SHIPPED pi_canon
tool, doctrine, schema, and lint, not a lab protocol. It tests the product.

## Shape

Two phases over the same lineages, three matched arms.

Phase 1, writers: each session receives a synthetic work transcript (a plausible
session record, 3,000 to 5,000 tokens) and finishes by persisting what matters
through the real pi_canon tool into a fresh real .canon store. Each transcript
plants a designed fact population:

- K needed facts: values a phase-2 task will require (limits, orderings, ids,
  who-consumes-what). The needed set is frozen at construction, so ground truth
  is mechanical, no judge model.
- Superseded facts: values stated then explicitly revised later in the same
  transcript. Writing the stale value as current is a named error class (the
  laundering failure the lint warns about, now measured end to end).
- Ephemeral noise: scheduling chatter, dead ends, restated context. Writing it
  all is itself a failure of selection, priced by write volume and reader input
  cost rather than by a rule.
- Placement traps: facts whose governing asset differs from the asset the
  transcript's work happened to touch. Filing at the touched asset instead of
  the governing one is the placement failure the doctrine names; under
  address-only surfacing it makes a fact written-but-unreachable.

Phase 2, readers: fresh sessions receive a task plus recall through the real
tool (surfacing on touch, read, search with the new split window), against
whatever store their arm's writer actually left. Graded exactly on typed task
decisions, W1-style. Readers per lineage need facts from several addresses, so
placement errors and retention errors separate cleanly.

## Arms

- A, shipped: the doctrine exactly as the package ships it today.
- B, guided: shipped doctrine plus one added paragraph of selection guidance
  (write values verbatim, prefer the governing address, journal the event).
  Tests whether prompt guidance moves selection, the way W1j arm B tested
  whether presentation moved precedence. Expectation set by W1: it will not,
  but that is exactly the measurement.
- C, no canon: the reader receives the raw phase-1 transcript instead of a
  store, at whatever token cost that is. The baseline that prices the entire
  product: distilled canonical memory must beat carrying the transcript, on
  decisions or on cost, ideally both. W1f/W1h measured this with ORACLE
  articles; C measures it with model-authored ones, which is the honest
  version.

## Frozen metrics

Per arm: reader decision exactness (primary); needed-fact retention in the
store (mechanical containment check, the unretained() machinery); staleness
errors (superseded value presented as current); placement (needed fact stored
at an address the reader's touch or read actually reaches); reader input
tokens (economy against arm C); writer call counts and write volume.

## Scale and cost sketch

Eight fresh domains, two lineages each: 16 transcripts, 3 arms of 16 writer
sessions (48), 2 reader tasks per lineage per arm (96 readers), 144 sessions
total. Writer sessions carry the fat inputs. Rough estimate 0.60 to 0.90 at
W1j prices; propose the familiar 1.50000000 ceiling, one run, zero retries,
same capture discipline (fresh bwrap sandbox per session, digest-pinned
contract, grade-blind, sequential).

## What W2 does not claim

Development selection only, one model, synthetic transcripts. No confirmatory,
domain-general, scale, or shipping claim. A positive arm C (transcript beats
store) would be a product-level alarm, not a verdict, and would gate a redesign
discussion, not a rerun.

## Open for Shane

1. Arm C in or out? It doubles reader input cost for the strongest baseline.
2. Transcript realism: synthetic-but-designed (proposed, oracle stays
   mechanical) vs harvested real sessions (realistic, but ground truth would
   need labeling and could not be exact).
3. Ceiling confirmation: 1.50000000, one run, on your explicit go as always.

## Also queued from R1, separate and cheap

The embedding rerun of the known-item eval: same harness, same 504 queries,
one embedding pass over ~2,900 documents, answers whether the 0.44 lexical
ceiling on quorum-scale stores is worth closing. Needs a decision on the
embedding source (API or local); pennies either way. Independent of W2.
