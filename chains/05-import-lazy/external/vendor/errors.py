"""Exceptions raised by the vendor SDK."""


class VendorError(Exception):
    """Base class for every error this SDK raises."""


class VendorConnectionError(VendorError):
    """The endpoint could not be reached from this process."""


class VendorAuthError(VendorError):
    """The endpoint rejected the credentials."""
