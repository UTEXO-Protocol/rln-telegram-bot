"""Messages to users module."""

from . import settings as sett

# pylint: disable=anomalous-backslash-in-string,unnecessary-lambda-assignment

USE_HELP = f"Use /{sett.HELP_CMD} for info on what you can do with this bot\."

START = (
    """
⚡️ Welcome to the RGB LN test bot\! ⚡️

"""
    + USE_HELP
)

TOO_MANY_ASSET_REQUESTS = """
You requested assets too many times in the past 24 hours\. You can try again \
{next_request_time}\.
"""

TOO_MANY_BTC_REQUESTS = """
You requested BTC too many times in the past 24 hours\. You can try again \
{next_request_time}\.
"""

INVALID_INPUT = """
This is neither a valid RGB invoice nor a valid bitcoin address\.
"""

INVALID_ADDRESS = "This is not a valid bitcoin address\."

INVALID_RGB_INVOICE = "This is not a valid RGB invoice\."

INVALID_RGB_TRANSPORT_ENDPOINTS = (
    INVALID_RGB_INVOICE
    + """\
 The embedded transport endpoints are invalid or not supported\.
"""
)

ASK_RGB_INVOICE = """
Please give me an RGB invoice to send some assets\.
"""

ASK_BTC_ADDRESS = """
Please give me an address where to send some bitcoins\.
"""

RGB_INVOICE_ALREADY_USED = """
This RGB invoice has already been used, please send another one\.
"""

RGB_INVOICE_INVALID_NETWORK = """
This RGB invoice is for a different bitcoin network, please send another one\.
"""

RGB_INVOICE_INVALID_TYPE = """
This RGB invoice is requesting to receive in witness but the bot supports \
only the blind mode, please send another one\.
"""

ASSET_SENT = (
    lambda: f"""
I have sent you {sett.ASSET_AMOUNT_TO_SEND} {sett.ASSET_TICKER} with \
TXID:
`{{txid}}`

Don't forget to refresh your wallet's transfers to complete the asset \
receiving process \(multiple refreshes may be needed for the transfer to get \
to the settled status\)\.

Once the tranfer has settled you can open a channel with
`{sett.NODE_URI}`
using
`{sett.ASSET_TICKER}` \(`{sett.ASSET_ID}`\)
as the RGB asset
"""
)

BTC_SENT = (
    lambda: f"""
I have sent you {sett.SAT_AMOUNT_TO_SEND} sats with TXID:
`{{txid}}`
"""
)

MESSAGE_TOO_LONG = """
Tried to send a message over the text length limit
"""

SENDING_ASSET = (
    lambda: f"""
I'm now sending {sett.ASSET_AMOUNT_TO_SEND} {sett.ASSET_TICKER}\.

This may take a while\.
"""
)

SENDING_BTC = (
    lambda: f"""
I'm now sending {sett.SAT_AMOUNT_TO_SEND} sats\.
"""
)

SOMETHING_WENT_WRONG = """
Oops! Something went wrong.

The issue has been reported. Try again later.
"""

UNKNOWN_COMMAND = (
    """
Sorry, I don't understand this command 😕

"""
    + USE_HELP
)

HELP = (
    lambda: f"""
This bot helps testing RGB on LN\.
This can be done using Iris Wallet desktop which you can find in its \
[GitHub releases page]\
(https://github.com/RGB-Tools/iris-wallet-desktop/releases)\.

Under the hood \
[RLN \(rgb\-lightning\-node\)](https://github.com/RGB-Tools/rgb-lightning-node) \
is used to provide LN functionality on a shared regtest\.

Features:
1\. get on\-chain bitcoins
2\. get on\-chain RGB assets
3\. pay an RGB LN invoice to simulate the purchase of a virtual item

How to test an RGB LN payment:
1\. request on\-chain bitcoins with the /{sett.GETBTC_CMD} command
2\. request on\-chain assets with the /{sett.GETASSET_CMD} command
3\. open an RGB LN channel with the received asset towards the bot's LN \
node\. Use /{sett.GETNODEINFO_CMD} to get the necessary info
4\. request an RGB LN invoice with the /{sett.GETINVOICE_CMD} command
5\. pay the invoice and wait for feedback from the bot
"""
)

GET_NODE_INFO = (
    lambda: f"""
Node URI:
`{sett.NODE_URI}`

RGB asset ID:
`{sett.ASSET_ID}`

RGB asset ticker:
`{sett.ASSET_TICKER}`
"""
)

INVOICE_PENDING = """
There's already a pending invoice:
`{invoice}`

If you haven't paid it yet, please do it, otherwise please wait for the \
payment to be detected\.
"""

INVOICE_SEND = """
Here's your invoice:
`{invoice}`

Once the payment will be detected I will send you a nice sticker\.

Make sure the channel is usable \(by checking the channel management page\) \
before attempting the payment\.
"""

INVOICE_PAID = """
LN payment received\. Here's your sticker, congrats\!
"""

INVOICE_EXPIRED = f"""
Invoice has expired\. Use /{sett.GETINVOICE_CMD} to request a new one\.
"""

INVOICE_CANCELLED = f"""
Invoice was cancelled\. Use /{sett.GETINVOICE_CMD} to request a new one\.
"""

INVOICE_FAILED = f"""
Invoice payment failed\. Use /{sett.GETINVOICE_CMD} to request a new one\.
"""

RLN_REQUEST_FAILED = """
Could not complete the request against the RGB LN node\. Try again later\.
"""
