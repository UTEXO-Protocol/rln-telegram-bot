"""Settings module."""

import os
import pathlib

from rgb_ln_telegram_bot.database import init_db_session
from rgb_ln_telegram_bot.utils import get_or_default, get_or_exit, parse_config

BOT_NAME = "RGB LN Bot"
BOT_DESCRIPTION = """
This bot is intended to be used to test RGB on Lightning Network.
It allows you to request some bitcoins and RGB assets and to use them to open \
a channel with the bot's node and to perform payments towards the bot.
"""
BOT_SHORT_DESCRIPTION = "Bot to test RGB payments on the LN"

GETASSET_CMD = "getasset"
GETBTC_CMD = "getbtc"
GETINVOICE_CMD = "getinvoice"
GETNODEINFO_CMD = "getnodeinfo"
HELP_CMD = "help"
START_CMD = "start"

REQUESTS_TIMEOUT = 30
TELEGRAM_TIMEOUT = 30

INVOICE_TASK_FIRST = 10
INVOICE_TASK_INTERVAL = 20
CHECKS_TASK_FIRST = 10
CHECKS_TASK_INTERVAL = 120

HTLC_MIN_MSAT = 3000000

MAX_SUCCESSFUL_INTERACTIONS_PER_DAY = 2  # for DoS prevention

STICKERS = [
    "CAACAgIAAxkBAAEmVJtlE_Vt_Zd66JpWjIDMyrRc3ZSvVQAC7xIAAvoRcUqeiC7y475i6jAE",
    "CAACAgIAAxkBAAEmVLdlE_ddPwjhGsilktAYjy4S11fi4gACIgADkP2aFWEdcLe06H36MAQ",
    "CAACAgIAAxkBAAEmVLllE_d2O6hRIrANSPmNGc6WJzgJYgACDAADkP2aFZ9oJ0jCaOrRMAQ",
    "CAACAgIAAxkBAAEmVLtlE_eao_tC8MN8EHVsjfpJDDIt9wACiAIAAkcVaAkNL7KdtavmWDAE",
    "CAACAgIAAxkBAAEmVO9lE_vCoU2AdHOoMlx9DkGbzlzHGAACFgADkP2aFRYdIyUluYSFMAQ",
    "CAACAgIAAxkBAAEmVPNlE_vg3t36jlVBCalGP8jCpAWEnQACigIAAkcVaAkO1Lftas8KSTAE",
    "CAACAgIAAxkBAAEmVPdlE_v5_0_a4XgCBEkqJYv6QSR-PwACEAADkP2aFThJcfEhi9-tMAQ",
    "CAACAgIAAxkBAAEmVPtlE_xPw9Aane5agsHmOCRaTijQXwACfwMAAkcVaAnlyInLm7w8ETAE",
]

MIN_ASSET_BALANCE = 10000
MIN_BTC_BALANCE = 500000000  # 5 BTCs

conf = parse_config()
API_TOKEN = get_or_exit(conf, "API_TOKEN")
DATA_DIR = get_or_exit(conf, "DATA_DIR")
LN_NODE_URL = get_or_exit(conf, "LN_NODE_URL")
LN_ANNOUNCEMENT_ADDR = get_or_exit(conf, "LN_ANNOUNCEMENT_ADDR")
ASSET_ID = get_or_exit(conf, "ASSET_ID")
ASSET_AMOUNT_TO_SEND = get_or_exit(conf, "ASSET_AMOUNT_TO_SEND", integer=True)
SAT_AMOUNT_TO_SEND = get_or_exit(conf, "SAT_AMOUNT_TO_SEND", integer=True)
INVOICE_EXPIRATION_SEC = get_or_exit(conf, "INVOICE_EXPIRATION_SEC", integer=True)
INVOICE_PRICE = get_or_exit(conf, "INVOICE_PRICE", integer=True)
UTXOS_TO_CREATE = get_or_exit(conf, "UTXOS_TO_CREATE", integer=True)
FEE_RATE = get_or_exit(conf, "FEE_RATE", integer=True)
DEVELOPER_CHAT_ID = get_or_default(conf, "DEVELOPER_CHAT_ID", "")
RLN_AUTH_TOKEN = get_or_default(conf, "RLN_AUTH_TOKEN", "")
LOG_LEVEL_CONSOLE = get_or_default(conf, "LOG_LEVEL_CONSOLE", "INFO")

# vars set at runtime
LIGHTNING_NODE_ID = ""
NETWORK = None
NODE_URI = ""
ASSET_TICKER = ""

pathlib.Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
DATABASE_URI = f"sqlite:///{DATA_DIR}/db.sqlite"
Session = init_db_session(DATABASE_URI)

LOG_TIMEFMT = "%Y-%m-%d %H:%M:%S %z"
LOG_TIMEFMT_SIMPLE = "%d %b %H:%M:%S"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)-8s %(message)s [%(name)s:%(lineno)s]",
            "datefmt": LOG_TIMEFMT,
        },
        "simple": {
            "format": "[%(asctime)s] %(levelname)-8s %(message)s",
            "datefmt": LOG_TIMEFMT_SIMPLE,
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL_CONSOLE,
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(DATA_DIR, "bot.log"),
            "maxBytes": 1048576,
            "backupCount": 12,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
        },
    },
}
