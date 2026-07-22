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
- **Commit messages** follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
  (e.g. `docs:`, `feat(scope):`, `fix:`).

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

<!-- Source: superpowers-bridge/templates/adopters/CLAUDE.md.fragment.md -->
<!-- Drop this section into your project's CLAUDE.md so Claude routes future work using this schema correctly. -->
<!-- Adjust the schema name and bridge repo URL if you customized them; otherwise keep as-is. -->

## Workflow routing (read on session start)

This repo uses [`superpowers-bridge`](https://github.com/JiangWay/openspec-schemas/tree/main/superpowers-bridge) to bridge OpenSpec and Superpowers. Integration rules (language, artifact paths, PRECHECK) follow that bridge's README; this section is the routing guidance for Claude.

### Entry routing

| Trigger you observe | What to do |
|---|---|
| User starts a narrative "design discussion / let's brainstorm" | Run verbal `superpowers:brainstorming`, but **do NOT** write to `docs/superpowers/specs/`. Once the conversation converges per the 5 criteria below, promote to `/opsx:propose` |
| User invokes `/opsx:new` / `/opsx:ff` / `/opsx:propose` directly | Follow the schema's flow; artifact instructions inject at each step |
| User explicitly says bug fix / typo / config tweak / doc update | Direct PR — **do NOT** open a change (see skip rules below) |
| User is mid-change | Advance with `/opsx:continue`, `/opsx:apply`, `/opsx:verify`, or `/opsx:archive` |

### When NOT to use opsx (direct PR)

| Scenario | Direct PR? |
|---|---|
| New feature / new capability / architectural change / breaking change | ❌ Use opsx |
| Bug fix (no contract change) / test backfill / linter tweak / non-breaking upgrade / typo / docs / config value tweak | ✅ Direct PR |

Principle: **process ceremony scales with risk**. External contracts / schema / cross-system integration / compliance → opsx. Otherwise → direct PR.

### Verbal brainstorm → opsx promotion criteria

All 5 must hold before promoting (any missing → keep brainstorming, **never** write to `docs/superpowers/specs/`):

1. **Scope locked** — one sentence describes what's in / out
2. **Major design forks resolved** — alternatives weighed; remaining TBDs have an owner and impact-scope statement
3. **Cross-system dependencies mapped** — ready / mockable / genuinely unknown — pick one per dep
4. **Acceptance criteria stateable** — concrete pass conditions (e.g., `./mvnw clean verify` passes + N deliverables)
5. **Conversation converging** — recent turns are confirmations, not new alternatives

When all 5 hold → proactively suggest "ready to `/opsx:propose`?" — wait for user ack. Never auto-trigger.

### Front-door anti-patterns (don't do)

- Letting brainstorming write to `docs/superpowers/specs/`
- Letting writing-plans write to `docs/superpowers/plans/`
- Promoting to opsx with unresolved blocking TBDs
- Opening a change for bug fix / typo

### Implementation subagent routing

- During `/opsx:apply` or subagent-driven plan execution, dispatch the
  project-scoped `implementer` subagent for implementation tasks instead of the
  generic `general` subagent.
- The controller owns worktree setup, task ordering, scope decisions, and final
  verification. Give `implementer` one bounded task brief at a time, including
  the relevant OpenSpec artifacts and acceptance criteria.
- Keep specification-conformance and code-quality review as separate dispatches;
  the implementation subagent must not review its own work.
- Do not grant commit approval implicitly. The developer retains approval of
  each commit unless they explicitly delegate it for the current task.

Full detail: [superpowers-bridge README §Entry & exit gates](https://github.com/JiangWay/openspec-schemas/blob/main/superpowers-bridge/README.md#entry--exit-gates).
