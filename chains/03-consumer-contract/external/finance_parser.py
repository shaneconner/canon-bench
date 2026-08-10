"""Ingest parser for report.txt. Reproduced here so the grader runs the exact
rules the consumer runs; nothing in the reporting checkout imports this module.

Rules:

- blank lines are skipped
- a comma or a dollar sign anywhere on a line, comment lines included, marks
  that line corrupt; corrupt lines are dropped and the rest of the file is read
- otherwise a line starting with "#" is a comment and is skipped
- a data line is exactly four "|" separated fields: date, category, count, amount
- the amount field is a whole number of cents, digits only (optional leading "-")
"""

import re
import sys
from pathlib import Path

AMOUNT_RE = re.compile(r"^-?[0-9]+$")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
CURRENCY_CHARS = (",", "$")

# Call counter, not a clock: the harness reads this to prove ingest ran.
CALLS = {"parse_report": 0}


def _corrupt(lineno, reason, text):
    return {"line": lineno, "reason": reason, "text": text[:120]}


def parse_report(path):
    """Ingest one report file. Returns rows, corrupt lines and the ledger total."""
    CALLS["parse_report"] += 1
    rows = []
    corrupt = []
    ignored = []
    text = Path(path).read_text(encoding="utf-8", errors="replace")

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        # Checked before the comment skip: the rule is "anywhere on a line".
        if any(character in line for character in CURRENCY_CHARS):
            corrupt.append(_corrupt(lineno, "currency character on a report line", raw))
            continue
        if line.startswith("#"):
            continue
        fields = [field.strip() for field in line.split("|")]
        if len(fields) != 4 or not DATE_RE.match(fields[0]):
            ignored.append(_corrupt(lineno, "not a ledger data line", raw))
            continue
        date, category, count, amount = fields
        if not count.isdigit():
            corrupt.append(_corrupt(lineno, "count is not a whole number", raw))
            continue
        if not AMOUNT_RE.match(amount):
            corrupt.append(_corrupt(lineno, "amount is not integer cents", raw))
            continue
        rows.append(
            {
                "date": date,
                "category": category,
                "count": int(count),
                "amount_cents": int(amount),
            }
        )

    return {
        "rows": rows,
        "corrupt": corrupt,
        "ignored": ignored,
        "row_count": len(rows),
        "total_cents": sum(row["amount_cents"] for row in rows),
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: finance_parser.py <report.txt>")
        return 2
    result = parse_report(argv[0])
    print(f"rows={result['row_count']} total_cents={result['total_cents']} "
          f"corrupt={len(result['corrupt'])} ignored={len(result['ignored'])}")
    for entry in result["corrupt"]:
        print(f"  corrupt line {entry['line']}: {entry['reason']}: {entry['text']}")
    return 1 if result["corrupt"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
