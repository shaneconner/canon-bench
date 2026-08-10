"""Response bodies the v3 endpoints return for this account.

The fleet endpoints answer with the same 23-host fleet and the same sample
series on every call, so the bodies are computed rather than transcribed.
"""

from vendor.errors import VendorAuthError, VendorError

API_KEY = "mk-7731-prod"
ACCOUNT = "acct-4417"
FLEET = tuple("node-%02d" % index for index in range(23))
METRIC_SALT = {"cpu": 17, "mem": 23, "disk": 31}


def sample_value(host, metric):
    """The value the sample endpoint serves for one host and metric."""
    return ((FLEET.index(host) + 3) * METRIC_SALT[metric]) % 97


def body(path, params):
    if path == "/session":
        if params.get("key") != API_KEY:
            raise VendorAuthError("api key rejected")
        return {"account": ACCOUNT, "plan": "fleet"}
    if path == "/hosts":
        return {"hosts": list(FLEET)}
    if path == "/sample":
        host = params.get("host")
        metric = params.get("metric")
        if metric not in METRIC_SALT:
            raise ValueError("unknown metric %r" % (metric,))
        if host not in FLEET:
            raise ValueError("unknown host %r" % (host,))
        return {"host": host, "metric": metric, "value": sample_value(host, metric)}
    raise VendorError("no such endpoint: %s" % (path,))
