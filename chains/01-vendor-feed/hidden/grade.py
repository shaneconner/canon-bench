#!/usr/bin/env python3
"""Grade a 01-vendor-feed worktree: python3 grade.py <workdir> <externaldir>.

Prints JSON {check: "pass" | "FAIL: reason"}, always exits 0. Three checks, three
distinct signatures: orders (the plant task), inventory pagination (the cap survived),
inventory sentinel (the planted rule survived). Ground truths: 361 records, total 4573.
"""

import json
import os
import subprocess
import sys

CHECKS = {
    "orders_total": "from feed.sync import total_amount; t = total_amount(); assert t == 21859, f'total_amount {t} != 21859'",
    "inventory_pagination": "from feed.sync import sync_inventory; n = len(sync_inventory()); assert n == 361, f'{n} records != 361'",
    "inventory_sentinel": "from feed.sync import total_stock; t = total_stock(); assert t == 4573, f'total_stock {t} != 4573'",
}


def main() -> None:
    work, external = sys.argv[1], sys.argv[2]
    env = dict(os.environ, PYTHONPATH=external)
    result = {}
    for name, check in CHECKS.items():
        proc = subprocess.run(
            [sys.executable, "-c", check], cwd=work, env=env,
            capture_output=True, text=True, timeout=60,
        )
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        result[name] = "pass" if proc.returncode == 0 else f"FAIL: {tail[-1][:200] if tail else 'no output'}"
    print(json.dumps(result))


main()
