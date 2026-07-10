# Hulubul V1 Model

The Hulubul V1 conceptual model and everything generated from it. The **LinkML
schema is the single source of truth**; every artifact under
[`generated/`](generated/) is produced by `make` and must never be hand-edited.

## Layout

| Path | What |
|------|------|
| [`linkml/`](linkml/) | **Source of truth** — LinkML schema, six domain modules over a common base |
| [`modelspecs/`](modelspecs/) | Human source specs the model was derived from (provenance) |
| [`generated/`](generated/) | All generated artifacts (committed; regenerate with `make`) |
| `*.qea`, `*.png` | Enterprise Architect project + exported source diagrams |

### Source schema ([`linkml/`](linkml/))

| Module | Covers |
|--------|--------|
| [`hulubul.yaml`](linkml/hulubul.yaml) | Umbrella — imports the six modules |
| [`hulubul_common.yaml`](linkml/hulubul_common.yaml) | Shared base: prefixes, reusable slots (`id`, `name`, …) |
| [`hulubul_spatial.yaml`](linkml/hulubul_spatial.yaml) | Address / Area / Place / GeoCoordinates |
| [`hulubul_channel.yaml`](linkml/hulubul_channel.yaml) | Communication channels |
| [`hulubul_agent.yaml`](linkml/hulubul_agent.yaml) | Agents and roles |
| [`hulubul_service.yaml`](linkml/hulubul_service.yaml) | Transport services / offers |
| [`hulubul_request.yaml`](linkml/hulubul_request.yaml) | Delivery requests, parcels |
| [`hulubul_feedback.yaml`](linkml/hulubul_feedback.yaml) | Feedback |

## Regenerating (after any change in `linkml/`)

The LinkML schema is the only thing you edit by hand. Whenever anything under
[`linkml/`](linkml/) changes, regenerate every artifact — run from the repo root:

```bash
pip install linkml neomodel   # once
make all                      # regenerate everything into generated/
```

Or rebuild a single artifact with its target (e.g. `make plantuml`,
`make neomodel`, `make neo4j-constraints`). `make lint` alone validates the
schema; `make clean` wipes `generated/`. The `generated/` tree is committed, so
**commit its changes alongside the schema edit that produced them**. Never edit
files under `generated/` by hand — they are overwritten on the next run. CI
should run `make all` and fail if `generated/` changes (schema and committed
artifacts out of sync).

## Generated artifacts (`make <target>`)

All land under a single `generated/` tree. Run `make all` for the lot.

| Target | Output | Purpose |
|--------|--------|---------|
| `pydantic` | `generated/pydantic/hulubul_models.py` | Pydantic models |
| `owl` | `generated/owl/hulubul.owl.ttl` | OWL ontology |
| `shacl` | `generated/shacl/hulubul.shacl.ttl` | SHACL shapes (validation) |
| `jsonschema` | `generated/jsonschema/hulubul.schema.json` | JSON Schema |
| `erdiagram` | `generated/diagrams/hulubul.er.md` | Mermaid ER diagram (whole model) |
| `plantuml` | `generated/diagrams/hulubul.puml` | UML class diagram, whole model (PlantUML) |
| `classdiagram` | `generated/diagrams/hulubul.class.md` | **UML class diagram, whole model** (Mermaid, renders on GitHub) |
| `neo4j-constraints` | `generated/neo4j/constraints.cypher` | Neo4j constraint DDL |
| `neomodel` | `generated/neomodel/hulubul_ogm.py` | neomodel OGM classes |

Requires `pip install linkml neomodel`. The two custom generators live in
[`../scripts/`](../scripts/).

## Class diagram (whole model)

Generated, not hand-drawn — regenerate with `make classdiagram` (Mermaid,
renders on GitHub) or `make plantuml` (authoritative PlantUML). All diagrams live
under `generated/diagrams/`:

- `generated/diagrams/hulubul.class.md` — whole-model Mermaid class diagram
- `generated/diagrams/hulubul.puml` — whole-model PlantUML UML
- `generated/diagrams/hulubul.er.md` — whole-model Mermaid ER diagram
