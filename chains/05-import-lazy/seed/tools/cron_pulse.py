"""Nightly cron entry: pull every metric and print one machine-readable line each."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collector import cpu, disk, memory
from collector.aggregate import summarize

METRICS = (("cpu", cpu), ("mem", memory), ("disk", disk))


def run():
    lines = []
    for name, module in METRICS:
        rollup = summarize(module.collect())
        lines.append(
            "%s reporting=%s total=%s peak=%s@%s"
            % (name, rollup["reporting"], rollup["total"], rollup["peak"], rollup["peak_host"])
        )
    return lines


def main():
    for line in run():
        print(line)


if __name__ == "__main__":
    main()
