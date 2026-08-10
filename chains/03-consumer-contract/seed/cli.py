"""Daily ledger reporting job.

    python3 cli.py --date 2026-03-03

Prints the day summary and writes the report file.
"""

import argparse

from report import config
from report import summary
from report import writer


def main(argv=None):
    parser = argparse.ArgumentParser(description="daily ledger report")
    parser.add_argument("--date", default=config.DEFAULT_DATE, help="ledger date to report on")
    parser.add_argument("--no-write", action="store_true", help="print the summary only")
    args = parser.parse_args(argv)

    for line in summary.summary_lines(args.date):
        print(line)

    if not args.no_write:
        path = writer.write_report(args.date)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
