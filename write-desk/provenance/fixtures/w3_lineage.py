"""W3 lineages: K-session fact evolution and the hidden oracle.

Each lineage is K session transcripts (K in 1, 2, 4, 8) over one domain's three
assets, evolving the W2 fact set so the truth at lineage end depends on the
whole history: capacity_limit revised EVERY session, operating_mode revised on
even sessions, alert_threshold revised on odd sessions from 3, confirmation
flipped once mid-lineage, sequence_rule set in session 1 and never touched (the
untouched-old-fact probe), consumer_id set in session 1 and RETIRED near the
end (the retired-fact probe). Narration phrasing is rotated across four
templates so the staleness measurement is not keyed to one wording.

Determinism from DEV_SEED per lineage; every value token in a lineage
(revisions, decoys, task constants) is construction-asserted distinct, so
containment and contamination checks stay mechanical.
"""

import hashlib
import random
import re

DEV_SEED = hashlib.sha256(b"w3-dev-seed-v1").digest()

K_RUNGS = (1, 2, 4, 8)

DOMAINS = (
    "vineyard_netting", "foundry_ladle", "observatory_chiller", "salt_pan_rakes",
    "funicular_brakes", "mushroom_tunnel", "regatta_timing", "gravel_washplant",
)

VOCAB = {
    "vineyard_netting": ("vineyard/net/scheduler", "vineyard/span/limits",
                         "vineyard/frost/fans", "rows", ("furl", "stake"), "tension"),
    "foundry_ladle": ("foundry/pour/planner", "foundry/ladle/limits",
                      "foundry/gas/purge", "heats", ("preheat", "skim"), "lining"),
    "observatory_chiller": ("observatory/run/scheduler", "observatory/loop/limits",
                            "observatory/dome/vents", "hours", ("flush", "prime"), "coolant"),
    "salt_pan_rakes": ("saltpan/rake/rota", "saltpan/brine/limits",
                       "saltpan/pump/house", "beds", ("drain", "rake"), "salinity"),
    "funicular_brakes": ("funicular/service/rota", "funicular/load/limits",
                         "funicular/cable/watch", "cars", ("chock", "release"), "wear"),
    "mushroom_tunnel": ("tunnel/flush/planner", "tunnel/climate/limits",
                        "tunnel/spawn/store", "trays", ("mist", "vent"), "casing"),
    "regatta_timing": ("regatta/heat/scheduler", "regatta/course/limits",
                       "regatta/mark/boats", "lanes", ("set", "sight"), "current"),
    "gravel_washplant": ("washplant/feed/planner", "washplant/screen/limits",
                         "washplant/fines/press", "loads", ("rinse", "screen"), "turbidity"),
}

MODES = ("conservative", "standard", "aggressive")

# Narration templates for a revision, rotated so staleness is not one phrasing.
# Direction-neutral: values fall as often as they rise.
REVISIONS = (
    "{name} was changed from {old} to {new}",
    "{name} is now {new}; {old} is retired",
    "{name} recalibrated: {new} replaces {old}",
    "{name} set to {new} (was {old})",
)

ID_WORDS = ("mica", "heron", "basalt", "tiller", "damson", "gantry", "petrel",
            "umber", "sloop", "corbel", "russet", "moraine", "teasel", "bight",
            "skerry", "marl")


def _mode_after(rng, current):
    choices = [m for m in MODES if m != current]
    return rng.choice(choices)


def build_lineage(domain: str, k: int) -> dict:
    rng = random.Random(DEV_SEED + f"{domain}:K{k}".encode())
    work, limits, trap, unit, (seq_a, seq_b), reading = VOCAB[domain]
    assets = {"W": work, "L": limits, "G": trap}

    used: set[str] = set()

    def fresh_int(low: int, high: int, step: int = 1) -> int:
        while True:
            value = rng.randrange(low, high, step)
            if str(value) not in used:
                used.add(str(value))
                return value

    capacities = [fresh_int(120, 880, 10) for _ in range(k)]
    thresholds = [fresh_int(20, 95)]
    for s in range(3, k + 1, 2):
        thresholds.append(fresh_int(20, 95))
    modes = [rng.choice(MODES)]
    for s in range(2, k + 1):
        if s % 2 == 0:
            modes.append(_mode_after(rng, modes[-1]))
    confirmation_initial = rng.random() < 0.5
    flip_at = (k // 2) + 1 if k >= 2 else None
    confirmation_final = (not confirmation_initial) if flip_at else confirmation_initial
    seq_first = rng.random() < 0.5
    sequence = f"{seq_a}_before_{seq_b}" if seq_first else f"{seq_b}_before_{seq_a}"
    sequence_phrase = sequence.replace("_", " ")
    consumer = f"svc-{ID_WORDS[rng.randrange(16)]}-{fresh_int(10, 90)}"
    retire_at = max(2, k - 1) if k >= 2 else None

    def fresh_offset(base: int, offsets: tuple[int, ...]) -> int:
        for offset in rng.sample(offsets, len(offsets)):
            if str(base + offset) not in used:
                used.add(str(base + offset))
                return base + offset
        raise AssertionError((domain, k, base, offsets))

    proposed = fresh_offset(capacities[-1], (-30, 40, -50, 60))
    observed = fresh_offset(thresholds[-1], (-7, 9, -11, 13))

    def confirmation_line(value: bool) -> str:
        return (f"starting a {unit} run requires two-person confirmation"
                if value else f"{unit} runs may start single-operator")

    sessions = []
    cap_i = 0
    thr_i = 0
    mode_i = 0
    for s in range(1, k + 1):
        decoys = [str(fresh_int(1000, 9600)) for _ in range(8)]
        lines = [f"Session {s} record, {domain.replace('_', ' ')} maintenance."]
        if s == 1:
            cap_i = 0
            lines += [
                f"Baseline pass on {work}. Operating mode for {work} is {modes[0]}; "
                f"{confirmation_line(confirmation_initial)}.",
                f"{limits} baseline: the capacity limit is {capacities[0]} {unit}, and "
                f"the {reading} alert threshold is {thresholds[0]}.",
                f"Also settled, and it concerns {trap} rather than {work}: the rule is "
                f"{sequence_phrase}, always, and the export from that path is consumed "
                f"by {consumer}.",
                f"Working notes from the day, kept for the record. First replay took "
                f"{decoys[0]}ms over {decoys[1]} entries and cleared on the second "
                f"pass; the fallback path still rejects envelopes over {decoys[2]}; "
                f"the retry counter sat at {decoys[3]} all day and nothing about it "
                f"was acted on.",
                f"Chased an apparent duplicate-delivery blip for a while: {decoys[4]} "
                f"envelopes went out and {decoys[4]} receipts came back, so the "
                f"mismatch on the dashboard was a display artifact, not a delivery "
                f"problem. An hour, no change to anything.",
                f"There was loose talk about raising the batch floor to something in "
                f"the {decoys[5]} range and about moving the weekly pass to a "
                f"different day. Neither was decided; both are explicitly still open, "
                f"and nothing should be recorded as if they were settled.",
                f"End-of-day sweep: reconciled the ledger view ({decoys[6]} rows "
                f"scanned, {decoys[7]} touched), confirmed the standby node is still "
                f"pinned to the same build, and left the queue empty. Nothing else "
                f"about {work} changed today.",
            ]
        else:
            cap_i = s - 1
            revision = REVISIONS[(s - 2) % len(REVISIONS)]
            lines.append("Changes this session:")
            lines.append(revision.format(
                name=f"the {limits} capacity limit", old=capacities[s - 2],
                new=f"{capacities[s - 1]} {unit}") + ".")
            if s % 2 == 0:
                mode_i += 1
                lines.append(REVISIONS[(s - 1) % len(REVISIONS)].format(
                    name=f"the {work} operating mode", old=modes[mode_i - 1],
                    new=modes[mode_i]) + ".")
            if s >= 3 and s % 2 == 1:
                thr_i += 1
                lines.append(REVISIONS[s % len(REVISIONS)].format(
                    name=f"the {reading} alert threshold", old=thresholds[thr_i - 1],
                    new=thresholds[thr_i]) + ".")
            if flip_at == s:
                lines.append(
                    f"Start policy reversed: from now on {confirmation_line(confirmation_final)}; "
                    f"the previous policy is withdrawn.")
            if retire_at == s:
                lines.append(
                    f"The {trap} export was decommissioned this session: {consumer} no "
                    f"longer consumes anything from it. The {sequence_phrase} rule itself "
                    f"still stands.")
            lines.append(
                f"Routine otherwise: sweep scanned {decoys[0]} rows and touched "
                f"{decoys[1]}; standby build still pinned at {decoys[2]}; one dead-end "
                f"probe of the mirror path aborted at {decoys[3]} entries and was "
                f"abandoned where it stood.")
            lines.append(
                f"Diagnostic tangent, no outcome: suspected the {reading} sensor lag "
                f"was inflating the third pass, so {decoys[4]} samples were captured "
                f"off the secondary tap and the windows compared; the medians "
                f"differed by noise and the suspicion was dropped. A separate check "
                f"replayed {decoys[5]} entries against the mirror and found no drift.")
            lines.append(
                f"End-of-session sweep: ledger view reconciled ({decoys[6]} rows "
                f"scanned, {decoys[7]} touched), queue left empty. Nothing else about "
                f"{work} changed this session.")
        sessions.append("\n\n".join(lines))

    facts_final = {
        "capacity_limit": capacities[-1],
        "operating_mode": modes[-1],
        "confirmation_required": confirmation_final,
        "sequence_rule": sequence,
        "alert_threshold": thresholds[-1],
        "consumer_id": consumer,
        "consumer_status": "retired" if retire_at else "active",
    }
    superseded = {
        "capacity_limit": [str(v) for v in capacities[:-1]],
        "alert_threshold": [str(v) for v in thresholds[:-1]],
        "operating_mode": sorted({m for m in modes[:-1] if m != modes[-1]}),
    }

    joined = "\n".join(sessions).lower()
    for value in ([str(capacities[-1]), str(thresholds[-1]), modes[-1],
                   sequence_phrase, consumer]
                  + superseded["capacity_limit"] + superseded["alert_threshold"]):
        assert value.lower() in joined, (domain, k, value)

    proceed = proposed <= capacities[-1] and modes[-1] != "aggressive"
    notify = confirmation_final or observed > thresholds[-1]
    tasks = [
        {
            "task_kind": "capacity",
            "prompt": (
                f"A run of {proposed} {unit} is proposed for {work}. Establish the "
                f"CURRENT capacity limit ({limits}), the CURRENT operating mode of "
                f"{work}, and the standing order-of-operations rule for {trap}. Decide: "
                f"proceed only if the proposed volume is within the capacity limit AND "
                f"the operating mode is not aggressive; otherwise hold. Values were "
                f"revised over time; only the latest state counts. Submit exactly one "
                f"review."
            ),
            "expected": {
                "capacity_limit": capacities[-1],
                "operating_mode": modes[-1],
                "sequence_rule": sequence,
                "decision": "proceed" if proceed else "hold",
            },
        },
        {
            "task_kind": "watch",
            "prompt": (
                f"The latest {reading} reading is {observed}. Establish whether starting "
                f"a {unit} run CURRENTLY requires two-person confirmation ({work}), the "
                f"CURRENT {reading} alert threshold ({limits}), and the status and "
                f"identifier of the consumer of the {trap} export (active if it still "
                f"consumes, retired if it was decommissioned; report the identifier "
                f"either way). Decide: notify only if confirmation is required OR the "
                f"reading exceeds the alert threshold; otherwise skip. Values were "
                f"revised over time; only the latest state counts. Submit exactly one "
                f"review."
            ),
            "expected": {
                "confirmation_required": confirmation_final,
                "alert_threshold": thresholds[-1],
                "consumer_status": facts_final["consumer_status"],
                "consumer_id": consumer,
                "decision": "notify" if notify else "skip",
            },
        },
    ]

    return {
        "lineage_key": f"{domain}_k{k}",
        "domain": domain,
        "k": k,
        "assets": assets,
        "unit": unit,
        "sessions": sessions,
        "facts_final": facts_final,
        "superseded": superseded,
        "capacities": capacities,
        "thresholds": thresholds,
        "modes": modes,
        "confirmation_initial": confirmation_initial,
        "flip_at": flip_at,
        "retire_at": retire_at,
        "sequence_phrase": sequence_phrase,
        "proposed": proposed,
        "observed": observed,
        "tasks": tasks,
    }


def state_at(entry: dict, s: int) -> dict:
    """Current fact values as of session s, which fact ids changed AT s, and
    the values superseded as of s. Session indices are 1-based."""
    assert 1 <= s <= entry["k"]
    cap_i = s - 1
    mode_i = sum(1 for x in range(2, s + 1) if x % 2 == 0)
    thr_i = sum(1 for x in range(3, s + 1) if x % 2 == 1)
    flip_at = entry["flip_at"]
    retire_at = entry["retire_at"]
    changed = set()
    if s == 1:
        changed = {"capacity_limit", "operating_mode", "confirmation_required",
                   "sequence_rule", "alert_threshold", "consumer_id"}
    else:
        changed.add("capacity_limit")
        if s % 2 == 0:
            changed.add("operating_mode")
        if s >= 3 and s % 2 == 1:
            changed.add("alert_threshold")
        if flip_at == s:
            changed.add("confirmation_required")
        if retire_at == s:
            changed.add("consumer_id")
    mode = entry["modes"][mode_i]
    return {
        "capacity_limit": entry["capacities"][cap_i],
        "operating_mode": mode,
        "confirmation_required": (
            (not entry["confirmation_initial"]) if flip_at and s >= flip_at
            else entry["confirmation_initial"]),
        "sequence_rule": entry["facts_final"]["sequence_rule"],
        "alert_threshold": entry["thresholds"][thr_i],
        "consumer_id": entry["facts_final"]["consumer_id"],
        "consumer_status": "retired" if retire_at and s >= retire_at else "active",
        "changed": sorted(changed),
        "superseded_as_of": {
            "capacity_limit": [str(v) for v in entry["capacities"][:cap_i]],
            "alert_threshold": [str(v) for v in entry["thresholds"][:thr_i]],
            "operating_mode": sorted(
                {m for m in entry["modes"][:mode_i] if m != mode}),
        },
    }


def build_all() -> list[dict]:
    lineages = [build_lineage(domain, k) for domain in DOMAINS for k in K_RUNGS]
    assert len(lineages) == 32
    assert sum(entry["k"] for entry in lineages) == 120
    decisions = [t["expected"]["decision"] for e in lineages for t in e["tasks"]]
    # Notify skews high (confirmation OR excess reading); W2 accepted 13/16.
    assert 5 <= decisions.count("proceed") <= 27, decisions.count("proceed")
    assert 5 <= decisions.count("notify") <= 28, decisions.count("notify")
    retired = [e for e in lineages if e["facts_final"]["consumer_status"] == "retired"]
    assert len(retired) == 24  # every K >= 2 lineage
    return lineages


if __name__ == "__main__":
    built = build_all()
    sample = next(e for e in built if e["k"] == 4)
    for i, s in enumerate(sample["sessions"], 1):
        print(f"--- session {i} ---")
        print(s)
    print()
    print("final:", sample["facts_final"])
    print("superseded:", sample["superseded"])
