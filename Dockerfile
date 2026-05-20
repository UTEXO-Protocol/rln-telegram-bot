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

COPY . .

# UTEXO rgb-lib: place a manylinux cp311 wheel in source/, or pass RGB_LIB_WHEEL_URL
ARG RGB_LIB_WHEEL_URL=
RUN if ls source/rgb_lib-*-manylinux_*.whl >/dev/null 2>&1; then \
        pip install source/rgb_lib-*-manylinux_*.whl; \
    elif [ -n "$RGB_LIB_WHEEL_URL" ]; then \
        pip install "$RGB_LIB_WHEEL_URL"; \
    else \
        echo "No Linux rgb-lib wheel in source/ and RGB_LIB_WHEEL_URL is unset" >&2; exit 1; \
    fi

RUN poetry install --no-interaction --no-cache --without dev

CMD [ "poetry", "run", "bot" ]
