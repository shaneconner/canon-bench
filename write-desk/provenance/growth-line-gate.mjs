/* The shipping gate for the growth line, copied verbatim from tests/verify.mjs in
   the pi-canon repository at commit 0339489. The block is lines 2318 to 2343 of
   that file and its SHA-256 is
   d2217d83dd0aa218b770bf1de08a01bab758cbb53bb8c1904703f554cddfde45
   so a reader can confirm this copy is the shipped one rather than take it on
   trust. It is not runnable on its own: `canon` and `pass` come from that suite.
   It ships here so the paper's claim that the line shipped with a gate asserting
   it stays quiet on creation, shrinking, capsule-only edits, and no-op writes can
   be read rather than believed. The message text the gate matches is the same text
   Figure 4 quotes. */

/* The growth line: when a rewrite grows the body, the write's own result names
   the growth in bytes and restates the article/journal split. Measured over three
   captures on byte-identical eight-session lineages: prompt-side guidance does not
   change the narration habit, and the arm that got this line ended with fewer
   standing superseded values every time, 51 and 45 and 71 of 96 against 88 and 87
   and 85. The direction holds and the size does not; the counterbalanced capture
   kept the first and lost most of the second. What this gate pins is the behavior,
   not the effect. Creation is not growth, shrinking is not growth, a capsule-only
   write never grows the stored body, and the no-op path returns before it. */
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
