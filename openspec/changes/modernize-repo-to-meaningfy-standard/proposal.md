# EPIC: Modernize hulubul-broker to the Meaningfy project-setup standard

## Appetite

Large — a full-repo brownfield modernization, but shaped as an ordered
sequence of small, independently reviewable slices rather than one big-bang
change. Each slice is a single commit gated by `make check-all`.

## Why

The repo grew organically through the channel-gateway build and the
in-flight input-connector feature and has diverged from the Meaningfy
project-setup standard: a `/src` layout, tool config sprawled across
`pyproject.toml`, a duplicated tox/Makefile task-runner surface, an
un-pinned OpenSpec schema, and — most urgently — a `CLAUDE.md` symlink that
resolves to an absolute path on a different machine (`/home/greg/...`),
which is broken on every checkout but the one it was authored on. Left
alone, each new feature branch adds further divergence and the fix gets more
expensive. Now — before more work lands on top of `feature/input-connector`
— is the cheapest point to correct course.

## Solution outline

Apply the brownfield method from `meaningfy-building:project-setup`
(`references/modernizing-existing-projects.md`): the gap audit is already
done (see `inputs/audit-and-elicitation.md`); this EPIC sequences the
detected gaps least-risk-first, additive and reversible work before
high-blast-radius work, each slice landing green on `make check-all` before
the next starts. The `/src` → top-level package lift — the one step that
rewrites every import root — is deliberately sequenced last, in its own
isolated commit, once everything else is stable.

## Key decisions

- **DEC-1**: Continue from `feature/input-connector` (the latest
  channel-gateway implementation), synced with `origin/develop` and any
  conflicts resolved, rather than a fresh branch off `main` — `develop` is
  where feature work actually merges in this repo; `main` is stale.
- **DEC-2**: Antora documentation (D10 — migrating `architecture/*.md` into
  a Diátaxis-shaped `docs/` component) is explicitly deferred to a separate
  future EPIC. It is a content-judgment migration, not mechanical tooling,
  and doesn't belong in the same appetite as a build-tooling modernization.
- **DEC-3**: `sonar-project.properties` is skipped. No SonarQube/SonarCloud
  integration exists anywhere in this repo's CI today; adding the stub file
  would be unused scaffolding (YAGNI) — add it in the same change that
  actually wires Sonar in, if that ever happens.
- **DEC-4**: The `/src` → top-level package lift is in scope but sequenced
  last, isolated in its own commit, after every other slice is green. It is
  the highest-blast-radius step (rewrites `pyproject.toml` packaging, pytest
  `pythonpath`, and the manual `sys.path` shim in `tests/conftest.py`) —
  GitNexus confirms 0 import cycles in the current graph, which de-risks it,
  but it still touches every path-based config in one pass.
- **DEC-5**: `tox.ini` is removed. Its 3 eval-only environments
  (`evaluation`, `evaluation-live`, the live-model judge eval) are ported to
  real Makefile targets (currently commented-out placeholders) first, so no
  capability is lost — the Makefile becomes the single task-runner surface
  (D7).
- **DEC-6**: `openspec/config.yaml` is pinned to `schema: meaningfy` with the
  schema copied in per `spine-projection.md`. The in-flight
  `deliver-phase-1-request-intake-thread` change keeps its own
  `schema: superpowers-bridge` pin in its `.openspec.yaml` (per-change schema
  pinning already exists in this repo) rather than being force-migrated
  mid-flight — only newly authored changes, including this one, use
  `meaningfy` going forward.

## Rabbit-holes

- Don't refactor business logic, tests, or channel-gateway/request_intake
  behavior while doing config/layout moves — this EPIC is tooling and spine
  only.
- The `/src` lift does not change any Python import statement — the
  installed package name stays `hulubul` (only its on-disk parent directory
  moves from `src/hulubul/` to `hulubul/`). Don't go hunting for import
  rewrites that aren't needed.
- Don't tighten `.importlinter` contracts beyond what's already enforced —
  the existing cosmic-python boundaries are conformant and out of scope.
- Don't chase 100% coverage of the Meaningfy standard in one pass — Antora
  docs and Sonar are explicit no-gos below, not partial attempts.

## No-gos

- Antora documentation / `docs/` migration (DEC-2 — separate future EPIC).
- SonarQube/SonarCloud integration (DEC-3).
- Any change to channel-gateway or request_intake business logic, tests, or
  behavior.
- WhatsApp adapter work, identity-merge, or Phase-3 concurrency — tracked
  separately (see project memory), unrelated to this modernization.
- Committing directly to `main` or `develop` — this lands via PR from an
  implementation branch.

---

## What Changes

- Add dedicated root config files (`ruff.toml`, `mypy.ini`, `pytest.ini`,
  `.coveragerc`, `.pre-commit-config.yaml`, `CHANGELOG.md`, `SECURITY.md`)
  and strip the equivalent `[tool.*]` blocks out of `pyproject.toml`.
- Remove `tox.ini`; port its 3 eval-only environments to real Makefile
  targets.
- Pin `openspec/config.yaml` to `schema: meaningfy`; copy in the pinned
  `openspec/schemas/meaningfy/` schema.
- Fix the broken `CLAUDE.md` symlink: `CLAUDE.md` becomes the canonical
  file, `AGENTS.md` becomes a relative symlink to it (**BREAKING** for any
  tooling that reads `AGENTS.md` expecting it to be the real file — none is
  known to exist).
- Add `.claude/memory/MEMORY.md` as a regenerable orientation index.
- Consolidate `infra/channel-gateway/Dockerfile` and `infra/mcp/Dockerfile`
  toward the prescribed multistage layout with co-located dockerignore.
- **BREAKING**: move `src/hulubul/` → `hulubul/` (top-level package); update
  `pyproject.toml` packaging, `pytest.ini` `pythonpath`, and
  `tests/conftest.py`'s `sys.path` shim accordingly.

## Capabilities

### New Capabilities

- `repository-tooling-standard`: normative requirements that the repo's
  build tooling, agent files, and OpenSpec spine conform to the Meaningfy
  standard — the four proof scenarios agreed during elicitation (green
  `check-all` per slice, agent-file resolution on a fresh clone, strict
  schema validation, and CI/local parity).

### Modified Capabilities

None — no existing `openspec/specs/` capability's requirements change.

## Impact

- **Code:** `src/hulubul/` → `hulubul/` (path only, no import changes);
  `tests/conftest.py`.
- **Config:** `pyproject.toml` (stripped to `[project]`/`[tool.poetry]`/
  `[dependency-groups]`/`[build-system]`), new `ruff.toml`, `mypy.ini`,
  `pytest.ini`, `.coveragerc`, `.pre-commit-config.yaml`; `tox.ini` removed.
- **Build:** `Makefile` (new eval targets, updated paths post-`/src` lift).
- **Agentic files:** `CLAUDE.md`, `AGENTS.md`, new `.claude/memory/MEMORY.md`.
- **Spine:** `openspec/config.yaml`, `openspec/schemas/meaningfy/` (new).
- **Infra:** `infra/channel-gateway/Dockerfile`, `infra/mcp/Dockerfile`
  (or their consolidated replacements), `.dockerignore` files.
- **CI:** `.github/workflows/ci.yaml` (paths only — it already calls `make`
  targets, D12 is already satisfied).
- **Dependencies:** none added or removed; `tox` group dependency dropped
  from `pyproject.toml`'s `quality` group.
