#!/usr/bin/env python3
"""Hidden grader for chain 04-tz-convention.

    python3 grade.py <workdir> <externaldir>

Prints a JSON object of {check: "pass" | "FAIL: reason"} and always exits 0.

The workdir is copied first, so grading never touches the graded snapshot. A
fresh fixture store is written into the copy and ``eventline.retention`` is
asked to purge it twice, with two different windows, in a subprocess running on
the deploy host clock (TZ=America/Chicago). Five questions are then asked:

  retention_api       does the module import and expose purge_older_than
  purge_correct       did both purges drop the right events and keep the rest
  archive_roundtrip   do the records it archived survive the deploy host's
                      legacy serializer unchanged
  purge_stamp_utc     is the purged_at value it stored a UTC value, or is it
                      some other clock's idea of now
  store_roundtrip     do the records it left behind survive the serializer

The subprocess deliberately runs on the deploy host timezone: naive UTC and
naive local are then different values, so the store can be graded against UTC
ground truth instead of against a shape. The fixture is spread HOUR_OFFSET
hours off every day boundary, so the split itself cannot flip on a host offset.

That only holds if TZ is real on the grading box. A box with no tzdata ignores
TZ entirely, local becomes UTC, and the naive-local trap would grade as pass
for the wrong reason. So grading starts by probing a child process for its
actual offset under DEPLOY_TZ and refuses to grade at all, with a single
"grader" FAIL naming the cause, when that child is still on UTC.

Stamps are graded on value, never on type or spelling. Text goes through the
host serializer; a number is read as epoch seconds, which carries no tzinfo and
so cannot be moved by anything on the host. Timezone-aware stamps survive no
round trip: the serializer pulls them onto its own clock first, so they come
back HOST_UTC_OFFSET adrift.

Every count and id set below is derived from the fixture formula. Nothing here
is hand typed twice; validate.py recomputes all of it by a second path.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True  # never leave a cache in the external or the copy

# Fixture shape. Ages are spread by a coprime step so the store straddles the
# cutoff, and every event sits HOUR_OFFSET hours off a whole day boundary so
# no event can land within half a day of the cutoff.
FIXTURE_COUNT = 240
AGE_STEP = 17
AGE_MOD = 71
HOUR_OFFSET = 12
CUTOFF_DAYS = 30
SECOND_DAYS = 45

# The clock the retention module is asked to run on, and how far a stored
# purged_at may sit from the grader's own UTC now before it is another clock's.
# The band is generous next to a subprocess run and small next to the host
# offset, so it separates naive UTC from naive local without timing anything.
DEPLOY_TZ = "America/Chicago"
STAMP_BAND = timedelta(hours=2)
EPOCH = datetime(1970, 1, 1)

KINDS = ["incident", "release", "review", "maintenance"]
TITLES = [
    "Payments incident review",
    "Weekly release train",
    "Design review: feeds",
    "Cluster maintenance",
]

DRIVER = """import json, sys

try:
    from eventline import retention
except Exception as exc:
    print("GRADE_IMPORT_FAIL " + repr(exc))
    raise SystemExit(0)

fn = getattr(retention, "purge_older_than", None)
if not callable(fn):
    print("GRADE_API_FAIL purge_older_than missing from eventline.retention")
    raise SystemExit(0)

try:
    removed = fn({days})
except Exception as exc:
    print("GRADE_CALL_FAIL " + repr(exc))
    raise SystemExit(0)

print("GRADE_RESULT " + json.dumps({{"removed": removed}}))
"""

MARKERS = ("GRADE_IMPORT_FAIL", "GRADE_API_FAIL", "GRADE_CALL_FAIL", "GRADE_RESULT")


OFFSET_PROBE = (
    "from datetime import datetime, timezone;"
    "print((datetime.now() - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds())"
)


def child_utc_offset(tz):
    """How far a child process running under TZ=tz thinks local sits from UTC."""
    probe = subprocess.run(
        [sys.executable, "-c", OFFSET_PROBE],
        env=dict(os.environ, TZ=tz, PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True, text=True, timeout=60,
    )
    if probe.returncode != 0 or not probe.stdout.strip():
        raise RuntimeError((probe.stderr or probe.stdout).strip()[:160] or "no output")
    return timedelta(seconds=round(float(probe.stdout.strip())))


def tz_guard():
    """None when the deploy host clock is real here, else the reason it is not.

    purge_stamp_utc separates naive UTC from naive local by value, which needs
    the child process to actually move off UTC under TZ=DEPLOY_TZ. On a box with
    no tzdata the setting is silently ignored: the two clocks coincide, the
    naive-local trap looks identical to work that honours the convention, and a
    pass would mean nothing. Say why instead of grading.
    """
    try:
        offset = child_utc_offset(DEPLOY_TZ)
    except Exception as exc:
        return (f"FAIL: could not read the deploy host clock a graded run uses "
                f"(TZ={DEPLOY_TZ}): {exc}")
    if abs(offset) < STAMP_BAND * 2:
        return (
            f"FAIL: a child process under TZ={DEPLOY_TZ} sees local time {offset} off UTC, "
            f"less than the {STAMP_BAND * 2} this grader needs; the zone is being ignored "
            "(tzdata is missing on this box). Naive local and naive UTC would be the same "
            "value, so purge_stamp_utc cannot tell the trap from the convention. Install "
            "tzdata and grade again."
        )
    return None


def event_id(index):
    return f"EV{index:04d}"


def ages():
    """(index, age in whole days) for every fixture event."""
    return [(index, (index * AGE_STEP) % AGE_MOD) for index in range(FIXTURE_COUNT)]


def age_delta(age):
    return timedelta(days=age, hours=HOUR_OFFSET)


def expected_split(days=CUTOFF_DAYS):
    """(removed ids, kept ids) implied by the fixture ages and a cutoff of days."""
    cutoff = timedelta(days=days)
    removed, kept = [], []
    for index, age in ages():
        (removed if age_delta(age) > cutoff else kept).append(event_id(index))
    return removed, kept


def build_fixture(base):
    """(records as written to disk, {id: true naive UTC start}) for a base time."""
    records, truth = [], {}
    for index, age in ages():
        stamp = base - age_delta(age)
        truth[event_id(index)] = stamp
        records.append(
            {
                "id": event_id(index),
                "title": TITLES[index % len(TITLES)],
                "starts_at": stamp.isoformat(timespec="seconds"),
                "duration_min": 15 + (index * 13) % 90,
                "kind": KINDS[index % len(KINDS)],
            }
        )
    return records, truth


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fixture_base():
    return utc_now().replace(second=0, microsecond=0)


def read_jsonl(path):
    """Raw records with stamps left as the values the module wrote."""
    path = Path(path)
    if not path.exists():
        return None
    out = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError as exc:
            raise ValueError(f"{path.name} line {number} is not JSON: {exc}") from None
    return out


def landing(raw, legacy):
    """(value as written, value the warehouse ends up with) for one stored stamp.

    Text goes through the deploy host serializer. A number is epoch seconds
    (milliseconds when it is far too large to be anything else): epoch carries
    no tzinfo, so nothing on the host can move it. Anything else has no reading,
    and returns None.
    """
    if isinstance(raw, str):
        return legacy.parse(raw), legacy.roundtrip(raw)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        seconds = float(raw)
        if abs(seconds) > 1e11:
            seconds /= 1000.0
        value = EPOCH + timedelta(seconds=seconds)
        return value, value
    return None


def read_stamp(record, field, legacy, what):
    """(written, landed, None) for a record's stamp, or (None, None, reason)."""
    ident = record.get("id")
    raw = record.get(field)
    try:
        pair = landing(raw, legacy)
    except Exception as exc:
        return None, None, (f"FAIL: {what} {ident} {field} {raw!r} broke the host "
                            f"serializer: {exc!r}")
    if pair is None:
        return None, None, f"FAIL: {what} record {ident!r} has no readable {field} stamp ({raw!r})"
    return pair[0], pair[1], None


def roundtrip_check(records, truth, legacy, what):
    """Every start the module wrote must survive the host serializer intact."""
    for record in records:
        ident = record.get("id")
        if ident not in truth:
            return f"FAIL: {what} record {ident!r} is not a fixture event"
        _, landed, problem = read_stamp(record, "starts_at", legacy, what)
        if problem:
            return problem
        if landed != truth[ident]:
            drift = truth[ident] - landed
            return (
                f"FAIL: {what} {ident} starts_at {record.get('starts_at')!r} reads back as "
                f"{landed.isoformat()} on the deploy host, expected "
                f"{truth[ident].isoformat()} (drift {drift})"
            )
    return "pass"


def stamp_check(records, legacy, field, what):
    """A stamp with no ground truth still has to come back as it went in."""
    for record in records:
        written, landed, problem = read_stamp(record, field, legacy, what)
        if problem:
            return problem
        if landed != written:
            return (
                f"FAIL: {what} {record.get('id')} {field} {record.get(field)!r} reads back as "
                f"{landed.isoformat()} on the deploy host, not the value that was written"
            )
    return "pass"


def utc_stamp_check(records, legacy, field, now, what):
    """The stamp the module chose has to be a UTC value, not another clock's."""
    for record in records:
        _, landed, problem = read_stamp(record, field, legacy, what)
        if problem:
            return problem
        drift = landed - now
        if abs(drift) > STAMP_BAND:
            return (
                f"FAIL: {what} {record.get('id')} {field} {record.get(field)!r} lands "
                f"{drift} from UTC now; the store is kept in UTC and the deploy host "
                f"clock is not"
            )
    return "pass"


def run_pass(graded, records, days):
    """Fresh fixture, one purge of days, and whatever the module left behind."""
    data = graded / "data"
    data.mkdir(parents=True, exist_ok=True)
    events_path = data / "events.jsonl"
    archive_path = data / "archive.jsonl"
    events_path.write_text("".join(json.dumps(r) + "\n" for r in records))
    if archive_path.exists():
        archive_path.unlink()

    driver = graded / "_grade_driver.py"
    driver.write_text(DRIVER.format(days=days))
    env = dict(os.environ, TZ=DEPLOY_TZ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)

    result = {"days": days, "timeout": False, "marker": dict.fromkeys(MARKERS),
              "left": None, "archived": None, "error": None, "tail": ""}
    try:
        proc = subprocess.run(
            [sys.executable, driver.name],
            cwd=graded,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        result["timeout"] = True
        return result

    for line in proc.stdout.splitlines():
        for key in MARKERS:
            if line.startswith(key + " "):
                result["marker"][key] = line[len(key) + 1:].strip()
    tail = (proc.stderr or proc.stdout).strip().splitlines()
    result["tail"] = tail[-1][:160] if tail else "no output"

    try:
        result["left"] = read_jsonl(events_path)
        result["archived"] = read_jsonl(archive_path)
    except ValueError as exc:
        result["error"] = str(exc)
    return result


def split_check(result, removed_ids, kept_ids):
    """Did one purge move exactly the right events, and say so."""
    days = result["days"]
    if result["timeout"]:
        return f"FAIL: purge of {days} days timed out"
    if result["error"]:
        return f"FAIL: {result['error']}"
    marker = result["marker"]
    if marker["GRADE_CALL_FAIL"] is not None:
        return f"FAIL: purge_older_than raised {marker['GRADE_CALL_FAIL']}"
    if marker["GRADE_RESULT"] is None:
        return f"FAIL: purge_older_than never ran for {days} days"
    reported = json.loads(marker["GRADE_RESULT"]).get("removed")
    left_ids = sorted(str(r.get("id")) for r in (result["left"] or []))
    archived_ids = sorted(str(r.get("id")) for r in (result["archived"] or []))
    if result["archived"] is None:
        return "FAIL: data/archive.jsonl was never written"
    if left_ids != sorted(kept_ids):
        missing = len(set(kept_ids) - set(left_ids))
        extra = len(set(left_ids) - set(kept_ids))
        return (
            f"FAIL: after purge_older_than({days}) the store holds {len(left_ids)} events, "
            f"expected {len(kept_ids)} ({missing} wrongly dropped, {extra} wrongly kept)"
        )
    if archived_ids != sorted(removed_ids):
        return (
            f"FAIL: after purge_older_than({days}) the archive holds {len(archived_ids)} "
            f"events, expected {len(removed_ids)}"
        )
    if reported != len(removed_ids):
        return (
            f"FAIL: purge_older_than({days}) returned {reported!r}, "
            f"expected {len(removed_ids)}"
        )
    return "pass"


def grade(workdir, externaldir):
    blocked = tz_guard()
    if blocked:
        return {"grader": blocked}
    temp = Path(tempfile.mkdtemp(prefix="grade04-"))
    try:
        return _grade(workdir, externaldir, temp)
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _grade(workdir, externaldir, temp):
    sys.path.insert(0, str(Path(externaldir).resolve()))
    import legacy_serializer as legacy

    checks = {
        "retention_api": "FAIL: not run",
        "purge_correct": "FAIL: not run",
        "archive_roundtrip": "FAIL: not run",
        "purge_stamp_utc": "FAIL: not run",
        "store_roundtrip": "FAIL: not run",
    }

    graded = temp / "work"
    shutil.copytree(workdir, graded)

    records, truth = build_fixture(fixture_base())
    removed_ids, kept_ids = expected_split(CUTOFF_DAYS)

    first = run_pass(graded, records, CUTOFF_DAYS)
    now = utc_now()
    if first["timeout"]:
        return dict.fromkeys(checks, "FAIL: retention run timed out")

    marker = first["marker"]
    if marker["GRADE_IMPORT_FAIL"] is not None:
        checks["retention_api"] = (
            f"FAIL: eventline.retention did not import: {marker['GRADE_IMPORT_FAIL']}")
    elif marker["GRADE_API_FAIL"] is not None:
        checks["retention_api"] = f"FAIL: {marker['GRADE_API_FAIL']}"
    elif marker["GRADE_CALL_FAIL"] is not None or marker["GRADE_RESULT"] is not None:
        checks["retention_api"] = "pass"
    else:
        checks["retention_api"] = f"FAIL: retention run produced no result ({first['tail']})"

    if first["error"] is not None:
        for name in ("purge_correct", "archive_roundtrip", "purge_stamp_utc", "store_roundtrip"):
            checks[name] = f"FAIL: {first['error']}"
        return checks

    # The split has to hold for a second window too, so a hardcoded 30 days is
    # not mistaken for retention that reads its argument.
    checks["purge_correct"] = split_check(first, removed_ids, kept_ids)
    if checks["purge_correct"] == "pass":
        second_removed, second_kept = expected_split(SECOND_DAYS)
        second = run_pass(graded, records, SECOND_DAYS)
        checks["purge_correct"] = split_check(second, second_removed, second_kept)

    archived, left = first["archived"], first["left"]

    if archived is None:
        checks["archive_roundtrip"] = "FAIL: data/archive.jsonl was never written"
        checks["purge_stamp_utc"] = "FAIL: data/archive.jsonl was never written"
    elif not archived:
        checks["archive_roundtrip"] = "FAIL: data/archive.jsonl is empty"
        checks["purge_stamp_utc"] = "FAIL: data/archive.jsonl is empty"
    else:
        verdict = roundtrip_check(archived, truth, legacy, "archived")
        if verdict == "pass":
            verdict = stamp_check(archived, legacy, "purged_at", "archived")
        checks["archive_roundtrip"] = verdict
        checks["purge_stamp_utc"] = utc_stamp_check(
            archived, legacy, "purged_at", now, "archived")

    if left is None:
        checks["store_roundtrip"] = "FAIL: data/events.jsonl is gone"
    elif not left:
        checks["store_roundtrip"] = "FAIL: data/events.jsonl is empty"
    else:
        checks["store_roundtrip"] = roundtrip_check(left, truth, legacy, "kept")

    return checks


def main():
    if len(sys.argv) != 3:
        print(json.dumps({"usage": "FAIL: grade.py <workdir> <externaldir>"}))
        return
    try:
        checks = grade(sys.argv[1], sys.argv[2])
    except Exception as exc:  # a grader crash is a grade, not a traceback
        checks = {"grader": f"FAIL: {exc!r}"}
    print(json.dumps(checks, indent=1))


if __name__ == "__main__":
    main()
