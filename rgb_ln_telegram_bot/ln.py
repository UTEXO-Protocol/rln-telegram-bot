"""Module to perform API calls to RLN."""

from logging import getLogger

import requests

from rgb_ln_telegram_bot.exceptions import (
    AllocationsAlreadyAvailable,
    APIException,
    InvalidInvoice,
    InvalidTransportEndpoints,
    RecipientIDAlreadyUsed,
)

from . import settings as sett

LOGGER = getLogger(__name__)

_ERROR_NAMES = {
    "AllocationsAlreadyAvailable": AllocationsAlreadyAvailable,
    "InvalidTransportEndpoints": InvalidTransportEndpoints,
    "RecipientIDAlreadyUsed": RecipientIDAlreadyUsed,
    "InvalidInvoice": InvalidInvoice,
}


def _api_headers():
    headers = {}
    if sett.RLN_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {sett.RLN_AUTH_TOKEN}"
    return headers


def _check_if_err(res):
    if "error" not in res:
        return
    err = res["error"]
    name = res.get("name", "")
    exc_type = _ERROR_NAMES.get(name)
    if exc_type is not None:
        raise exc_type(err)
    if "Allocations already available" in err:
        raise AllocationsAlreadyAvailable
    if "Invalid transport endpoints" in err:
        raise InvalidTransportEndpoints
    if "Recipient ID already used" in err:
        raise RecipientIDAlreadyUsed
    raise APIException(err)


def _request(method, path, json_payload=None):
    """Perform an HTTP request to RLN and return the parsed JSON body."""
    url = f"{sett.LN_NODE_URL}{path}"
    kwargs = {
        "timeout": sett.REQUESTS_TIMEOUT,
        "headers": _api_headers(),
    }
    if json_payload is not None:
        kwargs["json"] = json_payload
    try:
        response = requests.request(method, url, **kwargs)
    except requests.RequestException as exc:
        raise APIException(f"RLN request failed: {type(exc).__name__}") from exc
    try:
        res = response.json()
    except ValueError as exc:
        raise APIException(f"Invalid JSON response (HTTP {response.status_code})") from exc
    if not isinstance(res, dict):
        raise APIException(f"Expected a JSON object (HTTP {response.status_code})")
    if "error" in res:
        _check_if_err(res)
    if not response.ok:
        raise APIException(f"HTTP {response.status_code}")
    return res


def asset_balance():
    """Call the /assetbalance API."""
    return _request("POST", "/assetbalance", {"asset_id": sett.ASSET_ID})


def btc_balance():
    """Call the /btcbalance API."""
    return _request("POST", "/btcbalance", {"skip_sync": False})


def create_utxos():
    """Call the /createutxos API."""
    return _request(
        "POST",
        "/createutxos",
        {
            "up_to": True,
            "num": sett.UTXOS_TO_CREATE,
            "size": None,
            "fee_rate": sett.FEE_RATE,
            "skip_sync": False,
        },
    )


def get_invoice():
    """Call the /lninvoice API."""
    res = _request(
        "POST",
        "/lninvoice",
        {
            "amt_msat": sett.HTLC_MIN_MSAT,
            "expiry_sec": sett.INVOICE_EXPIRATION_SEC,
            "asset_id": sett.ASSET_ID,
            "asset_amount": sett.INVOICE_PRICE,
        },
    )
    return res["invoice"]


def get_invoice_status(invoice):
    """Call the /invoicestatus API."""
    res = _request("POST", "/invoicestatus", {"invoice": invoice})
    return res["status"]


def get_network_info():
    """Call the /networkinfo API."""
    return _request("GET", "/networkinfo")


def get_node_info():
    """Call the /nodeinfo API."""
    return _request("GET", "/nodeinfo")


def list_assets():
    """Call the /listassets API."""
    return _request("POST", "/listassets", {"filter_asset_schemas": []})


def decode_rgb_invoice(invoice):
    """Decode the complete invoice using the same RGB version as the wallet."""
    return _request("POST", "/decodergbinvoice", {"invoice": invoice})


def refresh_transfers():
    """Call the /refreshtransfers API."""
    return _request("POST", "/refreshtransfers", {"filter": [], "skip_sync": False})


def send_asset(invoice):
    """Send to a complete invoice, retaining its proxy authentication data."""
    res = _request(
        "POST",
        "/sendrgbinvoice",
        {
            "invoice": invoice,
            "asset_id": sett.ASSET_ID,
            "amount": sett.ASSET_AMOUNT_TO_SEND,
            "donation": True,
            "fee_rate": sett.FEE_RATE,
            "min_confirmations": 0,
        },
    )
    return res["txid"]


def send_btc(address):
    """Call the /sendbtc API."""
    res = _request(
        "POST",
        "/sendbtc",
        {
            "amount": sett.SAT_AMOUNT_TO_SEND,
            "address": address,
            "fee_rate": sett.FEE_RATE,
            "skip_sync": False,
        },
    )
    return res["txid"]
