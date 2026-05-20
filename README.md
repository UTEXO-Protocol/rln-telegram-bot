# RGB Lightning Node Telegram Bot

Telegram bot to test RGB payments on the Lightning Network.

It requires a running instance of [rgb-lightning-node (RLN)].

It uses [UTEXO rgb-lib] Python bindings **v0.3.0-beta.20** (aligned with
[utexo-rgb-lib]), vendored as a wheel under `source/`. Python **3.11** is
required (`cp311` wheel).

## Build and run

First, clone the project:
```sh
git clone https://github.com/RGB-Tools/rln-telegram-bot
```

Then obtain an API token that is necessary to create the Telegram bot.
The token can be obtained by contacting `@BotFather` on Telegram, issuing
the `/newbot` command and following the steps.

Once you obtained the token you can copy the sample config file (`cp
config.ini.sample config.ini`) and set the `API_TOKEN` key to its value.

Then, issue an asset on your RGB LN node, set the `ASSET_ID` key of the
config file to its ID, set the `LN_NODE_URL` so the bot can call the RGN LN
node APIs, set the `LN_ANNOUNCEMENT_ADDR` to the public LN endpoint of the RGN
LN node and optionally set the other keys to suit your needs. The RLN LN node
needs to be reachable at the provided URL and unlocked for the bot to work.
If the node uses Biscuit authentication, set `RLN_AUTH_TOKEN` in `config.ini`.

Finally, provided you have **Python 3.11** and [poetry] installed, install
dependencies and run the bot:
```sh
poetry env use python3.11   # cp311 wheel
poetry lock                 # refresh lock after rgb-lib URL change
poetry install
poetry run bot
```

The macOS arm64 wheel lives at
`source/rgb_lib-0.3.0b20-cp311-cp311-macosx_15_0_arm64.whl` and is referenced from
`pyproject.toml` (wheels are gitignored; copy yours into `source/` after clone). For **Docker/Linux**, add a matching `manylinux` wheel under
`source/` or pass `RGB_LIB_WHEEL_URL` at image build time.

The docker image can be built with:
```sh
docker build -t rln-telegram-bot .
```

The docker image can be run with:
```sh
docker run \
    -v ./config.ini:/app/config.ini:ro \
    -v ./data:/app/data:rw \
    rln-telegram-bot
```

## Develop

When developing, you can run the following utilities:
```sh
# lint code
poetry run pylint rgb_ln_telegram_bot

# format code
poetry run black rgb_ln_telegram_bot

# sort imports
poetry run isort --profile black rgb_ln_telegram_bot

# find unused code
poetry run vulture rgb_ln_telegram_bot

# check compliance with docstring conventions
poetry run flake8 rgb_ln_telegram_bot

# check for known vulnerabilities
poetry run pip-audit
```


[poetry]: https://python-poetry.org/docs/
[rgb-lightning-node (RLN)]: https://github.com/RGB-Tools/rgb-lightning-node
[UTEXO rgb-lib]: https://github.com/UTEXO-Protocol/rgb-lib
[utexo-rgb-lib]: https://github.com/UTEXO-Protocol/rgb-lib
[rgb-lib-python release wheels]: https://github.com/UTEXO-Protocol/rgb-lib-python/releases/tag/v0.3.0-beta.20
