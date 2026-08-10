"""Writes report.txt at the end of a run."""

from pathlib import Path

from report import aggregate
from report import config


def report_lines(date):
    lines = ["# ledger daily report"]
    separator = config.FIELD_SEPARATOR
    for row in aggregate.category_rows(date):
        lines.append(
            separator.join(
                [date, row["category"], str(row["count"]), str(row["amount_cents"])]
            )
        )
    return lines


def write_report(date, path=None):
    target = Path(path) if path is not None else config.REPORT_PATH
    target.write_text("\n".join(report_lines(date)) + "\n", encoding="utf-8")
    return target
