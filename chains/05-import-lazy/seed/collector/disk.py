"""Disk busy pull."""

import vendor

ENDPOINT = "https://api.vendor.example/v3"
KEY = "mk-7731-prod"
TIMEOUT = 20

METRIC = "disk"


def collect():
    """Return {host: sample} for every host the vendor knows about."""
    api = vendor.Client(ENDPOINT, KEY, timeout=TIMEOUT)
    hosts = api.list_hosts()
    return dict((host, api.sample(host, METRIC)) for host in hosts)
