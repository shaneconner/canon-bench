"""The client object applications use."""

from vendor import transport

API_VERSION = "v3"


class Client:
    """An authenticated session against the metrics API.

    Constructing one dials the endpoint and exchanges the API key for an account
    session. That exchange is the expensive part of a collection run; the calls
    that follow ride the session it opened.
    """

    def __init__(self, endpoint, api_key, timeout=10):
        self.endpoint = endpoint
        self.timeout = timeout
        self._session = transport.connect(endpoint, timeout)
        self.account = self._session.get("/session", key=api_key)["account"]

    def __repr__(self):
        return "<vendor.Client %s account=%s>" % (self.endpoint, self.account)

    def list_hosts(self):
        """Every host this account can read."""
        return list(self._session.get("/hosts")["hosts"])

    def sample(self, host, metric):
        """The latest sample for one host and one metric."""
        return self._session.get("/sample", host=host, metric=metric)["value"]

    def close(self):
        self._session.close()
