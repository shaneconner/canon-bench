"""Replay spec for 06-audit-actor. Never ships in the checkout.

xcut1 could not separate three explanations for the probe writing
`system:dispatch-sweep`: the article never carried the dispatch id (capture), the
article carried it but at an address that framed it as billing trivia (addressing),
or the agent had everything it needed and did not act on it (execution).

A full chain run cannot separate them, because the plant session decides all three
at once. This spec freezes everything except the article and runs the probe alone.

The checkout is the seed with the plant's own fix to ops/billing.py applied, which is
what the probe would have faced after a real plant session. The store is written
directly, so the article under test is exactly the bytes named here.

The two factors:

    content   as_written  the article the agent actually wrote in xcut1, which states
                          the rule's SHAPE and gives only billing's own id
              with_values the same article plus the one sentence carrying the registry

    address   ops/billing       an asset address; surfaces on touch
              policy/audit-actor  governs no asset, so it is residue and must be ranked

Bodies are byte-identical across addresses on purpose. It reads a little oddly at
policy/audit-actor, and that is the price of varying one thing.

Predictions, registered before the run:
    capture binding    with_values passes at both addresses, as_written fails at both
    address binding    policy passes at both contents, ops/billing fails at both
    execution binding  everything fails, including with_values
"""

CAPSULE_AS_WRITTEN = (
    "close_period uses system:billing-close; void_invoice records detail.period via its "
    "optional fourth period argument."
)

# Verbatim from the xcut1 canon arm, whitespace normalised. This is the article a real
# plant session distilled from a journal that held every registered id.
BODY_AS_WRITTEN = (
    "Billing audit behavior: close_period emits period.close with actor exactly "
    "system:billing-close, matching the scheduler's registered job id billing-close. "
    "void_invoice accepts an optional period argument and emits invoice.void with detail "
    "containing the period key; the optional default preserves existing three-argument "
    "callers. Scheduler ids are scheduler-owned identifiers, not module or function names."
)

# The single sentence the distillation dropped. Nothing else changes.
REGISTRY_SENTENCE = (
    " The scheduler's registered jobs are billing-close, inventory-reconcile and "
    "nightly-dispatch."
)

CAPSULE_WITH_VALUES = CAPSULE_AS_WRITTEN + " Registered jobs: billing-close, inventory-reconcile, nightly-dispatch."
BODY_WITH_VALUES = BODY_AS_WRITTEN + REGISTRY_SENTENCE

ASSET_ADDRESS = "ops/billing"
POLICY_ADDRESS = "policy/audit-actor"

VARIANTS = {
    "floor_no_article": {},
    "asset_as_written": {ASSET_ADDRESS: (CAPSULE_AS_WRITTEN, BODY_AS_WRITTEN)},
    "asset_with_values": {ASSET_ADDRESS: (CAPSULE_WITH_VALUES, BODY_WITH_VALUES)},
    "policy_as_written": {POLICY_ADDRESS: (CAPSULE_AS_WRITTEN, BODY_AS_WRITTEN)},
    "policy_with_values": {POLICY_ADDRESS: (CAPSULE_WITH_VALUES, BODY_WITH_VALUES)},
}


def post_plant(work):
    """Put the checkout in the state a real plant session leaves it: billing fixed.

    This is the same mutation validate.py asserts the trap survives, so the leaked
    `system:` prefix is present in every cell and cannot explain a difference between
    them."""
    billing = work / "ops" / "billing.py"
    text = billing.read_text(encoding="utf-8")
    fixed = text.replace('NIGHTLY_JOB = "ops-billing-close"', 'NIGHTLY_JOB = "system:billing-close"')
    if fixed == text:
        raise SystemExit("06 replay: the plant's fix did not apply; the seed has moved")
    billing.write_text(fixed, encoding="utf-8")
