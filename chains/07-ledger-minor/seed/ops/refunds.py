"""Refund arithmetic. Dollar amounts owed back on returned goods."""
from decimal import Decimal


def refund_amount(order_total, returned_units, ordered_units):
    """Dollars owed back when part of an order comes back."""
    ordered_units = int(ordered_units)
    returned_units = int(returned_units)
    if ordered_units <= 0:
        raise ValueError("ordered_units must be positive")
    if returned_units <= 0:
        raise ValueError("returned_units must be positive")
    if returned_units > ordered_units:
        raise ValueError("cannot return more units than were ordered")
    return Decimal(order_total).quantize(Decimal("0.01"))
