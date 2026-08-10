"""Memory pressure pull."""

import vendor

API_URL = "https://api.vendor.example/v3"
API_KEY = "mk-7731-prod"
READ_TIMEOUT = 15

METRIC = "mem"


def collect():
    """Return {host: sample} for every host the vendor knows about."""
    session = vendor.Client(API_URL, API_KEY, READ_TIMEOUT)
    samples = {}
    for host in session.list_hosts():
        samples[host] = session.sample(host, METRIC)
    return samples
