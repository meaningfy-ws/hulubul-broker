# AGENTS.md

Guidance for AI coding assistants (opencode, Claude Code, etc.) working in this
repository.

## Project purpose

Hulubul is an **autonomous, agent-driven parcel-brokerage service**: it turns a
Sender's intention into a structured Parcel Request, matches it to transporters,
and carries the communication through pick-up and delivery — over a chat channel
(Telegram in dev, WhatsApp in prod), on a **Neo4j graph** system of record.

The project is in a **conceptual / design / early scaffolding phase**: the LinkML
domain model and the local infrastructure stack exist, but the application code
under `src/hulubul/` is not yet written. Architecture documents under
`architecture/` describe the target system and an incremental (Phase 1–4)
build-up plan.

## Important commands

`make help` prints the canonical target list. Three groups:

**Model generation** (LinkML source under `model/linkml/` → `model/generated/`):
- `make all` — lint + regenerate every artifact
- `make lint` — lint the LinkML schema (note: this is `linkml-lint`, not Python linting)
- `make pydantic` / `owl` / `shacl` / `jsonschema` / `erdiagram` / `plantuml` / `classdiagram` / `neo4j-constraints` / `neomodel` — regenerate a single artifact
- `make clean` — wipe `model/generated/`

**Docker** (Neo4j + MCP + Langflow + Postgres):
- `make up` / `down` / `down-volumes` / `rebuild` / `logs` / `ps`
- Prerequisite: `cp infra/.env.example infra/.env` (gitignored; edit passwords)

**Neo4j + MCP**:
- `make neo4j-schema` / `neo4j-seed` / `neo4j-queries` / `neo4j-reset` / `neo4j-shell` / `neo4j-browser`
- `make mcp-logs` / `mcp-restart`

## Top-level architecture

| Path | Role |
|------|------|
| `model/linkml/` | **Source of truth** — LinkML schema (six domain modules over a common base) |
| `model/generated/` | Deterministic outputs (Pydantic, OWL, SHACL, JSON Schema, diagrams, Cypher, neomodel). Never hand-edit. |
| `model/modelspecs/` | Human-authored source specs the model was derived from (provenance) |
| `infra/` | Local stack: `docker-compose.yaml` (Neo4j + mcp-neo4j-cypher + Langflow + Postgres), cypher scripts, MCP Dockerfile |
| `architecture/` | Design documents: project statement, ADRs, use cases, blueprints, NFRs, incremental strategy |
| `scripts/` | Custom LinkML generators (`gen_neo4j_constraints.py`, `gen_neomodel.py`, `gen_mermaid_classdiagram.py`) |
| `src/hulubul/` | Application code (not yet written) |

### Visible conventions

- **LinkML is the single source of truth.** Files under `model/generated/` are
  produced by `make` and must never be hand-edited; the next `make` overwrites
  them. Commit generated artifacts in the same commit as the schema edit.
- **Secrets never live in VCS.** `infra/.env` is gitignored; copy from
  `infra/.env.example` and edit passwords (Neo4j password ≥ 8 characters).
- **`make lint` is schema linting** (`linkml-lint`), not Python linting — there
  is no Python application code or test suite yet.
- **Generated artifacts are committed** so they stay in sync with the schema; a
  CI drift check can re-run `make all` and fail on diff. Caveat: OWL and SHACL
  Turtle output is not byte-stable across runs (rdflib reorders blank nodes),
  so exclude those from a naive diff check.

## What could not be established

- `src/hulubul/` is empty — the actual Python application layout is not yet
  written.
- No `tests/` directory exists at repo root; the testing strategy is documented
  in `architecture/verification-testing-and-evaluation-strategy.md` but not yet
  implemented.
- No CI workflows, `make install`, `make test`, or `make ci` targets exist yet —
  only model-generation, Docker, and Neo4j/MCP targets.

## Local developer overrides

An optional, git-ignored tier of instructions is imported below. If the file
does not exist, the import is skipped. Anything it contains is local-only and
must never surface in commits, PRs, code, comments, or docs.

@AGENTS.local.md
