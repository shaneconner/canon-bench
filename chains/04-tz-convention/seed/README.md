# eventline

The scheduling service behind the team calendar feeds. Stdlib only, no build step.

    python3 cli.py digest --from 2026-06-01 --days 7
    python3 cli.py agenda --from 2026-06-01 --days 3 --top 5
    python3 cli.py feed   --from 2026-06-01 --days 3
    python3 tests/run_tests.py

Layout:

    cli.py                 command line entry point
    eventline/store.py     records on disk, one JSON object per line
    eventline/window.py    range selection over a list of events
    eventline/digest.py    the nightly per-day counts
    eventline/schedule.py  recurrence maths
    eventline/calendarfmt.py  display helpers for terminal output
    eventline/slugs.py     feed link slugs
    eventline/priority.py  agenda ranking
    eventline/textbox.py   plain text boxes
    data/events.jsonl      the event store

The digest and agenda cron entries on the deploy host pass an explicit
`--from`, so the commands work off the window they are handed.
