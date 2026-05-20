# RLN Telegram Bot — API alignment with rgb-lightning-node

This document compares **rln-telegram-bot** against **rgb-lightning-node** (`openapi.yaml`).

**Scope:** `ln.py`, `main.py`, `tasks.py`, `telegram_bot.py`, `utils.py`, `settings.py`.

---

## Summary

| Area | Status |
|------|--------|
| RLN HTTP endpoints | **Done** — aligned with current OpenAPI |
| `POST /sendrgb` | **Done** — `recipient_map` batch format |
| rgb-lib v0.3.0b20 | **Done** — local wheel in `source/` (gitignored) |
| `Testnet4` / `SignetCustom` | **Done** — `parse_network()` |
| Multi-schema `listassets` | **Done** — `find_asset_label()` (nia/uda/ifa/cfa) |
| Biscuit auth | **Done** — optional `RLN_AUTH_TOKEN` → `Authorization: Bearer` |
| Invoice statuses | **Done** — pending, claimable, claiming, succeeded, expired, cancelled, failed |
| Error handling | **Done** — `_request()`, `name` + message matching, HTTP status |
| User-facing API errors | **Done** — `APIException` → `RLN_REQUEST_FAILED` in handlers |

---

## RLN client (`ln.py`)

- Central `_request()` for all calls
- Optional `Authorization: Bearer <RLN_AUTH_TOKEN>`
- Parses JSON; maps `error` + `name` to bot exceptions
- `send_asset()` → `POST /sendrgb`

---

## Config

| Key | Required | Purpose |
|-----|----------|---------|
| `RLN_AUTH_TOKEN` | No | Biscuit token when node auth is enabled |

See `config.ini.sample`.

---

## rgb-lib

- Wheel: `source/rgb_lib-0.3.0b20-cp311-cp311-macosx_15_0_arm64.whl`
- Python `>=3.11,<3.12`
- Invoice validation via `rgb_lib.Invoice` / `invoice_data.network`

---

## Telegram commands

| Command | Status |
|---------|--------|
| `/start`, `/help`, `/getnodeinfo` | OK |
| `/getasset` (+ RGB invoice message) | OK — `/sendrgb` |
| `/getbtc` (+ address message) | OK — `/sendbtc` |
| `/getinvoice` | OK — `/lninvoice` + status polling |

---

## Optional future work

| Item | Notes |
|------|--------|
| `POST /decodergbinvoice` | Server-side invoice decode instead of rgb-lib |
| Linux Docker wheel | Add `manylinux` cp311 wheel under `source/` |

---

*Aligned with rgb-lightning-node `openapi.yaml` and implemented bot code.*
