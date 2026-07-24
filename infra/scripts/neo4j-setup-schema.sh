#!/usr/bin/env bash
# Apply the Hulubul Neo4j schema: uniqueness constraints (Community-safe subset
# of model/generated/neo4j/constraints.cypher) plus range indexes on hot query
# properties. Idempotent (every statement is IF NOT EXISTS). Requires a running
# Neo4j (make up).
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/neo4j-common.sh"

load_env
neo4j_wait

echo "Applying domain schema from infra/cypher/schema.cypher..."
neo4j_exec_file "$CYPHER_DIR/schema.cypher"

echo "Applying operational schema from infra/cypher/operational-schema.cypher..."
neo4j_exec_file "$CYPHER_DIR/operational-schema.cypher"

echo "Waiting for indexes to be ready..."
neo4j_exec_file <(echo "CALL db.awaitIndexes(120)")

echo "All schemas applied."
