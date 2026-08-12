"""Invoice actions. Emits to the shared audit sink."""
from . import audit

NIGHTLY_JOB = "ops-billing-close"


def void_invoice(workdir, invoice_id, actor):
    """A person voids an invoice. The actor is that person."""
    audit.emit(workdir, actor, "invoice.void", invoice_id)
    return {"invoice": invoice_id, "state": "void"}


def close_period(workdir, period):
    """The nightly close. Nobody is at a keyboard, so the actor is the job."""
    audit.emit(workdir, NIGHTLY_JOB, "period.close", period)
    return {"period": period, "state": "closed"}
