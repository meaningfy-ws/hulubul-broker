# Seed: repo modernization audit + elicitation record

Secondary input, archived verbatim. The authored EPIC (`../proposal.md`) is the
primary, shaped truth — this file is never groomed or deleted, only superseded.

## Trigger

User request: "It is time to do the project setup, as it already starts to be
crowded and divergent from blueprints" → later refined to "explore the project
and prepare a new epic about setting up this project according to
project-setup from meaningfy", then authorized to proceed end-to-end without
further check-ins.

## Audit method

Ran the brownfield gap rubric from
`meaningfy-building:project-setup`'s `references/modernizing-existing-projects.md`
by direct repo inspection (no `scaffold.sh --dry-run` available in this session;
findings below are from manual file inspection against the same rubric).

## Gap report (detected violations only)

| Dimension | Status | Detail |
|---|---|---|
| D1 — layout | ❌ | `src/hulubul/` present; `pythonpath=["src"]` in pyproject; manual `sys.path` shim in `tests/conftest.py` |
| D2 — pyproject sprawl | ❌ | `[tool.pytest.ini_options]`, `[tool.coverage.*]`, `[tool.ruff.*]`, `[tool.mypy]` all inline; no dedicated `ruff.toml`/`mypy.ini`/`pytest.ini`/`.coveragerc` |
| D4/D7 — dual task runners | ❌ | `tox.ini` (py310/architecture/schemas/integration/system/evaluation/evaluation-live envs) coexists with `Makefile`; 3 tox envs (`evaluation`, `evaluation-live`, live_model judge) have no Makefile equivalent (only commented-out placeholders) |
| D8/DEC-4 — agent file | ❌ | `AGENTS.md` is the real 13KB file; `CLAUDE.md` is a symlink pointing to an **absolute path on a different machine/user** (`/home/greg/PROJECTS/hulubul-broker/AGENTS.md`) — broken on every other checkout, and inverted from CLAUDE-canonical |
| D9 — memory index | ❌ | No `.claude/memory/MEMORY.md` |
| D13 — spine schema | ⚠️ | `openspec/` tree exists (changes/specs/schemas) but `config.yaml` pins `schema: spec-driven`; `openspec/schemas/` vendors `superpowers-bridge`, not the pinned `meaningfy` schema |
| D10 — docs | ❌ | No Antora `docs/`; architecture material lives in ad hoc `architecture/*.md` (blueprint, runbook, ADRs, use-cases, specs) |
| D11 — infra | ⚠️ | Top-level `infra/` + compose present, but Dockerfiles are per-component (`infra/channel-gateway/Dockerfile`, `infra/mcp/Dockerfile`), not the prescribed multistage `infra/docker/Dockerfile` + co-located dockerignore |
| Additive files | ❌ | Missing `.pre-commit-config.yaml`, `sonar-project.properties`, `CHANGELOG.md`, `SECURITY.md` |

**Conformant, not in scope** (kept as-is): `.importlinter` cosmic-python layering
(core/request_intake/channel_gateway boundaries, wired to `make check-architecture`
+ CI); Ruff/mypy/import-linter tool choice; type-split `tests/`
(unit/feature/e2e) + pytest-bdd; 80% coverage gate; `openspec/` tree structure;
CI calling `make` targets (D12 already satisfied); `LICENSE`; `infra/.env`
correctly gitignored. GitNexus `check` (cycle detection) confirmed 0 import
cycles in the current graph, de-risking the `/src` lift.

## Elicitation record (Q&A)

1. **Appetite** → *Full modernization, one EPIC, safe slices.* All detected
   gaps in one shaped bet, landed as an ordered sequence of small reviewable
   commits.
2. **`/src` lift timing** → *Include, sequenced last.* Highest blast radius;
   isolated in its own commit after every other slice is green.
3. **Docs & infra scope** → *Infra only, docs deferred.* Dockerfile
   consolidation (D11) is in scope; the `architecture/*.md` → Antora migration
   (D10) is deferred to a separate future EPIC (bigger, content-judgment work).
4. **Proof scenarios** (multi-select) → all four selected: `make check-all`
   green after every slice; `CLAUDE.md`/`AGENTS.md` resolve on a fresh clone;
   `openspec validate --strict` passes on the pinned schema; CI mirrors local
   `make check-all` exactly (no tox/Makefile duplication).
5. **Base branch** → *"from the last channel implementation, feature and pull
   in latest changes from develop, and resolve any conflicts"* — continue from
   `feature/input-connector` (the channel-gateway work), sync it with
   `origin/develop`, resolve conflicts, before starting the modernization
   slices. `main` is stale relative to `develop`.
6. **tox eval-only targets** → *Port to real Makefile targets.* No capability
   lost when tox is removed.
7. **Final authorization** (unprompted, mid-session): "proceed to analyse and
   propose best approaches among alternatives, work independently... start a
   new branch, pull in any changes and start a fresh implementation branch and
   implement independently towards completion, and then check in revise
   independently with subagents and make improvements; Do not ask me anything
   I am AFK and want to see the end result." — this authorizes branch
   creation, full-slice implementation, and subagent-driven review without
   further check-ins for the scope shaped above.

## Decisions made without a check-in (documented for audit trail)

- **Sonar** (`sonar-project.properties`): skipped as a no-go. No SonarQube/
  SonarCloud integration exists anywhere in this repo's Makefile or CI today;
  adding the stub file would be scaffolding with no consumer (YAGNI).
