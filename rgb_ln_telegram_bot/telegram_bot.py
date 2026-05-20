"""Bot handlers module."""

import datetime
import time
from functools import wraps
from logging import getLogger

import rgb_lib
import sqlalchemy as sa
from telegram.constants import ParseMode
from telegram.error import Forbidden

from rgb_ln_telegram_bot.exceptions import (
    APIException,
    InvalidTransportEndpoints,
    RecipientIDAlreadyUsed,
)
from rgb_ln_telegram_bot.ln import get_invoice, refresh_transfers, send_asset, send_btc

from . import msgs
from . import settings as sett
from .database import (
    Purchase,
    PurchaseStatus,
    SendBtcRequest,
    SendBtcRequestStatus,
    SendRequest,
    SendRequestStatus,
    User,
)

LOGGER = getLogger(__name__)


def _track_time(func):
    """Log the time spent on a handler."""

    @wraps(func)
    async def _wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        end = time.time()
        LOGGER.debug("%s ran in %0.3fs", func.__name__, round(end - start, 3))
        return result

    return _wrapper


async def _reply(update, msg):
    """Send a telegram message in markdown, disabling web page previews."""
    try:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True
        )
    except Forbidden as e:
        LOGGER.error("Didn't reply because action is forbidden: %s", e)


def _get_user(update, session):
    """Return the user from the DB, adding it if it isn't already there."""
    user_id = update.effective_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user is None:
        user = User(user_id=user_id)
        session.add(user)
        session.commit()
    return user


def _get_pending_reqs(session, user):
    pending_ass_req = (
        session.query(SendRequest)
        .where(
            sa.and_(
                SendRequest.user_idx == user.idx,
                sa.or_(
                    SendRequest.status == SendRequestStatus.PENDING,
                    SendRequest.status == SendRequestStatus.RGB_INVOICE_ALREADY_USED,
                ),
            )
        )
        .order_by(sa.desc(SendRequest.timestamp))
        .first()
    )
    pending_btc_req = (
        session.query(SendBtcRequest)
        .where(
            sa.and_(
                SendBtcRequest.user_idx == user.idx,
                SendBtcRequest.status == SendBtcRequestStatus.PENDING,
            )
        )
        .order_by(sa.desc(SendBtcRequest.timestamp))
        .first()
    )
    return (pending_ass_req, pending_btc_req)


async def _validate_user_input(update, user_input, pending_ass_req, pending_btc_req):
    invoice_data = address = None
    if pending_ass_req:
        try:
            invoice_data = rgb_lib.Invoice(user_input).invoice_data()
        except rgb_lib.RgbLibError.InvalidInvoice:
            if not pending_btc_req:
                await _reply(update, msgs.INVALID_RGB_INVOICE)
                return (None, None)
    if not invoice_data and pending_btc_req:
        try:
            address = rgb_lib.Address(user_input, sett.NETWORK)
        except rgb_lib.RgbLibError.InvalidAddress:
            if not pending_ass_req:
                await _reply(update, msgs.INVALID_ADDRESS)
                return (None, None)
    if not address and not invoice_data:
        await _reply(update, msgs.INVALID_INPUT)
        return (None, None)
    return (invoice_data, address)


async def _send_to_address(update, session, user_input, pending_btc_req):
    await _reply(update, msgs.SENDING_BTC())
    try:
        txid = send_btc(user_input)
    except APIException:
        LOGGER.exception("Send BTC failed")
        return await _reply(update, msgs.RLN_REQUEST_FAILED)
    pending_btc_req.status = SendBtcRequestStatus.SUCCESS
    pending_btc_req.txid = txid
    pending_btc_req.address = user_input
    session.commit()
    await _reply(update, msgs.BTC_SENT().format(txid=txid))


async def _send_to_invoice(
    update, session, user, invoice_data, user_input, pending_ass_req
):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    rgb_invoice_already_used = (
        session.query(SendRequest)
        .where(
            sa.and_(
                SendRequest.rgb_invoice == user_input,
                sa.or_(
                    SendRequest.status == SendRequestStatus.SUCCESS,
                    SendRequest.status == SendRequestStatus.RGB_INVOICE_ALREADY_USED,
                ),
            )
        )
        .count()
    )
    if rgb_invoice_already_used:
        return await _reply(update, msgs.RGB_INVOICE_ALREADY_USED)

    if pending_ass_req.status == SendRequestStatus.RGB_INVOICE_ALREADY_USED:
        pending_ass_req = SendRequest(user.idx)
        session.add(pending_ass_req)
        session.commit()

    if invoice_data.network != sett.NETWORK:
        return await _reply(update, msgs.RGB_INVOICE_INVALID_NETWORK)
    recipient_info = rgb_lib.RecipientInfo(invoice_data.recipient_id)
    if recipient_info.recipient_type() != rgb_lib.RecipientType.BLIND:
        return await _reply(update, msgs.RGB_INVOICE_INVALID_TYPE)

    await _reply(update, msgs.SENDING_ASSET())
    try:
        txid = send_asset(invoice_data.recipient_id, invoice_data.transport_endpoints)
        pending_ass_req.rgb_invoice = user_input
        pending_ass_req.status = SendRequestStatus.SUCCESS
        pending_ass_req.txid = txid
        session.commit()
        await _reply(update, msgs.ASSET_SENT().format(txid=txid))
        refresh_transfers()
    except InvalidTransportEndpoints:
        LOGGER.warning("Send failed because RGB invoice has invalid transport endpoints")
        await _reply(update, msgs.INVALID_RGB_TRANSPORT_ENDPOINTS)
    except RecipientIDAlreadyUsed:
        LOGGER.warning("Send failed because RGB invoice has already been used")
        pending_ass_req.status = SendRequestStatus.RGB_INVOICE_ALREADY_USED
        session.commit()
        await _reply(update, msgs.RGB_INVOICE_ALREADY_USED)
    except APIException:
        LOGGER.exception("Send asset failed")
        await _reply(update, msgs.RLN_REQUEST_FAILED)


async def help_handler(update, _context):
    """Handle the /help command."""
    await _reply(update, msgs.HELP())


async def unknown_command_handler(update, _context):
    """Handle an unknown command."""
    await _reply(update, msgs.UNKNOWN_COMMAND)


async def get_node_info_handler(update, _context):
    """Handle the /getnodeinfo command."""
    await _reply(update, msgs.GET_NODE_INFO())


async def start_handler(update, _context):
    """Handle the /start command."""
    with sett.Session() as session:
        _get_user(update, session)
    await _reply(update, msgs.START)


@_track_time
async def get_asset_handler(update, _context):
    """Handle the /getasset command."""
    now = datetime.datetime.now()
    time_24hours_ago = now - datetime.timedelta(days=1)
    with sett.Session() as session:
        user = _get_user(update, session)
        successful_interactions = (
            session.query(SendRequest)
            .where(
                sa.and_(
                    SendRequest.user_idx == user.idx,
                    SendRequest.timestamp > time_24hours_ago,
                    SendRequest.status == SendRequestStatus.SUCCESS,
                )
            )
            .order_by(SendRequest.timestamp)
        )
        if successful_interactions.count() >= sett.MAX_SUCCESSFUL_INTERACTIONS_PER_DAY:
            next_request_time = successful_interactions.first().timestamp + datetime.timedelta(
                days=1
            )
            when = "today"
            if now.weekday() != next_request_time.weekday():
                when = "tomorrow"
            nrt = f"{when} after {next_request_time.strftime('%H:%M:%S')}"
            return await _reply(
                update,
                msgs.TOO_MANY_ASSET_REQUESTS.format(next_request_time=nrt),
            )

        pending_request = (
            session.query(SendRequest)
            .filter_by(
                user_idx=user.idx,
                status=SendRequestStatus.PENDING,
            )
            .count()
        )
        if not pending_request:
            session.add(SendRequest(user_idx=user.idx))
            session.commit()
        await _reply(update, msgs.ASK_RGB_INVOICE)


@_track_time
async def get_btc_handler(update, _context):
    """Handle the /getbtc command."""
    now = datetime.datetime.now()
    time_24hours_ago = now - datetime.timedelta(days=1)
    with sett.Session() as session:
        user = _get_user(update, session)
        successful_interactions = (
            session.query(SendBtcRequest)
            .where(
                sa.and_(
                    SendBtcRequest.user_idx == user.idx,
                    SendBtcRequest.timestamp > time_24hours_ago,
                    SendBtcRequest.status == SendBtcRequestStatus.SUCCESS,
                )
            )
            .order_by(SendBtcRequest.timestamp)
        )
        if successful_interactions.count() >= sett.MAX_SUCCESSFUL_INTERACTIONS_PER_DAY:
            next_request_time = successful_interactions.first().timestamp + datetime.timedelta(
                days=1
            )
            when = "today"
            if now.weekday() != next_request_time.weekday():
                when = "tomorrow"
            nrt = f"{when} after {next_request_time.strftime('%H:%M:%S')}"
            return await _reply(
                update,
                msgs.TOO_MANY_BTC_REQUESTS.format(next_request_time=nrt),
            )

        pending_request = (
            session.query(SendBtcRequest)
            .filter_by(
                user_idx=user.idx,
                status=SendBtcRequestStatus.PENDING,
            )
            .count()
        )
        if not pending_request:
            session.add(SendBtcRequest(user_idx=user.idx))
            session.commit()
        await _reply(update, msgs.ASK_BTC_ADDRESS)


@_track_time
async def msg_handler(update, _context):
    """Handle messages that are not commands.

    If the user has a pending SendRequest check if the message is a valid RGB
    invoice and, if so, try to send assets to it.

    If the user has a pending SendBtcRequest check if the message is a valid
    bitcoin address and, if so, try to send bitcoins to it.
    """
    with sett.Session() as session:
        user = _get_user(update, session)

        if not update.message.text:
            return
        user_input = update.message.text.strip()

        pending_ass_req, pending_btc_req = _get_pending_reqs(session, user)

        if not pending_ass_req and not pending_btc_req:
            return

        invoice_data, address = await _validate_user_input(
            update, user_input, pending_ass_req, pending_btc_req
        )

        LOGGER.info("Sending to %s for user %s", user_input, user.user_id)

        if invoice_data:
            await _send_to_invoice(update, session, user, invoice_data, user_input, pending_ass_req)
        elif address:
            await _send_to_address(update, session, user_input, pending_btc_req)


@_track_time
async def get_invoice_handler(update, _context):
    """Handle the /getinvoice command."""
    with sett.Session() as session:
        ongoing_purchase = (
            session.query(Purchase)
            .filter_by(chat_id=update.effective_chat.id, status=PurchaseStatus.PENDING)
            .first()
        )
        if ongoing_purchase:
            return await _reply(
                update,
                msgs.INVOICE_PENDING.format(invoice=ongoing_purchase.invoice),
            )

        LOGGER.info("Getting invoice for chat %s", update.effective_chat.id)
        try:
            invoice = get_invoice()
        except APIException:
            LOGGER.exception("LN invoice creation failed")
            return await _reply(update, msgs.RLN_REQUEST_FAILED)
        purchase = Purchase(invoice=invoice, chat_id=update.effective_chat.id)
        session.add(purchase)
        session.commit()
        await _reply(update, msgs.INVOICE_SEND.format(invoice=invoice))
