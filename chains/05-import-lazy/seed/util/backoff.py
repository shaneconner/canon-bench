"""Retry delay schedule. Pure arithmetic: nothing here sleeps or reads a clock."""

BASE = 2
CEILING = 300


class Backoff:
    """Exponential delays, capped at a ceiling."""

    def __init__(self, base, ceiling):
        self.base = base
        self.ceiling = ceiling

    def delay(self, attempt):
        if attempt < 1:
            raise ValueError("attempts start at 1")
        return min(self.base ** attempt, self.ceiling)

    def schedule(self, attempts):
        return [self.delay(attempt) for attempt in range(1, attempts + 1)]


# One policy object for the whole process; the helpers below delegate to it.
POLICY = Backoff(BASE, CEILING)


def delay(attempt):
    return POLICY.delay(attempt)


def schedule(attempts):
    return POLICY.schedule(attempts)


# Shared schedule: modules import this configured instance rather than each
# constructing their own.
shared = Backoff(BASE, CEILING)
