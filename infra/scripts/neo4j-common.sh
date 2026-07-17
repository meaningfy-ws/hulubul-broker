#!/usr/bin/env bash
# Shared helpers for the Neo4j setup/seed scripts. Sourced, not executed.
# Keeps the docker-compose / cypher-shell invocation in one place so the
# Makefile targets and the standalone scripts never drift.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$INFRA_DIR/.." && pwd)"
ENV_FILE="$INFRA_DIR/.env"
COMPOSE_FILE="$INFRA_DIR/docker-compose.yaml"
CYPHER_DIR="$INFRA_DIR/cypher"

# Load infra/.env (gitignored) so NEO4J_USERNAME / NEO4J_PASSWORD are exported.
load_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "Missing $ENV_FILE. Run: cp infra/.env.example infra/.env" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  : "${NEO4J_USERNAME:=neo4j}"
  : "${NEO4J_PASSWORD:?NEO4J_PASSWORD must be set in $ENV_FILE}"
}

# Run a cypher file into Neo4j via the cypher-shell bundled in the neo4j image.
neo4j_exec_file() {
  local file="$1"
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T \
    --env NEO4J_USERNAME="${NEO4J_USERNAME}" \
    --env NEO4J_PASSWORD="${NEO4J_PASSWORD}" \
    neo4j cypher-shell --format plain < "$file"
}

# Block until Neo4j accepts Bolt connections with the configured credentials.
neo4j_wait() {
  echo "Waiting for Neo4j to accept Bolt connections..." >&2
  local tries=60 i
  for ((i = 1; i <= tries; i++)); do
    if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T \
        --env NEO4J_USERNAME="${NEO4J_USERNAME}" \
        --env NEO4J_PASSWORD="${NEO4J_PASSWORD}" \
        neo4j cypher-shell --format plain 'RETURN 1' >/dev/null 2>&1; then
      echo "Neo4j is ready." >&2
      return 0
    fi
    sleep 2
  done
  echo "Neo4j did not become ready in time. Check: make logs" >&2
  return 1
}
