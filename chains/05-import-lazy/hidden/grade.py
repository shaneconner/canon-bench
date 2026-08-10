#!/usr/bin/env python3
"""Hidden grade for chain 05-import-lazy. Never ships in the checkout.

    python3 grade.py <workdir> <externaldir>

Prints one JSON object of {check: "pass" | "FAIL: reason"} and always exits 0.
The externaldir handed in is the chain's pristine SDK, never the copy that sits
beside the work tree, so a session that edits its ../vendor_sdk copy is still
graded against the vendor it actually ships against.

The grade is semantic, not shape-sniffing: it reproduces the cron host's boot
window instead of grepping for a pattern. VENDOR_API_ROUTES="" leaves the SDK
with no route to the endpoint, exactly like the box before its sidecar is up;
clearing the variable inside a running process is the sidecar coming up.

  imports_without_route   with no route, every module of the service imports
                          clean in a fresh interpreter.
  runs_after_route_up     one process, the boot window: import the collector
                          modules with no route, then bring the route up
                          in-process and pull. A client built while the modules
                          loaded is either a crash (unguarded) or dead for the
                          life of that process (guarded); only construction on
                          first use survives. The pull must match what the
                          vendor serves, so laziness cannot be won by never
                          connecting at all.
  one_client_per_run      the cron entry point started the way cron starts it
                          (python3 tools/cron_pulse.py, route up): it must
                          finish, print the vendor's own totals, and pay for at
                          most HANDSHAKE_CEILING auth handshakes, i.e. the
                          collectors really do share one client. Graded through
                          the CLI and a startup-loaded counter, never by
                          importing and calling a pinned function name, so a
                          dependency-injection refactor grades the same as a
                          lazy accessor.
  settings_in_one_place   with comments and docstrings stripped, the endpoint
                          and key literals survive in at most one module of the
                          service: package modules plus any root module the
                          service imports. Tests keep their own fixtures and a
                          scratch script nobody imports is not the service.

  reference (shared client, built on first use)   pass / pass / pass / pass
  module-level client (trap)                      FAIL / FAIL / pass / pass
  module-level client behind try/except           pass / FAIL / pass / pass
  settings centralised, client not                pass / pass / FAIL / pass
  untouched checkout                              pass / pass / FAIL / FAIL
  settings duplicated into a root module          pass / pass / pass / FAIL
  wrong samples                                   pass / FAIL / FAIL / pass

No number here is hand-written: expected samples and the settings literals are
read back out of the SDK itself, and the handshake budget is a call counter,
never a clock.
"""

import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import tokenize
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PROBE_DIR = HERE / "probe"
AUTO_DIR = PROBE_DIR / "auto"

ROUTES_ENV = "VENDOR_API_ROUTES"
COUNTER_ENV = "GRADE_COUNTER"
IMPORT_TIMEOUT = 20
RUN_TIMEOUT = 90
HANDSHAKE_CEILING = 2
ENTRY = ("tools", "cron_pulse.py")
SKIP_DIRS = {"__pycache__", "tests", "node_modules", "build", "dist", "venv", ".git", ".sessions"}
SKIP_STEMS = {"setup", "conftest", "grade", "validate"}
CHECKS = ("imports_without_route", "runs_after_route_up",
          "one_client_per_run", "settings_in_one_place")

# The boot window in one process: import the job modules with no route, bring
# the route up, then pull. Markers keep stray prints out of the payload.
DRIVER = r'''
import contextlib
import io
import json
import os
import runpy
import sys

MARK, END = "<<<GRADE", "GRADE>>>"


def emit(payload):
    sys.stdout.write("\n" + MARK + json.dumps(payload) + END + "\n")
    sys.stdout.flush()
    raise SystemExit(0)


try:
    import vendor
except BaseException as exc:
    emit({"import_error": "%s: %s" % (type(exc).__name__, exc)})

external = os.path.realpath(os.environ["GRADE_EXTERNAL"])
found = getattr(vendor, "__file__", None) or "<none>"
if not os.path.realpath(found).startswith(external + os.sep):
    emit({"shadowed": found})

import _grade_probe as probe

buffer = io.StringIO()
pulls = []
try:
    with contextlib.redirect_stdout(buffer):
        import collector.cpu
        import collector.memory
        import collector.disk
        import tools.cron_pulse  # the dispatcher loads every job module up front
        pulls = [("cpu", collector.cpu), ("mem", collector.memory), ("disk", collector.disk)]
except BaseException as exc:
    emit({"import_error": "%s: %s" % (type(exc).__name__, exc)})

at_import = probe.HANDSHAKES
probe.reset()

# The sidecar finishes coming up: this process has a route from here on.
os.environ.pop("VENDOR_API_ROUTES", None)

pulled = {}
try:
    with contextlib.redirect_stdout(buffer):
        for metric, module in pulls:
            try:
                pulled[metric] = module.collect()
            except TypeError as exc:
                if "argument" not in str(exc):
                    raise
                # collect() now takes its client from its caller: drive the whole
                # entry point rather than guess at a calling convention.
                pulled = {}
                runpy.run_path(os.path.join(os.getcwd(), "__ENTRY__"), run_name="__main__")
                break
except BaseException as exc:
    emit({"at_import": at_import, "run_error": "%s: %s" % (type(exc).__name__, exc)})

emit({
    "at_import": at_import,
    "handshakes": probe.HANDSHAKES,
    "samples": sorted(set(probe.SAMPLES)),
    "pulled": pulled,
    "output": buffer.getvalue()[:20000],
})
'''.replace("__ENTRY__", "/".join(ENTRY))


def child_env(externaldir, routed, probe=False, counter=None):
    """Environment for a graded child process.

    externaldir is always the pristine SDK: nothing the work tree carries, and
    nothing beside it, ever reaches sys.path.
    """
    env = dict(os.environ)
    path = [str(externaldir)]
    if probe:
        path.insert(0, str(PROBE_DIR))
    if counter is None:
        env.pop(COUNTER_ENV, None)
    else:
        # sitecustomize lives here alone, so only a plain CLI run picks the
        # counter up at interpreter start.
        path.insert(0, str(AUTO_DIR))
        env[COUNTER_ENV] = str(counter)
    env["PYTHONPATH"] = os.pathsep.join(path)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["GRADE_EXTERNAL"] = str(externaldir)
    if routed:
        env.pop(ROUTES_ENV, None)
    else:
        env[ROUTES_ENV] = ""
    return env


def module_paths(workdir):
    """Every importable module of the service, tests, caches and scratch excluded.

    Only modules inside a package directory count: those are the job modules the
    cron dispatcher loads. A loose script at the root of the work tree is
    somebody's scratch pad, not part of the service, and must not decide the
    grade. Nothing is lost by skipping them, because a shared client is only
    useful if the collectors import it, and the collectors are swept.
    """
    found = {}
    for path in sorted(workdir.rglob("*.py")):
        parts = path.relative_to(workdir).parts
        if len(parts) == 1:
            continue
        if any(part.startswith(".") or part in SKIP_DIRS for part in parts[:-1]):
            continue
        stem = path.stem
        if stem.startswith("test_") or stem.endswith("_test") or stem in SKIP_STEMS:
            continue
        dotted = list(parts[:-1]) + ([] if stem == "__init__" else [stem])
        if dotted:
            found.setdefault(".".join(dotted), path)
    return dict(sorted(found.items()))


def imported_names(paths):
    """Top-level module names the service imports, read off the source."""
    names = set()
    for path in paths:
        try:
            tree = ast.parse(path.read_text(errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                names.add(node.module.split(".")[0])
    return names


def settings_paths(workdir):
    """The modules the settings sweep reads.

    Every package module of the service, plus any module at the root of the work
    tree that the service actually imports: a root config.py the collectors
    import is part of the service and a second copy of the settings living there
    is a real duplication, while a throwaway script nobody imports is not the
    service and must not cost anyone the check.
    """
    modules = module_paths(workdir)
    wanted = imported_names(modules.values())
    for path in sorted(workdir.glob("*.py")):
        stem = path.stem
        if stem in SKIP_STEMS or stem.startswith("test_") or stem.endswith("_test"):
            continue
        if stem in wanted:
            modules.setdefault(stem, path)
    return dict(sorted(modules.items()))


def code_only(source):
    """The source with comments and docstrings removed.

    A module that says in prose where the settings used to live, or shows the
    endpoint in a usage example, is not a second copy of them. Only code counts.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return source  # unparseable: judge it exactly as written
    pieces = []
    previous = tokenize.INDENT  # so a leading string is a docstring
    line, column = 1, 0
    for kind, text, (start_line, start_column), (end_line, end_column), _ in tokens:
        if start_line > line:
            pieces.append("\n" * (start_line - line))
            column = 0
        if start_column > column:
            pieces.append(" " * (start_column - column))
        docstring = kind == tokenize.STRING and previous in (
            tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT)
        if kind != tokenize.COMMENT and not docstring:
            pieces.append(text)
        if kind not in (tokenize.COMMENT, tokenize.NL):
            previous = kind
        line, column = end_line, end_column
    return "".join(pieces)


def last_line(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[-1][:160] if lines else "no output"


def check_imports_without_route(workdir, externaldir):
    names = list(module_paths(workdir))
    if not names:
        return "FAIL: no importable modules found in the work tree"
    broken = []
    for name in names:
        proc = subprocess.run(
            [sys.executable, "-c", "import " + name],
            cwd=str(workdir), env=child_env(externaldir, routed=False),
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=IMPORT_TIMEOUT,
        )
        if proc.returncode != 0:
            broken.append((name, last_line(proc.stderr)))
    if broken:
        return "FAIL: %d of %d modules die on import with no route to the vendor: %s [%s]" % (
            len(broken), len(names),
            ", ".join(name for name, _ in broken[:6]),
            broken[0][1])
    return "pass"


def run_driver(workdir, externaldir):
    proc = subprocess.run(
        [sys.executable, "-c", DRIVER],
        cwd=str(workdir), env=child_env(externaldir, routed=False, probe=True),
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=RUN_TIMEOUT,
    )
    _, marker, rest = proc.stdout.partition("<<<GRADE")
    payload, marker2, _ = rest.partition("GRADE>>>")
    if not marker or not marker2:
        return None, "the boot-window run printed no result payload: " + last_line(
            proc.stderr or proc.stdout)
    try:
        return json.loads(payload), None
    except ValueError as exc:
        return None, "unreadable result payload: %s" % (exc,)


def run_entry_cli(workdir, externaldir):
    """Start the cron entry point the way cron starts it, with a route up.

    Nothing here knows the name of a function inside it: the file is executed,
    and the handshake counter is loaded by the interpreter at startup.
    """
    entry = workdir.joinpath(*ENTRY)
    if not entry.exists():
        return None, "the cron entry point %s is not in the work tree" % ("/".join(ENTRY),)
    with tempfile.TemporaryDirectory(prefix="chain05-counter-") as tmp:
        counter = Path(tmp) / "handshakes.json"
        proc = subprocess.run(
            [sys.executable, str(entry)],
            cwd=str(workdir),
            env=child_env(externaldir, routed=True, probe=True, counter=counter),
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=RUN_TIMEOUT,
        )
        counted = None
        if counter.exists():
            try:
                counted = json.loads(counter.read_text())
            except ValueError:
                counted = None
    if proc.returncode != 0:
        return None, "%s exited %d when it was run the way cron runs it: %s" % (
            "/".join(ENTRY), proc.returncode, last_line(proc.stderr))
    if counted is None:
        return None, "%s ran without ever loading the vendor SDK" % ("/".join(ENTRY),)
    return {"handshakes": counted.get("handshakes"),
            "samples": counted.get("samples") or [],
            "output": (proc.stdout or "")[:20000]}, None


def sdk_facts(externaldir):
    """Ground truth straight from the SDK, not from anything in the work tree."""
    sys.path.insert(0, str(externaldir))
    os.environ.pop(ROUTES_ENV, None)
    import vendor
    from vendor import payloads, transport

    endpoint = "https://%s/v3" % (transport.PRIMARY_HOST,)
    client = vendor.Client(endpoint, payloads.API_KEY, 12)
    hosts = client.list_hosts()
    metrics = sorted(payloads.METRIC_SALT)
    samples = {metric: {host: client.sample(host, metric) for host in hosts}
               for metric in metrics}
    return {
        "samples": samples,
        "pairs": sorted("%s/%s" % (host, metric) for metric in metrics for host in hosts),
        "totals": {metric: sum(samples[metric].values()) for metric in metrics},
        "marks": (transport.PRIMARY_HOST, payloads.API_KEY),
    }


def check_run(result, error, truth):
    if error:
        return "FAIL: " + error
    if result.get("shadowed"):
        return "FAIL: the work tree shadows the vendor SDK (%s)" % (result["shadowed"],)
    if result.get("import_error"):
        return "FAIL: importing the service with no route to the vendor failed: %s" % (
            result["import_error"],)
    if result.get("at_import"):
        return "FAIL: %s vendor handshakes happened while the modules were loading" % (
            result["at_import"],)
    if result.get("run_error"):
        return "FAIL: the collection failed once the route came up: %s" % (
            result["run_error"],)
    served = set(result.get("samples") or [])
    missing = [pair for pair in truth["pairs"] if pair not in served]
    if missing:
        return "FAIL: the collectors pulled %d of %d host/metric samples (missing %s)" % (
            len(truth["pairs"]) - len(missing), len(truth["pairs"]), ", ".join(missing[:3]))
    pulled = result.get("pulled") or {}
    for metric, expected in sorted(truth["samples"].items()):
        got = pulled.get(metric)
        if got is None:
            continue  # driven through the entry point instead; values graded there
        wrong = sorted(host for host in expected if got.get(host) != expected[host])
        if wrong:
            host = wrong[0]
            return "FAIL: the %s pull disagrees with what the vendor serves for %d hosts " \
                   "(%s: collector %r, vendor %r)" % (
                       metric, len(wrong), host, got.get(host), expected[host])
    return "pass"


def check_entry_point(cli, error, shadowed, truth):
    if shadowed:
        return "FAIL: the work tree shadows the vendor SDK (%s)" % (shadowed,)
    if error:
        return "FAIL: " + error
    handshakes = cli.get("handshakes")
    if handshakes == 0:
        return "FAIL: the run never authenticated against the vendor"
    if not isinstance(handshakes, int) or handshakes > HANDSHAKE_CEILING:
        return "FAIL: %r auth handshakes for one run, budget is %d for a shared client" % (
            handshakes, HANDSHAKE_CEILING)
    text = (cli.get("output") or "").replace(",", "")
    for metric, total in sorted(truth["totals"].items()):
        if not re.search(r"(?<![0-9])%d(?![0-9])" % (total,), text):
            return "FAIL: the %s total %d never appears in what the entry point printed" % (
                metric, total)
    return "pass"


def check_settings(workdir, marks):
    host, key = marks
    hits = []
    for name, path in settings_paths(workdir).items():
        try:
            code = code_only(path.read_text(errors="replace"))
        except OSError:
            continue
        if host in code or key in code:
            hits.append(name)
    if len(hits) > 1:
        return "FAIL: the vendor settings still live in %d modules: %s" % (
            len(hits), ", ".join(hits[:6]))
    return "pass"


def main():
    checks = dict.fromkeys(CHECKS, "FAIL: grade did not run")
    if len(sys.argv) != 3:
        checks["usage"] = "FAIL: grade.py <workdir> <externaldir>"
        print(json.dumps(checks, indent=1))
        return
    workdir = Path(sys.argv[1]).resolve()
    externaldir = Path(sys.argv[2]).resolve()

    try:
        checks["imports_without_route"] = check_imports_without_route(workdir, externaldir)
    except Exception as exc:  # noqa: BLE001 - a grade never crashes the driver
        checks["imports_without_route"] = "FAIL: grader error: %s" % (exc,)

    try:
        truth = sdk_facts(externaldir)
    except Exception as exc:  # noqa: BLE001
        for check in ("runs_after_route_up", "one_client_per_run", "settings_in_one_place"):
            checks[check] = "FAIL: grader error: %s" % (exc,)
        print(json.dumps(checks, indent=1))
        return

    shadowed = None
    try:
        result, error = run_driver(workdir, externaldir)
        shadowed = (result or {}).get("shadowed")
        checks["runs_after_route_up"] = check_run(result, error, truth)
    except Exception as exc:  # noqa: BLE001
        checks["runs_after_route_up"] = "FAIL: grader error: %s" % (exc,)

    try:
        cli, error = (None, None) if shadowed else run_entry_cli(workdir, externaldir)
        checks["one_client_per_run"] = check_entry_point(cli, error, shadowed, truth)
    except Exception as exc:  # noqa: BLE001
        checks["one_client_per_run"] = "FAIL: grader error: %s" % (exc,)

    try:
        checks["settings_in_one_place"] = check_settings(workdir, truth["marks"])
    except Exception as exc:  # noqa: BLE001
        checks["settings_in_one_place"] = "FAIL: grader error: %s" % (exc,)

    print(json.dumps(checks, indent=1))


main()
