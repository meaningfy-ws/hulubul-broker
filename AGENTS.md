# AGENTS.md

Guidance for AI coding assistants (Claude Code, opencode, etc.) working in this
repository. This is the canonical agent instruction file. `CLAUDE.md` only
points here — never write repo guidance into `CLAUDE.md`, and never let the
two diverge.

## Project purpose

Hulubul is an autonomous, agent-driven parcel-brokerage service: it turns a
Sender's chat message into a structured Parcel Request, matches it to
transporters, and carries the communication through pick-up and delivery —
over Telegram (dev) / WhatsApp (prod), on a Neo4j graph system of record,
orchestrated by LangFlow.

Built so far: the LinkML domain model, the local infra stack, the `hulubul`
Python application (cosmic-python layered: `core`, `request_intake`,
`channel_gateway`), and a Telegram channel-gateway adapter. Architecture
docs under `architecture/` describe the target system and an incremental
(Phase 1–4) build-up plan; current in-flight and completed work is tracked
in `openspec/changes/` and `openspec/specs/` (see "Golden thread" below) —
that is the truth, not this file.

## Git workflow: PR-only merges

**CRITICAL:** All changes to `develop` and `main` go through pull requests
with human review — never push directly to either. Open a PR, wait for
explicit human approval, then merge. No exceptions.

## Important commands

`make help` prints the full target list (model generation, Docker, Neo4j/MCP,
quality gates). The ones you'll use every session:

- `make check-all` — the full local quality gate (lint, types, architecture,
  model checks, tests) — run before claiming any work done
- `make test-unit` / `test-feature` — unit tests (80% coverage enforced) /
  pytest-bdd feature suites
- `make lint-python` / `format-check-python` / `typecheck` — Ruff / Ruff /
  mypy (`make lint` is LinkML schema linting, not Python)
- `make check-architecture` — import-linter boundary check
- `make all` (from `model/`, or repo root) — regenerate every LinkML-derived
  artifact after a schema edit
- `make up` (Docker stack) needs `cp infra/.env.example infra/.env` first
  (gitignored; edit passwords)

## Top-level architecture

| Path | Role |
|------|------|
| `model/linkml/` | **Source of truth** — LinkML schema (six domain modules over a common base) |
| `model/generated/` | Deterministic outputs (Pydantic, OWL, SHACL, JSON Schema, diagrams, Cypher, neomodel). Never hand-edit. |
| `model/modelspecs/` | Human-authored source specs the model was derived from (provenance) |
| `infra/` | Local stack: `docker-compose.yaml` (Neo4j + mcp-neo4j-cypher + Langflow + Postgres), cypher scripts, MCP/channel-gateway Dockerfiles |
| `architecture/` | Design documents: project statement, ADRs, use cases, blueprints, NFRs, incremental strategy |
| `scripts/` | Custom LinkML generators (`gen_neo4j_constraints.py`, `gen_neomodel.py`, `gen_mermaid_classdiagram.py`, `gen_operational_schemas.py`) |
| `hulubul/` | Application code (top-level package, no `/src` — D1): `core` (shared operational contracts), `request_intake`, `channel_gateway` — cosmic-python layered (models/adapters/services/entrypoints per component), enforced by `.importlinter` |
| `openspec/` | The spine: EPICs/PLANs (`changes/`), durable capability specs (`specs/`), the pinned `meaningfy` schema |

### Visible conventions

- **LinkML is the single source of truth.** Files under `model/generated/` are
  produced by `make` and must never be hand-edited; the next `make` overwrites
  them. Commit generated artifacts in the same commit as the schema edit.
  `hulubul/core/models/domain/` is likewise `make`-generated (`make pydantic`)
  and must never be hand-edited.
- **Secrets never live in VCS.** `infra/.env` is gitignored; copy from
  `infra/.env.example` and edit passwords (Neo4j password ≥ 8 characters).
  Secret scanning is provided at the organization level (SonarQube, Snyk,
  GitHub secret scanning) — no in-repo scanner (see `f98729f`).
- **`make lint` is schema linting** (`linkml-lint`); Python linting is
  `make lint-python`.
- **Generated artifacts are committed** so they stay in sync with the schema; a
  CI drift check re-runs `make all`/`make check-model-generated` and fails on
  diff. Caveat: OWL and SHACL Turtle output is not byte-stable across runs
  (rdflib reorders blank nodes), so those are excluded from the diff check.
- **Commit messages** follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
  (e.g. `docs:`, `feat(scope):`, `fix:`).
- **Single task-runner surface: the Makefile.** No `tox.ini` — CI and local
  runs both call `make` targets exclusively.

## Golden thread (cite your parent)

This repo uses the Meaningfy spine (`openspec/`, schema `meaningfy`):
**EPIC** (`openspec/changes/<id>/proposal.md`, the shaped bet) → **PLAN**
(`design.md` + `tasks.md`, scored by the clarity gate ≥9/10) → **specs**
(`specs/` deltas, RFC-2119 SHALL + Given/When/Then) → commit. A PLAN's
`tasks.md` cites its parent EPIC id on the first line; treat that citation as
load-bearing, not decorative. `openspec/specs/` is the durable truth;
`openspec/config.yaml`'s `context:` field is the one orientation index
(injected into every artifact's instructions) — point at it, never
hand-maintain a second one. In-flight changes authored before the `meaningfy`
schema pin (e.g. `deliver-phase-1-request-intake-thread`) keep their own
schema in their `.openspec.yaml` — only newly authored changes use
`meaningfy`, and that pointer, not a restated copy, is how you'll always
find the current truth.

## Local developer overrides (Claude Code specific)

Claude Code's `@file` import syntax pulls in an optional, git-ignored tier
of instructions below — this mechanism is Claude Code specific; other
AGENTS.md-reading tools will just see this line as plain text and can
ignore it. If `AGENTS.local.md` doesn't exist, the import is a no-op.
Anything it contains is local-only — keep it out of commits, PRs, code,
comments, and other docs.

@AGENTS.local.md

## Workflow routing (read on session start)

This repo's OpenSpec artifacts follow the pinned `meaningfy` schema (see
"Golden thread" above). This section is the routing guidance for Claude
between free-form exploration and the spine's `/opsx:*` verbs.

### Entry routing

| Trigger you observe | What to do |
|---|---|
| User starts a narrative "design discussion / let's brainstorm" | Run verbal `superpowers:brainstorming`, but **do NOT** write to `openspec/changes/`. Once the conversation converges per the 5 criteria below, promote to `/opsx:propose` |
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

All 5 must hold before promoting (any missing → keep brainstorming, **never** write to `openspec/changes/`):

1. **Scope locked** — one sentence describes what's in / out
2. **Major design forks resolved** — alternatives weighed; remaining TBDs have an owner and impact-scope statement
3. **Cross-system dependencies mapped** — ready / mockable / genuinely unknown — pick one per dep
4. **Acceptance criteria stateable** — concrete pass conditions (e.g., `make check-all` passes + N deliverables)
5. **Conversation converging** — recent turns are confirmations, not new alternatives

When all 5 hold → proactively suggest "ready to `/opsx:propose`?" — wait for user ack. Never auto-trigger.

### Front-door anti-patterns (don't do)

- Letting brainstorming write to `openspec/changes/`
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

### Meaningfy skill routing

`meaningfy-skillery` (22 skills: core/building/consulting/architecture) isn't otherwise
routed here — this table is that routing.

| When | Skill |
|---|---|
| Apply-readiness gate, before `/opsx:apply` (not optional) | `meaningfy-building:clarity-gate` — score ≥9/10 |
| System design, ADRs, C4 | `meaningfy-architecture:architecture` |
| Editing the LinkML schema or its generation pipeline | `meaningfy-architecture:linkml-engineering` + `meaningfy-architecture:modelling-conventions` |
| Generated-domain vs. hand-written model boundary | `meaningfy-architecture:conceptual-modelling` |
| Code layering/SOLID under `hulubul/` | `meaningfy-building:cosmic-python` |
| Gherkin feature files | `meaningfy-building:bdd-gherkin` |
| Architecture docs, READMEs, docstrings | `meaningfy-core:technical-writing` |
| Broad-audience explainer prose | `meaningfy-core:explanatory-writing` |
| Chat input reaching an LLM agent | `meaningfy-core:guardrails` |
| Commits, branches, PRs | `meaningfy-core:meaningfy-git-workflow` |
| Post-implementation review (separate dispatch, never self-review) | `meaningfy-building:meaningfy-code-review` |
| `/opsx:archive` | `meaningfy-building:spec-stewardship` |
| New-repo or repo-wide scaffolding | `meaningfy-building:project-setup` |
| Deploy/CD setup (real deployment, not local Compose) | `meaningfy-building:ci-cd-delivery` |
| Release/versioning/publish | `meaningfy-building:meaningfy-release` |

`meaningfy-consulting:*` (coach/decision-package/proposal-writing/estimation/
executive-communication) is **not applicable** to this repo — it's for running a consulting
engagement, not building this product. `/opsx:propose` and `proposal-writing` are unrelated
despite the name overlap.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **hulubul-broker**. Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "develop"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/hulubul-broker/context` | Codebase overview, check index freshness |
| `gitnexus://repo/hulubul-broker/clusters` | All functional areas |
| `gitnexus://repo/hulubul-broker/processes` | All execution flows |
| `gitnexus://repo/hulubul-broker/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
