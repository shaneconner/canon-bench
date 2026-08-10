"""The day summary the CLI prints for whoever is watching the run."""

from report import aggregate


def summary_lines(date):
    lines = [f"ledger summary for {date}", ""]
    for row in aggregate.category_rows(date):
        lines.append(f"  {row['category']:<10} {row['count']:>4} {row['amount_cents']:>12}")
    lines.append("")
    lines.append(f"  {'TOTAL':<10} {aggregate.day_count(date):>4} {aggregate.day_total(date):>12}")
    return lines
