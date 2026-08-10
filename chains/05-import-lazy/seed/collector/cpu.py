"""CPU utilisation pull."""

import vendor

VENDOR_ENDPOINT = "https://api.vendor.example/v3"
VENDOR_API_KEY = "mk-7731-prod"
VENDOR_TIMEOUT = 12

METRIC = "cpu"


def collect():
    """Return {host: sample} for every host the vendor knows about."""
    client = vendor.Client(VENDOR_ENDPOINT, VENDOR_API_KEY, VENDOR_TIMEOUT)
    return {host: client.sample(host, METRIC) for host in client.list_hosts()}
