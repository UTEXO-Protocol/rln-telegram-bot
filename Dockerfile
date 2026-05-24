# syntax=docker/dockerfile:1.7

# ---- Builder ----
FROM python:3.11-slim-trixie AS builder

ENV POETRY_VERSION=2.2.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /app

COPY pyproject.toml poetry.lock README.md ./
COPY rgb_ln_telegram_bot ./rgb_ln_telegram_bot

RUN poetry install --no-interaction --no-cache --without dev \
    && /app/.venv/bin/pip uninstall -y pip setuptools wheel 2>/dev/null || true \
    && find /app/.venv -depth -type d -name '__pycache__' -exec rm -rf {} + \
    && find /app/.venv -type f -name '*.pyc' -delete \
    && find /app/.venv -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true

# ---- Runtime ----
FROM python:3.11-slim-trixie AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/rgb_ln_telegram_bot /app/rgb_ln_telegram_bot

CMD ["bot"]
