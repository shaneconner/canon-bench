"""Unit suite for the pure helpers.

    python3 tests/run_tests.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collector.aggregate import delta, summarize
from util.backoff import delay, schedule
from util.hashring import layout, moved, place
from util.quantile import percentile, spread
from util.tabular import Table, render

# util.quantile
assert percentile([5, 1, 4, 2, 3], 50) == 3
assert percentile([5, 1, 4, 2, 3], 100) == 5
assert percentile([5, 1, 4, 2, 3], 1) == 1
assert spread(list(range(1, 11))) == 8

# util.backoff
assert schedule(4) == [2, 4, 8, 16]
assert delay(9) == 300

# util.hashring
assert place(7, ["a", "b", "c"]) == place(7, ["c", "b", "a"])
assert place(3, ["a", "b", "c"]) in ("a", "b", "c")
assert len(layout(["a", "b"])) == 200
assert set(layout(["a", "b", "c"]).values()) == {"a", "b", "c"}
assert moved(layout(["a", "b"]), layout(["a", "b"])) == 0

# util.tabular
assert render(["a", "bb"], [[1, 2]]) == "a  bb\n-  --\n1  2"
assert Table(["a", "bb"]).render([[1, 2]]) == "a  bb\n-  --\n1  2"

# collector.aggregate
assert delta({"n1": 4, "n2": 9}, {"n2": 11, "n3": 1}) == {"n2": 2}

# node-04 missed its window last night, so the vendor reported null for it and
# the digest job blew up on the rollup instead of skipping the host.
pull = {"node-01": 51, "node-02": 68, "node-03": 85, "node-04": None, "node-05": 12}
rollup = summarize(pull)
assert rollup["hosts"] == 5, rollup
assert rollup["reporting"] == 4, rollup
assert rollup["total"] == 216, rollup
assert rollup["peak"] == 85, rollup
assert rollup["peak_host"] == "node-03", rollup
assert rollup["busy"] == 1, rollup

empty = summarize({})
assert empty["hosts"] == 0 and empty["reporting"] == 0, empty
assert empty["total"] == 0 and empty["peak"] == 0, empty
assert empty["peak_host"] is None, empty

print("tests pass")
