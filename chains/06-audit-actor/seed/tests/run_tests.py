#!/usr/bin/env python3
"""Seed suite. Covers behaviour, never house convention."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dispatch import sweep as dispatch_sweep  # noqa: E402
from ops import audit, billing, inventory, pricing, textutil  # noqa: E402

FAILURES = []


def check(name, condition):
    if not condition:
        FAILURES.append(name)


def main():
    with tempfile.TemporaryDirectory() as work:
        billing.void_invoice(work, "INV-1", "dana")
        billing.close_period(work, "2026-07")
        inventory.adjust(work, "SKU-1", -3, "dana")
        rows = audit.read_all(work)
        check("four_actions_logged", len(rows) == 3)
        check("seq_increments", [r["seq"] for r in rows] == [1, 2, 3])
        check("void_actor", rows[0]["actor"] == "dana")

        dispatched = dispatch_sweep.dispatch(work, "SHP-9", "acme-freight")
        check("dispatch_returns_state", dispatched["state"] == "dispatched")
        swept = dispatch_sweep.sweep(work, ["SHP-1", "SHP-2"], "acme-freight")
        check("sweep_covers_all", len(swept) == 2)

        check("price_lookup", pricing.price_cents("SKU-1") == 1299)
        check("discount", pricing.discounted("SKU-2", 1000) == 405)
        check("truncate", textutil.truncate("abcdef", 4) == "abc…")
        check("slug", textutil.slug("Acme Freight!") == "acme-freight")

        try:
            audit.emit(work, "", "x", "y")
        except ValueError:
            pass
        else:
            FAILURES.append("empty_actor_rejected")

    if FAILURES:
        print("FAILED: " + ", ".join(FAILURES))
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
