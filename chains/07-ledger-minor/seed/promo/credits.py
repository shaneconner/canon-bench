"""Store credits issued to customers.

Credits are handed out at the counter and tracked on the customer record. Nothing
about them reaches the ledger.
"""
from decimal import Decimal


def issue_credit(workdir, customer_id, dollars, reason):
    """Issue a store credit. `dollars` is a decimal dollar amount, e.g. "5.00"."""
    amount = Decimal(dollars).quantize(Decimal("0.01"))
    if amount <= 0:
        raise ValueError("credit must be positive")
    return {"customer": customer_id, "dollars": str(amount), "reason": reason}
