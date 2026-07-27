# repository-tooling-standard Specification

## Purpose
Defines the repository's own build-tooling conformance to the Meaningfy
project-setup standard: a single, green (modulo one documented carve-out)
quality gate, a canonical agent instruction file that resolves on any
checkout, a strictly-validating OpenSpec spine, and one task-runner surface
shared by CI and local runs. This is infrastructure/tooling truth, not
product behavior — it exists so future changes to build config, CI, or the
agent files have a normative baseline to check against instead of
re-deriving "what does green even mean here" from scratch.

## Requirements
### Requirement: Quality gate stays green across the migration
The repository's `make check-all` target SHALL pass (lint, architecture,
tests, coverage) after every commit that lands as part of the repository
modernization, with the sole carve-out of `typecheck` (DEC-7): 69
pre-existing mypy strict-mode errors in `tests/unit/hulubul/channel_gateway/**`
predate this change (confirmed present on `origin/develop`) and are
explicitly out of this EPIC's scope (no channel-gateway test changes). No
*new* mypy error may be introduced by this change.

#### Scenario: A slice commit is green modulo the pre-existing typecheck debt
- **WHEN** any modernization slice (config files, spine schema pin, agent
  file reconciliation, pyproject normalization, infra consolidation, or the
  `/src` lift) is committed
- **THEN** running `make check-all` on that commit exits successfully for
  every component except `typecheck`, and `typecheck`'s error count does not
  increase relative to the pre-modernization baseline (69)

### Requirement: Agent instruction file resolves on any checkout
`AGENTS.md` SHALL be the canonical agent instruction file (DEC-8), and
`CLAUDE.md` SHALL contain only a pointer to it, so a contributor or tool on
any machine or checkout path always finds the real instructions and never a
broken or absolute-path reference.

#### Scenario: Fresh clone on a different machine
- **WHEN** a contributor clones the repository onto a machine other than the
  one it was authored on
- **THEN** `AGENTS.md` is a readable, complete file with no absolute path
  pointing outside the repository, and `CLAUDE.md` points to it

### Requirement: OpenSpec spine validates under the pinned schema
`openspec/config.yaml` SHALL pin `schema: meaningfy`, and all newly authored
changes SHALL validate against it.

#### Scenario: Strict validation passes
- **WHEN** `openspec validate --all --strict` runs against the repository after
  the schema pin
- **THEN** it exits successfully for every change that declares
  `schema: meaningfy` in its `.openspec.yaml`

### Requirement: CI mirrors local quality gates exactly
The repository SHALL have a single task-runner surface (the Makefile) for
quality gates, so CI and local runs of `make check-all`/`make ci-static`
exercise identical commands. Scope note: `.github/workflows/ci.yaml` only
runs `ci-static` (`static-quality` job) — it does not invoke `ci-acceptance`
(integration/system/BDD tests, which need the Docker acceptance stack), so
this requirement's parity claim covers `ci-static` only, not `ci-acceptance`.

#### Scenario: No duplicated or diverging task runner
- **WHEN** the repository's root is inspected after the modernization
- **THEN** no `tox.ini` (or other parallel task-runner config) exists, and
  `.github/workflows/ci.yaml` invokes only `make` targets that also exist
  and are runnable locally

