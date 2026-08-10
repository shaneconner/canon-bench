# metrics-collector

Pulls per-host samples from the vendor metrics API and rolls them up for the
nightly digest. Runs on metrics-cron-01.

    collector/   cpu, memory and disk pulls, plus the rollup maths
    tools/       the cron entry point and the human-readable report
    util/        table, percentile, retry and shard-placement helpers
    tests/       python3 tests/run_tests.py

The vendor SDK comes from the internal package index and is not checked in. In a
dev checkout it sits beside the work tree, so
`PYTHONPATH=../vendor_sdk python3 tools/report.py`.

Rough edges

  - the auth handshake dominates a collection run, and cpu/memory/disk each pay
    for their own with their own copy of the same settings, which have drifted
  - util/hashring.py only feeds the placement report nobody reads
  - util/quantile.py and util/backoff.py are leftovers from the old agent-side
    collector; nothing in the nightly path calls them yet
