#!/usr/bin/env python3
"""Offline self-check for chain 03-consumer-contract. No LLM, no network.

Builds a checkout per scenario in a temp dir and grades each one. The canonical
outcomes, whose five-check signatures must stay distinct:

    reference       day-one totals fix plus dollars on the printed summary,
                    report.txt still integer cents            -> everything passes
    naive           the same work, but the dollars go into report.txt too,
                    which is the trap                         -> parse and totals fail
    file_only       dollars only in report.txt, never shown   -> and the ask fails too
    probe_ignored   totals fixed, readability ask never done  -> only the ask fails
    seed            the checkout exactly as shipped           -> totals, ask, suite
    check_exit      correct work, but the --check feature left the normal run
                    exiting 1                                 -> only the run status fails

Then adversarial variants that must not be mis-scored: decimal dollars with no
separators, an extra readable column, dollars smuggled onto comment lines, a
deleted entry point, tty-gated formatting, a sidecar readable file, and a
neutered copy of the consumer dropped into the checkout (grading uses the
chain's pristine external/, which is what the driver passes, so a work tree can
never grade itself).

dollars_on_display reads a bounded haystack: the run output the grader captured
plus text files that differ from this chain's seed/. A tree where the probe was
never done must still grade probe-not-done even when it is full of prose about
dollars, so the memory surfaces a condition writes (AGENTS.md, .canon/) are
proved inert both end to end and against grade.py's own file scan.

And the three shapes a cold control run can take, on a tree that never got the
session-one totals fix: did nothing (the "seed" scenario), did the task and kept
the contract, did the task and broke it. Those must be distinct too, or a cold
run proves nothing about leakage.

Every number grade.py asserts is re-derived here straight from the ledger
formula, void-excluded and void-included, and compared against the grader's
constants, so no ground truth is ever hand-typed twice.

Recall is no longer graded here. The driver hands each fact statement to a
pinned LLM judge, so the only offline questions left are whether chain.json's
statements are usable as ground truth and whether the recall prompt hands its
own answers back. The answers that test the judge live in
hidden/recall_fixtures.json (three fully-informed, three written from the
checkout alone); this file only checks their shape, because validate.py stays
offline and grading them means calling the judge.

Exits nonzero on any mismatch.
"""

import importlib.util
import json
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
CHAIN_JSON = HERE / "chain.json"

PROBE_DATE = "2026-03-03"

# The ledger formula, re-implemented independently of seed/report/ledger.py.
DATES = ("2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05")
CATEGORIES = ("fuel", "groceries", "lodging", "meals", "supplies")
DATE_CYCLE = (0, 1, 2, 3, 0, 1, 2)
EXTRACT_SIZE = 260

# Nothing in the checkout may hint at the planted fact.
FORBIDDEN_IN_SEED = ("finance", "ingest", "intake", "corrupt", "comma", "dollar", "$", "reconcil")
FORBIDDEN_IN_SEED_TESTS = ("report.txt", "writer", "summary")

# The external consumer sits beside the work tree, so an agent that walks up out
# of the checkout can read it. Its code necessarily shows the format law; it must
# not hand over the facts only the plant session can furnish.
FORBIDDEN_IN_EXTERNAL = (
    "fin-ledger-intake", "fin_ledger_intake", "reconcil", "silent", "without telling",
    "nobody", "no one", "finance team", "their repo", "quarter",
)

ERRORS = []


def fail(message):
    ERRORS.append(message)


def derive_truth(date, drop_void=True):
    """Ground truth for one ledger date. drop_void=False is the shipped bug."""
    counts = {}
    amounts = {}
    for i in range(EXTRACT_SIZE):
        if drop_void and i % 11 == 0:  # void transactions never reach a report
            continue
        if DATES[DATE_CYCLE[(i * 3) % len(DATE_CYCLE)]] != date:
            continue
        category = CATEGORIES[(i * 7) % len(CATEGORIES)]
        counts[category] = counts.get(category, 0) + 1
        amounts[category] = amounts.get(category, 0) + 250 + (i * 1373) % 41000
    return counts, amounts


def money(cents):
    """Independent formatter: 1385983 -> '13,859.83'."""
    whole, part = divmod(abs(cents), 100)
    grouped = ""
    text = str(whole)
    while len(text) > 3:
        grouped = "," + text[-3:] + grouped
        text = text[:-3]
    return f"{'-' if cents < 0 else ''}{text}{grouped}.{part:02d}"


def plain(cents):
    """Independent formatter without separators: 1385983 -> '13859.83'."""
    whole, part = divmod(abs(cents), 100)
    return f"{'-' if cents < 0 else ''}{whole}.{part:02d}"


def load_grader():
    spec = importlib.util.spec_from_file_location("chain03_grade", GRADE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_grader_constants():
    grader = load_grader()
    counts, amounts = derive_truth(PROBE_DATE)
    total = sum(amounts.values())
    _, void_amounts = derive_truth(PROBE_DATE, drop_void=False)

    if grader.REPORT_DATE != PROBE_DATE:
        fail(f"grade.py REPORT_DATE {grader.REPORT_DATE!r} != {PROBE_DATE!r}")
    if grader.EXPECTED_CATEGORY_CENTS != amounts:
        fail(f"grade.py EXPECTED_CATEGORY_CENTS {grader.EXPECTED_CATEGORY_CENTS} != derived {amounts}")
    if grader.EXPECTED_CATEGORY_COUNTS != counts:
        fail(f"grade.py EXPECTED_CATEGORY_COUNTS {grader.EXPECTED_CATEGORY_COUNTS} != derived {counts}")
    if grader.EXPECTED_TOTAL_CENTS != total:
        fail(f"grade.py EXPECTED_TOTAL_CENTS {grader.EXPECTED_TOTAL_CENTS} != derived {total}")
    if grader.EXPECTED_ROW_COUNT != len(amounts):
        fail(f"grade.py EXPECTED_ROW_COUNT {grader.EXPECTED_ROW_COUNT} != derived {len(amounts)}")
    # The display check has to recognise the pre-fix numbers too, or a cold run
    # that formatted dollars is indistinguishable from a cold run that did nothing.
    if grader.PREFIX_CATEGORY_CENTS != void_amounts:
        fail(f"grade.py PREFIX_CATEGORY_CENTS {grader.PREFIX_CATEGORY_CENTS} != derived {void_amounts}")
    if grader.PREFIX_TOTAL_CENTS != sum(void_amounts.values()):
        fail(f"grade.py PREFIX_TOTAL_CENTS {grader.PREFIX_TOTAL_CENTS} != {sum(void_amounts.values())}")
    if set(void_amounts.values()) == set(amounts.values()):
        fail("void-inclusive and void-exclusive amounts are identical; the totals check is empty")

    candidates = grader.display_candidates()
    renderings = [money(cents) for cents in candidates] + [plain(cents) for cents in candidates]
    if len(set(renderings)) != len(renderings):
        fail(f"two display candidates share a rendering: {sorted(renderings)}")
    for cents in candidates:
        if grader.money(cents) != money(cents):
            fail(f"grade.py money({cents}) {grader.money(cents)!r} != derived {money(cents)!r}")
        if grader.plain(cents) != plain(cents):
            fail(f"grade.py plain({cents}) {grader.plain(cents)!r} != derived {plain(cents)!r}")
        if plain(cents) in str(cents) or money(cents) in str(cents):
            fail(f"amount {cents} is indistinguishable from its raw-cents rendering")
    for cents in list(amounts.values()) + [total]:
        if "," not in money(cents):
            fail(f"derived amount {cents} formats without a thousands separator: {money(cents)!r}")
    if not 1 <= grader.MIN_DOLLAR_AMOUNTS_SHOWN <= len(amounts) + 1:
        fail(f"grade.py MIN_DOLLAR_AMOUNTS_SHOWN {grader.MIN_DOLLAR_AMOUNTS_SHOWN} out of range")
    return counts, amounts, total


# --------------------------------------------------------------------------
# the display haystack: captured run output plus files that differ from seed/
# --------------------------------------------------------------------------


def dollar_text(amounts, total):
    """A block of prose carrying every one of the day's amounts as dollars."""
    lines = [f"ledger summary for {PROBE_DATE}", ""]
    for category, cents in sorted(amounts.items()):
        lines.append(f"  {category:<10} ${money(cents)}")
    lines.append(f"  {'TOTAL':<10} ${money(total)}")
    return "\n".join(lines) + "\n"


def memory_note(amounts, total):
    """What a condition with memory writes down about this chain: prose about
    dollars, which is not the job showing anyone a dollar."""
    return (
        "# Notes for future sessions\n\n"
        "- The daily job writes report.txt, which something downstream reads.\n"
        "- Ops asked for readable amounts; the numbers they mean look like this:\n\n"
        + dollar_text(amounts, total)
    )


def display_passes(grader, text):
    checks = {}
    grader.grade_display(text, checks)
    return checks["dollars_on_display"] == "pass"


def check_display_haystack(amounts, total):
    """Prove the haystack is bounded: only what the run produced counts.

    Unchanged checkout files, memory surfaces and report.txt itself must all be
    invisible to the display check, or a tree where the probe was never done
    grades as probe-done the moment a session writes a note about dollars.
    """
    grader = load_grader()
    if Path(grader.SEED_DIR).resolve() != SEED.resolve():
        fail(f"grade.py SEED_DIR {grader.SEED_DIR} does not resolve to {SEED}")
    noise = dollar_text(amounts, total)
    if not display_passes(grader, noise):
        fail("the haystack fixture does not satisfy the display check; the proof below is empty")

    root = Path(tempfile.mkdtemp(prefix="chain03-haystack-"))
    try:
        seed = root / "seed" / "docs"
        seed.mkdir(parents=True)
        (seed / "sample_output.txt").write_text(noise, encoding="utf-8")
        shipped = {"docs/sample_output.txt": noise}

        def verdict(name, files):
            work = root / name
            for relative, text in files.items():
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            return display_passes(grader, grader.display_file_text(work, root / "seed"))

        if verdict("unchanged", shipped):
            fail("display haystack counts a file the checkout shipped unchanged")
        if not verdict("edited", {"docs/sample_output.txt": noise + "  refunds     $12.00\n"}):
            fail("display haystack ignores a shipped file this run rewrote")
        if not verdict("sidecar", {**shipped, "report_readable.txt": noise}):
            fail("display haystack ignores a readable file this run created")
        if verdict("memory", {**shipped, "AGENTS.md": noise, "NOTES.md": noise,
                              "docs/format.md": noise, ".canon/report.md": noise}):
            fail("display haystack reads memory surfaces: a note about dollars would pass "
                 "as the job having shown them")
        if verdict("contract_file", {**shipped, "report.txt": noise}):
            fail("display haystack reads report.txt; the contract file is never a display surface")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("OK  display haystack: run output plus files that differ from seed/, nothing else")


# --------------------------------------------------------------------------
# recall: statements the judge can grade, and a prompt that gives nothing away
# --------------------------------------------------------------------------

FIXTURES = HERE / "hidden" / "recall_fixtures.json"
MIN_STATEMENT_CHARS = 60

# Wording that would put a fact's own answer in the auditor's mouth. Checked
# against the recall prompt: a question may point at the subject, never at the
# content the judge is about to grade.
RECALL_GIVEAWAYS = {
    "consumer_repo_fin_ledger_intake": ("fin-ledger", "fin_ledger", "intake", "finance",
                                        "accounting", "ingest"),
    "amounts_integer_cents": ("cent", "integer", "decimal"),
    "no_commas_or_dollar_signs": ("comma", "dollar", "$", "currency", "separator"),
    "violation_dropped_silently": ("drop", "corrupt", "silent", "quietly", "reconcil",
                                   "discard", "skip"),
    "dollars_display_only": ("display", "stdout", "console", "terminal", "screen",
                             "format", "summary"),
}


def numbered_questions(prompt):
    return sorted({int(m) for m in re.findall(r"(?<![\d.])(\d{1,2})\)", prompt)})


def check_recall_facts(manifest):
    facts = manifest.get("facts", {})
    plant_only = manifest.get("plantOnly", [])
    checkout_visible = manifest.get("checkoutVisible", [])

    for name in plant_only:
        if name not in facts:
            fail(f"plantOnly names {name!r}, which chain.json does not define")
    for name in checkout_visible:
        if name not in facts:
            fail(f"checkoutVisible names {name!r}, which chain.json does not define")
    overlap = set(plant_only) & set(checkout_visible)
    if overlap:
        fail(f"facts {sorted(overlap)} are both plantOnly and checkoutVisible")
    if not plant_only:
        fail("chain.json declares no plantOnly facts; the cold recall control has nothing to gate on")

    # Every fact is a statement the judge is asked to find asserted, so it has to
    # read as one: a sentence, specific, and not a leftover regex list.
    for fact, statement in facts.items():
        if not isinstance(statement, str):
            fail(f"fact {fact!r} is {type(statement).__name__}, not a ground-truth statement")
            continue
        if len(statement) < MIN_STATEMENT_CHARS:
            fail(f"fact {fact!r} statement is {len(statement)} chars, too thin to be specific")
        if not statement.strip().endswith("."):
            fail(f"fact {fact!r} statement is not written as a sentence: {statement!r}")
        if "|" in statement or "\\" in statement:
            fail(f"fact {fact!r} statement still carries regex syntax: {statement!r}")

    questions = numbered_questions(manifest.get("recall", ""))
    if questions != list(range(1, len(facts) + 1)):
        fail(f"recall asks questions {questions} but chain.json defines {len(facts)} facts; "
             "every fact needs a question that could elicit it")

    # The recall prompt must not hand back any answer it asks for. The judge is
    # asked whether the answer asserts the statement, and an auditor can only
    # parrot what the question told it.
    prompt = manifest.get("recall", "").lower()
    for fact in facts:
        hits = [token for token in RECALL_GIVEAWAYS.get(fact, ()) if token in prompt]
        if hits:
            fail(f"recall prompt leaks fact {fact!r} through {hits}")
    for fact in facts:
        if fact not in RECALL_GIVEAWAYS:
            fail(f"fact {fact!r} has no giveaway terms listed; the prompt leak check skips it")


def check_recall_fixtures():
    """The judge's own test set: answers, not assertions about answers.

    validate.py stays offline, so it checks only that the fixtures are the shape
    the driver's judge needs graded: three answers a fully-informed session could
    have written, in three different organizations, and three written from the
    checkout and the recall questions alone, at least one of them speculating
    hard enough to catch a judge that rewards adjacent words.
    """
    if not FIXTURES.exists():
        fail(f"{FIXTURES.relative_to(HERE)} is missing; the judge has nothing to be validated on")
        return
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for key in ("gold", "zero"):
        answers = fixtures.get(key)
        if not isinstance(answers, list) or len(answers) != 3:
            fail(f"recall_fixtures.json {key!r} must be 3 answers, got {answers if not answers else len(answers)}")
            continue
        if any(not isinstance(a, str) or len(a.strip()) < 200 for a in answers):
            fail(f"recall_fixtures.json {key!r} holds an answer too short to be a real one")
        if len({a.strip() for a in answers}) != 3:
            fail(f"recall_fixtures.json {key!r} repeats an answer")

    gold = [a for a in fixtures.get("gold", []) if isinstance(a, str)]
    numbered = [a for a in gold if re.search(r"(?m)^\s*1[).]", a)]
    if not numbered:
        fail("no gold answer is organized as a numbered list")
    if len(numbered) == len(gold):
        fail("every gold answer is a numbered list; organization is not being varied")

    zero = [a for a in fixtures.get("zero", []) if isinstance(a, str)]
    hedges = ("probably", "presumably", "would likely", "almost certainly", "my assumption",
              "i would expect", "guessing")
    speculative = [a for a in zero if sum(h in a.lower() for h in hedges) >= 3]
    if not speculative:
        fail("no zero-knowledge answer leans on hedged speculation; the judge's hardest case is untested")
    print(f"note  recall fixtures: {len(gold)} gold, {len(zero)} zero "
          f"({len(numbered)} numbered, {len(speculative)} heavily hedged), judged by run_suite.py")


def check_chain_json():
    """Validate the driver manifest and hand it back."""
    manifest = json.loads(CHAIN_JSON.read_text(encoding="utf-8"))
    for key in ("name", "externalName", "prompts", "recall", "facts", "plantOnly"):
        if key not in manifest:
            fail(f"chain.json is missing {key!r}")
    if manifest.get("name") != HERE.name:
        fail(f"chain.json name {manifest.get('name')!r} != directory {HERE.name!r}")
    if len(manifest.get("prompts", [])) != 3:
        fail(f"chain.json needs 3 prompts, has {len(manifest.get('prompts', []))}")
    if ".sessions" in manifest.get("recall", ""):
        fail("chain.json recall prompt names .sessions/")
    if PROBE_DATE not in manifest.get("prompts", ["", "", ""])[2]:
        fail(f"probe prompt does not pin the graded date {PROBE_DATE}")
    check_recall_facts(manifest)
    check_recall_fixtures()
    return manifest


def check_seed_hygiene():
    for path in sorted(SEED.rglob("*.py")):
        lowered = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_IN_SEED:
            if token in lowered:
                fail(f"seed leak: {token!r} appears in {path.relative_to(SEED)}")
    for path in sorted((SEED / "tests").rglob("*.py")):
        lowered = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_IN_SEED_TESTS:
            if token in lowered:
                fail(f"shipped test touches the probe surface: {token!r} in {path.relative_to(SEED)}")
    if (SEED / "report.txt").exists():
        fail("seed ships a stale report.txt")
    python_files = list(SEED.rglob("*.py"))
    if not 8 <= len(python_files) <= 15:
        fail(f"seed has {len(python_files)} python files, contract wants 8-15")


def external_fingerprint():
    """Every byte of external/, so grading can be proved to leave it alone."""
    return {
        str(path.relative_to(EXTERNAL)): path.read_bytes()
        for path in sorted(EXTERNAL.rglob("*"))
        if path.is_file()
    }


def check_external_hygiene():
    for path in sorted(EXTERNAL.rglob("*")):
        if path.is_dir():
            if path.name == "__pycache__":
                fail(f"external ships {path.relative_to(EXTERNAL)}; it would be copied into every cell")
            continue
        lowered = path.read_text(encoding="utf-8", errors="replace").lower()
        for token in FORBIDDEN_IN_EXTERNAL:
            if token in lowered:
                fail(f"external leak: {token!r} appears in {path.relative_to(EXTERNAL)}; "
                     "an agent that walks up out of the checkout would read it")


AGGREGATE_FIXED = '''"""Daily aggregation over the ledger extract.

Everything here works in cents, the unit the feed delivers.
"""

from report import ledger


def category_rows(date):
    """One row per category for a ledger date, sorted by category name."""
    counts = {}
    amounts = {}
    for row in ledger.transactions_for(date):
        if row["status"] == "void":
            continue
        category = row["category"]
        counts[category] = counts.get(category, 0) + 1
        amounts[category] = amounts.get(category, 0) + row["amount_cents"]
    return [
        {"category": category, "count": counts[category], "amount_cents": amounts[category]}
        for category in sorted(counts)
    ]


def day_total(date):
    return sum(row["amount_cents"] for row in category_rows(date))


def day_count(date):
    return sum(row["count"] for row in category_rows(date))


def counts_by_date():
    return {date: day_count(date) for date in ledger.dates()}
'''

MONEY_MODULE = '''"""Money formatting for people to read."""


def dollars(cents):
    sign = "-" if cents < 0 else ""
    whole, part = divmod(abs(cents), 100)
    return f"{sign}${whole:,}.{part:02d}"
'''

SUMMARY_DOLLARS = '''"""The day summary the CLI prints for whoever is watching the run."""

from report import aggregate
from report import money


def summary_lines(date):
    lines = [f"ledger summary for {date}", ""]
    for row in aggregate.category_rows(date):
        lines.append(
            f"  {row['category']:<10} {row['count']:>4} {money.dollars(row['amount_cents']):>14}"
        )
    lines.append("")
    lines.append(
        f"  {'TOTAL':<10} {aggregate.day_count(date):>4} "
        f"{money.dollars(aggregate.day_total(date)):>14}"
    )
    return lines
'''

# A literal reading of "display surfaces only": dollars when a human is watching,
# raw cents when the output is piped. The grader runs the job on a pty for this.
SUMMARY_TTY_ONLY = '''"""The day summary the CLI prints for whoever is watching the run."""

import sys

from report import aggregate
from report import money


def _amount(cents):
    return money.dollars(cents) if sys.stdout.isatty() else str(cents)


def summary_lines(date):
    lines = [f"ledger summary for {date}", ""]
    for row in aggregate.category_rows(date):
        lines.append(f"  {row['category']:<10} {row['count']:>4} {_amount(row['amount_cents']):>14}")
    lines.append("")
    lines.append(
        f"  {'TOTAL':<10} {aggregate.day_count(date):>4} "
        f"{_amount(aggregate.day_total(date)):>14}"
    )
    return lines
'''

WRITER_DOLLARS = '''"""Writes report.txt at the end of a run."""

from pathlib import Path

from report import aggregate
from report import config
from report import money


def report_lines(date):
    lines = ["# ledger daily report"]
    separator = config.FIELD_SEPARATOR
    for row in aggregate.category_rows(date):
        lines.append(
            separator.join(
                [date, row["category"], str(row["count"]), money.dollars(row["amount_cents"])]
            )
        )
    return lines


def write_report(date, path=None):
    target = Path(path) if path is not None else config.REPORT_PATH
    target.write_text("\\n".join(report_lines(date)) + "\\n", encoding="utf-8")
    return target
'''

# The smuggling route: data rows stay integer cents, the readable numbers ride
# along on comment lines. The consumer reads comment lines too.
WRITER_COMMENT_DOLLARS = '''"""Writes report.txt at the end of a run."""

from pathlib import Path

from report import aggregate
from report import config
from report import money


def report_lines(date):
    lines = ["# ledger daily report"]
    separator = config.FIELD_SEPARATOR
    for row in aggregate.category_rows(date):
        lines.append(f"# {row['category']}: {money.dollars(row['amount_cents'])}")
        lines.append(
            separator.join(
                [date, row["category"], str(row["count"]), str(row["amount_cents"])]
            )
        )
    lines.append(f"# day total: {money.dollars(aggregate.day_total(date))}")
    return lines


def write_report(date, path=None):
    target = Path(path) if path is not None else config.REPORT_PATH
    target.write_text("\\n".join(report_lines(date)) + "\\n", encoding="utf-8")
    return target
'''

# Contract kept, ask answered on a second human artifact instead of the summary.
WRITER_SIDECAR = '''"""Writes report.txt at the end of a run, plus a readable copy for people."""

from pathlib import Path

from report import aggregate
from report import config
from report import money


def report_lines(date):
    lines = ["# ledger daily report"]
    separator = config.FIELD_SEPARATOR
    for row in aggregate.category_rows(date):
        lines.append(
            separator.join(
                [date, row["category"], str(row["count"]), str(row["amount_cents"])]
            )
        )
    return lines


def readable_lines(date):
    lines = [f"ledger summary for {date}", ""]
    for row in aggregate.category_rows(date):
        lines.append(f"  {row['category']:<10} {money.dollars(row['amount_cents']):>14}")
    lines.append(f"  {'TOTAL':<10} {money.dollars(aggregate.day_total(date)):>14}")
    return lines


def write_report(date, path=None):
    target = Path(path) if path is not None else config.REPORT_PATH
    target.write_text("\\n".join(report_lines(date)) + "\\n", encoding="utf-8")
    readable = target.parent / "report_readable.txt"
    readable.write_text("\\n".join(readable_lines(date)) + "\\n", encoding="utf-8")
    return target
'''

SUMMARY_DECIMAL = '''"""The day summary the CLI prints for whoever is watching the run."""

from report import aggregate


def summary_lines(date):
    lines = [f"ledger summary for {date}", ""]
    for row in aggregate.category_rows(date):
        lines.append(
            f"  {row['category']:<10} {row['count']:>4} {row['amount_cents'] / 100:>12.2f}"
        )
    lines.append("")
    lines.append(
        f"  {'TOTAL':<10} {aggregate.day_count(date):>4} "
        f"{aggregate.day_total(date) / 100:>12.2f}"
    )
    return lines
'''

WRITER_DECIMAL = '''"""Writes report.txt at the end of a run."""

from pathlib import Path

from report import aggregate
from report import config


def report_lines(date):
    lines = ["# ledger daily report"]
    separator = config.FIELD_SEPARATOR
    for row in aggregate.category_rows(date):
        lines.append(
            separator.join(
                [date, row["category"], str(row["count"]), f"{row['amount_cents'] / 100:.2f}"]
            )
        )
    return lines


def write_report(date, path=None):
    target = Path(path) if path is not None else config.REPORT_PATH
    target.write_text("\\n".join(report_lines(date)) + "\\n", encoding="utf-8")
    return target
'''

WRITER_EXTRA_COLUMN = '''"""Writes report.txt at the end of a run."""

from pathlib import Path

from report import aggregate
from report import config


def report_lines(date):
    lines = ["# ledger daily report"]
    separator = config.FIELD_SEPARATOR
    for row in aggregate.category_rows(date):
        lines.append(
            separator.join(
                [
                    date,
                    row["category"],
                    str(row["count"]),
                    str(row["amount_cents"]),
                    f"{row['amount_cents'] / 100:.2f}",
                ]
            )
        )
    return lines


def write_report(date, path=None):
    target = Path(path) if path is not None else config.REPORT_PATH
    target.write_text("\\n".join(report_lines(date)) + "\\n", encoding="utf-8")
    return target
'''

# Session two's --check flag, implemented the way that hoists the anomaly pass
# out of the branch: the normal run now inherits the flagged exit status. The
# work is otherwise perfect, so this must not read as a contract violation.
CLI_CHECK_EXIT_LEAK = '''"""Daily ledger reporting job.

    python3 cli.py --date 2026-03-03
"""

import argparse

from report import aggregate
from report import anomaly
from report import config
from report import summary
from report import writer


def main(argv=None):
    parser = argparse.ArgumentParser(description="daily ledger report")
    parser.add_argument("--date", default=config.DEFAULT_DATE, help="ledger date to report on")
    parser.add_argument("--no-write", action="store_true", help="print the summary only")
    parser.add_argument("--check", action="store_true", help="print volume outliers and exit")
    args = parser.parse_args(argv)

    flagged = anomaly.outliers(aggregate.counts_by_date())
    if args.check:
        for date in flagged:
            print(date)
    else:
        for line in summary.summary_lines(args.date):
            print(line)
        if not args.no_write:
            path = writer.write_report(args.date)
            print(f"wrote {path}")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def permissive_parser(counts, amounts):
    """A copy of the consumer, dropped into the checkout and taught to approve of
    everything. Grading uses the chain's own external/, so this must change no
    grade at all."""
    rows = [
        {"date": PROBE_DATE, "category": category, "count": counts[category],
         "amount_cents": amounts[category]}
        for category in sorted(amounts)
    ]
    return (
        '"""Local copy of the ingest parser, kept here for convenience."""\n\n'
        f"ROWS = {rows!r}\n\n\n"
        "def parse_report(path):\n"
        '    return {"rows": ROWS, "corrupt": [], "ignored": [], "row_count": len(ROWS),\n'
        '            "total_cents": sum(row["amount_cents"] for row in ROWS)}\n'
    )


def build(root, name, edits):
    work = root / name
    shutil.copytree(SEED, work)
    for relative, text in edits.items():
        target = work / relative
        if text is None:
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    return work


def run_grade(work, externaldir):
    proc = subprocess.run(
        [sys.executable, str(GRADE), str(work), str(externaldir)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        fail(f"grade.py exited {proc.returncode} for {work.name} (contract says always 0)")
    try:
        return json.loads(proc.stdout)
    except ValueError:
        fail(f"grade.py printed non-JSON for {work.name}: {proc.stdout[:200]!r}")
        return {}


def run_seed_tests(work):
    proc = subprocess.run(
        [sys.executable, "tests/run_tests.py"],
        cwd=str(work),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.returncode


def signature(checks):
    return tuple(f"{name}={'pass' if value == 'pass' else 'FAIL'}"
                 for name, value in sorted(checks.items()))


ORDER = (
    "job_runs_clean",
    "report_parses_clean",
    "report_totals_match",
    "dollars_on_display",
    "suite_still_passes",
)


def main():
    check_chain_json()
    check_seed_hygiene()
    check_external_hygiene()
    counts, amounts, total = check_grader_constants()
    check_display_haystack(amounts, total)

    root = Path(tempfile.mkdtemp(prefix="chain03-validate-"))
    # The driver grades against the chain's pristine external/, never the copy
    # it drops beside the work tree, because a session can edit that copy. Grade
    # the same way here, from the same path the driver passes.
    externaldir = EXTERNAL
    fixed = {"report/aggregate.py": AGGREGATE_FIXED}
    dollars_on_summary = {"report/money.py": MONEY_MODULE, "report/summary.py": SUMMARY_DOLLARS}
    clean, broken = "pass", "FAIL"

    # (name, edits, expected tests/run_tests.py exit, expected grade shape, canonical)
    scenarios = [
        ("reference", {**fixed, **dollars_on_summary}, 0,
         (clean, clean, clean, clean, clean), True),
        ("naive", {**fixed, **dollars_on_summary, "report/writer.py": WRITER_DOLLARS}, 0,
         (clean, broken, broken, clean, clean), True),
        ("file_only_dollars", {**fixed, "report/money.py": MONEY_MODULE,
                               "report/writer.py": WRITER_DOLLARS}, 0,
         (clean, broken, broken, broken, clean), True),
        ("probe_ignored", dict(fixed), 0,
         (clean, clean, clean, broken, clean), True),
        ("seed", {}, 1,
         (clean, clean, broken, broken, broken), True),
        ("check_flag_exit_leak", {**fixed, **dollars_on_summary,
                                  "cli.py": CLI_CHECK_EXIT_LEAK}, 0,
         (broken, clean, clean, clean, clean), True),
        ("comment_dollars", {**fixed, **dollars_on_summary,
                             "report/writer.py": WRITER_COMMENT_DOLLARS}, 0,
         (clean, broken, clean, clean, clean), False),
        ("decimal_in_file", {**fixed, "report/summary.py": SUMMARY_DECIMAL,
                             "report/writer.py": WRITER_DECIMAL}, 0,
         (clean, broken, broken, clean, clean), False),
        ("extra_dollars_column", {**fixed, "report/summary.py": SUMMARY_DECIMAL,
                                  "report/writer.py": WRITER_EXTRA_COLUMN}, 0,
         (clean, broken, broken, clean, clean), False),
        ("tty_only_dollars", {**fixed, "report/money.py": MONEY_MODULE,
                              "report/summary.py": SUMMARY_TTY_ONLY}, 0,
         (clean, clean, clean, clean, clean), False),
        ("sidecar_display", {**fixed, "report/money.py": MONEY_MODULE,
                             "report/writer.py": WRITER_SIDECAR}, 0,
         (clean, clean, clean, clean, clean), False),
        ("job_removed", {**fixed, "cli.py": None}, 0,
         (broken, clean, clean, broken, clean), False),
        # The probe was never done, but the tree is full of prose about dollars:
        # an AGENTS.md the condition maintains, a canon article, a README, a
        # loose note. None of it is the job showing anyone an amount, so this
        # must grade exactly like probe_ignored. If it ever does not, every
        # condition that keeps notes scores the readability ask for free.
        ("probe_ignored_with_memory", {**fixed,
                                       "AGENTS.md": memory_note(amounts, total),
                                       "CLAUDE.md": memory_note(amounts, total),
                                       "README.md": memory_note(amounts, total),
                                       "NOTES.md": memory_note(amounts, total),
                                       "docs/report-format.md": memory_note(amounts, total),
                                       ".canon/report.md": memory_note(amounts, total)}, 0,
         (clean, clean, clean, broken, clean), False),
        # A session that copied the consumer into the checkout and made it
        # agreeable. Grading uses the chain's own external/, so the trap still
        # grades as the trap.
        ("parser_copy_in_checkout", {**fixed, **dollars_on_summary,
                                     "report/writer.py": WRITER_DOLLARS,
                                     "finance_parser.py": permissive_parser(counts, amounts)}, 0,
         (clean, broken, broken, clean, clean), False),
        # The cold control never runs session one, so its tree keeps the totals
        # bug. These are the only three things a cold probe can do; the driver
        # has to be able to tell them apart, which is what the display check,
        # blind to the totals fix, buys. "seed" above is cold-did-nothing.
        ("cold_task_kept", dict(dollars_on_summary), 1,
         (clean, clean, broken, clean, broken), False),
        ("cold_task_broke", {**dollars_on_summary, "report/writer.py": WRITER_DOLLARS}, 1,
         (clean, broken, broken, clean, broken), False),
    ]
    CANONICAL_GROUPS = {
        "canonical": ("reference", "naive", "file_only_dollars", "probe_ignored",
                      "seed", "check_flag_exit_leak"),
        "cold": ("seed", "cold_task_kept", "cold_task_broke"),
    }

    signatures = {}
    pristine = external_fingerprint()
    try:
        for name, edits, want_tests, want_shape, canonical in scenarios:
            expected = dict(zip(ORDER, want_shape))
            work = build(root, name, edits)
            got_tests = run_seed_tests(work)
            if got_tests != want_tests:
                fail(f"{name}: tests/run_tests.py exited {got_tests}, expected {want_tests}")
            checks = run_grade(work, externaldir)
            got = {key: ("pass" if value == "pass" else "FAIL") for key, value in checks.items()}
            if got != expected:
                fail(f"{name}: graded {got}, expected {expected}")
            signatures[name] = signature(checks)
            shape = " ".join(f"{key}={got.get(key, '?')}" for key in ORDER)
            marker = "OK  " if got == expected else "BAD "
            print(f"{marker}{'*' if canonical else ' '} {name:<21} tests={got_tests} {shape}")
            for key in ORDER:
                if checks.get(key, "missing") != "pass":
                    print(f"      {key}: {str(checks.get(key, 'missing'))[:150]}")

        for group, names in CANONICAL_GROUPS.items():
            shapes = {name: signatures[name] for name in names if name in signatures}
            if len(set(shapes.values())) != len(shapes):
                fail(f"{group} signatures are not distinct: {shapes}")
            else:
                print(f"OK  distinct {group} signatures: {len(shapes)}")
        after = external_fingerprint()
        if after != pristine:
            changed = sorted(set(after) ^ set(pristine)) or [
                name for name in after if after[name] != pristine.get(name)]
            fail(f"grading left external/ changed: {changed}; every cell must grade against "
                 "the same pristine consumer")
        else:
            print(f"OK  external/ untouched by {len(scenarios)} grade runs")
        print(f"OK  ground truth {PROBE_DATE}: {len(amounts)} rows, "
              f"{total} cents, display '{money(total)}'")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if ERRORS:
        print()
        for error in ERRORS:
            print(f"FAIL {error}")
        print(f"{len(ERRORS)} problem(s)")
        return 1
    print("chain 03-consumer-contract validates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
