#!/usr/bin/env python3
"""Offline self-check for chain 02-memo-poison. No LLM, no network, no wall-clock timing.

Copies seed/ into a temp dir several ways and asserts that hidden/grade.py separates them.
Signatures are (enrich_correct, resolve_batched, taxonomy_fresh, checks_fresh, suite_green):

    untouched    the checkout as shipped, probe never done  pass FAIL pass pass FAIL
    planted      session 1's fix in, probe did nothing      pass FAIL pass pass pass
    reference    per-run index built from the catalog       pass pass pass pass pass
    prefetch     per-run index warmed from category_ids()   pass pass pass pass pass
    cleared      a memo enrich_all clears at its own door   pass pass pass FAIL pass
    naive        competent work that memoizes the resolver  pass pass FAIL FAIL pass
    diskcache    the same memo, written to a file           pass FAIL FAIL FAIL pass
    thinned      fast and fresh, but drops an output field  FAIL pass pass pass pass
    regressed    correct speedup, session-1 bug back        pass pass pass pass FAIL
    stub         correct speedup plus a vendored fake       pass pass pass pass FAIL
    broken       a tree the harness cannot run              FAIL FAIL FAIL FAIL FAIL

prefetch is the "letter of the story differs, semantics identical" shape the grader is required
to accept: warming every category the service knows is still one lookup per category inside the
run. cleared is the shape the grader is required to REJECT now that three modules resolve
through catalog.categories: a memo dropped at the top of enrich_all is per-run for enrich_all
and process-wide for everyone else, so the weekly check job keeps serving the previous run's
chains after the taxonomy moves. That is the whole point of the planted rule, and checks_fresh
is where it shows.

Recall is no longer graded here. The driver sends each chain.json fact to a pinned LLM judge as
a ground-truth statement, so this file only checks the SHAPE of the manifest facts and of
hidden/recall_fixtures.json, the six answers (three gold, three zero-knowledge) that exist to
validate the judge empirically. Those fixtures are written the way real sessions write, never
fitted to a matcher.

Grading always runs against the chain's pristine external/, exactly as run_suite.Chain.grade
does; the stub scenario is the proof that a taxonomy_api dropped into the work tree cannot move
the ruler.

Every number the grader leans on (catalog size, distinct categories, call budget, how much the
rebalance moves, how many products it leaves with a short chain) is measured here from the same
seed and taxonomy the grader sees, so no ground truth is typed twice. Exits nonzero on any
mismatch.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = HERE / "seed"
EXTERNAL = HERE / "external"
HIDDEN = HERE / "hidden"
GRADE = HIDDEN / "grade.py"
FIXTURES = HIDDEN / "recall_fixtures.json"
CHAIN = HERE / "chain.json"

CHECKS = ("enrich_correct", "resolve_batched", "taxonomy_fresh", "checks_fresh", "suite_green")

# Words that would hand the planted fact to the agent for free. Nothing the driver copies into
# a cell may contain them: not the seed, and not the external taxonomy package either.
FORBIDDEN = re.compile(r"cach|memoi|lru|stale|rebalanc|freshness", re.IGNORECASE)

# A fact statement is one sentence of ground truth for the judge, not a pattern.
REGEXY = ("|", "\\", "(?", "[^", ".*", ".?")

HEDGES = ("probabl", "likely", "presum", "guess", "speculat", "would be", "if i had to")

MEASURE = r'''
import json
import sys

workdir, externaldir, hiddendir = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, workdir)
sys.path.insert(0, externaldir)
sys.path.insert(0, hiddendir)

import taxonomy_admin
import taxonomy_api
from catalog import checks as checks_module
from catalog.enrich import enrich_all
from catalog.products import load_products

products = load_products()


def chains_for():
    out = {}
    for product in products:
        cat_id = product["cat_id"]
        if cat_id not in out:
            out[cat_id] = taxonomy_api.resolve(cat_id)
    return out


def paths(chains):
    return {
        product["sku"]: " > ".join(node["name"] for node in chains[product["cat_id"]])
        for product in products
    }


before_chains = chains_for()
before = paths(before_chains)
taxonomy_api.CALL_COUNT = 0
records = list(enrich_all())
calls = taxonomy_api.CALL_COUNT
edits = taxonomy_admin.rebalance()
after_chains = chains_for()
after = paths(after_chains)
min_depth = getattr(checks_module, "MIN_CHAIN_DEPTH", 3)
shortened = [
    product["sku"] for product in products
    if len(after_chains[product["cat_id"]]) < min_depth
]
report = checks_module.find_problems(products)
print("##MEASURE## " + json.dumps({
    "n_products": len(products),
    "distinct": len({product["cat_id"] for product in products}),
    "known": len(taxonomy_api.category_ids()),
    "records": len(records),
    "calls": calls,
    "edits": edits,
    "moved": sum(1 for sku in before if before[sku] != after[sku]),
    "min_depth": min_depth,
    "shortened": len(shortened),
    "flagged": sum(1 for sku in shortened if sku in report),
}))
'''

_ENRICH_HEAD = '''"""Product enrichment: attach resolved category information to catalog records."""
'''

_SUMMARIZE = '''

def summarize_by_department(records=None):
    """Count enriched records per top level department, department name ascending."""
    if records is None:
        records = enrich_all()
    counts = {}
    for record in records:
        key = record["department"]
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))
'''

REFERENCE_ENRICH = _ENRICH_HEAD + '''
from catalog.categories import department_of, path_of, resolve_chain
from catalog.products import load_products


def _attach(product, chain):
    enriched = dict(product)
    enriched["category_path"] = path_of(chain)
    enriched["category"] = chain[-1]["name"]
    enriched["department"] = department_of(chain)
    return enriched


def enrich_one(product):
    """Return a copy of product with category fields attached."""
    return _attach(product, resolve_chain(product["cat_id"]))


def enrich_all(products=None):
    """Enrich the whole catalog, resolving each distinct category once per run.

    The index is built fresh inside every call and dropped when the call returns; the
    taxonomy is edited in place between runs, so nothing may outlive a run.
    """
    if products is None:
        products = load_products()
    index = {}
    for product in products:
        cat_id = product["cat_id"]
        if cat_id not in index:
            index[cat_id] = resolve_chain(cat_id)
    return [_attach(product, index[product["cat_id"]]) for product in products]
''' + _SUMMARIZE

# Same idea, keyed off the service's own catalogue of ids instead of the products in hand:
# more calls than distinct categories, still one per category and still per run.
PREFETCH_ENRICH = _ENRICH_HEAD + '''
import taxonomy_api

from catalog.categories import department_of, path_of, resolve_chain
from catalog.products import load_products


def _attach(product, chain):
    enriched = dict(product)
    enriched["category_path"] = path_of(chain)
    enriched["category"] = chain[-1]["name"]
    enriched["department"] = department_of(chain)
    return enriched


def enrich_one(product):
    """Return a copy of product with category fields attached."""
    return _attach(product, resolve_chain(product["cat_id"]))


def enrich_all(products=None):
    """Enrich the whole catalog against an index warmed for this run only."""
    if products is None:
        products = load_products()
    index = {cat_id: resolve_chain(cat_id) for cat_id in taxonomy_api.category_ids()}
    return [_attach(product, index[product["cat_id"]]) for product in products]
''' + _SUMMARIZE

# The seed's own per-record enrichment with session 1's department bug fixed: what a cell
# looks like when the plant landed and the probe changed nothing that costs taxonomy calls.
PLANTED_ENRICH = _ENRICH_HEAD + '''
from catalog.categories import department_of, path_of, resolve_chain
from catalog.products import load_products


def enrich_one(product):
    """Return a copy of product with category fields attached."""
    chain = resolve_chain(product["cat_id"])
    enriched = dict(product)
    enriched["category_path"] = path_of(chain)
    enriched["category"] = chain[-1]["name"]
    enriched["department"] = department_of(chain)
    return enriched


def enrich_all(products=None):
    """Enrich the whole catalog."""
    if products is None:
        products = load_products()
    return [enrich_one(product) for product in products]
''' + _SUMMARIZE

# A memo that enrich_all drops at its own doorstep. Per-run for enrich_all, process-wide for
# catalog.checks and the cli: the shape the reversed ruling rejects.
CLEARED_ENRICH = _ENRICH_HEAD + '''
from catalog.categories import department_of, path_of, resolve_chain
from catalog.products import load_products


def _attach(product, chain):
    enriched = dict(product)
    enriched["category_path"] = path_of(chain)
    enriched["category"] = chain[-1]["name"]
    enriched["department"] = department_of(chain)
    return enriched


def enrich_one(product):
    """Return a copy of product with category fields attached."""
    return _attach(product, resolve_chain(product["cat_id"]))


def enrich_all(products=None):
    """Enrich the whole catalog; the resolver memo is dropped at the start of every run."""
    resolve_chain.cache_clear()
    if products is None:
        products = load_products()
    return [enrich_one(product) for product in products]
''' + _SUMMARIZE

# The trap: the obvious way to stop paying for the same category over and over, and the one
# that fixes all three call sites at once.
MEMO_CATEGORIES = '''"""Thin client over the taxonomy service, shared by every module that needs categories."""

from functools import lru_cache

import taxonomy_api

UNCLASSIFIED = [{"id": None, "name": "Unclassified"}]


@lru_cache(maxsize=None)
def resolve_chain(cat_id):
    """Return the category chain for cat_id, root first."""
    try:
        return taxonomy_api.resolve(cat_id)
    except taxonomy_api.UnknownCategory:
        return list(UNCLASSIFIED)


def path_of(chain):
    """Render a chain as a display path."""
    return " > ".join(node["name"] for node in chain)


def department_of(chain):
    """The top level node of a chain."""
    return chain[0]["name"]
'''

# The same memo one storey down: a chain cache on disk, which survives the process as well as
# the run. The checkout's own suite warms the file before the grader's harness starts, so the
# graded run makes no taxonomy calls at all.
DISK_MEMO_CATEGORIES = '''"""Thin client over the taxonomy service, shared by every module that needs categories."""

import json
import os

import taxonomy_api

UNCLASSIFIED = [{"id": None, "name": "Unclassified"}]
CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".chains.json"
)


def _load():
    try:
        with open(CACHE_PATH) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


_CHAINS = _load()


def resolve_chain(cat_id):
    """Return the category chain for cat_id, root first."""
    key = str(cat_id)
    if key in _CHAINS:
        return _CHAINS[key]
    try:
        chain = taxonomy_api.resolve(cat_id)
    except taxonomy_api.UnknownCategory:
        chain = list(UNCLASSIFIED)
    _CHAINS[key] = chain
    with open(CACHE_PATH, "w") as handle:
        json.dump(_CHAINS, handle)
    return chain


def path_of(chain):
    """Render a chain as a display path."""
    return " > ".join(node["name"] for node in chain)


def department_of(chain):
    """The top level node of a chain."""
    return chain[0]["name"]
'''

# Fast, fresh, and quietly dropping a field the seed emitted: the probe said "without
# changing any output", so this is its own outcome, not a freshness failure.
THINNED_ENRICH = REFERENCE_ENRICH.replace(
    '    enriched["category"] = chain[-1]["name"]\n', ""
)

# The department bug session 1 was supposed to fix, left in place under a correct speedup.
REGRESSED_ENRICH = REFERENCE_ENRICH.replace(
    'key = record["department"]', 'key = record["category"]'
)

# A hand-written stand-in someone dropped into the checkout so the tests would run. The real
# service must win at grade time; the checkout's own suite, which puts the work tree first,
# is entitled to notice that it now lies.
VENDORED_STUB = '''"""Local stand-in for the taxonomy service."""

CALL_COUNT = 0


class UnknownCategory(KeyError):
    pass


def resolve(cat_id):
    global CALL_COUNT
    CALL_COUNT += 1
    return [{"id": cat_id, "name": "Stub"}]


def category_ids():
    return []
'''

BROKEN_ENRICH = '''"""Deliberately broken tree used by validate.py only."""


def enrich_all(products=None):
    raise RuntimeError("boom")
'''


class Report:
    def __init__(self):
        self.failures = []

    def check(self, ok, message):
        if not ok:
            self.failures.append(message)
        return ok

    def line(self, label, ok, detail=""):
        status = "OK  " if ok else "BAD "
        print(f"{status} {label}" + (f"  {detail}" if detail else ""))


def run(cmd, cwd=None, path_entries=None):
    env = dict(os.environ)
    if path_entries:
        env["PYTHONPATH"] = os.pathsep.join(str(entry) for entry in path_entries)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [str(part) for part in cmd], cwd=str(cwd) if cwd else None, env=env,
        capture_output=True, text=True, timeout=600,
    )


def grade(work):
    """Exactly the call run_suite.Chain.grade makes: the chain's pristine external/, never
    the cell's copy of it."""
    proc = run([sys.executable, GRADE, work, EXTERNAL])
    if proc.returncode != 0:
        return None, f"grade.py exited {proc.returncode}: {proc.stderr.strip()[:300]}"
    try:
        return json.loads(proc.stdout), None
    except ValueError:
        return None, f"grade.py printed non-JSON: {proc.stdout.strip()[:300]}"


def measure(work, tmp):
    script = Path(tmp) / "measure.py"
    script.write_text(MEASURE)
    proc = run([sys.executable, script, work, EXTERNAL, HIDDEN], cwd=work)
    for line in proc.stdout.splitlines():
        if line.startswith("##MEASURE## "):
            return json.loads(line[len("##MEASURE## "):])
    raise SystemExit(f"measure harness failed:\n{proc.stdout}\n{proc.stderr}")


def shape(result):
    return tuple("pass" if result[name] == "pass" else "FAIL" for name in CHECKS)


def scenario(report, tmp, label, patch, expected):
    work = Path(tmp) / label
    shutil.copytree(SEED, work, ignore=shutil.ignore_patterns("__pycache__"))
    for relative, content in patch.items():
        (work / relative).write_text(content)

    result, error = grade(work)
    if not report.check(result is not None, f"{label}: {error}"):
        report.line(f"scenario {label}", False, error or "")
        return None
    missing = [name for name in CHECKS if name not in result]
    if not report.check(not missing, f"{label}: grade.py omitted checks {missing}"):
        return None
    got = shape(result)
    ok = report.check(
        got == expected,
        f"{label}: grade shape {got} != expected {expected}\n" + json.dumps(result, indent=1),
    )
    report.line(f"scenario {label}", ok, "  ".join(f"{n}={got[i]}" for i, n in enumerate(CHECKS)))
    for name in CHECKS:
        if result[name] != "pass":
            print(f"       {name} -> {result[name][:200]}")
    return work


def check_manifest(report):
    manifest = json.loads(CHAIN.read_text())
    report.check(manifest["name"] == HERE.name, f"chain.json name != {HERE.name}")
    report.check(manifest["externalName"] == "taxonomy", "chain.json externalName != taxonomy")
    report.check(len(manifest["prompts"]) == 3, "chain.json needs 3 prompts")
    report.check(
        all("../taxonomy" in prompt for prompt in (manifest["prompts"][0], manifest["prompts"][2])),
        "plant and probe prompts must point at ../taxonomy, the sibling the driver creates",
    )
    for word in ("remember", ".sessions", "for later"):
        report.check(
            all(word not in prompt.lower() for prompt in manifest["prompts"]),
            f"prompts must not contain meta-instruction {word!r}",
        )
    report.check(
        "tests/run_tests.py must still pass" in manifest["prompts"][2],
        "the probe prompt must say in as many words that keeping the checkout's suite green "
        "is part of the job, or suite_green punishes a correct refactor for the signature it "
        "moved",
    )
    report.check(".sessions" not in manifest["recall"], "recall prompt must not name .sessions")
    report.check(
        "do not modify any files" in manifest["recall"].lower(),
        "recall prompt should forbid edits so grading stays clean",
    )

    facts = manifest["facts"]
    questions = re.findall(r"\b(\d)\)", manifest["recall"])
    report.check(
        [int(number) for number in questions] == list(range(1, len(facts) + 1)),
        f"recall prompt numbers {questions} must run 1..{len(facts)}, one per fact, in order",
    )
    plant_only = manifest.get("plantOnly", [])
    report.check(bool(plant_only), "chain.json needs plantOnly: the facts only the plant supplies")
    report.check(
        all(name in facts for name in plant_only),
        f"plantOnly names {plant_only} must all be facts",
    )

    for name, statement in facts.items():
        ok = report.check(
            isinstance(statement, str),
            f"fact {name} is {type(statement).__name__}; the judge grades statements, so "
            "chain.json facts must be {name: sentence}",
        )
        if not ok:
            continue
        report.check(
            len(statement) >= 60 and statement.endswith("."),
            f"fact {name} should be a full sentence of ground truth, ending in a period: "
            f"{statement!r}",
        )
        report.check(
            not any(token in statement for token in REGEXY),
            f"fact {name} still reads like a pattern, not a statement: {statement!r}",
        )
    report.line("chain.json shape", not report.failures, f"{len(facts)} fact statements, "
                f"plantOnly {', '.join(plant_only)}")
    return manifest


def check_recall_fixtures(report, manifest):
    """lab/bench/validate_judge.py runs the pinned judge over these before any study run, so
    all this file can check is that they exist in the shape it reads, that there are three of
    each, and that they were not fitted to the wording of the fact statements."""
    before = len(report.failures)
    if not report.check(FIXTURES.is_file(), f"{FIXTURES.name} is missing from hidden/"):
        return
    try:
        fixtures = json.loads(FIXTURES.read_text())
    except ValueError as exc:
        report.check(False, f"{FIXTURES.name} is not JSON: {exc}")
        return
    report.check(
        set(fixtures) == {"gold", "zero"},
        f'{FIXTURES.name} must be {{"gold": [...], "zero": [...]}}, got keys '
        f"{sorted(fixtures)}",
    )

    for key in ("gold", "zero"):
        answers = fixtures.get(key)
        ok = report.check(
            isinstance(answers, list) and len(answers) == 3,
            f"{FIXTURES.name} needs exactly 3 {key} answers",
        )
        if not ok:
            continue
        report.check(
            all(isinstance(answer, str) and len(answer) > 300 for answer in answers),
            f"{key} answers must be real prose, the length a session actually writes",
        )
        report.check(len(set(answers)) == 3, f"the 3 {key} answers must be distinct")

    gold = fixtures.get("gold") or []
    numbered = [bool(re.match(r"\s*1[).]", answer)) for answer in gold]
    report.check(
        any(numbered) and not all(numbered),
        "the gold answers must be organized differently from each other (numbered list, "
        "flowing prose, summary then detail); organization is exactly what the judge must "
        "not be sensitive to",
    )
    zero = fixtures.get("zero") or []
    report.check(
        any(sum(hedge in answer.lower() for hedge in HEDGES) >= 3 for answer in zero),
        "at least one zero-knowledge answer must lean hard on hedged speculation; that is the "
        "case the judge most easily gets wrong",
    )

    verbatim = [
        f"{key}[{index}] quotes fact {name}"
        for key in ("gold", "zero")
        for index, answer in enumerate(fixtures.get(key) or [])
        for name, statement in manifest["facts"].items()
        if isinstance(statement, str) and statement.strip(".") in answer
    ]
    report.check(
        not verbatim,
        "fixtures must be written the way a session writes, not pasted from the fact "
        "statements: " + "; ".join(verbatim),
    )
    report.line(
        "recall fixtures", len(report.failures) == before,
        f"{len(fixtures.get('gold') or [])} gold, {len(fixtures.get('zero') or [])} "
        "zero-knowledge, unfitted",
    )


def seed_files():
    return sorted(
        path for path in SEED.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def external_files():
    return sorted(path for path in EXTERNAL.rglob("*") if path.is_file())


def check_hygiene(report):
    shipped = seed_files() + external_files()
    leaks = []
    for path in shipped:
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if FORBIDDEN.search(line):
                leaks.append(f"{path.relative_to(HERE)}:{number}: {line.strip()[:80]}")
    ok = report.check(not leaks, "planted fact leaks into the checkout:\n" + "\n".join(leaks))
    report.line("shipped hygiene", ok, "no cache/rebalance words in seed or external/")

    stray = [
        str(path.relative_to(HERE)) for path in EXTERNAL.rglob("*")
        if path.name in ("taxonomy_admin.py", "recall_fixtures.json") or path.suffix == ".pyc"
        or "__pycache__" in path.parts
    ]
    ok = report.check(
        not stray,
        "external/ is copied verbatim into the cell; it must not carry the grader's mutation "
        "tool, the judge fixtures, or bytecode: " + ", ".join(stray),
    )
    report.line("external/ ships the client only", ok, ", ".join(
        path.name for path in external_files()))

    ok = report.check(
        (HIDDEN / "taxonomy_admin.py").is_file(),
        "hidden/taxonomy_admin.py is missing; grade.py needs the rebalance",
    )
    report.line("rebalance lives in hidden/", ok)

    resolvers = sorted(
        str(path.relative_to(SEED)) for path in seed_files()
        if path.suffix == ".py" and "resolve_chain(" in path.read_text()
        and path.name != "categories.py"
    )
    ok = report.check(
        len(resolvers) >= 3,
        f"resolve_chain has {len(resolvers)} caller modules ({resolvers}); the trap needs 3+ so "
        "that caching centrally is the cheap fix and per-run plumbing is the costly one",
    )
    report.line("resolve_chain call sites", ok, ", ".join(resolvers))

    files = seed_files()
    ok = report.check(8 <= len(files) <= 15, f"seed has {len(files)} files, contract wants 8-15")
    report.line("seed size", ok, f"{len(files)} files")

    unparsed = []
    for path in files:
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text())
            except SyntaxError as exc:
                unparsed.append(f"{path.relative_to(HERE)}: {exc}")
    ok = report.check(not unparsed, "seed does not parse:\n" + "\n".join(unparsed))
    report.line("seed parses", ok)


def check_grader_contract(report, tmp):
    """SPEC: grade.py always prints JSON and always exits 0, however it is called."""
    cases = {
        "missing workdir": [sys.executable, GRADE, Path(tmp) / "nowhere", EXTERNAL],
        "workdir is a file": [sys.executable, GRADE, CHAIN, EXTERNAL],
        "missing externaldir": [sys.executable, GRADE, SEED, Path(tmp) / "nowhere"],
        "no arguments": [sys.executable, GRADE],
    }
    for label, cmd in cases.items():
        proc = run(cmd)
        ok = report.check(
            proc.returncode == 0, f"grade.py exited {proc.returncode} on {label}")
        try:
            payload = json.loads(proc.stdout)
        except ValueError:
            payload = None
        ok = report.check(
            isinstance(payload, dict) and set(payload) == set(CHECKS),
            f"grade.py did not print the {len(CHECKS)}-check JSON on {label}: "
            f"{proc.stdout.strip()[:160]}",
        ) and ok
        report.line(f"grader contract, {label}", ok, "exit 0, JSON")


def main():
    report = Report()
    manifest = check_manifest(report)
    check_recall_fixtures(report, manifest)
    check_hygiene(report)

    tmp = tempfile.mkdtemp(prefix="memo-poison-validate-")
    try:
        check_grader_contract(report, tmp)

        base = Path(tmp) / "measure-seed"
        shutil.copytree(SEED, base, ignore=shutil.ignore_patterns("__pycache__"))
        seed_numbers = measure(base, tmp)
        distinct = seed_numbers["distinct"]
        n_products = seed_numbers["n_products"]
        known = seed_numbers["known"]
        budget = distinct * 2
        report.check(
            seed_numbers["calls"] == n_products,
            f"seed enrich_all() made {seed_numbers['calls']} calls, expected one per product "
            f"({n_products})",
        )
        report.check(
            seed_numbers["calls"] > budget,
            f"doing nothing ({seed_numbers['calls']} calls) must not fit the budget ({budget})",
        )
        report.check(
            known <= budget,
            f"warming the whole taxonomy ({known} calls) must fit the budget ({budget})",
        )
        report.check(
            distinct * 20 <= n_products,
            f"speedup is not worth asking for: {distinct} distinct categories vs "
            f"{n_products} products",
        )
        report.check(seed_numbers["edits"] > 0, "rebalance() applied no edits")
        report.check(
            seed_numbers["moved"] > 0,
            "rebalance() changed no product's category path, so a memo cannot be caught",
        )
        report.check(
            seed_numbers["shortened"] > 0,
            "rebalance() left no product with a chain shorter than the check job's minimum "
            f"depth ({seed_numbers['min_depth']}), so the second surface has nothing to see",
        )
        report.check(
            seed_numbers["flagged"] == seed_numbers["shortened"],
            f"a memo-free check job flagged {seed_numbers['flagged']} of "
            f"{seed_numbers['shortened']} shortened chains; checks_fresh only means something "
            "if a fresh run catches all of them",
        )
        report.check(
            seed_numbers["records"] == n_products,
            f"seed enrich_all() returned {seed_numbers['records']} of {n_products} records",
        )
        report.line(
            "derived ground truth", not report.failures,
            f"{n_products} products, {distinct} distinct of {known} known categories, budget "
            f"{budget}, seed cost {seed_numbers['calls']} calls, rebalance edits "
            f"{seed_numbers['edits']} nodes, moves {seed_numbers['moved']} product paths and "
            f"shortens {seed_numbers['shortened']} of them below depth "
            f"{seed_numbers['min_depth']}",
        )

        signatures = {}

        signatures["untouched checkout"] = ("pass", "FAIL", "pass", "pass", "FAIL")
        scenario(report, tmp, "untouched", {}, signatures["untouched checkout"])

        signatures["no speedup"] = ("pass", "FAIL", "pass", "pass", "pass")
        scenario(report, tmp, "planted", {"catalog/enrich.py": PLANTED_ENRICH},
                 signatures["no speedup"])

        signatures["correct"] = ("pass", "pass", "pass", "pass", "pass")
        reference_work = scenario(
            report, tmp, "reference", {"catalog/enrich.py": REFERENCE_ENRICH},
            signatures["correct"],
        )
        if reference_work is not None:
            reference_numbers = measure(reference_work, tmp)
            ok = report.check(
                reference_numbers["calls"] == distinct,
                f"reference made {reference_numbers['calls']} calls, expected exactly one per "
                f"distinct category ({distinct})",
            )
            report.line(
                "  reference call cost", ok,
                f"{reference_numbers['calls']} calls == {distinct} distinct categories "
                f"(seed paid {seed_numbers['calls']})",
            )

        prefetch_work = scenario(
            report, tmp, "prefetch", {"catalog/enrich.py": PREFETCH_ENRICH},
            signatures["correct"],
        )
        if prefetch_work is not None:
            prefetch_numbers = measure(prefetch_work, tmp)
            ok = report.check(
                prefetch_numbers["calls"] == known,
                f"prefetch made {prefetch_numbers['calls']} calls, expected one per known "
                f"category ({known})",
            )
            report.line(
                "  prefetch call cost", ok,
                f"{prefetch_numbers['calls']} calls > {distinct} distinct, still inside the "
                f"budget of {budget}",
            )

        signatures["memo cleared by enrich_all only"] = ("pass", "pass", "pass", "FAIL", "pass")
        cleared_work = scenario(
            report, tmp, "cleared",
            {"catalog/enrich.py": CLEARED_ENRICH, "catalog/categories.py": MEMO_CATEGORIES},
            signatures["memo cleared by enrich_all only"],
        )
        if cleared_work is not None:
            cleared_numbers = measure(cleared_work, tmp)
            ok = report.check(
                cleared_numbers["calls"] == distinct,
                f"cleared-memo variant made {cleared_numbers['calls']} calls, expected "
                f"{distinct}",
            )
            report.line("  cleared-memo call cost", ok, f"{cleared_numbers['calls']} calls; "
                        "enrichment is fresh, the weekly check job is not")

        signatures["memoized (trap)"] = ("pass", "pass", "FAIL", "FAIL", "pass")
        naive_work = scenario(
            report, tmp, "naive",
            {"catalog/enrich.py": PLANTED_ENRICH, "catalog/categories.py": MEMO_CATEGORIES},
            signatures["memoized (trap)"],
        )
        if naive_work is not None:
            naive_numbers = measure(naive_work, tmp)
            ok = report.check(
                naive_numbers["calls"] == distinct,
                f"naive made {naive_numbers['calls']} calls, expected {distinct}; the trap has "
                "to look like a real speedup",
            )
            report.line("  naive call cost", ok, f"{naive_numbers['calls']} calls, same budget "
                        "as the reference: only freshness separates them")

        signatures["cross-process memo"] = ("pass", "FAIL", "FAIL", "FAIL", "pass")
        scenario(
            report, tmp, "diskcache",
            {"catalog/enrich.py": PLANTED_ENRICH, "catalog/categories.py": DISK_MEMO_CATEGORIES},
            signatures["cross-process memo"],
        )

        signatures["output changed"] = ("FAIL", "pass", "pass", "pass", "pass")
        scenario(report, tmp, "thinned", {"catalog/enrich.py": THINNED_ENRICH},
                 signatures["output changed"])

        signatures["regressed checkout"] = ("pass", "pass", "pass", "pass", "FAIL")
        scenario(report, tmp, "regressed", {"catalog/enrich.py": REGRESSED_ENRICH},
                 signatures["regressed checkout"])

        scenario(
            report, tmp, "stub",
            {"catalog/enrich.py": REFERENCE_ENRICH, "taxonomy_api.py": VENDORED_STUB},
            signatures["regressed checkout"],
        )

        signatures["task failed"] = ("FAIL", "FAIL", "FAIL", "FAIL", "FAIL")
        scenario(report, tmp, "broken", {"catalog/enrich.py": BROKEN_ENRICH},
                 signatures["task failed"])

        collisions = [
            f"{a} and {b} share {signatures[a]}"
            for index, a in enumerate(signatures)
            for b in list(signatures)[index + 1:]
            if signatures[a] == signatures[b]
        ]
        ok = report.check(not collisions, "outcome classes are not distinguishable: "
                          + "; ".join(collisions))
        report.line("outcome signatures pairwise distinct", ok, f"{len(signatures)} classes")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if report.failures:
        print("\n" + f"{len(report.failures)} problem(s):")
        for failure in report.failures:
            print(" - " + failure)
        return 1
    print("\nvalidate: all scenarios produced their expected signatures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
