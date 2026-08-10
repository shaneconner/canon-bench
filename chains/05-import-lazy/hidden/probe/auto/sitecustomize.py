"""Loads the handshake counter into a process the grader starts as a plain CLI.

Only this directory carries it, and only the entry-point run puts this directory
on PYTHONPATH. The boot-window driver deliberately does not: it has to watch the
work tree resolve `import vendor` itself before anything patches the SDK, which
is how a stub vendor.py shadowing the real one gets reported as a shadow rather
than as a broken implementation.
"""

import _grade_probe  # noqa: F401  (importing it is the whole point)
