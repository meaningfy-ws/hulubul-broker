# Multistage, multi-target Dockerfile for the repo's Python service images.
# Build context is the repo root (see infra/docker-compose.yaml); select an
# image with `docker build --target <channel-gateway|mcp> -f infra/docker/Dockerfile .`

# ---------------------------------------------------------------------------
# channel-gateway
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS channel-gateway-builder

WORKDIR /app

RUN pip install poetry==2.3.2 \
    && poetry config virtualenvs.in-project true

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main,gateway --no-interaction --no-ansi --no-root

COPY hulubul/ hulubul/

FROM python:3.12-slim AS channel-gateway

RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

# Copy only the venv (runtime deps), not poetry itself or its own build-only
# dependency tree (poetry-core, cleo, etc.) — actually slims the image,
# unlike copying the builder's whole system-wide site-packages would.
COPY --from=channel-gateway-builder /app/.venv /app/.venv
COPY --from=channel-gateway-builder /app/hulubul /app/hulubul

# poetry install --no-root above skips installing the hulubul package itself
# (only its dependencies); put its top-level parent dir on the path so
# `python -m hulubul...` resolves. The venv's bin/ takes PATH priority so
# `python` resolves to the venv interpreter with its site-packages.
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

USER appuser
CMD ["python", "-m", "hulubul.channel_gateway.entrypoints.telegram_bot"]

# ---------------------------------------------------------------------------
# mcp (neo4j-labs/mcp-neo4j-cypher — third-party package, no local source)
# ---------------------------------------------------------------------------
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de AS mcp

RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

COPY infra/mcp/requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

EXPOSE 8000

# All runtime config comes from environment variables (see docker-compose.yaml).
# NEO4J_URL / NEO4J_USERNAME / NEO4J_PASSWORD / NEO4J_TRANSPORT=http / ...
USER appuser
CMD ["mcp-neo4j-cypher"]
