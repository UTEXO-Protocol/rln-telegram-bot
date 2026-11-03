"""Import the bot with a temporary config and database, never the operator's config."""

import atexit
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock

if "rgb_ln_telegram_bot.settings" in sys.modules:
    raise RuntimeError("Import tests.support before bot modules to isolate configuration and data")

_TEMP = TemporaryDirectory(prefix="rln-bot-test-")
atexit.register(_TEMP.cleanup)
_ROOT = Path(__file__).resolve().parents[1]
_CONFIG = (_ROOT / "config.ini.sample").read_text(encoding="utf-8")
_CONFIG = _CONFIG.replace("DATA_DIR=data", f"DATA_DIR={_TEMP.name}/data")
_CONFIG = _CONFIG.replace("http://localhost:3001", "http://127.0.0.1:9")
_CONFIG = _CONFIG.replace("DEVELOPER_CHAT_ID=YourDeveloperChatID", "DEVELOPER_CHAT_ID=")
Path(_TEMP.name, "config.ini").write_text(_CONFIG, encoding="utf-8")
_CWD = os.getcwd()
try:
    os.chdir(_TEMP.name)
    from rgb_ln_telegram_bot import settings
finally:
    os.chdir(_CWD)

settings.NETWORK = "Regtest"
settings.FEE_RATE = 1


def fake_update(text="", user_id=123):
    """Telegram-shaped input with local async mocks for every outgoing message."""
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=user_id),
        message=SimpleNamespace(text=text, reply_text=AsyncMock()),
    )


def fake_context():
    """Capture replies and stickers without creating a Telegram client."""
    return SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock(), send_sticker=AsyncMock()))
