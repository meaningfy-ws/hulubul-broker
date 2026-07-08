# Specifications (data structures) — PLACEHOLDER

The canonical **LinkML domain schema** and derived contracts live here. **Not yet
written — deferred to the modelling session** (the one blocked item of task #3).

## What goes here (after modelling)

- `domain.linkml.yaml` — canonical entities, attributes, relationships:
  **Brokerage**, **ParcelRequest**, **Sender**, **Receiver**, **Parcel**,
  **ContactPoint** (⊂ **TransporterProfile**), **Route/Zone**, **Session/GoalStack**,
  **SlotForm**, **CommunicationEntry**, plus the **Status** enum
  (mirroring `../diagrams/workflows.md`).
- The **access-visibility rules** (ADR-015): what "own pact" and "public info of prior
  contacts" mean as concrete relationships/properties.
- The **scoped-MCP operation catalogue** (ADR-005/015): named per-party read ops +
  validated write use-cases.
- The **dialogue-act / slot naming subset** (ADR-018) — optional vocabulary only.

## Why deferred

The data model is the subject of a dedicated modelling session (see
`../HANDOVER.md` §6). Writing LinkML before that would bake in guesses. Everything
else in the architecture set is complete and cross-references these placeholders.
