# RGB Lightning Node Telegram Bot

Telegram bot to test RGB payments on the Lightning Network.

It requires an unlocked [rgb-lightning-node (RLN)] deployed separately by DevOps.
The supported development revision is
**`89ebe9fdb1be94cbba0b2bd722cea9af297399f1`** from
[PR #212](https://github.com/UTEXO-Protocol/rgb-lightning-node/pull/212).

Python **3.11** is required. RGB invoice decoding is performed by RLN itself;
the bot no longer depends on platform-specific `rgb-lib` Python wheels.
Bitcoin address checks use `embit` (Base58Check, Bech32 and Bech32m).

## Build and run

Clone the project:

```sh
git clone https://github.com/UTEXO-Protocol/rln-telegram-bot
cd rln-telegram-bot
```

Obtain a Telegram API token from [@BotFather](https://t.me/BotFather) (`/newbot`).

Copy and edit config:

```sh
cp config.ini.sample config.ini
```

Set at least:

- `API_TOKEN` — Telegram bot token
- `ASSET_ID` — a funded fungible RGB asset ID known to your RLN node
- `LN_NODE_URL` — RLN HTTP API (e.g. `http://localhost:3001`)
- `LN_ANNOUNCEMENT_ADDR` — LN peer host:port (e.g. `127.0.0.1:9735` for local tests)

RLN must be funded, **unlocked** and reachable. If authentication is enabled,
set `RLN_AUTH_TOKEN`. Settings are read from `config.ini`; `.env` is not loaded.
The bot connects to this external node over HTTP and does not build or start it.

Use the protocol-1-compatible RGB proxy required by PR #212. BFA assets require
`eth_rpc_url` configured on each participating RLN node. Mainnet Lightning is
disabled in this RLN revision.

Install and run (macOS / Linux host):

```sh
poetry env use python3.11
poetry install
poetry run bot
```

## Docker

Build:

```sh
docker build -t rln-telegram-bot .
```

Run (RLN on the host — not `localhost` inside the container):

```sh
# use host.docker.internal in config.ini for LN_NODE_URL when RLN runs on the Mac/PC host
docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  -v "$(pwd)/config.ini:/app/config.ini:ro" \
  -v "$(pwd)/data:/app/data:rw" \
  rln-telegram-bot
```

Example `config.ini` for Docker on macOS:

```ini
LN_NODE_URL=http://host.docker.internal:3001
```

## Develop

```sh
poetry run python -m unittest discover -s tests -v
poetry run pylint rgb_ln_telegram_bot
poetry run black rgb_ln_telegram_bot
poetry run isort --profile black rgb_ln_telegram_bot
poetry run vulture rgb_ln_telegram_bot
poetry run flake8 rgb_ln_telegram_bot
poetry run pip-audit
```

The tests use temporary configuration and SQLite databases; they do not read
your `config.ini` or connect to Telegram.

[poetry]: https://python-poetry.org/docs/
[rgb-lightning-node (RLN)]: https://github.com/UTEXO-Protocol/rgb-lightning-node
