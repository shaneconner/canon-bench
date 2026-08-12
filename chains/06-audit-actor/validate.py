#!/usr/bin/env python3
"""Offline self-check for chain 06-audit-actor. No LLM, no network.

Writes each outcome's implementation into a temp copy of seed/ and asserts the
grader returns exactly that outcome's signature. Exits nonzero on any mismatch.

    python3 validate.py

The point is not that the grader runs. It is that the three outcomes the study
has to tell apart produce three DIFFERENT signatures, and that the trap is a
trap: the naive implementation is what a competent agent with no memory of the
plant session would plausibly write, and it must fail on the rule check alone
while passing everything else. If the naive implementation ever passes, the
chain measures nothing.
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

# What the plant session teaches, applied to the probe's module.
REFERENCE = '''"""Dispatch. Moves shipments to carriers."""
from ops import audit

SWEEP_JOB = "system:shipping-sweep"


def dispatch(workdir, shipment_id, carrier, actor=SWEEP_JOB):
    audit.emit(workdir, actor, "shipment.dispatch", shipment_id, {"carrier": carrier})
    return {"shipment": shipment_id, "carrier": carrier, "state": "dispatched"}


def sweep(workdir, shipments, carrier):
    return [dispatch(workdir, shipment, carrier, SWEEP_JOB) for shipment in shipments]
'''

# What an agent that never saw the plant session writes: the pattern the checkout is
# showing it. ops/inventory.py still emits as "ops-inventory-reconcile", so copying the
# house style is both the obvious move and the wrong one. The seed baits the trap
# rather than merely failing to prevent it.
NAIVE = '''"""Dispatch. Moves shipments to carriers."""
from ops import audit

SWEEP_JOB = "ops-dispatch-sweep"


def dispatch(workdir, shipment_id, carrier, actor=SWEEP_JOB):
    audit.emit(workdir, actor, "shipment.dispatch", shipment_id, {"carrier": carrier})
    return {"shipment": shipment_id, "carrier": carrier, "state": "dispatched"}


def sweep(workdir, shipments, carrier):
    return [dispatch(workdir, shipment, carrier, SWEEP_JOB) for shipment in shipments]
'''

# Other shapes of the same miss, all of which must fail the rule check.
NEAR_MISSES = {
    "bare_system_no_job": 'SWEEP_JOB = "system"',
    "bot_suffix": 'SWEEP_JOB = "shipping-bot"',
    "human_shaped": 'SWEEP_JOB = "ops"',
    "copied_from_inventory": 'SWEEP_JOB = "ops-inventory-reconcile"',
}

EXPECTED = {
    "correct": {
        "sweep_runs_clean": PASS,
        "dispatch_audited": PASS,
        "sweep_not_human_attributed": PASS,
        "suite_still_passes": PASS,
    },
    "trap": {
        "sweep_runs_clean": PASS,
        "dispatch_audited": PASS,
        "sweep_not_human_attributed": "FAIL",
        "suite_still_passes": PASS,
    },
    "ignored": {
        "sweep_runs_clean": PASS,
        "dispatch_audited": "FAIL",
        "sweep_not_human_attributed": PASS,
        "suite_still_passes": PASS,
    },
}

FAILURES = []


def signature(checks):
    return {key: (PASS if value == PASS else "FAIL") for key, value in checks.items()}


def grade_with(shipping_source):
    """Copy the seed, optionally replace dispatch/sweep.py, grade, return checks."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(SEED, work)
        if shipping_source is not None:
            (work / "dispatch" / "sweep.py").write_text(shipping_source, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(GRADER), str(work), str(EXTERNAL)],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            raise AssertionError(f"grader exited {result.returncode}: {result.stderr[:400]}")
        return json.loads(result.stdout)


def expect(name, shipping_source, expected):
    checks = grade_with(shipping_source)
    got = signature(checks)
    if got != expected:
        FAILURES.append(f"{name}: expected {expected}, got {json.dumps(checks, sort_keys=True)}")
        print(f"  MISMATCH {name}")
    else:
        print(f"  ok {name}: {' / '.join(got[k] for k in expected)}")
    return checks


def main():
    print("chain 06-audit-actor")

    print(" outcomes")
    expect("correct", REFERENCE, EXPECTED["correct"])
    trap = expect("trap", NAIVE, EXPECTED["trap"])
    expect("ignored (untouched seed)", None, EXPECTED["ignored"])

    # The trap's failure has to name the actor the naive code chose, or the
    # signature is right for the wrong reason.
    if "ops-dispatch-sweep" not in trap.get("sweep_not_human_attributed", ""):
        FAILURES.append("trap: the rule failure does not name the naive actor")

    print(" near misses (each must fail the rule check and nothing else)")
    for name, replacement in NEAR_MISSES.items():
        source = NAIVE.replace('SWEEP_JOB = "shipping-sweep"', replacement)
        expect(f"near miss: {name}", source, EXPECTED["trap"])

    # The seed must not already contain the answer: the checkout is the null
    # memory system, and if the prefix is discoverable there the chain is dead.
    print(" leakage")
    leaked = []
    for path in sorted(SEED.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        # The prefix itself is the answer. A seed that shows it anywhere lets a cold
        # agent copy the convention and pass, which is the failure mode SPEC.md calls
        # out first: would a competent agent with no memory plausibly do the right
        # thing anyway. Here it must not, and the seed's own emitters bait the
        # opposite, so copying the house style is the wrong move.
        if "system:" in text or "ops-bot" in text or "attribut" in text.lower() or "compliance" in text.lower():
            leaked.append(str(path.relative_to(SEED)))
    if leaked:
        FAILURES.append(f"seed leaks the plant: {leaked}")
        print(f"  MISMATCH seed leaks: {leaked}")
    else:
        print("  ok the seed never shows the prefix, the incident, the reader, or attribution")

    # The prefix appears in the seed only as a value other services already use,
    # which is legitimate: an agent CAN see billing uses "system:billing-close".
    # What it cannot see is that the prefix is load-bearing. Assert the seed says
    # nothing about why, so the trap survives a careful reader.
    audit_text = (SEED / "ops" / "audit.py").read_text(encoding="utf-8")
    if "system:" in audit_text:
        FAILURES.append("the sink itself documents the prefix; the rule must live outside the code")
        print("  MISMATCH ops/audit.py documents the prefix")
    else:
        print("  ok the sink validates shape, never policy")

    # The defining property of this chain: the address spine cannot carry the rule
    # from where it is learned to where it is needed. pi-canon resolves an asset to
    # its article by exact address then by ancestor walk, so a constraint filed at
    # the plant's asset is reachable from the probe's asset only if one is an
    # ancestor of the other. Here the nearest shared ancestor is the root, and a
    # root article surfaces on every touch of anything, which is the degenerate
    # case rather than a filing. This is what makes 06 measure retrieval instead of
    # measuring the spine a second time.
    print(" scoping")

    def ancestors(address):
        parts = address.split("/")
        return [ "/".join(parts[:i]) for i in range(len(parts), 0, -1) ]

    plant = "ops/billing"
    probe = "dispatch/sweep"
    reachable = set(ancestors(plant)) & set(ancestors(probe))
    if reachable:
        FAILURES.append(f"plant and probe share an addressable ancestor: {sorted(reachable)}")
        print(f"  MISMATCH the spine can reach the rule via {sorted(reachable)}")
    else:
        print(f"  ok no shared ancestor between {plant} and {probe} short of the root")

    # And the probe's own asset must not be where the rule would naturally be filed:
    # if the plant session ever touches the probe's module, the plant could file it
    # there and the spine would carry it after all.
    plant_prompt_files = ("ops/billing.py", "tests/run_tests.py")
    if any("dispatch" in name for name in plant_prompt_files):
        FAILURES.append("the plant session touches the probe's package")
        print("  MISMATCH the plant touches dispatch/")
    else:
        print("  ok the plant session never touches the probe's package")

    print()
    if FAILURES:
        for failure in FAILURES:
            print(f"FAIL {failure}")
        return 1
    print("06-audit-actor: all outcomes distinct, trap holds, no leakage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
