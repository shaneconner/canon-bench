"""Build the W4C fixture, the 160-assignment counterbalanced instrument, and its
validate-only contract.

W4C exists because W4 and W4R cannot identify their own effect. In both of those
captures the instrument builder iterated the arms as ("A", "G") for every lineage,
so within each lineage the untreated arm always ran before the treated one.
Condition was therefore perfectly confounded with execution order, and running a
second model repeated the contrast without breaking the confound. W4C reverses the
order in half the lineages so the two can be separated.

Everything else is held: the same eight K=8 lineages from w4_lineage, the same
prompts and submit tools from w3_contract, the same two arm tools under arms/, and
the same grading path. The ONLY difference from W4 is the per-lineage arm order.

Order assignment is deterministic and declared here rather than sampled, because a
fixed instrument with a declared schedule is auditable and a seeded shuffle of eight
items is not meaningfully more random. Lineages are taken in the sorted order
w4_lineage emits; even indices run A before G, odd indices run G before A. That
gives four lineages each way, and it is recorded in the instrument as
`arm_order_by_lineage` so a reader never has to infer it.

Provenance differs from W4 in one deliberate way. W4's builder asserted the repo
HEAD equalled e1312e6. That assertion is not reused, because HEAD has since moved
and, more importantly, because a commit label is weaker evidence than the bytes: W4
itself pinned schema.ts and tool.ts at their pre-b6dc366 state and then had both
change underneath it partway through the run. W4C asserts the seven package files
against explicit hashes recorded below, records the actual HEAD for the record, and
relies on the capture harness's launch snapshot so nothing can move mid-run.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "w3"))
sys.path.insert(0, str(HERE.parents[1] / "bench"))

import sandbox  # noqa: E402

import w3_contract as cm  # noqa: E402
import w4_lineage as lineage  # noqa: E402

REPO = Path("/home/shane/pi-canon")
PACKAGE_FILES = (
    "extensions/canon.ts",
    "extensions/lib/lint.ts",
    "extensions/lib/retrieval.ts",
    "extensions/lib/schema.ts",
    "extensions/lib/store.ts",
    "extensions/lib/surfacing.ts",
    "extensions/lib/tool.ts",
)
W4C_SOURCES = (
    "w4_lineage.py", "w4c_build_instrument.py", "w4_model_capture.py",
    "w4_build_injections.py", "w4_grade_capture.py",
    "w4_writer_canon.mjs", "w4_reader_ab.mjs", "w4_submit_lib.mjs",
    "w4_fake_session.mjs", "arms/tool-A.ts", "arms/tool-G.ts",
)
EXTERNAL_SOURCES = (
    "../w3/w3_lineage.py",
    "../w3/w3_contract.py",
    "../w2/w2_model_capture.py",
    "../w1i_lean/w1i_model_capture.py",
)
VALIDATION_MODULE = (
    Path.home() / ".npm-global/lib/node_modules/@earendil-works/pi-coding-agent"
    / "node_modules/@earendil-works/pi-ai/dist/utils/validation.js"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def ident(prefix: str, *parts: str) -> str:
    return f"{prefix}_{hashlib.sha256(':'.join(parts).encode()).hexdigest()[:12]}"


def arm_order(index: int) -> tuple[str, ...]:
    """Even lineages untreated first, odd lineages treated first."""
    return ("A", "G") if index % 2 == 0 else ("G", "A")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--contract-id", default="w4c-one-model-run-001")
    parser.add_argument("--capture-id", default="20260822-w4c-model-001")
    parser.add_argument("--out", default="contract-w4c-validate-only.json")
    parser.add_argument("--ceiling", default="1.50000000")
    parser.add_argument("--expect-instrument-sha256",
                        help="assert the rebuilt instrument matches a prior build")
    args = parser.parse_args()

    lineages = lineage.build_all()

    fixture = HERE / "build" / "fixture"
    visible = fixture / "visible"
    hidden = fixture / "hidden"
    hidden.mkdir(parents=True, exist_ok=True)
    for entry in lineages:
        lineage_dir = visible / "transcripts" / entry["lineage_key"]
        lineage_dir.mkdir(parents=True, exist_ok=True)
        for index, session in enumerate(entry["sessions"], 1):
            (lineage_dir / f"session-{index}.md").write_text(session + "\n")
    (hidden / "expected.json").write_text(
        json.dumps({"schema_version": 1, "lineages": lineages},
                   indent=2, sort_keys=True) + "\n")

    assignments = []
    order_by_lineage = {}
    ordinal = 0
    for lineage_index, entry in enumerate(lineages):
        key = entry["lineage_key"]
        order = arm_order(lineage_index)
        order_by_lineage[key] = list(order)
        sequence_options = sorted({
            entry["facts_final"]["sequence_rule"],
            "_before_".join(reversed(
                entry["facts_final"]["sequence_rule"].split("_before_"))),
        })
        for arm in order:
            for session_index in range(1, 9):
                ordinal += 1
                session_text = entry["sessions"][session_index - 1]
                assignments.append({
                    "ordinal": ordinal,
                    "assignment_id": ident("assignment", "writer", arm, key,
                                           str(session_index)),
                    "task_id": ident("task", "writer", arm, key, str(session_index)),
                    "role": "writer",
                    "arm": arm,
                    "lineage_key": key,
                    "k": 8,
                    "session_index": session_index,
                    "task_kind": None,
                    "prompt": session_text,
                    "transcript_sha256": digest_text(session_text),
                })
            for task in entry["tasks"]:
                ordinal += 1
                kind = task["task_kind"]
                task_id = ident("task", "reader", arm, key, kind)
                tool = cm.submit_tool(kind, sequence_options)
                prompt = (f"{task['prompt']}\n\nYour task_id for the submit tool is "
                          f"{task_id}.")
                assignments.append({
                    "ordinal": ordinal,
                    "assignment_id": ident("assignment", "reader", arm, key, kind),
                    "task_id": task_id,
                    "role": "reader",
                    "arm": arm,
                    "lineage_key": key,
                    "k": 8,
                    "session_index": None,
                    "task_kind": kind,
                    "prompt": prompt,
                    "task_contract": {
                        "schema_version": 1,
                        "contract_id": "w4-reader-assignment-contract-001",
                        "task": {"task_id": task_id, "tool": tool},
                    },
                })

    assert ordinal == 160
    writers = [a for a in assignments if a["role"] == "writer"]
    readers = [a for a in assignments if a["role"] == "reader"]
    assert len(writers) == 128 and len(readers) == 32
    for reader in readers:
        owners = [w["ordinal"] for w in writers
                  if w["lineage_key"] == reader["lineage_key"]
                  and w["arm"] == reader["arm"]]
        assert len(owners) == 8 and max(owners) < reader["ordinal"], (
            reader["assignment_id"])

    # The counterbalance itself is an invariant, not a hope: exactly four lineages
    # each way, and within every lineage the two arms' writer blocks do not interleave.
    a_first = [k for k, v in order_by_lineage.items() if v == ["A", "G"]]
    g_first = [k for k, v in order_by_lineage.items() if v == ["G", "A"]]
    assert len(a_first) == 4 and len(g_first) == 4, order_by_lineage
    for key, order in order_by_lineage.items():
        blocks = {}
        for w in writers:
            if w["lineage_key"] == key:
                blocks.setdefault(w["arm"], []).append(w["ordinal"])
        first, second = order
        assert max(blocks[first]) < min(blocks[second]), key

    instrument_dir = HERE / "build" / "instrument"
    instrument_dir.mkdir(parents=True, exist_ok=True)
    instrument = {
        "schema_version": 1,
        "instrument_id": "w4c-instrument-001",
        "assignment_count": 160,
        "writer_count": 128,
        "reader_count": 32,
        "arm_order_by_lineage": order_by_lineage,
        "assignments": assignments,
    }
    (instrument_dir / "instrument-w4c.json").write_text(
        json.dumps(instrument, indent=2, sort_keys=True) + "\n")
    instrument_sha256 = digest(instrument_dir / "instrument-w4c.json")
    if args.expect_instrument_sha256:
        assert instrument_sha256 == args.expect_instrument_sha256, (
            f"instrument drifted: {instrument_sha256} != "
            f"{args.expect_instrument_sha256}")

    head = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    pi_package = sandbox.PI.parent.parent / "package.json"
    contract = {
        "schema_version": 1,
        "contract_id": args.contract_id,
        "capture_id": args.capture_id,
        "model_run_authorized": False,
        "provider": "openai-codex",
        "model": args.model,
        "thinking": "high",
        "writer_session_timeout_seconds": 300,
        "reader_session_timeout_seconds": 240,
        "total_reported_model_cost_ceiling": args.ceiling,
        "assignment_count": 160,
        "writer_count": 128,
        "reader_count": 32,
        "writer_turns_max": 14,
        "reader_turns_max": 8,
        "schema_recovery_limit": 2,
        "retry_count": 0,
        "replacement_count": 0,
        "selective_rerun_count": 0,
        "resume_supported": False,
        "counterbalanced": True,
        "arm_order_by_lineage": order_by_lineage,
        "instrument_resource": "build/instrument/instrument-w4c.json",
        "instrument_sha256": instrument_sha256,
        "fixture_hidden_resource": "build/fixture/hidden/expected.json",
        "fixture_hidden_sha256": digest(hidden / "expected.json"),
        "writer_system_prompt_sha256": digest_text(cm.WRITER_SYSTEM_PROMPT),
        "reader_system_prompt_a_sha256": digest_text(cm.READER_SYSTEM_PROMPT_A),
        "source_sha256": {name: digest(HERE / name) for name in W4C_SOURCES},
        "external_source_sha256": {
            name: digest((HERE / name).resolve()) for name in EXTERNAL_SOURCES},
        "package_commit": head,
        "package_source_sha256": {name: digest(REPO / name) for name in PACKAGE_FILES},
        "arm_tool_sha256": {arm: digest(HERE / "arms" / f"tool-{arm}.ts")
                            for arm in ("A", "G")},
        "sandbox_source_sha256": digest(Path(sandbox.__file__)),
        "pi_executable": str(sandbox.PI),
        "pi_executable_sha256": digest(sandbox.PI),
        "pi_package_json_sha256": digest(pi_package),
        "pi_package_version": json.loads(pi_package.read_text()).get("version"),
        "validation_module": str(VALIDATION_MODULE),
        "validation_module_sha256": digest(VALIDATION_MODULE),
    }
    (instrument_dir / args.out).write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "assignments": 160,
        "writers": 128,
        "readers": 32,
        "a_first_lineages": sorted(a_first),
        "g_first_lineages": sorted(g_first),
        "instrument_sha256": contract["instrument_sha256"],
        "hidden_sha256": contract["fixture_hidden_sha256"],
        "arm_tool_sha256": contract["arm_tool_sha256"],
        "package_commit": contract["package_commit"],
    }, indent=2))


if __name__ == "__main__":
    main()
