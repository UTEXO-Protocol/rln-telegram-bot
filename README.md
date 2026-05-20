# RGB Lightning Node Telegram Bot

Telegram bot to test RGB payments on the Lightning Network.

It requires a running instance of [rgb-lightning-node (RLN)].

It uses [UTEXO rgb-lib] Python bindings **v0.3.0-beta.20** from
[rgb-lib-python releases](https://github.com/UTEXO-Protocol/rgb-lib-python/releases/tag/v0.3.0-beta.20).
Python **3.11** is required (`cp311` wheels; platform picked automatically in `pyproject.toml`).

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
- `ASSET_ID` — RGB asset ID from `POST /issueassetnia` on your RLN node
- `LN_NODE_URL` — RLN HTTP API (e.g. `http://localhost:3001`)
- `LN_ANNOUNCEMENT_ADDR` — LN peer host:port (e.g. `127.0.0.1:9735` for local tests)

RLN must be **unlocked** and reachable. If authentication is enabled, set `RLN_AUTH_TOKEN`.

Install and run (macOS / Linux host):

```sh
poetry env use python3.11
poetry install
poetry run bot
```

`poetry install` downloads the matching rgb-lib wheel from GitHub (macOS arm64 or Linux manylinux).

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
poetry run pylint rgb_ln_telegram_bot
poetry run black rgb_ln_telegram_bot
poetry run isort --profile black rgb_ln_telegram_bot
poetry run vulture rgb_ln_telegram_bot
poetry run flake8 rgb_ln_telegram_bot
poetry run pip-audit
```

[poetry]: https://python-poetry.org/docs/
[rgb-lightning-node (RLN)]: https://github.com/UTEXO-Protocol/rgb-lightning-node
[UTEXO rgb-lib]: https://github.com/UTEXO-Protocol/rgb-lib
