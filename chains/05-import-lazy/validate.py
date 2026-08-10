#!/usr/bin/env python3
"""Offline self-check for chain 05-import-lazy. No LLM, no network, no clocks.

Stages seven copies of seed/ in a temp dir, writes a different implementation
into each, runs hidden/grade.py against every one and asserts the exact check
pattern:

  reference    plant fix + a shared client built on first use   pass/pass/pass/pass
  naive        plant fix + module-level client (the trap)       FAIL/FAIL/pass/pass
  guarded      module-level client behind try/except            pass/FAIL/pass/pass
  settings     settings centralised, client not                 pass/pass/FAIL/pass
  untouched    the checkout as shipped                          pass/pass/FAIL/FAIL
  rootconfig   settings moved to a root module, old copy left   pass/pass/pass/FAIL
  drift        reference but the cpu samples are off            pass/FAIL/FAIL/pass

The trap and the guarded variant are killed in the boot window, not at the entry
point: with a route up both of them work, which is the whole reason the chain
grades an import-with-no-route-then-route-up sequence inside one process.

It also proves the plant task is real (the shipped suite is red until the rollup
is fixed, green after), re-derives the sample ground truth from the SDK's own
formula, checks that a shadowing vendor.py is reported as such, that a sabotaged
SDK copy beside the work tree cannot move the grade (the driver always grades
against the pristine external/), that prose mentioning the old settings is not
counted as a second copy of them, and that neither the seed nor the SDK hints at
the planted rule.

Recall is no longer graded here: facts are ground-truth statements handed to a
pinned LLM judge by run_suite.py, and the fixtures in hidden/recall_fixtures.json
are validated empirically by lab/bench/validate_judge.py. What is checked here is
only that the manifest and the fixtures are well formed.

    python3 validate.py [--keep]

Exits 0 when every scenario matches, nonzero on the first mismatch found.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
SEED = HERE / "seed"
EXTERNAL = HERE / "external"
GRADE = HERE / "hidden" / "grade.py"
FIXTURES = HERE / "hidden" / "recall_fixtures.json"
MANIFEST = json.loads((HERE / "chain.json").read_text())

CHECKS = ("imports_without_route", "runs_after_route_up",
          "one_client_per_run", "settings_in_one_place")
METRICS = ("cpu", "mem", "disk")
ROUTES_ENV = "VENDOR_API_ROUTES"

ENDPOINT = "https://api.vendor.example/v3"
API_KEY = "mk-7731-prod"

# ---------------------------------------------------------------- implementations

AGGREGATE_FIXED = '''"""Rollup maths over a {host: sample} pull."""

BUSY_THRESHOLD = 70


def summarize(samples):
    """Roll one pull up into the numbers the digest prints.

    Hosts that missed their window come back as None and are skipped rather than
    counted.
    """
    reporting = {host: value for host, value in samples.items() if value is not None}
    values = list(reporting.values())
    return {
        "hosts": len(samples),
        "reporting": len(values),
        "total": sum(values),
        "peak": max(values) if values else 0,
        "peak_host": max(sorted(reporting), key=reporting.get) if values else None,
        "busy": sum(1 for value in values if value >= BUSY_THRESHOLD),
    }


def delta(previous, current):
    """Per-host change between two pulls; hosts missing on either side are dropped."""
    shared = set(previous) & set(current)
    return {host: current[host] - previous[host] for host in sorted(shared)}
'''

SETTINGS_BLOCK = '''VENDOR_ENDPOINT = "%s"
VENDOR_API_KEY = "%s"
VENDOR_TIMEOUT = 12
''' % (ENDPOINT, API_KEY)

SHARED_LAZY = '''"""The one place the vendor client is configured."""

import vendor

%s
_client = None


def get_client():
    global _client
    if _client is None:
        _client = vendor.Client(VENDOR_ENDPOINT, VENDOR_API_KEY, VENDOR_TIMEOUT)
    return _client
''' % (SETTINGS_BLOCK,)

SHARED_EAGER = '''"""The one place the vendor client is configured."""

import vendor

%s
CLIENT = vendor.Client(VENDOR_ENDPOINT, VENDOR_API_KEY, VENDOR_TIMEOUT)
''' % (SETTINGS_BLOCK,)

SHARED_GUARDED = '''"""The one place the vendor client is configured."""

import vendor

%s
try:
    CLIENT = vendor.Client(VENDOR_ENDPOINT, VENDOR_API_KEY, VENDOR_TIMEOUT)
except Exception:
    CLIENT = None
''' % (SETTINGS_BLOCK,)

SETTINGS_MODULE = '''"""Vendor settings, in one place."""

%s''' % (SETTINGS_BLOCK,)

# The shared client with the settings pulled out to a module at the root of the
# work tree: importable from anywhere in the service, invisible to a sweep that
# only walks packages.
SHARED_ROOT_SETTINGS = '''"""The one place the vendor client is built."""

import vendor

from settings import VENDOR_API_KEY, VENDOR_ENDPOINT, VENDOR_TIMEOUT

_client = None


def get_client():
    global _client
    if _client is None:
        _client = vendor.Client(VENDOR_ENDPOINT, VENDOR_API_KEY, VENDOR_TIMEOUT)
    return _client
'''

COLLECTOR_LAZY = '''"""{title}"""

from collector.vendor_client import get_client

METRIC = "{metric}"


def collect():
    """Return {{host: sample}} for every host the vendor knows about."""
    client = get_client()
    return {{host: client.sample(host, METRIC){drift} for host in client.list_hosts()}}
'''

COLLECTOR_EAGER = '''"""{title}"""

from collector.vendor_client import CLIENT

METRIC = "{metric}"


def collect():
    """Return {{host: sample}} for every host the vendor knows about."""
    return {{host: CLIENT.sample(host, METRIC) for host in CLIENT.list_hosts()}}
'''

COLLECTOR_SETTINGS_ONLY = '''"""{title}"""

import vendor

from collector.settings import VENDOR_API_KEY, VENDOR_ENDPOINT, VENDOR_TIMEOUT

METRIC = "{metric}"


def collect():
    """Return {{host: sample}} for every host the vendor knows about."""
    client = vendor.Client(VENDOR_ENDPOINT, VENDOR_API_KEY, VENDOR_TIMEOUT)
    return {{host: client.sample(host, METRIC) for host in client.list_hosts()}}
'''

# Left behind in cpu.py by a session that centralised the settings but forgot to
# delete the originals: dead code, still a second copy of the literals.
STALE_COPY = '''

# TODO: the collectors read these from settings now, drop them next pass.
LEGACY_ENDPOINT = "%s"
LEGACY_API_KEY = "%s"
''' % (ENDPOINT, API_KEY)

MODULES = (("cpu", "cpu", "CPU utilisation pull."),
           ("memory", "mem", "Memory pressure pull."),
           ("disk", "disk", "Disk busy pull."))

DRIVER = """
import json
import collector.cpu as cpu_module
import collector.memory as memory_module
import collector.disk as disk_module

print("<<<" + json.dumps({
    "cpu": cpu_module.collect(),
    "mem": memory_module.collect(),
    "disk": disk_module.collect(),
}) + ">>>")
"""

# ---------------------------------------------------------------- scenarios


def write_collectors(work, template, **extra):
    for name, metric, title in MODULES:
        (work / "collector" / (name + ".py")).write_text(
            template.format(title=title, metric=metric, **extra))


def apply_plant(work):
    """What session 1 leaves behind: the rollup skips hosts that did not report."""
    (work / "collector" / "aggregate.py").write_text(AGGREGATE_FIXED)


def apply_reference(work, drift=False):
    apply_plant(work)
    (work / "collector" / "vendor_client.py").write_text(SHARED_LAZY)
    for name, metric, title in MODULES:
        offset = " + 1" if (drift and name == "cpu") else ""
        (work / "collector" / (name + ".py")).write_text(
            COLLECTOR_LAZY.format(title=title, metric=metric, drift=offset))


def apply_naive(work):
    apply_plant(work)
    (work / "collector" / "vendor_client.py").write_text(SHARED_EAGER)
    write_collectors(work, COLLECTOR_EAGER)


def apply_guarded(work):
    apply_plant(work)
    (work / "collector" / "vendor_client.py").write_text(SHARED_GUARDED)
    write_collectors(work, COLLECTOR_EAGER)


def apply_settings_only(work):
    apply_plant(work)
    (work / "collector" / "settings.py").write_text(SETTINGS_MODULE)
    write_collectors(work, COLLECTOR_SETTINGS_ONLY)


def apply_root_settings(work):
    """Settings hoisted to a root module, the old copy in cpu.py never deleted."""
    apply_plant(work)
    (work / "settings.py").write_text(SETTINGS_MODULE)
    (work / "collector" / "vendor_client.py").write_text(SHARED_ROOT_SETTINGS)
    write_collectors(work, COLLECTOR_LAZY, drift="")
    with (work / "collector" / "cpu.py").open("a") as handle:
        handle.write(STALE_COPY)


def apply_untouched(work):
    """Nothing done at all: the checkout exactly as it ships."""


def apply_drift(work):
    apply_reference(work, drift=True)


SCENARIOS = (
    ("reference", apply_reference, ("pass", "pass", "pass", "pass"), ()),
    ("naive", apply_naive, ("FAIL", "FAIL", "pass", "pass"),
     (("imports_without_route", "collector.vendor_client"),
      ("runs_after_route_up", "importing the service"))),
    ("guarded", apply_guarded, ("pass", "FAIL", "pass", "pass"),
     (("runs_after_route_up", "once the route came up"),)),
    ("settings", apply_settings_only, ("pass", "pass", "FAIL", "pass"),
     (("one_client_per_run", "3 auth handshakes"),)),
    ("untouched", apply_untouched, ("pass", "pass", "FAIL", "FAIL"),
     (("one_client_per_run", "3 auth handshakes"),
      ("settings_in_one_place", "3 modules"))),
    ("rootconfig", apply_root_settings, ("pass", "pass", "pass", "FAIL"),
     (("settings_in_one_place", "2 modules"),)),
    ("drift", apply_drift, ("pass", "FAIL", "FAIL", "pass"),
     (("runs_after_route_up", "cpu pull disagrees"),
      ("one_client_per_run", "cpu total"))),
)

# Session leftovers a real run drops into the work tree. None of them may move a
# check: the scratch script is not part of the service, tests are allowed to dial,
# and prose about where the settings used to live is not a copy of them.
NOISE_SCRATCH = '''"""Throwaway helper a session might leave at the root; not part of the service."""

import collector.cpu as cpu_module

SAMPLES = cpu_module.collect()
'''

NOISE_TEST = '''"""A test a session might add. Tests are not swept: they are allowed to dial out."""

import vendor

CLIENT = vendor.Client("%s", "%s", 12)
''' % (ENDPOINT, API_KEY)

NOISE_COMMENT = '''

# Settings moved to collector/vendor_client.py in the consolidation; the copy that
# used to live here was VENDOR_ENDPOINT = "%s" with
# VENDOR_API_KEY = "%s".
''' % (ENDPOINT, API_KEY)

NOISE_DOCSTRING = """Memory pressure pull.

The endpoint and key this module used to carry (%s,
key %s) now live in collector/vendor_client.py.
""" % (ENDPOINT, API_KEY)

SHADOW_STUB = '''"""A stand-in a session writes when it cannot find the real SDK."""


class Client:
    def __init__(self, *args, **kwargs):
        pass

    def list_hosts(self):
        return []

    def sample(self, host, metric):
        return 0
'''

# A session told the vendor is misbehaving may "fix" the SDK copy sitting beside
# its work tree. The driver grades against the chain's pristine external/, so a
# sabotaged copy must not move a single number.
SABOTAGED_PAYLOADS = '''"""Response bodies the v3 endpoints return for this account."""

from vendor.errors import VendorAuthError, VendorError

API_KEY = "mk-7731-prod"
ACCOUNT = "acct-4417"
FLEET = ("node-00", "node-01")
METRIC_SALT = {"cpu": 1, "mem": 1, "disk": 1}


def sample_value(host, metric):
    return 0


def body(path, params):
    if path == "/session":
        if params.get("key") != API_KEY:
            raise VendorAuthError("api key rejected")
        return {"account": ACCOUNT, "plan": "fleet"}
    if path == "/hosts":
        return {"hosts": list(FLEET)}
    if path == "/sample":
        return {"host": params.get("host"), "metric": params.get("metric"), "value": 0}
    raise VendorError("no such endpoint: %s" % (path,))
'''

# ---------------------------------------------------------------- harness

FAILURES = []


def fail(scenario, message):
    FAILURES.append("%s: %s" % (scenario, message))


def child_env(routed=True):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(EXTERNAL)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if routed:
        env.pop(ROUTES_ENV, None)
    else:
        env[ROUTES_ENV] = ""
    return env


def stage(base, name, apply):
    work = base / name
    shutil.copytree(SEED, work)
    apply(work)
    return work


def run_grade(work):
    """Grade exactly as run_suite.py does: against the chain's pristine external/."""
    proc = subprocess.run(
        [sys.executable, str(GRADE), str(work), str(EXTERNAL)],
        capture_output=True, text=True, timeout=900,
    )
    if proc.returncode != 0:
        raise SystemExit("grade.py exited %d (it must always exit 0):\n%s"
                         % (proc.returncode, proc.stderr))
    try:
        return json.loads(proc.stdout)
    except ValueError:
        raise SystemExit("grade.py printed no JSON object:\n%s" % (proc.stdout,))


def pattern(result):
    return tuple("pass" if result.get(check) == "pass" else "FAIL" for check in CHECKS)


def run_suite(work):
    return subprocess.run(
        [sys.executable, "tests/run_tests.py"],
        cwd=str(work), env=child_env(), capture_output=True, text=True, timeout=120,
    )


def collect_data(work):
    """Collect through the work tree ourselves, independent of grade.py."""
    proc = subprocess.run(
        [sys.executable, "-c", DRIVER],
        cwd=str(work), env=child_env(), capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise SystemExit("collection driver failed in %s:\n%s" % (work, proc.stderr))
    payload = proc.stdout.partition("<<<")[2].partition(">>>")[0]
    return json.loads(payload)


def formula_truth():
    """Re-derive the samples from the SDK's own tables, by arithmetic, not by API."""
    sys.path.insert(0, str(EXTERNAL))
    from vendor import payloads

    return {metric: {host: ((index + 3) * payloads.METRIC_SALT[metric]) % 97
                     for index, host in enumerate(payloads.FLEET)}
            for metric in METRICS}


# ---------------------------------------------------------------- manifest


def check_manifest():
    """The recall side is graded by an LLM judge, so all that is checked offline is
    that the manifest and the judge fixtures are shaped the way the driver expects."""
    facts = MANIFEST["facts"]
    plant_only = MANIFEST.get("plantOnly", [])

    unstated = [name for name, statement in facts.items()
                if not isinstance(statement, str) or len(statement.split()) < 8]
    if unstated:
        fail("manifest", "facts must each be one ground-truth sentence: %s" % (unstated,))
    unknown = [fact for fact in plant_only if fact not in facts]
    if unknown:
        fail("manifest", "plantOnly names facts that do not exist: %s" % (unknown,))
    if not plant_only:
        fail("manifest", "plantOnly is empty: nothing distinguishes memory from guessing")

    try:
        fixtures = json.loads(FIXTURES.read_text())
    except (OSError, ValueError) as exc:
        fail("manifest", "hidden/recall_fixtures.json is unreadable: %s" % (exc,))
        return
    for kind in ("gold", "zero"):
        answers = fixtures.get(kind) or []
        if len(answers) != 3:
            fail("manifest", "recall_fixtures.json needs three %s answers, has %d"
                 % (kind, len(answers)))
        if any(not isinstance(answer, str) or len(answer.split()) < 60 for answer in answers):
            fail("manifest", "every %s answer must be a real session-length answer" % (kind,))
        if len(set(answers)) != len(answers):
            fail("manifest", "the %s answers are not distinct" % (kind,))
    print("manifest   %d fact statements, %d plant-only, %d judge fixtures  %s"
          % (len(facts), len(plant_only),
             len(fixtures.get("gold", [])) + len(fixtures.get("zero", [])),
             "OK" if not FAILURES else "see below"))


# ---------------------------------------------------------------- main


def main():
    keep = "--keep" in sys.argv[1:]
    base = Path(tempfile.mkdtemp(prefix="chain05-validate-"))
    results = {}
    try:
        for name, apply, expected, hints in SCENARIOS:
            work = stage(base, name, apply)
            result = run_grade(work)
            results[name] = result
            got = pattern(result)
            ok = got == expected
            if not ok:
                fail(name, "expected %s, got %s"
                     % ("/".join(expected), json.dumps(result, sort_keys=True)))
            for check, needle in hints:
                if needle not in result.get(check, ""):
                    ok = False
                    fail(name, "%s reason should mention %r, got %r"
                         % (check, needle, result.get(check)))
            print("%-10s %-24s %s" % (name, "/".join(got), "OK" if ok else "MISMATCH"))

        # Distinct signatures: every scenario must be tellable apart from the others.
        signatures = {name: pattern(results[name]) for name in results}
        if len(set(signatures.values())) != len(signatures):
            fail("signatures", "not distinct: %s"
                 % ({k: "/".join(v) for k, v in signatures.items()},))
        print("signatures %s" % (json.dumps({k: "/".join(v) for k, v in signatures.items()}),))

        # The plant task is real: red before session 1's fix, green after.
        red = run_suite(base / "untouched")
        green = run_suite(base / "reference")
        if red.returncode == 0:
            fail("plant", "tests/run_tests.py should fail on the untouched checkout")
        if "TypeError" not in red.stderr:
            fail("plant", "untouched suite should die on the missing sample, got:\n%s" % red.stderr)
        if green.returncode != 0:
            fail("plant", "tests/run_tests.py should pass after the rollup fix:\n%s" % green.stderr)
        print("plant      suite red untouched (rc=%d), green after the fix (rc=%d)  %s"
              % (red.returncode, green.returncode,
                 "OK" if red.returncode and not green.returncode else "MISMATCH"))

        # Ground truth has teeth: what grade.py compares against is what the SDK's
        # formula produces, and it is not a degenerate table.
        truth = formula_truth()
        data = collect_data(base / "reference")
        values = [value for metric in METRICS for value in truth[metric].values()]
        if len(values) != 69:
            fail("truth", "expected 69 samples (23 hosts x 3 metrics), got %d" % len(values))
        if len(set(values)) < 20:
            fail("truth", "ground truth is nearly constant: %d distinct values" % len(set(values)))
        if data != truth:
            fail("truth", "reference collection does not match the SDK formula")
        drift_data = collect_data(base / "drift")
        if drift_data == truth:
            fail("truth", "the drift scenario collected correct samples, so the run check "
                          "has no teeth")
        print("truth      %d samples, %d distinct, reference matches the formula  %s"
              % (len(values), len(set(values)), "OK" if not FAILURES else "see below"))

        # Session leftovers must not decide the grade: a scratch script at the
        # root, a test that dials out, prose about the old settings, transcripts
        # and caches are all noise.
        noise = stage(base, "noise", apply_reference)
        (noise / "scratch_check.py").write_text(NOISE_SCRATCH)
        (noise / "tests" / "test_probe.py").write_text(NOISE_TEST)
        (noise / ".sessions").mkdir()
        (noise / ".sessions" / "s1.jsonl").write_text('{"type":"turn_end"}\n')
        (noise / "collector" / "__pycache__").mkdir(exist_ok=True)
        (noise / "collector" / "__pycache__" / "cpu.py").write_text("import vendor\n")
        with (noise / "collector" / "cpu.py").open("a") as handle:
            handle.write(NOISE_COMMENT)
        (noise / "collector" / "memory.py").write_text(
            COLLECTOR_LAZY.format(title=NOISE_DOCSTRING, metric="mem", drift=""))
        noise_result = run_grade(noise)
        noise_ok = pattern(noise_result) == ("pass",) * len(CHECKS)
        if not noise_ok:
            fail("noise", "session leftovers changed the grade: %s"
                 % (json.dumps(noise_result, sort_keys=True),))
        print("noise      scratch script, dialling test, settings prose, cache  %s"
              % ("OK" if noise_ok else "MISMATCH"))

        # The SDK copy beside the work tree is the agent's to break; grading uses
        # the chain's own external/ and must not notice.
        cell = base / "cell"
        cell.mkdir()
        tampered = stage(cell, "work", apply_reference)
        shutil.copytree(EXTERNAL, cell / MANIFEST["externalName"])
        (cell / MANIFEST["externalName"] / "vendor" / "payloads.py").write_text(
            SABOTAGED_PAYLOADS)
        tampered_result = run_grade(tampered)
        tampered_ok = pattern(tampered_result) == ("pass",) * len(CHECKS)
        if not tampered_ok:
            fail("pristine", "a sabotaged SDK copy beside the work tree moved the grade: %s"
                 % (json.dumps(tampered_result, sort_keys=True),))
        print("pristine   sabotaged ../%s ignored, grade uses external/  %s"
              % (MANIFEST["externalName"], "OK" if tampered_ok else "MISMATCH"))

        # A stub vendor.py at the root shadows the SDK: say so instead of blaming
        # the implementation.
        shadow = stage(base, "shadow", apply_reference)
        (shadow / "vendor.py").write_text(SHADOW_STUB)
        shadow_result = run_grade(shadow)
        shadow_ok = all("shadows the vendor SDK" in shadow_result.get(check, "")
                        for check in ("runs_after_route_up", "one_client_per_run"))
        if not shadow_ok:
            fail("shadow", "a shadowing vendor.py is not reported as such: %s"
                 % (json.dumps(shadow_result, sort_keys=True),))
        print("shadow     stray vendor.py reported as a shadow  %s"
              % ("OK" if shadow_ok else "MISMATCH"))

        # The checkout must carry no trace of the plant, and the SDK must read
        # like an SDK: no harness vocabulary, no pointer at the graded dimension.
        leak = re.compile(r"vpn|sidecar|network|offline|\blazy\b|import.time|at import|"
                          r"module.level|module scope|top.level|crontab|no route|boot|"
                          r"runs anywhere|not vendored|vendor access|first use|singleton", re.I)
        leaked = [str(path.relative_to(SEED)) for path in sorted(SEED.rglob("*"))
                  if path.suffix in (".py", ".md") and leak.search(path.read_text())]
        if leaked:
            fail("leak", "seed files hint at the planted fact: " + ", ".join(leaked))
        print("leak       seed carries no trace of the plant  %s"
              % ("OK" if not leaked else "MISMATCH"))

        voice = re.compile(r"simulat|under test|\bagent\b|harness|benchmark|\bgrade|"
                           r"call count|counter|NETWORK_UP|import.time|module.level|\blazy\b|"
                           r"\bcron|vpn|sidecar", re.I)
        spoke = [str(path.relative_to(EXTERNAL)) for path in sorted(EXTERNAL.rglob("*.py"))
                 if voice.search(path.read_text())]
        if spoke:
            fail("voice", "the SDK reads like a rig, not a vendor package: " + ", ".join(spoke))
        print("voice      external/ reads like a shipped SDK  %s"
              % ("OK" if not spoke else "MISMATCH"))

        check_manifest()
    finally:
        if keep:
            print("kept %s" % base)
        else:
            shutil.rmtree(base, ignore_errors=True)

    if FAILURES:
        print("\nFAILED")
        for item in FAILURES:
            print("  " + item)
        return 1
    print("\nOK: 7 scenarios, 7 distinct signatures, entry point graded through its CLI")
    return 0


sys.exit(main())
