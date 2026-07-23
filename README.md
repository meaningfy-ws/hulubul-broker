# hulubul-broker

An AI broker for ad-hoc package transport arrangements — an autonomous,
agent-driven parcel-brokerage service over a chat channel (Telegram in dev,
WhatsApp in prod) and a Neo4j graph system of record.

## Setup

Install dependencies with Poetry:

```bash
make install                                # Install base + test + quality groups
poetry install --with test --with quality  # Same as above (explicit Poetry syntax)
poetry install --with test --with quality --with langflow --with integration  # All groups
```

Dependencies are split into optional groups:
- `test` — pytest, pytest-bdd, pytest-cov for unit and BDD testing
- `quality` — import-linter, ruff, mypy, tox for static analysis and linting
- `integration` — httpx, neo4j driver, testcontainers for integration tests
- `langflow` — LangFlow SDK (lfx) for flow-as-code tooling

## Development workflow

`make help` prints all targets. Key groups:

**Python testing & quality**:
- `make test-unit` — run unit tests with 80% coverage enforcement
- `make lint-python` — run ruff linter
- `make format-check-python` — check formatting with ruff
- `make typecheck` — run mypy type checker
- `make check-architecture` — validate import boundaries with import-linter
- `make ci-static` — run the full static quality gate (all of the above + model checks)

**Commands**

`make help` prints the canonical target list. Four groups:

**Model generation** (LinkML source under `model/linkml/` → `model/generated/`):
- `make all` — lint + regenerate every artifact
- `make lint` — lint the LinkML schema
- `make pydantic` / `owl` / `shacl` / `jsonschema` / `erdiagram` / `plantuml` / `classdiagram` / `neo4j-constraints` / `neomodel` — regenerate a single artifact
- `make clean` — wipe `model/generated/`

**Docker** (Neo4j + MCP + Langflow + Postgres):
- `make up` / `down` / `down-volumes` / `rebuild` / `logs` / `ps`
- Prerequisite: `cp infra/.env.example infra/.env` (gitignored; edit passwords)

**Neo4j + MCP**:
- `make neo4j-schema` / `make neo4j-seed` / `make neo4j-queries` / `make neo4j-reset` / `make neo4j-shell` / `make neo4j-browser`
- `make mcp-logs` / `make mcp-restart`

**CI/CD**:
- `make ci` — full CI pipeline (static quality + model + schema + secrets checks)
- GitHub Actions runs on every push to `main` and on pull requests, executing `make install && make ci-static`

## Project structure

```
.
├── model/linkml/              # LinkML domain model (source of truth)
├── model/generated/           # Generated artifacts (Pydantic, Cypher, diagrams, etc.)
├── src/hulubul/               # Python application code
├── tests/                     # Unit, integration, and BDD tests
├── scripts/                   # Custom LinkML generators & utilities
├── infra/                     # Docker Compose, Neo4j, MCP, LangFlow
├── architecture/              # Design documents & ADRs
├── .github/workflows/ci.yaml  # GitHub Actions CI pipeline
├── Makefile                   # Build & development automation
├── pyproject.toml             # Poetry: dependencies, pytest, coverage, linting config
├── tox.ini                    # Tox: test environments (py310, architecture, schemas, integration, etc.)
└── README.md                  # This file
```

## LinkML schema as source of truth

The LinkML domain model under `model/linkml/` is the single source of truth. Generated artifacts
(Pydantic, Neo4j constraints, Cypher queries, Mermaid diagrams, JSON Schema, etc.) under `model/generated/`
are deterministic outputs—never edit them by hand. Regenerate with `make all` after schema changes.

Generated artifacts are committed to Git to ensure they stay in sync with the schema.
