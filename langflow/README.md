# LangFlow Flows (Flow-As-Code)

This directory is the Git-authoritative source for Hulubul's LangFlow flows.
`langflow/flow-manifest.yaml` is the single source of truth for which flows
exist, their stable IDs, and their deployment order — never LangFlow's own
database or UI state.

## The three Change 1 flows

Deployed in this fixed order (also declared in `flow-manifest.yaml`'s
`deployment_order`):

1. **`lf-70-data-access`** (`flows/10-lf-70-data-access.json`) — the only flow
   allowed to hold an MCP toolkit against Neo4j. Accepts one
   `DataOperationRequest` and returns one validated `DataOperationResult`.
2. **`lf-10-request-intake`** (`flows/20-lf-10-request-intake.json`) — the
   intake agent. Uses `lf-70-data-access` as its sole logical tool (via
   `RunFlow`), never talks to Neo4j directly.
3. **`lf-00-main-router`** (`flows/30-lf-00-main-router.json`) — the Chat
   Input/Output entrypoint. Fetches routing context from `lf-70-data-access`
   and hands off to `lf-10-request-intake` as its only tool.

Flow files themselves are created later, from a pinned LangFlow 1.10.2
export (see the plan doc's Task 32/38/44) — this README documents the
toolchain that governs them, not the flows' internal contents.

## Manifest as source of truth

`flow-manifest.yaml` declares, per flow: its stable UUIDv5 `id`, its file
path, its public input/result component IDs, and any `RunFlow` references to
other manifest flows. `runtime_bindings` declares the only environment
variables a flow's `OpenAIModel` components are ever allowed to reference at
runtime (currently `HULUBUL_LLM_MODEL`, `HULUBUL_LLM_BASE_URL`,
`HULUBUL_LLM_API_KEY`) — nothing outside that list may be restored into a
flow file.

`.lfx/environments.yaml` maps the `local`/`ci` LFX environment names used by
the push/pull/status tooling to their target URLs and secrets.

## Edit-cycle workflow

1. Export the flow from a running, pinned LangFlow 1.10.2 instance (UI or
   `lfx export`).
2. Normalize it deterministically:
   ```
   poetry run python scripts/normalize_langflow_flows.py langflow/flows/<file>.json
   ```
   This sorts JSON keys, preserves node/edge array order, and restores only
   the manifest-allowlisted runtime variable names into `load_from_db=true`
   fields — restoring anything else raises `NormalizationError`.
3. Validate it against the manifest, topology, and security rules:
   ```
   poetry run python scripts/validate_langflow_assets.py langflow/flow-manifest.yaml
   ```
   This enforces: exact manifest schema/IDs/deployment order, no flows
   outside the manifest ("UI-only" flows), no `LF-20` references, MCP tools
   only inside `lf-70-data-access`, and an environment-variable allowlist.
4. Commit the normalized flow file together with any manifest changes in the
   same commit.

`make check-flows` runs steps 2-3 (plus strict `lfx validate`/`lfx upgrade`),
but is **not** part of `make ci-static` yet. Its manifest/topology validation
step (`validate_langflow_assets.py`) is currently commented out in the
Makefile with a `TODO(Checkpoint 8)` note, since it requires the flow JSON
files this README describes creating "later" — see step 2 above.

## Drift detection and pinned component schemas

`scripts/inspect_langflow_components.py` captures the pinned LangFlow 1.10.2
component schemas (ports, handles, MCP tool inventory) used to catch
component-shape drift; its output is checked in at
`.lfx/component-schemas-pinned.json`.

LFX push/pull/status Make targets and the clean-instance drift check (failing
on UI-only, missing, duplicate, or untracked remote flows) are tracked
separately — see `openspec/changes/deliver-phase-1-request-intake-thread/tasks.md`
task 7.6.
