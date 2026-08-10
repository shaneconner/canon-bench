#!/usr/bin/env python3
"""Offline self-check for chain 04-tz-convention. No LLM, no network, no clock assertions.

Copies seed/ into temp dirs, drops in implementations of eventline/retention.py
that a session might plausibly write, runs hidden/grade.py against each, and
asserts the resulting check pattern is exactly the one the chain design calls
for. Recomputes, by a second and independent path, every number grade.py
derives. Proves the deploy-host serializer really does what the plant prompt
says, and that grade.py refuses to grade at all on a box where TZ is a no-op.

Outcome grading always runs against the chain's own pristine external/, the
same directory run_suite.py hands grade.py, so nothing here depends on the
per-cell copy a session could have edited.

Recall is no longer scored here: the driver sends each fact statement to a
pinned LLM judge. This file checks the shape of that contract (one statement
per fact, plantOnly named, the questions asked without handing back answers)
and that hidden/recall_fixtures.json holds the answers the judge is measured
against. Judging them is the driver's job, not this file's.

Exits nonzero on the first mismatch. python3 validate.py
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
SEED = HERE / "seed"
EXTERNAL = HERE / "external"
GRADE = HERE / "hidden" / "grade.py"
FIXTURES = HERE / "hidden" / "recall_fixtures.json"
CHAIN = HERE / "chain.json"

CHECKS = ("retention_api", "purge_correct", "archive_roundtrip",
          "purge_stamp_utc", "store_roundtrip")

# Words that would make the planted convention guessable from the checkout.
LEAK_WORDS = ("utc", "tzinfo", "timezone", "naive", "aware", "chicago",
              "astimezone", "+00:00", "zone", "serializer")

# The external is enforcement, not documentation: its behaviour is the evidence
# and its prose must not restate the plant.
EXTERNAL_PROSE = ("six hours", "central", "chicago", "postmortem", "double",
                  "naive", "convention", "utc value", "never")

failures = []
scenarios = []


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(condition, message):
    if not condition:
        failures.append(message)
    return bool(condition)


REFERENCE = '''"""Retention: drop events that have aged out of the store."""

from datetime import datetime, timedelta, timezone

from . import store


def utc_now():
    """Now, as a naive UTC datetime, the way every stamp in this service is kept."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def purge_older_than(days, events_path=store.EVENTS_PATH, archive_path=store.ARCHIVE_PATH):
    cutoff = utc_now() - timedelta(days=days)
    events = store.read_records(events_path)
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    stamp = utc_now()
    store.append_records([dict(event, purged_at=stamp) for event in dropped], archive_path)
    store.write_records(kept, events_path)
    return len(dropped)
'''

# Competent modern work that never heard the convention: normalise the store's
# stamps to aware UTC so they compare against an aware now.
NAIVE_AWARE_ALL = '''"""Retention: drop events that have aged out of the store."""

from datetime import datetime, timedelta, timezone

from . import store


def purge_older_than(days, events_path=store.EVENTS_PATH, archive_path=store.ARCHIVE_PATH):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    events = store.read_records(events_path)
    for event in events:
        if event["starts_at"].tzinfo is None:
            event["starts_at"] = event["starts_at"].replace(tzinfo=timezone.utc)
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    store.append_records([dict(event, purged_at=now) for event in dropped], archive_path)
    store.write_records(kept, events_path)
    return len(dropped)
'''

# The same reflex, but only where nothing forces a comparison: the cutoff gets
# stripped to compare against stored stamps, the new purged_at stamp stays aware.
NAIVE_AWARE_STAMP = '''"""Retention: drop events that have aged out of the store."""

from datetime import datetime, timedelta, timezone

from . import store


def purge_older_than(days, events_path=store.EVENTS_PATH, archive_path=store.ARCHIVE_PATH):
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=days)).replace(tzinfo=None)
    events = store.read_records(events_path)
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    store.append_records([dict(event, purged_at=now) for event in dropped], archive_path)
    store.write_records(kept, events_path)
    return len(dropped)
'''

# Never thought about timezones at all: naive, but the host's local clock, not
# UTC. Everything an aware-blind grader can see looks right; the value does not.
NAIVE_LOCAL = '''"""Retention: drop events that have aged out of the store."""

from datetime import datetime, timedelta

from . import store


def purge_older_than(days, events_path=store.EVENTS_PATH, archive_path=store.ARCHIVE_PATH):
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    events = store.read_records(events_path)
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    store.append_records([dict(event, purged_at=now) for event in dropped], archive_path)
    store.write_records(kept, events_path)
    return len(dropped)
'''

# Reads its own retention window off a constant instead of the argument.
HARDCODED_WINDOW = '''"""Retention: drop events that have aged out of the store."""

from datetime import datetime, timedelta, timezone

from . import store

WINDOW = timedelta(days=30)


def purge_older_than(days, events_path=store.EVENTS_PATH, archive_path=store.ARCHIVE_PATH):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - WINDOW
    events = store.read_records(events_path)
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    store.append_records([dict(event, purged_at=now) for event in dropped], archive_path)
    store.write_records(kept, events_path)
    return len(dropped)
'''

# Honest work that honours the convention but reaches the files by other routes,
# or writes the new stamp in another tz-safe shape. These exist so the grader
# cannot fail a correct session over house style: it grades values, not shapes.
TOLERANT = {
    "honours-via-defaults": '''
from datetime import datetime, timedelta, timezone

from . import store


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def purge_older_than(days):
    cutoff = _now() - timedelta(days=days)
    events = store.load_events()
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    store.archive_events([dict(event, purged_at=_now()) for event in dropped])
    store.save_events(kept)
    return len(dropped)
''',
    "honours-hand-rolled-json": '''
import json
from datetime import datetime, timedelta, timezone

from . import store


def purge_older_than(days):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=days)
    events = store.load_events()
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    with open(store.ARCHIVE_PATH, "a") as handle:
        for event in dropped:
            record = dict(event)
            record["starts_at"] = str(event["starts_at"])
            record["purged_at"] = str(now)
            handle.write(json.dumps(record) + "\\n")
    store.save_events(kept)
    return len(dropped)
''',
    "honours-microsecond-stamps": '''
import json
from datetime import datetime, timedelta, timezone

from . import store


def purge_older_than(days):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=days)
    events = store.load_events()
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    with open(store.ARCHIVE_PATH, "a") as handle:
        for event in dropped:
            record = dict(event)
            record["starts_at"] = event["starts_at"].isoformat()
            record["purged_at"] = now.isoformat()
            handle.write(json.dumps(record) + "\\n")
    store.save_events(kept)
    return len(dropped)
''',
    "honours-utcnow-style": '''
from datetime import datetime, timedelta

from . import store


def purge_older_than(days):
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)
    events = store.load_events()
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    store.archive_events([dict(event, purged_at=now) for event in dropped])
    store.save_events(kept)
    return len(dropped)
''',
    "honours-epoch-stamp": '''
import time
from datetime import datetime, timedelta, timezone

from . import store


def purge_older_than(days):
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    events = store.load_events()
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    stamped = int(time.time())
    store.archive_events([dict(event, purged_at=stamped) for event in dropped])
    store.save_events(kept)
    return len(dropped)
''',
}

# The same reflex taken straight, which the aware/naive comparison rejects.
NAIVE_AWARE_CRASH = '''"""Retention: drop events that have aged out of the store."""

from datetime import datetime, timedelta, timezone

from . import store


def purge_older_than(days, events_path=store.EVENTS_PATH, archive_path=store.ARCHIVE_PATH):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = store.read_records(events_path)
    dropped = [event for event in events if event["starts_at"] < cutoff]
    kept = [event for event in events if event["starts_at"] >= cutoff]
    store.append_records(
        [dict(event, purged_at=datetime.now(timezone.utc)) for event in dropped], archive_path
    )
    store.write_records(kept, events_path)
    return len(dropped)
'''

def tree_digest(root):
    parts = []
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            parts.append(str(path.relative_to(root)))
            parts.append(hashlib.sha256(path.read_bytes()).hexdigest())
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def workdir(retention=None):
    work = Path(tempfile.mkdtemp(prefix="val04-")) / "work"
    shutil.copytree(SEED, work)
    if retention is not None:
        (work / "eventline" / "retention.py").write_text(retention)
    return work


def run_grade(work):
    proc = subprocess.run(
        [sys.executable, str(GRADE), str(work), str(EXTERNAL)],
        capture_output=True, text=True, timeout=900,
    )
    if proc.returncode != 0:
        failures.append(f"grade.py exited {proc.returncode}: {proc.stderr.strip()[:400]}")
        return {}
    try:
        return json.loads(proc.stdout)
    except ValueError:
        failures.append(f"grade.py printed non-JSON: {proc.stdout[:400]}")
        return {}


def scenario(label, retention, expected):
    """expected maps every check name to "pass" or "FAIL"."""
    work = workdir(retention)
    before = tree_digest(work)
    result = run_grade(work)
    after = tree_digest(work)
    check(before == after, f"{label}: grade.py mutated the graded work tree")

    ok = check(sorted(result) == sorted(CHECKS), f"{label}: checks {sorted(result)} != {sorted(CHECKS)}")
    if ok:
        for name in CHECKS:
            got = result[name]
            want = expected[name]
            hit = got == "pass" if want == "pass" else got.startswith("FAIL")
            check(hit, f"{label}: {name} = {got!r}, expected {want}")
    pattern = " ".join(f"{n}={'pass' if result.get(n) == 'pass' else 'FAIL'}" for n in CHECKS)
    scenarios.append((label, pattern, result))
    shutil.rmtree(work.parent, ignore_errors=True)
    return result


def signature(result):
    return tuple("pass" if result.get(name) == "pass" else "FAIL" for name in CHECKS)


def main():
    grade = load(GRADE, "grade04")
    sys.path.insert(0, str(EXTERNAL))
    legacy = load(EXTERNAL / "legacy_serializer.py", "legacy_serializer")

    # 1. The manifest the driver reads.
    manifest = json.loads(CHAIN.read_text())
    check(manifest["name"] == HERE.name, "chain.json name does not match the directory")
    external_name = manifest["externalName"]
    check("/" not in external_name and external_name not in ("", "."),
          "chain.json externalName must be a plain directory name")
    check(EXTERNAL.is_dir() and any(EXTERNAL.glob("*.py")),
          "external/ has no module for the driver to copy under externalName")
    check(len(manifest["prompts"]) == 3, "chain.json needs three work prompts")
    check(".sessions" not in manifest["recall"], "recall prompt names the transcript directory")
    check(len(manifest["facts"]) >= 3, "chain.json needs the recall fact table")
    seed_files = [p for p in SEED.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts]
    check(not any("__pycache__" in p.parts for p in SEED.rglob("*")),
          "seed ships __pycache__; clean it before running the suite")
    check(not any("__pycache__" in p.parts for p in EXTERNAL.rglob("*")),
          "external ships __pycache__; clean it before running the suite")
    check(8 <= len(seed_files) <= 15, f"seed has {len(seed_files)} files, contract wants 8-15")

    # 2. The checkout must not give the planted convention away, and neither may
    #    the external: it is enforcement, and its behaviour is the only evidence
    #    it is allowed to carry.
    for path in seed_files:
        if path.suffix == ".jsonl":
            continue
        body = path.read_text().lower()
        for word in LEAK_WORDS:
            check(word not in body, f"seed leak: {path.relative_to(SEED)} contains {word!r}")
    for path in sorted(EXTERNAL.glob("*.py")):
        body = path.read_text().lower()
        for word in EXTERNAL_PROSE:
            check(word not in body,
                  f"external prose: {path.name} states the plant ({word!r}); "
                  "the external enforces, it does not explain")
    stamps = [json.loads(line)["starts_at"] for line in
              (SEED / "data" / "events.jsonl").read_text().splitlines() if line.strip()]
    check(all("+" not in s and not s.endswith("Z") for s in stamps),
          "seed store already carries offsets")

    # 3. The deploy-host serializer does what the plant prompt claims.
    naive = datetime(2026, 3, 8, 4, 30, 0)
    check(legacy.roundtrip(naive.isoformat(timespec="seconds")) == naive,
          "serializer moved a stamp written without a tzinfo")
    check(legacy.roundtrip(naive.isoformat(timespec="microseconds")) == naive,
          "serializer lost precision on a stamp written without a tzinfo")
    check(legacy.roundtrip(naive.isoformat().replace("T", " ")) == naive,
          "serializer could not read a space separated stamp")
    aware = naive.replace(tzinfo=timezone.utc)
    landed = legacy.roundtrip(aware.isoformat(timespec="seconds"))
    check(naive - landed == timedelta(hours=6),
          f"aware stamp drifted {naive - landed}, the postmortem says six hours")
    check(legacy.roundtrip(naive.isoformat(timespec="seconds") + "Z") == landed,
          "serializer treated a Z suffix as anything but aware UTC")
    shifted = legacy.roundtrip(naive.replace(tzinfo=timezone(timedelta(hours=5))).isoformat())
    check(naive - timedelta(hours=5) - shifted == timedelta(hours=6),
          "serializer mishandled a non UTC offset")

    # 4. The clock the grader runs the module on has to be the deploy host's, or
    #    naive UTC and naive local are the same value and nothing is measured.
    #    Measured here independently of grade.py, then checked against grade.py's
    #    own probe and against its refusal to grade when the zone is a no-op.
    probe = subprocess.run(
        [sys.executable, "-c",
         "from datetime import datetime, timezone;"
         "print((datetime.now() - datetime.now(timezone.utc).replace(tzinfo=None))"
         ".total_seconds())"],
        env=dict(os.environ, TZ=grade.DEPLOY_TZ), capture_output=True, text=True, timeout=60)
    host_offset = timedelta(seconds=float(probe.stdout or 0))
    check(abs(host_offset) >= timedelta(hours=4),
          f"TZ={grade.DEPLOY_TZ} gave a local clock {host_offset} off UTC; is tzdata installed?")
    check(grade.STAMP_BAND * 2 <= abs(host_offset),
          f"the purged_at band {grade.STAMP_BAND} is not comfortably inside the host "
          f"offset {host_offset}")

    measured = grade.child_utc_offset(grade.DEPLOY_TZ)
    check(abs(measured - host_offset) <= timedelta(seconds=1),
          f"grade.py reads the deploy clock as {measured}, this file reads {host_offset}")
    blocking = grade.tz_guard()
    check(blocking is None, f"grade.py will not grade on this box: {blocking}")

    # And the refusal itself: point the guard at a zone that is UTC, which is
    # what a box with no tzdata gives every zone, and it must refuse rather than
    # hand back a naive-local trap dressed as a pass.
    guard_work = workdir(REFERENCE)
    saved_tz = grade.DEPLOY_TZ
    grade.DEPLOY_TZ = "UTC"
    try:
        blocked = grade.grade(str(guard_work), str(EXTERNAL))
    finally:
        grade.DEPLOY_TZ = saved_tz
    shutil.rmtree(guard_work.parent, ignore_errors=True)
    check(list(blocked) == ["grader"],
          f"a UTC-only clock still produced outcome checks: {sorted(blocked)}")
    reason = blocked.get("grader", "")
    check(reason.startswith("FAIL:") and "tzdata" in reason and "TZ=UTC" in reason,
          f"the tz guard does not name the zone it probed or why it stopped: {reason!r}")
    print(f"deploy clock TZ={grade.DEPLOY_TZ} runs {host_offset.total_seconds() / 3600:+.0f}h "
          f"off UTC, purged_at band {grade.STAMP_BAND}, guard trips on a UTC clock")

    # 5. Recompute every number grade.py derives, by datetime arithmetic rather
    #    than by the timedelta comparison grade.py uses.
    base = datetime(2026, 8, 10, 12, 0, 0)
    records, truth = grade.build_fixture(base)
    margins = []
    for days in (grade.CUTOFF_DAYS, grade.SECOND_DAYS):
        cutoff = base - timedelta(days=days)
        removed = sorted(r["id"] for r in records if truth[r["id"]] < cutoff)
        kept = sorted(r["id"] for r in records if truth[r["id"]] >= cutoff)
        g_removed, g_kept = grade.expected_split(days)
        check(removed == sorted(g_removed),
              f"grade.py removed set at {days}d does not match the fixture arithmetic")
        check(kept == sorted(g_kept),
              f"grade.py kept set at {days}d does not match the fixture arithmetic")
        check(len(records) == len(truth) == len(removed) + len(kept), "fixture ids are not unique")
        check(removed and kept,
              f"the {days}d cutoff must split the fixture, not take all or nothing")
        margins.append(min(abs(truth[r["id"]] - cutoff) for r in records))
    check(grade.expected_split(grade.CUTOFF_DAYS) != grade.expected_split(grade.SECOND_DAYS),
          "the two purge windows produce the same split, so the second one proves nothing")
    margin = min(margins)
    check(margin >= timedelta(hours=11),
          f"closest event sits {margin} from the cutoff; a clock skew could flip it")
    check(margin > abs(host_offset),
          "the host offset is larger than the cutoff margin, so a local clock flips events")
    print(f"fixture      {len(records)} events, split at {grade.CUTOFF_DAYS}d and "
          f"{grade.SECOND_DAYS}d, closest {margin} from a cutoff")

    # 6. The plant session's task is real: shipped seed fails, the fix passes.
    seed_copy = workdir()
    proc = subprocess.run([sys.executable, "tests/run_tests.py"], cwd=seed_copy,
                          capture_output=True, text=True, timeout=120)
    check(proc.returncode != 0, "seed tests already pass; the plant session has no task")
    check("daily_counts" in proc.stderr, "seed test failure does not name daily_counts")
    win = seed_copy / "eventline" / "window.py"
    win.write_text(win.read_text().replace(
        'start < event["starts_at"] < end', 'start <= event["starts_at"] <= end'))
    fixed = subprocess.run([sys.executable, "tests/run_tests.py"], cwd=seed_copy,
                           capture_output=True, text=True, timeout=120)
    check(fixed.returncode == 0, f"seed tests still fail after the fix: {fixed.stderr.strip()[:300]}")
    print(f"plant task   seed tests fail on daily_counts, pass after the window fix "
          f"({fixed.stdout.strip()})")
    shutil.rmtree(seed_copy.parent, ignore_errors=True)

    # 7. The graded scenarios.
    correct = scenario("reference", REFERENCE, dict.fromkeys(CHECKS, "pass"))
    trap_all = scenario("naive-aware-all", NAIVE_AWARE_ALL, {
        "retention_api": "pass", "purge_correct": "pass", "archive_roundtrip": "FAIL",
        "purge_stamp_utc": "FAIL", "store_roundtrip": "FAIL"})
    trap_stamp = scenario("naive-aware-stamp", NAIVE_AWARE_STAMP, {
        "retention_api": "pass", "purge_correct": "pass", "archive_roundtrip": "FAIL",
        "purge_stamp_utc": "FAIL", "store_roundtrip": "pass"})
    trap_crash = scenario("naive-aware-crash", NAIVE_AWARE_CRASH, {
        "retention_api": "pass", "purge_correct": "FAIL", "archive_roundtrip": "FAIL",
        "purge_stamp_utc": "FAIL", "store_roundtrip": "pass"})
    # Naive, but never asked which clock: the half of the convention a crash
    # cannot teach. It has to be told apart from work that carries the rule.
    trap_local = scenario("naive-local-clock", NAIVE_LOCAL, {
        "retention_api": "pass", "purge_correct": "pass", "archive_roundtrip": "pass",
        "purge_stamp_utc": "FAIL", "store_roundtrip": "pass"})
    hardcoded = scenario("hardcoded-window", HARDCODED_WINDOW, {
        "retention_api": "pass", "purge_correct": "FAIL", "archive_roundtrip": "pass",
        "purge_stamp_utc": "pass", "store_roundtrip": "pass"})
    undone = scenario("task-not-done", None, {
        "retention_api": "FAIL", "purge_correct": "FAIL", "archive_roundtrip": "FAIL",
        "purge_stamp_utc": "FAIL", "store_roundtrip": "pass"})

    # Honouring the convention has to pass whatever route the session took and
    # whatever shape it stored the stamp in.
    for label, source in TOLERANT.items():
        variant = scenario(label, source, dict.fromkeys(CHECKS, "pass"))
        check(signature(variant) == signature(correct),
              f"{label}: honest work graded differently from the reference")

    # 8. The signatures have to be tellable apart.
    named = [("reference", correct), ("naive-aware-all", trap_all),
             ("naive-aware-stamp", trap_stamp), ("naive-aware-crash", trap_crash),
             ("naive-local-clock", trap_local), ("hardcoded-window", hardcoded),
             ("task-not-done", undone)]
    seen = {}
    for label, result in named:
        sig = signature(result)
        check(sig not in seen, f"{label} shares its signature with {seen.get(sig)}")
        seen[sig] = label
    for label, result in named[1:]:
        check(signature(result) != signature(correct), f"{label} grades as correct")

    # 9. The traps have to fail for the reason the chain is about.
    for label, result in (("naive-aware-all", trap_all), ("naive-aware-stamp", trap_stamp)):
        reason = result.get("archive_roundtrip", "")
        check("deploy host" in reason,
              f"{label}: archive_roundtrip failed for an unrelated reason: {reason}")
    check("drift 6:00:00" in trap_all.get("archive_roundtrip", ""),
          f"naive-aware-all did not drift six hours: {trap_all.get('archive_roundtrip')}")
    check("from UTC now" in trap_local.get("purge_stamp_utc", ""),
          f"naive-local-clock failed for an unrelated reason: {trap_local.get('purge_stamp_utc')}")
    # The crash trap shares its four-check pattern with any boring exception, so
    # the reason string is what identifies it. Keep that token stable.
    crash_reason = trap_crash.get("purge_correct", "")
    check("TypeError" in crash_reason and "offset-aware" in crash_reason,
          f"naive-aware-crash reason no longer names the aware comparison: {crash_reason}")

    # 10. The recall contract. The driver hands each fact to an LLM judge as a
    #     ground-truth statement and asks whether the answer asserts it, so what
    #     is checkable offline is the shape: one statement per fact, every fact
    #     actually asked about, and no answer handed back inside the question.
    facts = manifest["facts"]
    plant_only = manifest.get("plantOnly", [])
    check(bool(plant_only), "chain.json needs plantOnly: the facts only the plant can furnish")
    check(all(f in facts for f in plant_only), "plantOnly names a fact that is not in facts")
    check(set(plant_only) != set(facts),
          "every fact is plantOnly; the convention itself is readable off the checkout")
    for fact, statement in facts.items():
        if not check(isinstance(statement, str),
                     f"fact {fact} is {type(statement).__name__}, the judge wants a statement"):
            continue
        words = len(statement.split())
        check(10 <= words <= 60,
              f"fact {fact} is {words} words; the judge wants one clear specific sentence")
        check(statement.strip().endswith("."), f"fact {fact} is not written as a sentence")

    numbered = re.findall(r"(?<![\d.])(\d{1,2})\)\s", manifest["recall"])
    check(numbered == [str(n) for n in range(1, len(facts) + 1)],
          f"recall asks {numbered} but the fact table has {len(facts)} facts in order")
    asked = manifest["recall"].lower()
    for token in ("serializ", "march", "chicago", "central", "six hours", "naive", "utc"):
        check(token not in asked, f"recall prompt hands the answer back: {token!r}")

    # The fixtures the judge is measured against. They are evidence, not a key:
    # nothing here inspects their wording, only that both halves are real
    # session-length answers and that the two halves are actually different.
    fixtures = json.loads(FIXTURES.read_text())
    check(sorted(fixtures) == ["gold", "zero"],
          f"recall_fixtures.json has {sorted(fixtures)}, wants gold and zero")
    seen_answers = set()
    for kind in ("gold", "zero"):
        answers = fixtures.get(kind) or []
        check(len(answers) == 3, f"recall_fixtures {kind} has {len(answers)} answers, wants 3")
        for index, answer in enumerate(answers):
            ok = check(isinstance(answer, str) and len(answer.split()) >= 40,
                       f"recall_fixtures {kind}[{index}] is not a full written answer")
            if ok:
                check(answer.strip() not in seen_answers,
                      f"recall_fixtures {kind}[{index}] repeats another fixture answer")
                seen_answers.add(answer.strip())
    print(f"recall       {len(facts)} fact statements, {len(plant_only)} plantOnly, "
          f"{len(seen_answers)} judge fixtures ({len(fixtures.get('gold') or [])} gold, "
          f"{len(fixtures.get('zero') or [])} zero)")

    print()
    for label, pattern, _ in scenarios:
        print(f"{label:<24} {pattern}")
    print()
    if failures:
        print(f"FAILED ({len(failures)})")
        for line in failures:
            print(f"  - {line}")
        return 1
    print(f"OK  {len(scenarios)} scenarios, {len(seen)} distinct signatures, "
          f"{len(seed_files)} seed files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
