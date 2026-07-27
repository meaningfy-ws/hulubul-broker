# Single-purpose image: the Telegram channel-gateway service only.
# Build context is the repo root (see infra/docker-compose.yaml):
#   docker build -f infra/docker/channel-gateway/Dockerfile .

FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install poetry==2.3.2 \
    && poetry config virtualenvs.in-project true

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main,gateway --no-interaction --no-ansi --no-root

COPY hulubul/ hulubul/

FROM python:3.12-slim

RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

# Copy only the venv (runtime deps), not poetry itself or its own build-only
# dependency tree (poetry-core, cleo, etc.) — actually slims the image,
# unlike copying the builder's whole system-wide site-packages would.
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/hulubul /app/hulubul

# poetry install --no-root above skips installing the hulubul package itself
# (only its dependencies); put its top-level parent dir on the path so
# `python -m hulubul...` resolves. The venv's bin/ takes PATH priority so
# `python` resolves to the venv interpreter with its site-packages.
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

USER appuser
CMD ["python", "-m", "hulubul.channel_gateway.entrypoints.telegram_bot"]
