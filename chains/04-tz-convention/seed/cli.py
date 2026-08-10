"""eventline command line.

    python3 cli.py digest --from 2026-06-01 --days 7
    python3 cli.py agenda --from 2026-06-01 --days 3 [--top 5]
    python3 cli.py feed   --from 2026-06-01 --days 3

The cron entries on the deploy host always pass an explicit --from, so every
command works off the window it is handed rather than off a clock.
"""

import argparse
from datetime import datetime, time, timedelta

from eventline import calendarfmt, digest, priority, store, textbox, window


def parse_day(text):
    return datetime.combine(datetime.strptime(text, "%Y-%m-%d").date(), time(0, 0, 0))


def cmd_digest(args, events):
    start = parse_day(args.start)
    end = start + timedelta(days=args.days - 1, hours=23, minutes=59, seconds=59)
    counts = digest.daily_counts(events, start, end)
    for line in textbox.render(f"digest from {args.start}", digest.render(counts)):
        print(line)


def cmd_agenda(args, events):
    start = parse_day(args.start)
    picked = window.upcoming(events, start, args.days)
    if args.top:
        picked = priority.rank(picked, args.top)
    for line in textbox.render(f"agenda from {args.start}", [calendarfmt.line(e) for e in picked]):
        print(line)


def cmd_feed(args, events):
    from eventline import slugs

    start = parse_day(args.start)
    picked = window.upcoming(events, start, args.days)
    for slug in slugs.slug_batch([event["title"] for event in picked]):
        print(slugs.feed_path(slug))


def build_parser():
    parser = argparse.ArgumentParser(prog="eventline")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("digest", "agenda", "feed"):
        child = sub.add_parser(name)
        child.add_argument("--from", dest="start", required=True)
        child.add_argument("--days", type=int, default=7)
        if name == "agenda":
            child.add_argument("--top", type=int, default=0)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    events = store.load_events()
    handler = {"digest": cmd_digest, "agenda": cmd_agenda, "feed": cmd_feed}[args.command]
    handler(args, events)


if __name__ == "__main__":
    main()
