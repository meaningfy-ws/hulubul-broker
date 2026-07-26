## ADDED Requirements

### Requirement: Quality gate stays green across the migration
The repository's `make check-all` target SHALL pass (lint, types,
architecture, tests, coverage) after every commit that lands as part of the
repository modernization.

#### Scenario: A slice commit is green
- **WHEN** any modernization slice (config files, spine schema pin, agent
  file reconciliation, pyproject normalization, infra consolidation, or the
  `/src` lift) is committed
- **THEN** running `make check-all` on that commit exits successfully

### Requirement: Agent instruction file resolves on any checkout
`CLAUDE.md` SHALL be the canonical agent instruction file, and `AGENTS.md`
SHALL be a relative symlink to it, so both resolve to the same content on
any machine or checkout path.

#### Scenario: Fresh clone on a different machine
- **WHEN** a contributor clones the repository onto a machine other than the
  one it was authored on
- **THEN** both `CLAUDE.md` and `AGENTS.md` resolve to readable, identical
  content, with no absolute path pointing outside the repository

### Requirement: OpenSpec spine validates under the pinned schema
`openspec/config.yaml` SHALL pin `schema: meaningfy`, and all newly authored
changes SHALL validate against it.

#### Scenario: Strict validation passes
- **WHEN** `openspec validate --strict` runs against the repository after
  the schema pin
- **THEN** it exits successfully for every change that declares
  `schema: meaningfy` in its `.openspec.yaml`

### Requirement: CI mirrors local quality gates exactly
The repository SHALL have a single task-runner surface (the Makefile) for
quality gates, so CI and local runs of `make check-all` exercise identical
commands.

#### Scenario: No duplicated or diverging task runner
- **WHEN** the repository's root is inspected after the modernization
- **THEN** no `tox.ini` (or other parallel task-runner config) exists, and
  `.github/workflows/ci.yaml` invokes only `make` targets that also exist
  and are runnable locally
