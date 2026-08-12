#!/usr/bin/env python3
"""canon-bench suite driver: run one chain through conditions x reps, or a cold control.

Chains follow the contract in chains/SPEC.md (chain.json, seed/, external/, hidden/grade.py).
Per chain x rep x condition: seed the worktree, run the work sessions, grade a post-probe
snapshot with the chain's own grader, hand the condition its transcripts at .sessions/, run
the recall session, grade recall facts, record the full usage ledger.

Layout rules that exist because agents hunt when paths break: the external package is copied
INTO each cell as a sibling of the work tree, so ../<externalName> in prompts always resolves;
and runs live OUTSIDE the pi-canon checkout so no filesystem search from a work tree can reach
chains/ (where prompts, graders, and reference solutions live).

Cold mode is the empirical leakage control, two halves on fresh seeds under bare:
probe-cold (can the trap be beaten without the plant?) and recall-cold (do the recall
questions leak their own answers?). Facts listed in chain.json plantOnly must come back false
in recall-cold or the chain leaks.

  run_suite.py --chain 01-vendor-feed [--reps 2] [--conditions canon,bare,agentsmd] [--tag study]
  run_suite.py --chain 01-vendor-feed --cold [--tag cold]
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
RUNS_ROOT = Path.home() / "canon-bench-runs"
SUFFIX_C = " Keep AGENTS.md up to date with anything future sessions must know."
TRANSCRIPT_DROP = {"message_update", "tool_execution_update"}

# canondoc: pi-canon plus a static AGENTS.md carrying the doctrine, testing whether
# prompting the configuration moves the read-before/write-after loop.
DOCTRINE = """# Agent instructions

This project uses pi_canon as canonical memory. Before working on any asset, read its
governing article (pi_canon read). After any real change, update the article and journal
the event. Articles hold current truth; specifics beat summaries: record who consumes
what, exact limits, and what breaks, not just the rule.
"""
# agentsmd: preloaded with realistic mature-project noise so planted facts compete for
# attention the way they would in a real AGENTS.md.
PRELOAD = BENCH / "assets" / "agents-preload.md"


def events(path: Path):
    for line in path.read_text().splitlines():
        try:
            yield json.loads(line)
        except ValueError:
            continue


def final_answer(session: Path) -> str:
    answer = ""
    for event in events(session):
        message = event.get("message") or {}
        if event.get("type") == "turn_end" and message.get("role") == "assistant":
            texts = [c.get("text", "") for c in message.get("content") or []
                     if isinstance(c, dict) and c.get("type") == "text"]
            if texts:
                answer = "\n".join(texts)
    return answer


def usage_of(out: Path) -> dict:
    metrics = json.loads((out / "metrics.json").read_text())
    u = metrics["usage"]
    return {
        "tokens": sum(u[k] for k in ("input", "output", "cacheRead", "cacheWrite", "reasoning")),
        "output": u["output"] + u["reasoning"],
        "cost": round(u["cost"], 5),
        "wallSeconds": metrics["wallSeconds"],
        "toolCalls": metrics["toolCalls"],
    }


# Worker model for the sessions under test; the judge stays pinned in judge() regardless,
# so grading is identical across spot-check models. Post-freeze amendment, disclosed in
# PLAN.md: the headline run used the frozen driver with these exact defaults.
WORKER = {"model": "gpt-5.6-luna", "provider": "openai-codex"}


class CellFailed(Exception):
    """One cell could not be run to completion. Isolated so the remaining cells still
    run: a single hung worker session used to take the whole matrix down with it, and
    the report only reached disk at the very end, so every finished cell was lost too."""


def run_session(condition: str, work: Path, out: Path, prompt: str) -> None:
    done = subprocess.run(
        [sys.executable, str(BENCH / "run_session.py"), "--condition", condition,
         "--workdir", str(work), "--out", str(out), "--prompt", prompt,
         "--model", WORKER["model"], "--provider", WORKER["provider"]],
        check=False,
    )
    if done.returncode != 0 or not (out / "metrics.json").exists():
        raise CellFailed(f"{condition} session {out.name} exited {done.returncode}")


JUDGE_PROMPT = """You are grading one answer from a memory benchmark. The fact under grade:

{statement}

The answer being graded:
---
{answer}
---

Does the answer ASSERT this fact as known and true? Hedged speculation ("probably", "a strict
loader would likely..."), enumerating possibilities, or generic reasoning that merely brushes
related words do NOT count; the answer must commit to the fact. Contradicting the fact, or
saying it is not recorded, is no. Reply with exactly one word: yes or no."""


def judge(statement: str, answer: str) -> tuple[bool, str]:
    """One pinned Luna call per fact. Deterministic outcome grading stays primary; the
    judge exists because regex fact-matching provably misgrades paraphrase and hedging."""
    proc = subprocess.run(
        ["pi", "-p", "--mode", "json", "--provider", "openai-codex", "--model", "gpt-5.6-luna",
         "--thinking", "low", "--no-extensions", "--no-skills", "--no-prompt-templates",
         "--no-context-files", "--no-session", JUDGE_PROMPT.format(statement=statement, answer=answer)],
        capture_output=True, text=True, timeout=180,
    )
    verdict = ""
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message") or {}
        if event.get("type") == "turn_end" and message.get("role") == "assistant":
            texts = [c.get("text", "") for c in message.get("content") or []
                     if isinstance(c, dict) and c.get("type") == "text"]
            if texts:
                verdict = "\n".join(texts)
    return verdict.strip().lower().startswith("yes"), verdict.strip()


class Chain:
    def __init__(self, chain_id: str):
        self.dir = BENCH / "chains" / chain_id
        manifest = json.loads((self.dir / "chain.json").read_text())
        self.name = manifest["name"]
        self.external_name = manifest["externalName"]
        self.prompts = manifest["prompts"]
        self.recall = manifest["recall"]
        self.facts = manifest["facts"]
        self.plant_only = manifest.get("plantOnly", [])

    def seed_cell(self, cell: Path) -> Path:
        work = cell / "work"
        shutil.copytree(self.dir / "seed", work)
        shutil.copytree(self.dir / "external", cell / self.external_name)
        return work

    def grade(self, work: Path) -> dict:
        """Always grades against the chain's PRISTINE external, never the cell copy:
        a session told the external is broken may try to fix it in place."""
        try:
            out = subprocess.run(
                [sys.executable, str(self.dir / "hidden" / "grade.py"), str(work),
                 str(self.dir / "external")],
                capture_output=True, text=True, timeout=900,
            )
            return json.loads(out.stdout)
        except subprocess.TimeoutExpired:
            return {"grader": "FAIL: grade.py timed out"}
        except ValueError:
            return {"grader": f"FAIL: no JSON ({(out.stderr or out.stdout).strip()[:200]})"}

    def grade_recall(self, answer: str, archive: Path) -> dict:
        """One judge call per fact over the whole answer, so organization cannot move the
        score. Judge transcripts land beside the answer for audit."""
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {fact: pool.submit(judge, statement, answer)
                       for fact, statement in self.facts.items()}
        results = {fact: future.result() for fact, future in futures.items()}
        archive.write_text(json.dumps(
            {fact: {"verdict": v, "raw": raw} for fact, (v, raw) in results.items()}, indent=1) + "\n")
        return {fact: v for fact, (v, _) in results.items()}


def run_cell(chain: Chain, base: Path, condition: str, rep: int,
             hand_transcripts: bool = True) -> dict:
    cell = base / f"rep{rep}" / condition
    work = chain.seed_cell(cell)
    if condition == "canondoc":
        (work / "AGENTS.md").write_text(DOCTRINE)
    elif condition == "agentsmd":
        (work / "AGENTS.md").write_text(PRELOAD.read_text())

    sessions = {}
    for index, prompt in enumerate(chain.prompts, 1):
        out = cell / f"s{index}"
        run_session(condition, work, out, prompt + (SUFFIX_C if condition == "agentsmd" else ""))
        sessions[f"s{index}"] = usage_of(out)

    graded = cell / "work-graded"
    shutil.copytree(work, graded)
    outcome = chain.grade(graded)

    # Archived beside the cell always. ALSO placing them in the work tree hands them to
    # the recall session, which is the frozen design ("hand the condition its
    # transcripts"), and it is load bearing on how recall reads: s1 contains the plant
    # prompt verbatim, so a recall session that opens the dump answers every fact with no
    # memory at all. xcut2 caught a bare cell doing exactly that, 4/4 with an empty store,
    # while its sibling rep read less and scored 0/4. Default keeps the frozen behaviour so
    # numbers stay comparable; --no-hand-transcripts measures recall without the crutch.
    transcripts = cell / "transcripts"
    transcripts.mkdir()
    for index in range(1, len(chain.prompts) + 1):
        kept = [json.dumps(e) for e in events(cell / f"s{index}" / "session.jsonl")
                if e.get("type") not in TRANSCRIPT_DROP]
        (transcripts / f"s{index}.jsonl").write_text("\n".join(kept) + "\n")

    if hand_transcripts:
        shutil.copytree(transcripts, work / ".sessions")

    recall_out = cell / "recall"
    run_session(condition, work, recall_out, chain.recall)
    answer = final_answer(recall_out / "session.jsonl")
    (recall_out / "answer.md").write_text(answer + "\n")
    sessions["recall"] = usage_of(recall_out)

    return {"outcome": outcome, "recall": chain.grade_recall(answer, recall_out / "judge.json"),
            "sessions": sessions}


def run_cold(chain: Chain, base: Path) -> dict:
    probe_work = chain.seed_cell(base / "cold-probe")
    run_session("bare", probe_work, base / "cold-probe" / "session", chain.prompts[-1])

    recall_work = chain.seed_cell(base / "cold-recall")
    run_session("bare", recall_work, base / "cold-recall" / "session", chain.recall)
    answer = final_answer(base / "cold-recall" / "session" / "session.jsonl")
    (base / "cold-recall" / "answer.md").write_text(answer + "\n")
    facts = chain.grade_recall(answer, base / "cold-recall" / "judge.json")

    return {
        "outcome": chain.grade(probe_work),
        "probe": usage_of(base / "cold-probe" / "session"),
        "recallFacts": facts,
        "leaks": [f for f in chain.plant_only if facts.get(f)],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--conditions", default="canon,canondoc,bare,agentsmd")
    # canonret is not in the default set: it is the 2.0 arm and belongs to the
    # cross-cutting chains, so pass it explicitly rather than paying for it on
    # every asset-scoped run where it can only tie.
    ap.add_argument("--tag", default="study")
    ap.add_argument("--runs-root", default=str(RUNS_ROOT))
    ap.add_argument("--no-hand-transcripts", action="store_true",
                    help="do not place the session transcripts in the work tree before "
                         "recall; recall then measures the store rather than the dump")
    ap.add_argument("--cold", action="store_true", help="probe-cold + recall-cold leakage controls")
    ap.add_argument("--model", default=WORKER["model"])
    ap.add_argument("--provider", default=WORKER["provider"])
    args = ap.parse_args()
    WORKER.update(model=args.model, provider=args.provider)

    chain = Chain(args.chain)
    base = Path(args.runs_root) / args.tag / chain.name
    if base.exists():
        base.rename(base.with_name(f"{chain.name}-{time.strftime('%Y%m%d-%H%M%S')}"))
    base.mkdir(parents=True)

    if args.cold:
        report = {"cold": run_cold(chain, base)}
    else:
        report = {}
        for rep in range(1, args.reps + 1):
            for condition in args.conditions.split(","):
                key = f"rep{rep}/{condition}"
                try:
                    report[key] = run_cell(chain, base, condition, rep,
                                       hand_transcripts=not args.no_hand_transcripts)
                except CellFailed as exc:
                    report[key] = {"cell": f"FAILED: {exc}"}
                    print(f"!! {key} failed: {exc}", flush=True)
                # checkpoint after every cell: a crash later must not cost the cells
                # already paid for.
                (base / "grades.json").write_text(json.dumps(report, indent=1) + "\n")

    (base / "grades.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
