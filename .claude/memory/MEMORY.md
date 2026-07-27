# Memory Index

Regenerable orientation index (≤200 lines, stable patterns only). If this
disagrees with `openspec/specs/`, **specs/ wins** — this file is a pointer,
not authority.

## Orientation

- Project context, architecture summary, and conventions: `openspec/config.yaml`'s `context:` field.
- Durable capability specs (the truth): `openspec/specs/`.
- In-flight work (EPICs + PLANs): `openspec/changes/`.
- Agent routing, commands, and the golden thread: `AGENTS.md` (canonical; `CLAUDE.md` just points there).

## Stable patterns

- Cosmic-python layering per component (`core`, `request_intake`,
  `channel_gateway`): models → adapters/services → entrypoints, enforced by
  `.importlinter` (`make check-architecture`).
- LinkML (`model/linkml/`) is the domain source of truth; everything under
  `model/generated/` and `hulubul/core/models/domain/` is generated,
  never hand-edited.
- Single task-runner surface: the Makefile (no `tox.ini`).
- OpenSpec schema: `meaningfy`, pinned per `openspec/config.yaml`. In-flight
  changes authored before the pin keep their own schema in `.openspec.yaml`.
