"""eventline test suite: python3 tests/run_tests.py"""

import sys
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eventline import digest, priority, schedule, slugs, store, textbox, window

TITLES = [
    "Payments incident review",
    "Weekly release train",
    "Design review: feeds",
    "Cluster maintenance",
    "Team standup",
    "Roadmap review",
]
KINDS = ["incident", "release", "review", "maintenance", "standup", "review"]
DAY_TIMES = [time(0, 0, 0), time(9, 30, 0), time(17, 15, 0), time(23, 59, 59)]
FIRST_DAY = date(2026, 5, 4)
DAYS = 6


def sample_events():
    """DAYS days x len(DAY_TIMES) events, including the first and last second."""
    events = []
    for step in range(DAYS):
        day = FIRST_DAY + timedelta(days=step)
        for slot, moment in enumerate(DAY_TIMES):
            index = step * len(DAY_TIMES) + slot
            events.append(
                {
                    "id": f"T{index:02d}",
                    "title": TITLES[index % len(TITLES)],
                    "starts_at": datetime.combine(day, moment),
                    "duration_min": 15 + (index * 7) % 90,
                    "kind": KINDS[index % len(KINDS)],
                }
            )
    return events


def test_window_bounds():
    events = sample_events()
    day = FIRST_DAY + timedelta(days=2)
    low, high = digest.day_bounds(day)
    picked = window.events_between(events, low, high)
    assert len(picked) == len(DAY_TIMES), f"events_between(day): {len(picked)} != {len(DAY_TIMES)}"
    assert [e["starts_at"].date() for e in picked] == [day] * len(DAY_TIMES)


def test_daily_counts():
    events = sample_events()
    start = datetime.combine(FIRST_DAY, time(0, 0, 0))
    end = datetime.combine(FIRST_DAY + timedelta(days=DAYS - 1), time(23, 59, 59))
    counts = digest.daily_counts(events, start, end)
    assert len(counts) == DAYS, f"daily_counts(): {len(counts)} days != {DAYS}"
    total = sum(counts.values())
    assert total == len(events), f"daily_counts(): counted {total} of {len(events)} events"
    assert sorted(counts.values()) == [len(DAY_TIMES)] * DAYS, f"daily_counts(): {sorted(counts.values())}"
    assert digest.busiest(counts) == (FIRST_DAY, len(DAY_TIMES))


def test_upcoming():
    events = sample_events()
    since = datetime.combine(FIRST_DAY, time(0, 0, 0))
    picked = window.upcoming(events, since, 1)
    assert picked[0]["starts_at"] == since
    assert all(e["starts_at"] <= since + timedelta(days=1) for e in picked)


def test_schedule():
    start = datetime(2026, 5, 4, 9, 0, 0)
    occurrences = schedule.next_occurrences(start, 7, 3)
    assert occurrences == [start + timedelta(days=7 * n) for n in (1, 2, 3)]
    between = schedule.occurrences_between(start, 7, start, start + timedelta(days=21))
    assert len(between) == 4, f"occurrences_between(): {len(between)} != 4"
    expanded = schedule.expand(sample_events()[0], 7, 2)
    assert [e["id"] for e in expanded] == ["T00-r1", "T00-r2"]


def test_store_roundtrip():
    events = sample_events()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "events.jsonl"
        store.write_records(events, path)
        loaded = store.read_records(path)
    assert loaded == events, "store round trip changed the records"


def test_slugs():
    assert slugs.slugify("Design review: feeds") == "design-review-feeds"
    assert slugs.slugify("!!!") == "event"
    batch = slugs.slug_batch(["Team standup", "Cluster maintenance"])
    assert batch == ["team-standup", "cluster-maintenance"]


def test_priority():
    events = sample_events()
    top = priority.rank(events, 1)[0]
    assert top["kind"] == "incident", f"rank(): top kind {top['kind']}"
    kept = priority.load_shed(events, 120)
    assert sum(e["duration_min"] for e in kept) <= 120


def test_textbox():
    lines = textbox.box(["ab", "cdef"])
    assert lines[0] == "+------+" and lines[1] == "| ab   |"
    assert textbox.wrap("one two three four", 9) == ["one two", "three", "four"]


def main():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} eventline tests pass")


if __name__ == "__main__":
    main()
