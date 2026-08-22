/* The shipping gate for the growth line, copied verbatim from tests/verify.mjs in
   the pi-canon repository. It is not runnable on its own: `canon` and `pass` come
   from that suite. It ships here so the paper's claim that the line shipped with a
   gate asserting it stays quiet on creation, shrinking, capsule-only edits, and
   no-op writes can be read rather than believed. The message text the gate matches
   is the same text Figure 4 quotes. */

/* The growth line: when a rewrite grows the body, the write's own result names
   the growth in bytes and restates the article/journal split. Measured (W4, two
   arms over byte-identical eight-session lineages): prompt-side guidance does not
   change the narration habit, and the arm that got this line at the write
   boundary ended with 51 of 96 standing superseded values against the untreated
   arm's 88, with a median store a fifth smaller and no reader regression. Arms
   ran in a fixed order, so read that as a difference between two conditions.
   Creation is not growth, shrinking is not growth, a capsule-only write never
   grows the stored body, and the no-op path returns before it. */
const seeded = await canon({ action: "write", path: "src/ledger", capsule: "Ledger.", body: "# Ledger\nShort." });
assert.match(seeded, /Wrote src\/ledger\./);
assert.doesNotMatch(seeded, /Body grew/);
const grownWrite = await canon({ action: "write", path: "src/ledger", body: "# Ledger\nShort.\nA second line that makes the body longer." });
assert.match(grownWrite, /Wrote src\/ledger\./);
assert.match(grownWrite, /Body grew \d+ -> \d+ bytes\./);
assert.match(grownWrite, /move it to the journal/);
const shrunkWrite = await canon({ action: "write", path: "src/ledger", body: "# Ledger\nTiny." });
assert.match(shrunkWrite, /Wrote src\/ledger\./);
assert.doesNotMatch(shrunkWrite, /Body grew/);
const ledgerCapsuleOnly = await canon({ action: "write", path: "src/ledger", capsule: "Ledger, retold." });
assert.match(ledgerCapsuleOnly, /Wrote src\/ledger\./);
assert.doesNotMatch(ledgerCapsuleOnly, /Body grew/);
const restatedLedger = await canon({ action: "write", path: "src/ledger", body: "# Ledger\nTiny." });
assert.match(restatedLedger, /already current/);
assert.doesNotMatch(restatedLedger, /Body grew/);
pass("a growing rewrite names its growth; creation, shrinking, capsule-only, and no-op stay silent");
