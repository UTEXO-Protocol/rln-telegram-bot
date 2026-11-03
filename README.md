# RGB Lightning Node Telegram Bot

Telegram bot to test RGB payments on the Lightning Network.

It requires an unlocked [rgb-lightning-node (RLN)] from
[PR #212](https://github.com/UTEXO-Protocol/rgb-lightning-node/pull/212), pinned to
**`89ebe9fdb1be94cbba0b2bd722cea9af297399f1`** in [`rln-revision`](rln-revision).
This is a development revision, also used by the LSP migration.

Python **3.11** is required. RGB invoice decoding is performed by RLN itself;
the bot no longer depends on platform-specific `rgb-lib` Python wheels.
Bitcoin address checks use `embit` (Base58Check, Bech32 and Bech32m).

## RLN compatibility

Build the pinned node using the Rust/toolchain prerequisites in RLN's README:

```sh
bash scripts/build-rln.sh
# Binary: .rln/target/release/rgb-lightning-node
# Configure, fund and unlock this node before running the bot.
```

The script uses a dedicated `.rln` checkout and refuses to overwrite local changes.
An existing node built at the same revision can be used instead. `LN_NODE_URL`
selects the external node; installing or deploying the bot does not upgrade that
node. RLN's HTTP API does not report its Git revision, so verify the node build
against `rln-revision` when deploying. The bot image includes this pin at
`/app/rln-revision`.

| Bot behavior | PR #212 API |
| --- | --- |
| RGB invoice validation | `/decodergbinvoice` on the configured node |
| `/getasset` faucet | `/sendrgbinvoice` with the original invoice, including proxy keys, encryption and expiry |
| Transfer refresh | `/refreshtransfers` with `filter: []` |
| `/getbtc` faucet | `/sendbtc` |
| `/getinvoice` purchase | `/lninvoice`, then `/invoicestatus`; deliver after `Succeeded` |
| Configured asset lookup | NIA, UDA, IFA, CFA and BFA list buckets |

RGB faucet payouts remain fungible, blind-receive transfers with a fixed configured
amount. The invoice must use the node's network, request the configured asset
(or leave it unspecified), and request the configured amount (or use `Any`/zero).
Expired and witness invoices are rejected. The full invoice is also stored for
duplicate checks. Commands, daily faucet limits and ordinary auto-claim LN
purchases are retained; this does not add an APay command.

Use the protocol-1-compatible RGB proxy required by PR #212 (RGB proxy 0.4.0 in
the tested regtest setup). Existing wallets and invoices from older RGB versions
must follow the upstream migration instructions. Mainnet Lightning is disabled
in this RLN revision. BFA requires a funded bridged asset and a working
`eth_rpc_url` configured on **each participating RLN node**; this is node
configuration, not a Telegram bot option. The regtest flow below covers IFA;
BFA asset lookup is covered by the offline tests, not a live bridge test.

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

RLN must be **unlocked** and reachable. If authentication is enabled, set `RLN_AUTH_TOKEN`.

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

### Headless regtest flow

Use two unlocked nodes at the pinned RLN revision on the same regtest chain, with
a usable RGB Lightning channel for the configured asset. The bot node needs
spendable on-chain RGB and BTC; the peer needs a free RGB allocation and outbound
channel liquidity for at least 1 asset base unit and 3,000 sats. Bitcoin Core must
have a loaded mining wallet and both nodes must use the same protocol-1 proxy.

```sh
poetry run python -m tests.regtest \
  --bot-node http://127.0.0.1:3005 \
  --peer-node http://127.0.0.1:3020 \
  --asset-id 'YOUR_REGTEST_ASSET_ID' \
  --bitcoin-rpc http://127.0.0.1:18443/wallet/miner
```

This opt-in test sends 42 RGB base units and 50,000 sats from the bot node to the
peer, mines blocks, and pays a 1-unit/3,000-sat LN purchase from the peer to the
bot. It runs the actual command/message handlers and purchase polling task with
mock Telegram replies, checks both RGB settlements and balance changes, confirms
the BTC output, verifies the LN preimage and checks exactly one delivery.
It refuses non-regtest nodes and Bitcoin Core, uses a temporary bot database,
and writes evidence to `logs/regtest.json`. It does not start or reset nodes.
Use `--help` for proxy and RPC options; `REGTEST_RPC_USER`/`REGTEST_RPC_PASSWORD`
override the local `user`/`password` RPC defaults. Authentication is assumed
disabled on these isolated test nodes.

[poetry]: https://python-poetry.org/docs/
[rgb-lightning-node (RLN)]: https://github.com/UTEXO-Protocol/rgb-lightning-node
