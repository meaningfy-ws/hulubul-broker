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
- **DEC-3** *(revised during branch sync — see below)*: `sonar-project.properties`
  is added as a minimal stub, **not wired into CI**. Originally scoped as a
  skip (no Sonar integration visible in this repo's own config); merging
  `develop` surfaced commit `f98729f`'s message stating the organization
  already runs a licensed SonarQube instance at the platform level — so the
  project key/sources stub is cheap and forward-compatible, but actually
  wiring a CI step needs a `SONAR_TOKEN` and project registration this EPIC
  doesn't have, so that step stays a documented TODO, not a live gate.
- **DEC-4**: The `/src` → top-level package lift is in scope but sequenced
  last, isolated in its own commit, after every other slice is green. It is
  the highest-blast-radius step (rewrites `pyproject.toml` packaging, pytest
  `pythonpath`, and the manual `sys.path` shim in `tests/conftest.py`) —
  GitNexus confirms 0 import cycles in the current graph, which de-risks it,
  but it still touches every path-based config in one pass.
- **DEC-5** *(corrected during implementation)*: `tox.ini` is removed. It had
  exactly 2 marker-based eval environments (`evaluation`,
  `evaluation-live`) — not 3; the Makefile's 3 commented-out placeholder
  targets (`test-evaluation-recorded/-live/-judge`) were aspirational and
  already referenced test files that never existed. The 2 real tox envs are
  ported 1:1 (marker-based, `pytest -m evaluation tests` /
  `pytest -m "evaluation and live_model" tests`) to real Makefile targets;
  the third, never-real "judge" placeholder is dropped, not ported — no
  capability is actually lost. The Makefile becomes the single task-runner surface
  (D7).
- **DEC-6**: `openspec/config.yaml` is pinned to `schema: meaningfy` with the
  schema copied in per `spine-projection.md`. The in-flight
  `deliver-phase-1-request-intake-thread` change keeps its own
  `schema: superpowers-bridge` pin in its `.openspec.yaml` (per-change schema
  pinning already exists in this repo) rather than being force-migrated
  mid-flight — only newly authored changes, including this one, use
  `meaningfy` going forward.
- **DEC-7** *(added post-review)*: `make ci-static`/`make check-all` include
  `typecheck`, and it stays red — 69 pre-existing mypy strict-mode errors
  (missing type annotations) in `tests/unit/hulubul/channel_gateway/**`,
  confirmed present on `origin/develop` already and never caught because
  `feature/input-connector` never ran through CI (no PR had opened against
  `main`/`develop` yet). This branch is the first thing to actually exercise
  that CI path, so **this PR will show a red `typecheck` step** — that is
  this pre-existing debt surfacing, not a regression introduced here. Per
  this EPIC's own no-go (no channel-gateway test changes), fixing those 69
  annotations is explicitly out of scope for this change. The alternative —
  dropping `typecheck` from `ci-static` — was rejected: it would hide the
  debt instead of surfacing it, defeating the point of a modernization EPIC
  whose Requirement 1 is "the gate SHALL pass." Recommendation to the human
  reviewer: land a small, separate PR annotating those 69 test functions
  (mechanical, no behavior change) before or alongside merging this one.
- **DEC-8** *(reverses this EPIC's original D8/DEC-4 choice, per explicit
  developer instruction)*: `AGENTS.md` — not `CLAUDE.md` — is the canonical
  agent instruction file. `CLAUDE.md` is a minimal pointer
  ("Read AGENTS.md") rather than a symlink, so a tool that reads `CLAUDE.md`
  directly sees only the pointer and is forced to actually read `AGENTS.md`.
  Rationale given: `AGENTS.md` is the cross-tool standard name (readable by
  more than just Claude Code); the developer wants it to be the one real
  file. This is a deliberate, logged reversal of the Meaningfy
  project-setup standard's default (CLAUDE-canonical, D8/DEC-4) — every
  place that cited the original direction (this proposal, design.md,
  tasks.md, specs/repository-tooling-standard/spec.md, `README.md`) was
  updated to match, not left silently stale.
- **DEC-9** *(removes two of this EPIC's own additions, per explicit
  developer questioning — "why do we need X, don't we already have Y")*:
  - `.claude/memory/MEMORY.md` is **removed**. It hand-restated the same
    facts already in `openspec/config.yaml`'s `context:` field — OpenSpec's
    own native, automatically-injected orientation index — which is
    exactly the kind of duplicate-index drift risk D9's own text warned
    about while this EPIC went ahead and created it anyway. One index
    (`openspec/config.yaml`), not two.
  - `SECURITY.md` is **removed**. Its content (a public vulnerability-
    disclosure process) doesn't fit an internal product repo with no
    external security-research audience; the org-level scanning note it
    carried already lives in `AGENTS.md`'s "Visible conventions". Added
    originally because the project-setup standard's file list names it as
    a default additive file — that default doesn't fit here.

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
  `.coveragerc`, `.pre-commit-config.yaml`, `CHANGELOG.md`,
  `sonar-project.properties` — stub only, not CI-wired, DEC-3) and strip the
  equivalent `[tool.*]` blocks out of `pyproject.toml`. (`SECURITY.md` was
  added, then removed — DEC-9.)
- Remove `tox.ini`; port its 2 real eval-only environments (a 3rd,
  "judge", was only ever an already-broken Makefile placeholder — DEC-5)
  to real Makefile targets.
- Pin `openspec/config.yaml` to `schema: meaningfy`; copy in the pinned
  `openspec/schemas/meaningfy/` schema.
- Fix the broken `CLAUDE.md` symlink: `AGENTS.md` becomes the canonical
  file (DEC-8, reversing the original CLAUDE-canonical choice per explicit
  developer instruction), `CLAUDE.md` becomes a minimal pointer
  (**BREAKING** for any tooling that reads `CLAUDE.md` expecting it to
  carry the full instructions — none is known to exist).
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
- **Agentic files:** `CLAUDE.md`, `AGENTS.md`.
- **Spine:** `openspec/config.yaml`, `openspec/schemas/meaningfy/` (new).
- **Infra:** `infra/channel-gateway/Dockerfile`, `infra/mcp/Dockerfile`
  (or their consolidated replacements), `.dockerignore` files.
- **CI:** `.github/workflows/ci.yaml` (paths only — it already calls `make`
  targets, D12 is already satisfied).
- **Dependencies:** none added or removed; `tox` group dependency dropped
  from `pyproject.toml`'s `quality` group.
