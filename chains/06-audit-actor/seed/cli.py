#!/usr/bin/env python3
"""Ops entry point.

    python3 cli.py close-period <period>
    python3 cli.py reconcile <sku> <counted>
    python3 cli.py sweep <carrier> <shipment> [<shipment> ...]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dispatch import sweep as dispatch_sweep  # noqa: E402
from ops import billing, inventory  # noqa: E402


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    workdir = str(Path(__file__).resolve().parent)
    command = argv[1]
    if command == "close-period" and len(argv) == 3:
        print(billing.close_period(workdir, argv[2]))
        return 0
    if command == "reconcile" and len(argv) == 4:
        print(inventory.reconcile(workdir, argv[2], int(argv[3])))
        return 0
    if command == "sweep" and len(argv) >= 4:
        for record in dispatch_sweep.sweep(workdir, argv[3:], argv[2]):
            print(record)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
