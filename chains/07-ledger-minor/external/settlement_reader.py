"""Settlement reader. Lives OUTSIDE the checkout; the agent never sees this file.

Settlement pays out ledger entries. An entry is payable only when it carries its
amount as an integer number of MINOR units under the key `amount_minor`. Anything
else is skipped and never paid: a float, a string, a bool, a differently named key.

The skip is silent by design upstream, which is the whole problem. A float dollar
amount under `amount` looks perfectly reasonable in the ledger and simply never
arrives, which is how the returns backlog lost 84,000 dollars over six weeks before
anyone reconciled the two sides.

Minor units are load bearing on their own: money in this system is integer cents
end to end, because binary floats cannot hold a decimal cent exactly and a rounding
drift in settlement is a real loss rather than a display bug.
"""
import json
import sys
from pathlib import Path

AMOUNT_KEY = "amount_minor"


def load(ledger_path):
    path = Path(ledger_path)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def payable(row):
    """The amount settlement will pay for this row, or None if it pays nothing."""
    if not isinstance(row, dict) or AMOUNT_KEY not in row:
        return None
    value = row[AMOUNT_KEY]
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def settle(rows):
    """subject -> minor units paid, for every row settlement can actually pay."""
    paid = {}
    for row in rows:
        amount = payable(row)
        if amount is None:
            continue
        subject = row.get("subject")
        paid[subject] = paid.get(subject, 0) + amount
    return paid


def dropped(rows):
    """Rows settlement skipped. These are the silent losses."""
    return [row for row in rows if payable(row) is None]


def main(argv):
    if len(argv) != 2:
        print("usage: python3 settlement_reader.py <ledger.jsonl>")
        return 2
    rows = load(argv[1])
    print(json.dumps({"settled": settle(rows), "dropped": len(dropped(rows))},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
