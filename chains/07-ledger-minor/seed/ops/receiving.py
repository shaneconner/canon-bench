"""Inbound receiving against purchase orders."""
from ledger.entry import record


def receive_shipment(workdir, po_id, sku, units):
    """Book a received quantity against a PO. Units are whole items."""
    units = int(units)
    if units <= 0:
        raise ValueError("units must be positive")
    record(workdir, "receiving.accept", po_id, {"sku": sku, "units": units})
    return {"po": po_id, "sku": sku, "units": units}
