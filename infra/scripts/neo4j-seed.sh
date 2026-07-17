#!/usr/bin/env bash
# Load deterministic Hulubul demo data (infra/cypher/seed.cypher) into Neo4j.
# Idempotent: every node/relationship is MERGEd by its graph id, so re-running
# is safe and produces the same fixture set. Requires schema to be applied first
# (make neo4j-schema).
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/neo4j-common.sh"

load_env
neo4j_wait

echo "Loading seed data from infra/cypher/seed.cypher..."
neo4j_exec_file "$CYPHER_DIR/seed.cypher"
echo "Seed loaded."
