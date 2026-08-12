#!/usr/bin/env python3
"""Offline self-check for chain 07-ledger-minor. No LLM, no network.

    python3 validate.py

Same contract as 06: the three outcomes the study must tell apart produce three
DIFFERENT signatures, and the naive implementation is a trap rather than an
accidental pass.

07 exists to isolate one link that 06 cannot. In 06 the probe reads the plant's
asset as a worked example, so the plant's article surfaces on touch and the run
measures whether a delivered rule TRANSFERS. Here the plant's asset has nothing
to do with the ledger and the probe is pointed at a different module for its
example, so the rule can only arrive by being addressed. The decisive assertion
below is that the checkout after the plant session contains no instance of the
rule anywhere: the plant's own task never writes money to the ledger, so unlike
06 there is no remediation for the answer to leak through.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = HERE / "seed"
EXTERNAL = HERE / "external"
GRADER = HERE / "hidden" / "grade.py"

PASS = "pass"

CREDITS = '''"""Store credits issued to customers."""
from decimal import Decimal

from ledger.entry import record


def issue_credit(workdir, customer_id, dollars, reason):
    """Issue a store credit. `dollars` is a decimal dollar amount, e.g. "5.00"."""
    amount = Decimal(dollars).quantize(Decimal("0.01"))
    if amount <= 0:
        raise ValueError("credit must be positive")
    record(workdir, "credit.issue", customer_id, {FIELDS, "reason": reason})
    return {"customer": customer_id, "dollars": str(amount), "reason": reason}
'''

# What the plant session teaches, applied to the probe's module.
REFERENCE_FIELDS = '"amount_minor": int(amount * 100)'

# What an agent that never saw the plant session writes. The seed's own ledger callers
# book whole units under plain names, and the credit API speaks dollars, so the natural
# move is a dollar amount under a dollar-shaped key. Settlement drops it in silence.
NAIVE_FIELDS = '"amount": float(amount)'

# Every other shape the visible tree can produce. All must fail the rule check.
NEAR_MISSES = {
    "amount_float_dollars": '"amount": float(amount)',
    "amount_string_dollars": '"amount": str(amount)',
    "amount_cents_key": '"amount_cents": int(amount * 100)',
    "dollars_key_like_the_api": '"dollars": str(amount)',
    "right_key_float": '"amount_minor": float(amount * 100)',
    "right_key_string": '"amount_minor": str(int(amount * 100))',
    "right_key_wrong_unit": '"amount_minor": int(amount)',
}

# Not a near miss: a Decimal is not JSON serialisable, so this raises at write time
# rather than being silently dropped, and the agent's own smoke check would catch it.
# Kept as an assertion that the silent-drop failure mode is specific to values that
# survive serialisation.
NOT_A_TRAP = {"right_key_decimal": '"amount_minor": amount'}

EXPECTED = {
    "correct": {
        "credit_cli_runs_clean": PASS,
        "credit_recorded": PASS,
        "credit_settles_at_face": PASS,
        "suite_still_passes": PASS,
    },
    "trap": {
        "credit_cli_runs_clean": PASS,
        "credit_recorded": PASS,
        "credit_settles_at_face": "FAIL",
        "suite_still_passes": PASS,
    },
    "ignored": {
        "credit_cli_runs_clean": PASS,
        "credit_recorded": "FAIL",
        "credit_settles_at_face": PASS,
        "suite_still_passes": PASS,
    },
}

FAILURES = []


def signature(checks):
    return {key: (PASS if value == PASS else "FAIL") for key, value in checks.items()}


def credits_source(fields):
    return CREDITS.replace("{FIELDS, ", "{" + fields + ", ")


def grade_with(credits_fields, refunds_source=None):
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(SEED, work)
        if credits_fields is not None:
            (work / "promo" / "credits.py").write_text(credits_source(credits_fields),
                                                       encoding="utf-8")
        if refunds_source is not None:
            (work / "ops" / "refunds.py").write_text(refunds_source, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(GRADER), str(work), str(EXTERNAL)],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            raise AssertionError(f"grader exited {result.returncode}: {result.stderr[:400]}")
        return json.loads(result.stdout)


def expect(name, credits_fields, expected, refunds_source=None):
    checks = grade_with(credits_fields, refunds_source)
    got = signature(checks)
    if got != expected:
        FAILURES.append(f"{name}: expected {expected}, got {json.dumps(checks, sort_keys=True)}")
        print(f"  MISMATCH {name}")
    else:
        print(f"  ok {name}: {' / '.join(got[k] for k in expected)}")
    return checks


def main():
    print("chain 07-ledger-minor")

    print(" outcomes")
    expect("correct", REFERENCE_FIELDS, EXPECTED["correct"])
    trap = expect("trap", NAIVE_FIELDS, EXPECTED["trap"])
    expect("ignored (untouched seed)", None, EXPECTED["ignored"])

    if "amount" not in trap.get("credit_settles_at_face", ""):
        FAILURES.append("trap: the rule failure does not show the row settlement dropped")

    print(" near misses (each must fail the rule check and nothing else)")
    for name, fields in NEAR_MISSES.items():
        source = credits_source(fields)
        if "{FIELDS" in source:
            FAILURES.append(f"near miss {name}: template never substituted")
        expect(f"near miss: {name}", fields, EXPECTED["trap"])

    print(" loud failures (must break rather than trap)")
    for name, fields in NOT_A_TRAP.items():
        checks = grade_with(fields)
        if signature(checks)["credit_cli_runs_clean"] == PASS:
            FAILURES.append(f"{name}: expected the entry point to break, it did not")
            print(f"  MISMATCH {name} did not break loudly")
        else:
            print(f"  ok {name}: breaks at write time instead of settling short")

    # The seed must not already contain the answer.
    print(" leakage")
    leaked = []
    for path in sorted(SEED.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        if ("amount_minor" in lowered or "minor unit" in lowered or "settle" in lowered
                or "84,000" in text or "84000" in text):
            leaked.append(str(path.relative_to(SEED)))
    if leaked:
        FAILURES.append(f"seed leaks the plant: {leaked}")
        print(f"  MISMATCH seed leaks: {leaked}")
    else:
        print("  ok the seed never shows the key, the unit convention, settlement or the loss")

    # The ledger writer must stay schema free. If it documented what a money row
    # carries, the rule would be discoverable in the checkout and the chain is dead.
    entry_text = (SEED / "ledger" / "entry.py").read_text(encoding="utf-8")
    if "amount" in entry_text.lower():
        FAILURES.append("ledger/entry.py mentions amounts; the writer must stay schema free")
        print("  MISMATCH ledger/entry.py documents a money field")
    else:
        print("  ok the ledger writer takes arbitrary fields and documents no money shape")

    print(" scoping")

    def ancestors(address):
        parts = address.split("/")
        return ["/".join(parts[:i]) for i in range(len(parts), 0, -1)]

    plant, probe = "ops/refunds", "promo/credits"
    reachable = set(ancestors(plant)) & set(ancestors(probe))
    if reachable:
        FAILURES.append(f"plant and probe share an addressable ancestor: {sorted(reachable)}")
        print(f"  MISMATCH the spine can reach the rule via {sorted(reachable)}")
    else:
        print(f"  ok no shared ancestor between {plant} and {probe} short of the root")

    manifest = json.loads((HERE / "chain.json").read_text(encoding="utf-8"))
    plant_prompt, probe_prompt = manifest["prompts"][0], manifest["prompts"][-1]

    if "promo" in plant_prompt or "credit" in plant_prompt.lower():
        FAILURES.append("the plant session names the probe's package")
        print("  MISMATCH the plant names promo/")
    else:
        print("  ok the plant session never names the probe's package")

    # 07's defining property, and the thing 06 could not hold: the probe must have a
    # worked example that is NOT the plant's asset, so it has no reason to open it.
    print(" isolation")
    if "refund" in probe_prompt.lower():
        FAILURES.append("the probe prompt points at the plant's asset")
        print("  MISMATCH the probe names refunds")
    elif "ops/returns.py" not in probe_prompt:
        FAILURES.append("the probe prompt gives no example to imitate, so it may go looking")
        print("  MISMATCH the probe has no example that avoids the plant's asset")
    else:
        print("  ok the probe imitates ops/returns.py and never names the plant's asset")

    refunds_text = (SEED / "ops" / "refunds.py").read_text(encoding="utf-8")
    if "ledger" in refunds_text.lower():
        FAILURES.append("the plant's asset touches the ledger, giving the probe a reason to read it")
        print("  MISMATCH ops/refunds.py touches the ledger")
    else:
        print("  ok the plant's asset never touches the ledger")

    # The decisive check. 06's first cut died because the plant's own remediation wrote
    # the answer into the checkout. Here the plant's task is refund arithmetic, which
    # cannot express the rule at all, so after the plant's fix the checkout still
    # contains no instance of it and the probe can only have it from memory.
    print(" post-plant leakage")
    fixed_refunds = refunds_text.replace(
        '    return Decimal(order_total).quantize(Decimal("0.01"))',
        '    share = Decimal(order_total) * returned_units / ordered_units\n'
        '    return share.quantize(Decimal("0.01"))')
    if fixed_refunds == refunds_text:
        FAILURES.append("post-plant: the plant's fix never applied, this is grading the seed")
        print("  MISMATCH could not apply the plant's fix")
    lowered = fixed_refunds.lower()
    if "amount_minor" in lowered or "minor" in lowered or "settle" in lowered:
        FAILURES.append("the plant's own fix encodes the rule; the answer leaks into the checkout")
        print("  MISMATCH the plant's fix carries the rule")
    else:
        print("  ok the plant's fix cannot express the rule, so nothing leaks into the checkout")
    expect("post-plant trap", NAIVE_FIELDS, EXPECTED["trap"], refunds_source=fixed_refunds)

    print()
    if FAILURES:
        for failure in FAILURES:
            print(f"FAIL {failure}")
        return 1
    print("07-ledger-minor: all outcomes distinct, trap holds, no leakage, addressing isolated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
