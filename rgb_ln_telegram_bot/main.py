"""Entrypoint module."""

import html
import json
import traceback
from logging import getLogger
from logging.config import dictConfig

import requests
from telegram import Update
from telegram.constants import MessageLimit, ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from . import msgs
from . import settings as sett
from . import tasks
from .exceptions import APIException
from .ln import get_network_info, get_node_info, list_assets
from .telegram_bot import (
    get_asset_handler,
    get_btc_handler,
    get_invoice_handler,
    get_node_info_handler,
    help_handler,
    msg_handler,
    start_handler,
    unknown_command_handler,
)
from .utils import die, find_asset_label, parse_network

LOGGER = getLogger(__name__)


def main():
    """Start the bot."""
    dictConfig(sett.LOGGING)

    try:
        node_info = get_node_info()
    except requests.exceptions.ConnectionError:
        die("Cannot connect to the node")
    except APIException as exc:
        die(f"Cannot get node info: {exc}")
    sett.LIGHTNING_NODE_ID = node_info["pubkey"]
    sett.NODE_URI = f"{sett.LIGHTNING_NODE_ID}@{sett.LN_ANNOUNCEMENT_ADDR}"

    network_info = get_network_info()
    sett.NETWORK = parse_network(network_info["network"])

    assets = list_assets()
    sett.ASSET_TICKER = find_asset_label(assets, sett.ASSET_ID) or ""
    if not sett.ASSET_TICKER:
        die(f'Cannot find asset with ID "{sett.ASSET_ID}"')
    else:
        LOGGER.info('Found configured asset "%s"', sett.ASSET_TICKER)

    app = (
        Application.builder()
        .post_init(_post_init)
        .token(sett.API_TOKEN)
        .get_updates_connect_timeout(sett.TELEGRAM_TIMEOUT)
        .get_updates_pool_timeout(sett.TELEGRAM_TIMEOUT)
        .get_updates_read_timeout(sett.TELEGRAM_TIMEOUT)
        .get_updates_write_timeout(sett.TELEGRAM_TIMEOUT)
        .connect_timeout(sett.TELEGRAM_TIMEOUT)
        .pool_timeout(sett.TELEGRAM_TIMEOUT)
        .read_timeout(sett.TELEGRAM_TIMEOUT)
        .write_timeout(sett.TELEGRAM_TIMEOUT)
        .build()
    )

    app.add_handler(CommandHandler(sett.GETASSET_CMD, get_asset_handler))
    app.add_handler(CommandHandler(sett.GETBTC_CMD, get_btc_handler))
    app.add_handler(CommandHandler(sett.GETINVOICE_CMD, get_invoice_handler))
    app.add_handler(CommandHandler(sett.GETNODEINFO_CMD, get_node_info_handler))
    app.add_handler(CommandHandler(sett.HELP_CMD, help_handler))
    app.add_handler(CommandHandler(sett.START_CMD, start_handler))
    app.add_handler(MessageHandler(filters=filters.COMMAND, callback=unknown_command_handler))
    app.add_handler(MessageHandler(filters=filters.ALL, callback=msg_handler))

    app.job_queue.run_repeating(
        callback=tasks.get_invoice_check_task,
        interval=sett.INVOICE_TASK_INTERVAL,
        first=sett.INVOICE_TASK_FIRST,
    )

    app.job_queue.run_repeating(
        callback=tasks.node_checks,
        interval=sett.CHECKS_TASK_INTERVAL,
        first=sett.CHECKS_TASK_FIRST,
    )

    app.add_error_handler(_error_handler)

    app.run_polling()


async def _post_init(application):
    """Set up the bot commands and notify the developers the bot started."""
    await application.bot.set_my_commands(
        [
            (sett.START_CMD, "Show the welcome message"),
            (sett.HELP_CMD, "Show the help message"),
            (sett.GETINVOICE_CMD, "Get an RGB LN invoice"),
            (sett.GETASSET_CMD, "Get some RGB on-chain assets"),
            (sett.GETBTC_CMD, "Get some on-chain bitcoins"),
            (sett.GETNODEINFO_CMD, "Get info on the bot's RGB LN node"),
        ]
    )
    if (await application.bot.get_my_name()).name != sett.BOT_NAME:
        await application.bot.set_my_name(sett.BOT_NAME)
    await application.bot.set_my_description(sett.BOT_DESCRIPTION)
    await application.bot.set_my_short_description(sett.BOT_SHORT_DESCRIPTION)

    if sett.DEVELOPER_CHAT_ID:
        await application.bot.send_message(
            chat_id=sett.DEVELOPER_CHAT_ID,
            text="Bot started",
            parse_mode=ParseMode.HTML,
        )

    LOGGER.info("Start accepting commands")


async def _error_handler(update, context):
    """Log unhandled errors and notify the developers."""
    LOGGER.error("Exception while handling an update:", exc_info=context.error)

    if update:
        await update.message.reply_text(msgs.SOMETHING_WENT_WRONG)

    if not sett.DEVELOPER_CHAT_ID:
        return

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # avoid failing on too long messages
    if len(message) > MessageLimit.MAX_TEXT_LENGTH:
        message = msgs.MESSAGE_TOO_LONG

    await context.bot.send_message(
        chat_id=sett.DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML
    )


if __name__ == "main":
    main()
