"""Stock adjustments. Emits to the shared audit sink."""
from . import audit

RECONCILE_JOB = "system:inventory-reconcile"


def adjust(workdir, sku, delta, actor):
    audit.emit(workdir, actor, "stock.adjust", sku, {"delta": delta})
    return {"sku": sku, "delta": delta}


def reconcile(workdir, sku, counted):
    """Scheduled reconciliation. No human initiated it."""
    audit.emit(workdir, RECONCILE_JOB, "stock.reconcile", sku, {"counted": counted})
    return {"sku": sku, "counted": counted}
