#!/usr/bin/env python3
"""Run one benchmark session: bare pi, optional pi-canon, capture everything.

Conditions: canon (stock pi + pi-canon only), bare (nothing persists),
agentsmd (a self-maintained AGENTS.md is the memory).
Outputs per session: session.jsonl (full event stream), canon-before/after.tar,
metrics.json (tokens split by cache, cost, wall time, turns, tool calls,
pi-canon messages), stderr.log when nonempty.
"""

import argparse
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

PI_CANON = Path(__file__).resolve().parents[2] / "extensions/index.js"


def snapshot(canon_dir: Path, dest: Path) -> None:
    if canon_dir.exists():
        with tarfile.open(dest, "w") as tar:
            tar.add(canon_dir, arcname=".canon")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=["canon", "canondoc", "bare", "agentsmd"], required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--model", default="gpt-5.6-luna")
    ap.add_argument("--provider", default="openai-codex")
    ap.add_argument("--thinking", default="low")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    work = Path(args.workdir).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    canon_dir = work / ".canon"
    snapshot(canon_dir, out / "canon-before.tar")

    cmd = [
        "pi", "-p", "--mode", "json",
        "--provider", args.provider, "--model", args.model,
        "--thinking", args.thinking,
        "--no-extensions", "--no-skills", "--no-prompt-templates", "--no-session",
    ]
    if args.condition not in ("agentsmd", "canondoc"):
        cmd.append("--no-context-files")
    if args.condition in ("canon", "canondoc"):
        cmd += ["-e", str(PI_CANON)]
    cmd.append(args.prompt)

    env = dict(os.environ)
    if args.condition in ("canon", "canondoc"):
        env["PI_CANON_TRACE"] = str(out / "canon-trace.jsonl")

    start = time.time()
    proc = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=1800)
    wall = time.time() - start

    (out / "session.jsonl").write_text(proc.stdout)
    if proc.stderr:
        (out / "stderr.log").write_text(proc.stderr)
    snapshot(canon_dir, out / "canon-after.tar")

    usage = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "reasoning": 0, "cost": 0.0}
    turns = 0
    tool_calls = 0
    canon_messages = 0
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "turn_end":
            turns += 1
            u = event.get("message", {}).get("usage") or {}
            for key in ("input", "output", "cacheRead", "cacheWrite", "reasoning"):
                usage[key] += u.get(key) or 0
            usage["cost"] += (u.get("cost") or {}).get("total") or 0
            tool_calls += len(event.get("toolResults") or [])
        elif kind == "message_start" and event.get("message", {}).get("customType") == "pi-canon":
            canon_messages += 1

    metrics = {
        "condition": args.condition,
        "model": args.model,
        "thinking": args.thinking,
        "wallSeconds": round(wall, 1),
        "turns": turns,
        "toolCalls": tool_calls,
        "canonMessages": canon_messages,
        "canonTextSeen": "[pi-canon]" in proc.stdout,
        "usage": usage,
        "exit": proc.returncode,
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1) + "\n")
    print(json.dumps(metrics, indent=1))


main()
