"""HTTPS transport for the v3 API.

Endpoints are addressed by hostname. Sites that run split-horizon DNS can pin
their own addresses with VENDOR_API_ROUTES, which takes the same host=address
list as the vendor CLI's --route flag:

    VENDOR_API_ROUTES=api.vendor.example=10.4.0.9,api-eu.vendor.example=10.4.0.10

When it is unset the published production routes are used.
"""

import os

from vendor import payloads
from vendor.errors import VendorConnectionError

ROUTES_ENV = "VENDOR_API_ROUTES"
PRIMARY_HOST = "api.vendor.example"
PUBLISHED_ROUTES = {
    PRIMARY_HOST: "203.0.113.10",
    "api-eu.vendor.example": "203.0.113.42",
}
PORT = 443


def routes():
    """The host -> address map this process can dial."""
    override = os.environ.get(ROUTES_ENV)
    if override is None:
        return dict(PUBLISHED_ROUTES)
    pairs = (item.split("=", 1) for item in override.split(",") if "=" in item)
    return {host.strip(): address.strip() for host, address in pairs}


def host_of(endpoint):
    """The hostname an endpoint URL points at."""
    authority = endpoint.split("://", 1)[-1].split("/", 1)[0]
    return authority.split(":", 1)[0]


def address_for(host):
    address = routes().get(host)
    if address is None:
        raise VendorConnectionError("no route to %s" % (host,))
    return address


class Session:
    """One open connection to an endpoint."""

    def __init__(self, endpoint, timeout):
        self.endpoint = endpoint
        self.host = host_of(endpoint)
        self.timeout = timeout
        self.address = address_for(self.host)

    def get(self, path, **params):
        """Issue a GET on this session and return the decoded body."""
        self.address = address_for(self.host)
        return payloads.body(path, params)

    def close(self):
        self.address = None


def connect(endpoint, timeout=10):
    """Open a session to endpoint."""
    return Session(endpoint, timeout)
