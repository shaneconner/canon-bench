"""Grade-time instrumentation. Never on the work tree's path outside grading.

Imported by the grade driver before anything in the work tree, so that every
client the service builds afterwards is one of these. Wrapping the SDK here
keeps the SDK itself free of anything the checkout would not see in production.

When GRADE_COUNTER names a file, the counts are also written there, which is how
a run started as a plain CLI (python3 tools/cron_pulse.py) reports back without
the grader having to import the entry point and call a function inside it.
"""

import atexit
import json
import os

import vendor
import vendor.client

HANDSHAKES = 0
SAMPLES = []
COUNTER = os.environ.get("GRADE_COUNTER")

_Client = vendor.client.Client


def dump():
    """Write the counts out, if this process was asked to report them."""
    if not COUNTER:
        return
    try:
        with open(COUNTER, "w") as handle:
            json.dump({"handshakes": HANDSHAKES, "samples": sorted(set(SAMPLES))}, handle)
    except OSError:
        pass


class _CountedClient(_Client):
    def __init__(self, *args, **kwargs):
        global HANDSHAKES
        super().__init__(*args, **kwargs)
        HANDSHAKES += 1
        dump()

    def sample(self, host, metric):
        value = super().sample(host, metric)
        SAMPLES.append("%s/%s" % (host, metric))
        return value


vendor.Client = _CountedClient
vendor.client.Client = _CountedClient

atexit.register(dump)


def reset():
    global HANDSHAKES
    HANDSHAKES = 0
    del SAMPLES[:]
