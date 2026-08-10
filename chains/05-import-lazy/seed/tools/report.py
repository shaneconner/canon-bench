"""Human-readable table of the latest pull."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collector import cpu, disk, memory
from collector.aggregate import BUSY_THRESHOLD, summarize
from util.tabular import Table

METRICS = (("cpu", cpu), ("mem", memory), ("disk", disk))
HEADERS = ["metric", "hosts", "total", "peak", "peak host", "busy>=%d" % BUSY_THRESHOLD]

# The report's columns never change, so its table is built here and reused.
TABLE = Table(HEADERS)


def rows():
    out = []
    for name, module in METRICS:
        rollup = summarize(module.collect())
        out.append([
            name,
            rollup["reporting"],
            rollup["total"],
            rollup["peak"],
            rollup["peak_host"],
            rollup["busy"],
        ])
    return out


def main():
    print(TABLE.render(rows()))


if __name__ == "__main__":
    main()
