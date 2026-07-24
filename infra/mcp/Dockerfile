FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

EXPOSE 8000

# All runtime config comes from environment variables (see docker-compose.yaml).
# NEO4J_URL / NEO4J_USERNAME / NEO4J_PASSWORD / NEO4J_TRANSPORT=http / ...
CMD ["mcp-neo4j-cypher"]
