"""Exceptions module."""


class APIException(Exception):
    """API error."""


class InvalidInvoice(APIException):
    """RLN could not decode the supplied invoice."""


class AllocationsAlreadyAvailable(Exception):
    """Allocations already available error."""


class InvalidTransportEndpoints(Exception):
    """Invalid transport endpoints error."""


class RecipientIDAlreadyUsed(Exception):
    """Recipient ID already used error."""
