FROM python:3.11-slim-trixie

ENV POETRY_VERSION=2.2.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

RUN apt-get update \
    && apt-get install -y --no-install-recommends libssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /app

COPY pyproject.toml poetry.lock README.md ./
COPY rgb_ln_telegram_bot ./rgb_ln_telegram_bot

# rgb-lib: platform-specific wheel URLs in pyproject.toml (linux arm64/amd64, macOS arm64)
RUN poetry install --no-interaction --no-cache --without dev

CMD [ "poetry", "run", "bot" ]
