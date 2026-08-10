"""Reporting job test suite.

    python3 tests/run_tests.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from report import aggregate
from report import anomaly
from report import idcodes

DATE = "2026-03-03"
LIGHT_DATE = "2026-03-05"

EXPECTED_CATEGORY_ROWS = [
    {"category": "fuel", "count": 13, "amount_cents": 225565},
    {"category": "groceries", "count": 12, "amount_cents": 254338},
    {"category": "lodging", "count": 14, "amount_cents": 294802},
    {"category": "meals", "count": 15, "amount_cents": 329990},
    {"category": "supplies", "count": 13, "amount_cents": 281288},
]
EXPECTED_DAY_TOTAL = 1385983
EXPECTED_DAY_COUNT = 67
EXPECTED_LIGHT_TOTAL = 620827
EXPECTED_LIGHT_COUNT = 33
EXPECTED_COUNTS_BY_DATE = {
    "2026-03-02": 68,
    "2026-03-03": 67,
    "2026-03-04": 68,
    "2026-03-05": 33,
}

FAILURES = []


def check(name, actual, expected):
    if actual != expected:
        FAILURES.append(f"{name}: {actual!r} != {expected!r}")


def test_daily_totals():
    check("category_rows", aggregate.category_rows(DATE), EXPECTED_CATEGORY_ROWS)
    check("day_total", aggregate.day_total(DATE), EXPECTED_DAY_TOTAL)
    check("day_count", aggregate.day_count(DATE), EXPECTED_DAY_COUNT)
    check("day_total light", aggregate.day_total(LIGHT_DATE), EXPECTED_LIGHT_TOTAL)
    check("day_count light", aggregate.day_count(LIGHT_DATE), EXPECTED_LIGHT_COUNT)
    check("counts_by_date", aggregate.counts_by_date(), EXPECTED_COUNTS_BY_DATE)


def test_anomaly():
    counts = {"2026-04-01": 40, "2026-04-02": 41, "2026-04-03": 39, "2026-04-04": 12}
    check("outliers", anomaly.outliers(counts), ["2026-04-04"])
    check("outliers quiet", anomaly.outliers({"2026-04-01": 40, "2026-04-02": 41}), [])
    check("median", anomaly.median([3, 9, 4]), 4)


def test_idcodes():
    for number in (0, 7, 4321, 987654):
        check(f"idcode roundtrip {number}", idcodes.decode(idcodes.encode(number)), number)
    check("idcode shape", idcodes.encode(1295), "ZZ" + idcodes.check_digits("ZZ"))


def main():
    for test in (test_daily_totals, test_anomaly, test_idcodes):
        test()
    if FAILURES:
        for failure in FAILURES:
            print(f"FAIL {failure}")
        print(f"{len(FAILURES)} failing check(s)")
        return 1
    print("all checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
