"""Dispatch. Moves shipments to carriers.

A separate package from ops/ because dispatch talks to carrier APIs and has its
own release cadence. Emits nothing yet: it predates the audit sink and was never
wired up.
"""


def dispatch(workdir, shipment_id, carrier):
    """Hand a shipment to a carrier. Returns the dispatch record."""
    return {"shipment": shipment_id, "carrier": carrier, "state": "dispatched"}


def sweep(workdir, shipments, carrier):
    """The scheduled sweep: dispatch everything still waiting. No human here."""
    return [dispatch(workdir, shipment, carrier) for shipment in shipments]
