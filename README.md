# hulubul-broker

An AI broker for ad-hoc package transport arrangements — an autonomous,
agent-driven parcel-brokerage service over a chat channel (Telegram in dev,
WhatsApp in prod) and a Neo4j graph system of record.

## How the project is put together

The repository is organised around five concerns, each with its own directory
and its own rules.

**The domain model is the single source of truth** (`model/`). A LinkML schema
under `model/linkml/` defines what a delivery request, a party, a transport
service and a location are. Everything under `model/generated/` — Pydantic
classes, OWL, SHACL, JSON Schema, Neo4j constraints, neomodel OGM classes,
diagrams — is produced from it by `make`. Meaning changes in one place and
propagates outward.

**Agent behaviour and workflows live in flows, backed by Python** (`langflow/`,
`src/hulubul/`). LangFlow flows under `langflow/flows/` are the executable
orchestration; `langflow/flow-manifest.yaml` — not LangFlow's own database — is
authoritative for which flows exist and in what order they deploy. The Python
package under `src/hulubul/` supplies the custom LangFlow components and the
domain logic behind them, laid out in `core/` (shared) plus feature sub-modules,
each following the `models` / `services` / `entrypoints` layering enforced by
import-linter.

| File | Flow | What it does |
|------|------|---------------|
| `10-lf-70-data-access.json` | LF-70 Data Access | Validates a typed `DataOperationRequest`, executes it via the Data Access Agent against Neo4j MCP, returns a validated `DataOperationResult`. |
| `20-lf-10-request-intake.json` | LF-10 Request Intake | Validates a typed `IntakeInput`, extracts intake facts via the Request Intake Agent using LF-70 as a tool, returns a validated `IntakeResult`. |
| `30-lf-00-main-router.json` | LF-00 Main Router | Validates trusted chat input, prefetches routing context from LF-70, routes to LF-10 for intake-eligible states, renders a deterministic `RouterResult` to Chat Output. This is the deployed entry point. |
| `lf-10-70-merged-demo-1.json` | — | Demo/debug artifact, not in the manifest and not deployed by `make langflow-deploy`. Kept for reference only. |

**Flows exchange versioned contracts** (`src/hulubul/core/models/operational/`,
`schemas/`). The payloads flows pass to one another are defined as Pydantic
models, which are what actually validate a payload at runtime. Those models are
also published as language-neutral JSON Schema under `schemas/operational/v1/`,
generated and version-stamped so the contract can be read, diffed and consumed
without running the Python.

**The runtime lives in Docker** (`infra/`). A Compose stack brings up LangFlow
(orchestration), Neo4j Community with APOC (the graph system of record), a Neo4j
MCP server (the only channel through which agents reach the graph), and Postgres
(LangFlow's own metadata store). Cypher for schema and demo data lives alongside
it.

**Design intent is written down** (`architecture/`). The project and
architecture statements, ADRs, use cases (Cockburn white/blue), the agentic
system blueprint, non-functional requirements, the incremental development
strategy, and the verification, testing and evaluation strategy.

### Agentic development

This project is built *with* AI coding agents as much as it builds an AI system,
and that collaboration is governed rather than ad hoc. `AGENTS.md` (symlinked as
`CLAUDE.md`) carries the instructions any coding agent picks up on entry, and
`openspec/` holds the specification spine: proposals, designs and task
breakdowns are authored and reviewed as artifacts before implementation starts,
with the `/opsx:*` commands under `.claude/` and `.opencode/` driving that
workflow. The intent is that a change is specified, agreed and traceable first —
so agent-generated work lands against a written contract instead of a prompt.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | `>=3.10,<3.15` | CI runs 3.10 |
| Poetry | 2.3.2 | version pinned by CI; install with `pipx install poetry==2.3.2` |
| Docker Engine + Compose v2 | recent | `docker compose` (not `docker-compose`) |
| GNU Make + bash | — | every workflow goes through `make` |
| An OpenAI-compatible LLM endpoint | — | base URL, model name and API key; required to *run* flows, not to build or test |

## Setup

### Quick start

From a fresh clone to a running stack with flows deployed:

```bash
cp infra/.env.example infra/.env                    # 1. edit passwords
cp infra/langflow.env.example infra/langflow.env    # 2. edit LLM settings
make install                                        # 3. Python dependencies
make up                                             # 4. start the Docker stack
make neo4j-schema                                   # 5. constraints + indexes
make neo4j-seed                                     # 6. demo data (optional — see below)
                                                    # 7. deploy the flows (see below)
```

### 1. Environment files

Both files are gitignored and must be created from their examples before
anything else — `make up` fails without them.

```bash
cp infra/.env.example infra/.env
cp infra/langflow.env.example infra/langflow.env
```

`infra/.env` — infrastructure credentials and ports:

- `NEO4J_PASSWORD` — must be at least 8 characters; set at Neo4j's first boot.
- `POSTGRES_PASSWORD` — LangFlow's metadata database.
- `LANGFLOW_API_KEY` — any non-empty value locally; programmatic API calls must
  send it as `Authorization: Bearer <key>`.

`infra/langflow.env` — everything the flows themselves read at runtime:

- `HULUBUL_LLM_BASE_URL`, `HULUBUL_LLM_MODEL`, `HULUBUL_LLM_API_KEY` — the
  OpenAI-compatible endpoint the agents call. The example ships a placeholder
  URL that will not resolve; replace it.
- `HULUBUL_NEO4J_MCP_URL` — the MCP endpoint as seen from inside the Compose
  network (`http://mcp-neo4j:8000/mcp/`).
- `LANGFLOW_API_KEY` — set to the same value as in `infra/.env`.

The LLM settings are read from `infra/langflow.env`; that is the file Compose
mounts into the LangFlow container.

### 2. Python dependencies

```bash
make install     # poetry install --with test,quality,langflow,integration
```

This installs every optional group. All `make` targets run through
`poetry run`, so this step is required before model generation, tests and flow
tooling — not only before running the application.

The optional groups are:

- `test` — pytest, pytest-bdd, pytest-cov
- `quality` — ruff, mypy, import-linter, tox
- `integration` — httpx, neo4j driver, testcontainers
- `langflow` — the LangFlow SDK (`lfx`) for flow-as-code tooling

To install a subset explicitly, name the groups you want, e.g.
`poetry install --with test,quality`.

### 3. Start the stack

```bash
make up          # docker compose up -d
make ps          # check service status
make logs        # follow logs
```

### 4. Neo4j schema and demo data

```bash
make neo4j-schema    # constraints + indexes (required)
make neo4j-seed      # deterministic demo data (optional)
```

`make neo4j-schema` is a required step: the Compose stack does not apply the
schema for you. `make neo4j-seed` is separate and purely additive — **to start
with an empty graph, simply skip it**; nothing else in setup depends on the demo
data. To verify the seed loaded, run `make neo4j-queries`.

If you need to start over, `make neo4j-reset` wipes every node and re-applies
schema and seed (it prompts for confirmation first).

### 5. Deploy the flows

Flow JSON in `langflow/flows/` is the authoritative copy; a fresh LangFlow
instance starts empty and must have the flows pushed into it.

```bash
make langflow-deploy
```

This pushes every `*.json` file in `langflow/flows/` to the instance at
`LANGFLOW_URL` (default `http://localhost:7860`), upserting each by the stable
flow ID stored inside it. Files are pushed in filename order, which is why they
carry `10-`/`20-`/`30-` prefixes: a flow that references another by ID must be
deployed after it. The API key is read from `infra/.env`. To target a different
instance, override the URL: `make langflow-deploy LANGFLOW_URL=http://host:7860`.

Flows can also be imported through the LangFlow UI, but pushing by stable ID is
what keeps the instance and Git in agreement — see `langflow/README.md`.

Open http://localhost:7860 and the flows should be present.

### Ports and endpoints

All ports bind to `127.0.0.1` only.

| Service | Endpoint | Purpose |
|---------|----------|---------|
| LangFlow | http://localhost:7860 | UI, playground and REST API |
| Neo4j Browser | http://localhost:7474 | graph UI (`make neo4j-browser` prints credentials) |
| Neo4j Bolt | `bolt://localhost:7687` | drivers, `cypher-shell`, MCP server |
| Neo4j MCP | http://localhost:8000/mcp/ | MCP streamable HTTP (port from `NEO4J_MCP_PORT`) |
| Postgres | `localhost:5432` | LangFlow metadata |

Inside the Compose network, services address each other by name — the MCP server
is `http://mcp-neo4j:8000/mcp/`, not `localhost`.

## Development workflow

Each kind of change has its own routine. Whichever one you follow, finish with
`make ci-static` before committing.

### Changing the domain model

Edit the LinkML schema under `model/linkml/`, then regenerate and commit the
outputs in the same commit as the schema edit:

```bash
make all                      # lint + regenerate every artifact
make check-model-generated    # fails if generated output is stale
```

Never hand-edit anything under `model/generated/` — the next `make` overwrites
it.

### Changing an operational contract

Edit the Pydantic models under `src/hulubul/core/models/operational/`, then
regenerate the JSON schemas and commit both together:

```bash
make operational-schemas        # regenerate schemas/operational/v1
make check-operational-schemas  # fails if they are stale
```

### Changing Python code

```bash
make format-python        # apply Ruff formatting
make lint-python          # Ruff lint
make typecheck            # mypy (strict)
make check-architecture   # import-linter layer boundaries
make test-unit            # unit tests, fails under 80% coverage
make test-static          # static topology and repository-invariant tests
```

`make check-architecture` enforces the layering declared in `.importlinter`
(`entrypoints → services → models`, `adapters → models`, `core` importing
nothing outward). A new import that crosses a boundary fails here, not in
review.

### Changing a flow

Flows live in Git as normalised JSON, and there are two ways to change one.

**Edit visually, then bring it back into Git:**

1. Edit the flow in a running LangFlow instance.
2. Export it (UI or `lfx export`) over the file in `langflow/flows/`.
3. Normalise it deterministically:
   ```bash
   poetry run python scripts/normalize_langflow_flows.py langflow/flows/<file>.json
   ```
4. Run `make check-flows`.
5. Commit the normalised flow together with any `flow-manifest.yaml` change.

**Or edit the JSON directly, then deploy it:** the flow files are plain JSON and
can be changed in an editor — which is often quicker for a small, surgical edit
such as a prompt string, a component parameter or a stable ID. Normalise the
file, run `make check-flows`, then `make langflow-deploy` to push it into the
running instance. Reload the flow in the UI to see the result.

Whichever route you take, the file in Git is the authority: an edit made only in
the UI and never exported will be overwritten by the next deploy.

`make check-flows` is a deliberate manual pre-merge guard and is not part of
`make ci-static`. Its idempotence check is the one that reflects real drift; the
bundled `lfx` checks are diagnostic and report known false positives for custom
components. Full detail in `langflow/README.md`.

### Before you commit

```bash
make ci-static
```

This is the gate: LinkML lint, generated-model drift, Ruff lint and format
check, mypy, import-linter, operational-schema drift, unit tests and static
tests. Nothing is done until it exits 0. CI runs exactly this target on every
push and pull request against `main` and `develop`.

Two things sit outside it:

- `make test-integration` — integration tests against real adapters. Requires
  Docker (testcontainers) and, for the LangFlow tests, a running stack.
- `tests/manual/` — human-driven scenarios for the three flows. Not collected by
  pytest: they need the full local stack and call a real model, so no two runs
  are identical. They cover what the automated suites cannot — whether a flow
  behaves sensibly for a person talking to it. Run them after changing a flow's
  prompt, its wiring, or a boundary contract. Index and prerequisites in
  `tests/manual/README.md`.

### Merging

All changes to `develop` and `main` go through pull requests with human review;
direct pushes are not used. Commit messages follow
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

## Make targets

`make help` prints the canonical list, grouped as:

**Model generation** (LinkML source under `model/linkml/` → `model/generated/`)
- `make all` — lint + regenerate every artifact
- `make lint` — lint the LinkML schema (this is `linkml-lint`, not Python linting)
- `make pydantic` / `owl` / `shacl` / `jsonschema` / `erdiagram` / `plantuml` / `classdiagram` / `neo4j-constraints` / `neomodel` — regenerate a single artifact
- `make clean` — wipe `model/generated/`

**Docker**
- `make up` / `down` / `down-volumes` / `rebuild` / `rebuild-clean` / `logs` / `ps`

**Neo4j + MCP**
- `make neo4j-schema` / `neo4j-seed` / `neo4j-queries` / `neo4j-reset` / `neo4j-shell` / `neo4j-browser` / `neo4j-wait`
- `make mcp-logs` / `mcp-restart`

**LangFlow**
- `make langflow-deploy` — push every flow in `langflow/flows/` to `LANGFLOW_URL`
- `make check-flows` — validate flow assets before merging

**CI / quality gates**
- `make install` — install all dependency groups
- `make lint-python` / `format-python` / `format-check-python` / `typecheck` / `check-architecture`
- `make test-unit` / `test-static` / `test-feature` / `test-integration`
- `make operational-schemas` / `check-operational-schemas` / `check-model-generated`
- `make ci-static` — the everyday gate, and what CI runs
- `make ci` — `ci-static` plus the acceptance suite; the acceptance half needs
  the dedicated Docker acceptance stack (`make acceptance-up`), so use
  `ci-static` for local work

Tox mirrors part of this for multi-environment runs: `tox` runs the `py310`,
`architecture` and `schemas` environments; `integration`, `system` and
`evaluation` are opt-in via `tox -e <name>`.

## Repository layout

```
.
├── architecture/              # Design documents, ADRs, use cases, NFRs, strategies
├── infra/                     # Docker Compose stack, Cypher scripts, MCP server image
├── langflow/                  # Flow JSON (authoritative) + flow manifest
├── model/linkml/              # LinkML domain model (single source of truth)
├── model/generated/           # Generated artifacts — never hand-edit
├── model/modelspecs/          # Human-authored source specs the model derives from
├── openspec/                  # Specification spine: proposals, designs, task breakdowns
├── schemas/operational/       # Operational contracts published as JSON Schema — generated
├── scripts/                   # Custom LinkML generators and flow tooling
├── src/hulubul/               # Python package: custom components and domain logic
├── tests/                     # unit, static, integration, manual, features, fixtures, support
├── .github/workflows/ci.yaml  # CI: make install && make ci-static
├── AGENTS.md (→ CLAUDE.md)    # Instructions for AI coding agents
├── Makefile                   # Every workflow entry point
├── pyproject.toml             # Poetry, pytest, coverage, ruff, mypy configuration
├── tox.ini                    # Multi-environment test definitions
└── README.md                  # This file
```

## What is generated

Three parts of the tree are produced by tooling and must never be hand-edited.
Each has a drift check that fails the build if the committed output no longer
matches its source.

| Output | Generated from | Command | Drift check |
|--------|----------------|---------|-------------|
| `model/generated/**` | `model/linkml/*.yaml` | `make all` | `make check-model-generated` |
| `schemas/operational/v1/**` | `src/hulubul/core/models/operational/` | `make operational-schemas` | `make check-operational-schemas` |
| `.lfx/component-schemas-pinned.json` | the pinned LangFlow release | `poetry run python scripts/inspect_langflow_components.py` | — |

Generated artifacts are committed so they stay in sync with their source, and
belong in the same commit as the change that caused them. One caveat: OWL and
SHACL Turtle output is not byte-stable across runs (rdflib reorders blank
nodes), so those are excluded from the drift check.

## Documentation

| Document | Covers |
|----------|--------|
| `architecture/README.md` | Index of the architecture documentation |
| `architecture/project-statement.md`, `architecture-statement.md` | What the system is for and how it is shaped |
| `architecture/decisions/` | Architecture Decision Records |
| `architecture/use-cases/` | Cockburn white (summary) and blue (user-goal) use cases |
| `architecture/agentic-system-blueprint.md` | The agent design |
| `architecture/non-functional-requirements.md` | NFRs |
| `architecture/verification-testing-and-evaluation-strategy.md` | How the system is verified and evaluated |
| `architecture/incremental-system-development-strategy.md` | The phased build-up plan |
| `infra/README.md` | Stack internals, service topology, security posture |
| `langflow/README.md` | Flow-as-code toolchain, manifest rules, edit cycle |
| `model/README.md` | The domain model and its provenance |
| `tests/manual/README.md` | Manual test scenarios for the three flows, and how to run them |
| `AGENTS.md` | Conventions for AI coding agents working in this repository |

## Licence

Licensed under the Apache License 2.0 — see [LICENSE](LICENSE).
