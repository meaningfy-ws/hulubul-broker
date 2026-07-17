#!/usr/bin/env bash
# Apply the Hulubul Neo4j schema: uniqueness constraints (Community-safe subset
# of model/generated/neo4j/constraints.cypher) plus range indexes on hot query
# properties. Idempotent (every statement is IF NOT EXISTS). Requires a running
# Neo4j (make up).
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/neo4j-common.sh"

load_env
neo4j_wait

echo "Applying schema from infra/cypher/schema.cypher..."
neo4j_exec_file "$CYPHER_DIR/schema.cypher"
echo "Schema applied."
