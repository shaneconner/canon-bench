"""Customer returns."""
from ledger.entry import record


def accept_return(workdir, rma_id, sku, units):
    """Book a return against an RMA. Units are whole items."""
    units = int(units)
    if units <= 0:
        raise ValueError("units must be positive")
    record(workdir, "return.accept", rma_id, {"sku": sku, "units": units})
    return {"rma": rma_id, "sku": sku, "units": units}
