# W1 write-quality programme: consolidated results (W1e through W1i)

Status date: 2026-08-20. This document consolidates the five completed model
captures of the W1 series into one legible record. Each experiment's full
evidence (fixtures, capture trees, manifests, receipts, analyses) is retained
under its own run identity; the canonical detail lives in the memory store at
`lab/evolving-canon` and the append-only journal. Everything here is
development evidence: no experiment authorizes a package, shipping,
domain-general, confirmatory, or additional-model claim.

## The question

Does the way memory is WRITTEN let an agent DECIDE correctly later, from the
written bytes alone? The programme decomposes this into reader-side questions
(which surface suffices for exact current decisions) and writer-side questions
(can a writer maintain a canonical article across a lineage of events so that
it stays decision-sufficient).

## Results at a glance

| Exp | Question | Key cells | Outcome | Cost |
|-----|----------|-----------|---------|------|
| W1e | full-rewrite vs state-only writer | 320/320 field-exact BOTH arms | state-only selected (output ratio 0.846) | 0.29555800 |
| W1f | which read surface suffices | article 127/128, +journal 127/128, brief 111/128*, capsule 1/128 | negative; brief instrument invalid | 0.50299204 |
| W1g | article organization (linear vs scan) | linear 125/128**, scan 128/128, +journal 128/128, capsule 0/128, brief 128/128 | negative; selection gate unmet | 0.47757956 |
| W1h | canonical article sufficiency | article 124/128, +journal 128/128, capsule 0/128, brief 128/128 | negative under 128/128 gate | 0.52804172 |
| W1i | state-only writer across 12-event lineages | writers 186/192 (190/192 event-level), readers 127/128 | negative under all-exact gate | 0.48559000 |
| W1j | precedence rejection: control vs presentation vs mechanical guard | conditional rejection A 66/70, B 63/68, C 78/78 | guard closed the class; presentation did not help | 0.96554924 |

*brief omitted the lower-priority-wins instruction, so its ceiling was not
mechanically closed; instrument invalid independently of the misses.
**all three linear misses were protocol failures (an extra submit call), not
semantic misses.

All six captures: zero failed processes, zero timeouts (except one retained
120s timeout in W1f), zero retries, zero replacements, zero reruns, one model
(openai-codex / gpt-5.6-luna, high thinking) throughout.

## What is now established

1. **Capsules are not decision surfaces.** capsule_only scored 1/128 (W1f),
   0/128 (W1g), 0/128 (W1h). Three experiments, three floors. Capsules are
   surfacing hooks, not truth carriers.

2. **A complete, well-formed article is ~99% sufficient but not 100%.**
   127/128 (W1f), 125-128/128 (W1g), 124/128 (W1h), 127/128 (W1i readers).
   The registered gates demand exactness, so each is a negative result, but
   the residual is small, stable across designs, and now has a named shape.

3. **History (journal) is not the missing 1%.** article_plus_journal rescued
   W1h's four misses but failed the economy gate (output ratio 1.196 against
   the 1.10 bound, input 58-59% higher); in W1f it missed symmetrically with
   the article; in W1g it rescued nothing scan had not already fixed.

4. **State-only writing works, and cheaper.** W1e: both writer arms 320/320
   field-exact; state-only used 0.846 of full-rewrite's output tokens with
   fewer recoveries. W1i: across 192 lineage events the state-only writer was
   100% exact on every constructive operation (set, set_null, set_ambiguous,
   resolve, revoke, rollback: 160/160 changing events at event level) and
   100% on same-state restatements (16/16 no-ops).

5. **The residual failure modes are two, and they recur.**
   - **Rule-selection depth (reader).** Three of W1h's four article misses
     selected priority rank 2 of exactly three matching rules; W1i's single
     reader miss selected family position 2 where the eligible winner sat at
     position 3 (correct state entries, correct uncertainty, wrong rule).
     The shortcut-defeating winner layouts exist precisely to expose this.
   - **Precedence rejection (writer).** W1i's only two true writer errors
     (of 192 events) were the same mistake: accepting a lower-authority
     rejected_conflict claim (rank 6 against a rank-5 operative basis),
     2/16 on the rejection class. Both wrote and submitted state_changed.
     Every downstream miss was proven conditionally exact: each later writer
     applied its own event perfectly to the corrupted store it inherited.

6. **Protocol is a solved problem.** W1i corrected protocol: 320/320
   first-pass, zero schema recoveries on a nested 8-field typed-state schema,
   zero membership-guard refusals. W1h: 511/512 first-pass. Models execute
   frozen tool protocols essentially perfectly; the residual is judgment,
   not mechanics.

## The design lesson

Across five experiments the last 1% never yielded to prompting; it is always
a judgment call (which rule is deepest-eligible, whether a claim out-ranks
the basis), never a mechanical step. Where the instrument enforced a rule
mechanically at the tool boundary (revision freshness, schema shape,
identifier membership), the error rate was zero. Where the model judged, the
error rate was ~1%. The product implication for canonical memory: conflict
resolution and format constraints belong in the write path, enforced by the
tool, not delegated to the model's judgment.

W1j then tested the lesson directly and it held: the model-judged arms
failed 10-20% of near-rank precedence conflicts regardless of how the ranks
were presented, while the tool-guarded arm had zero true precedence failures
in 78 conditional cells, and the guard never even had to fire (see below).

## Known capture artifact (fixed 2026-08-20)

Pi 0.84.2 omits the terminate flag from turn_end.toolResults; the flag is
retained losslessly in tool_execution_end.result. Both the W1h and W1i real
captures initially classified all sessions protocol-invalid on that clause
(both fake preflights had emitted the flag synthetically). Both were resolved
by documented post-hoc corrections joining execution events by tool-call id
(W1h: analyses/20260817-w1h-model-001-protocol-corrected.json; W1i:
runs/20260819-w1i-lean-model-001/protocol-corrected-report.json). The W1i
harness transcript layer now performs the lossless join itself and the fake
driver now mirrors the real event shape, verified against both completed
runs (320/320 each) with the classifiers unchanged.

## W1j result (2026-08-20)

Run 20260820-w1j-model-001: 576/576 sessions, 3 matched arms over identical
16-asset x 12-event lineages, 80 rejection cells per arm in five difficulty
variants (R1 rank worse by 2, R2 worse by 1, R3 equal rank backdated
observed_at, R4 equal rank and time lower sequence, R5 worse by 1 on the
just-changed field). Cost 0.96554924 of the 1.50000000 ceiling. Protocol
572/576; the 4 invalid sessions are all arm C writes whose state was
unchanged (guard-passing no-ops) followed by the correct rejected_conflict
disposition, and all four stored cells graded exact.

Raw exactness is dominated by downstream propagation (A 163/192, B 157/192,
C 186/192 with A 25 and B 30 downstream cells from 4 and 5 first
divergences), so the decisive table is conditional on an on-oracle
predecessor:

| Arm | All | Rejection | R1 | R2 | R3 | R4 | R5 | Changing | Restatement |
|-----|-----|-----------|----|----|----|----|----|----------|-------------|
| A control | 163/167 | 66/70 | 15/16 | 12/15 | 15/15 | 12/12 | 12/12 | 85/85 | 12/12 |
| B rank-adjacent | 157/162 | 63/68 | 15/16 | 12/15 | 13/13 | 12/12 | 11/12 | 82/82 | 12/12 |
| C mechanical guard | 186/188 | 78/78 | 16/16 | 16/16 | 16/16 | 15/15 | 15/15 | 94/95 | 14/15 |

Findings:

1. **The guard closed the class.** Arm C: 78/78 conditional rejection, zero
   true precedence failures, and the guard fired zero times in protocol-valid
   sessions. One prompt sentence naming the tool refusal deterred every
   precedence-losing write. Deterrence, not interception.
2. **Presentation did not help.** B 63/68 vs A 66/70, within noise and
   directionally worse. The W1i postmortem's format hypothesis is dead; the
   failure is a judgment the model makes with the ranks in plain view.
3. **The hard case is rank-worse-by-1.** R2 carries 6 of the 9 A+B
   conditional rejection misses (20% miss rate on that variant). The tiebreak
   variants R3/R4 were flawless in every arm (0 misses in 67 conditional
   cells); R1 lost 2, R5 lost 1.
4. **Conditionally, everything else is perfect in A and B.** All changing
   events and restatements exact; precedence rejection is the only
   model-judged failure mode left, replicating W1i on 138 rejection cells
   instead of 16.
5. **One new leak.** C's two errors were non-precedence: one misapplied
   resolve the core refused to render (ordinal 381), and one restatement
   written as a change with an identical state, bumping only the revision
   (ordinal 558). The guard cannot catch a state-equal write because no field
   changes. The mechanical fix is obvious: treat a write whose composed state
   equals the current state as a restatement, not a change.

## Open next step

The programme's write-path question is answered: enforce precedence in the
tool. Remaining candidates, all mechanical closures rather than experiments:
(a) a state-equality check in the write path (closes the W1j ordinal-558
leak), (b) the reader-side rule-selection depth residual (W1h, W1i: still
~1%, never mechanically enforced), which would need its own instrument if
pursued. Any further paid run is Shane's call.
