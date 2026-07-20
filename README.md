# hulubul-broker

An AI broker for ad-hoc package transport arrangements — an autonomous,
agent-driven parcel-brokerage service over a chat channel (Telegram in dev,
WhatsApp in prod) and a Neo4j graph system of record.

## Commands

`make help` prints the canonical target list. Three groups:

**Model generation** (LinkML source under `model/linkml/` → `model/generated/`):
- `make all` — lint + regenerate every artifact
- `make lint` — lint the LinkML schema
- `make pydantic` / `owl` / `shacl` / `jsonschema` / `erdiagram` / `plantuml` / `classdiagram` / `neo4j-constraints` / `neomodel` — regenerate a single artifact
- `make clean` — wipe `model/generated/`

**Docker** (Neo4j + MCP + Langflow + Postgres):
- `make up` / `down` / `down-volumes` / `rebuild` / `logs` / `ps`
- Prerequisite: `cp infra/.env.example infra/.env` (gitignored; edit passwords)

**Neo4j + MCP**:
- `make neo4j-schema` / `neo4j-seed` / `neo4j-queries` / `neo4j-reset` / `neo4j-shell` / `neo4j-browser`
- `make mcp-logs` / `mcp-restart`
