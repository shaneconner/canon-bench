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

# canonret: the same package, registered with retrieval enabled.
#
# Turning retrieval on varies two things at once, and the study has to be read knowing
# that. It gives the run a ranker over articles governing no asset, AND it flips the
# tool's filing rule from "knowledge filed off the asset path never surfaces" to "a
# constraint governing many assets and owning none belongs at its own address". They are
# coupled deliberately: a ranker with nothing to find is not a mechanism, and inviting
# off-path filing with no ranker is advice to lose information. This arm measures the
# pair, not the ranker alone.
#
# The shim is generated per session with an ABSOLUTE import rather than committed with a
# relative one, so the bench runs the same from the working copy inside pi-canon and from
# a standalone clone, where a fixed ../.. would resolve somewhere else entirely.
RETRIEVAL_SHIM = """import {{ registerPiCanon }} from "{canon}";

export default function piCanonRetrieval(pi) {{
  return registerPiCanon(pi, {{ retrieval: "lexical" }});
}}
"""


# sham: the pi-canon TOOL SURFACE with no memory behind it.
#
# e2e3 measured canon's first code pass at 5/15 against bare's 15/15, and in every failing
# cell the bad edit landed before any pi_canon call. So whatever degraded it was already in
# the window: the tool schema and the session orientation, not anything memory did. This arm
# is the control that separates those. It registers a tool byte-identical to the real one,
# built through buildCanonTool so the description and parameters cannot drift, and delivers
# the same orientation line. Nothing persists, nothing surfaces, nothing nudges.
#
# Reading it: sham near canon means the cost is the surface, and no change to how memory
# works can recover it. sham near bare means the cost is in the memory work itself, which is
# the half a doctrine or a nudge could still fix.
SHAM_SHIM = """import {{ buildCanonTool }} from "{lib}/tool.ts";
import {{ CanonStore }} from "{lib}/store.ts";
import {{ Surfacer }} from "{lib}/surfacing.ts";
import {{ mkdtempSync }} from "node:fs";
import {{ tmpdir }} from "node:os";
import {{ join }} from "node:path";

const ORIENTATION =
  "[pi-canon] No articles yet in .canon/. When work teaches you something durable about an " +
  "asset, write its article with pi_canon and journal the source as it happened: names, " +
  "exact numbers, who said what. Articles distill; the journal keeps the original.";

export default function shamCanon(pi) {{
  /* Outside the work tree on purpose: the schema is the treatment under test, and a store
     the probe could later read would make this the full package again. */
  const store = new CanonStore(mkdtempSync(join(tmpdir(), "sham-canon-")));
  const real = buildCanonTool((ctx) => {{
    const cwd = (ctx && ctx.cwd) || process.cwd();
    const mounts = [{{ name: "", dir: cwd, store }}];
    return {{ store, surfacer: new Surfacer(mounts), cwd, mounts, retrieval: "none" }};
  }}, "none");
  pi.registerTool({{
    name: real.name,
    label: real.label,
    description: real.description,
    parameters: real.parameters,
    async execute(_id, params) {{
      const action = String((params && params.action) || "");
      const text = action === "read"
        ? "No article governs that path yet."
        : action === "map"
          ? "No articles yet."
          : "Recorded.";
      return {{ content: [{{ type: "text", text }}], details: {{}} }};
    }},
  }});
  pi.on("session_start", () => {{
    try {{
      pi.sendMessage(
        {{ customType: "pi-canon", content: ORIENTATION, display: false }},
        {{ deliverAs: "nextTurn" }},
      );
    }} catch {{}}
  }});
}}
"""


def sham_shim(out: Path) -> Path:
    lib = (PI_CANON.parent / "lib").resolve()
    if not lib.exists():
        raise SystemExit(f"sham needs {lib}, which does not exist")
    path = out / "canon-sham.mjs"
    path.write_text(SHAM_SHIM.format(lib=lib))
    return path


def retrieval_shim(out: Path) -> Path:
    canon = (PI_CANON.parent / "canon.ts").resolve()
    if not canon.exists():
        raise SystemExit(f"canonret needs {canon}, which does not exist")
    path = out / "canon-retrieval.mjs"
    path.write_text(RETRIEVAL_SHIM.format(canon=canon))
    return path


def snapshot(canon_dir: Path, dest: Path) -> None:
    if canon_dir.exists():
        with tarfile.open(dest, "w") as tar:
            tar.add(canon_dir, arcname=".canon")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=["canon", "canondoc", "canonret", "sham", "bare", "agentsmd"], required=True)
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
    if args.condition == "canonret":
        cmd += ["-e", str(retrieval_shim(out))]
    elif args.condition == "sham":
        cmd += ["-e", str(sham_shim(out))]
    elif args.condition in ("canon", "canondoc"):
        cmd += ["-e", str(PI_CANON)]
    cmd.append(args.prompt)

    env = dict(os.environ)
    if args.condition in ("canon", "canondoc", "canonret"):
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
