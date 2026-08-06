FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry==2.3.2

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main,gateway --no-interaction --no-ansi --no-root

COPY src/ src/

# poetry install --no-root above skips installing the hulubul package itself
# (only its dependencies); put src/ on the path so `python -m hulubul...` resolves.
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "hulubul.channel_gateway.entrypoints.telegram_bot"]
