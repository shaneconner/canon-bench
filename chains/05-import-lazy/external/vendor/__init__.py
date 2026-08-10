"""vendor-metrics 3.4.1 - Python bindings for the Vendor Metrics v3 API.

    import vendor

    client = vendor.Client("https://api.vendor.example/v3", api_key, timeout=10)
    for host in client.list_hosts():
        print(host, client.sample(host, "cpu"))

A Client opens one connection to the endpoint and exchanges the API key for an
account session; every call made through that client reuses it.
"""

from vendor.client import Client
from vendor.errors import VendorAuthError, VendorConnectionError, VendorError

__version__ = "3.4.1"
__all__ = ["Client", "VendorError", "VendorConnectionError", "VendorAuthError"]
