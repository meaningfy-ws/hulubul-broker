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

## Modelling workflow (how `linkml/` comes to exist)

The LinkML schema isn't hand-designed from scratch — it's derived through a
four-stage pipeline, each stage a deliberate hand-off between a modelling
tool, an LLM transformation, and deterministic generation:

1. **Model in Enterprise Architect.** The conceptual/domain model is drawn as
   UML in the Sparx EA project ([`hulubul-transport.qea`](hulubul-transport.qea)),
   then UML diagrams are exported as images (the `*.png` files in this
   directory — `feedback.png`, `request.png`, `roles.png`, `spatial.png`,
   `transportService.png`).
2. **Transform the diagram images into modelspecs.** An LLM reads the
   exported UML diagram images and writes two human-readable Markdown specs
   under [`modelspecs/`](modelspecs/):
   [`hulubul_v1_model_spec.md`](modelspecs/hulubul_v1_model_spec.md) (the
   domain model itself) and
   [`hulubul_v1_access_control.md`](modelspecs/hulubul_v1_access_control.md)
   (access-control rules). These are the provenance record between the UML
   diagrams and the LinkML schema — human-readable, reviewable prose, not
   generated output.
3. **Transform the modelspecs into LinkML.** An LLM, using the
   `meaningfy-architecture:linkml-engineering` skill (LinkML authoring
   conventions, generator wiring, quality gates), turns the two modelspecs
   into the LinkML schema modules under [`linkml/`](linkml/). This is the
   one hand-authored (LLM-assisted) step in the pipeline — everything
   downstream of it is deterministic.
4. **Generate every downstream artifact deterministically.** `make all`
   drives LinkML's stock generators plus the repo's custom generators
   under [`../scripts/`](../scripts/) to produce every artifact in
   [`generated/`](generated/) and the Pydantic domain models inside the
   `hulubul` package. See "How to use" and "Regenerating" below — this step
   has no LLM in the loop and is fully reproducible.

Each stage's output is committed; regenerating a downstream artifact never
requires re-running an upstream stage unless the upstream content actually
changed (e.g. don't re-derive `linkml/` from the modelspecs unless the
modelspecs themselves changed).

## How to use

Everything is driven by `make` from the **repo root** (not this folder). One-time
setup, then a single command regenerates all artifacts:

```bash
pip install linkml neomodel   # one-time: the generators + neomodel property types
make all                       # lint the schema, then regenerate everything
```

`make all` runs the schema linter first (`make lint`), then every generator,
writing into `generated/`.

## Regenerating (after any change in `linkml/`)

The **LinkML schema under [`linkml/`](linkml/) is the only thing you edit by hand.**
Files under `generated/` are outputs — never edit them; the next `make` overwrites
them. The workflow after touching the schema:

1. Edit the relevant module in [`linkml/`](linkml/).
2. `make all` (or a single target below, e.g. `make neomodel`) from the repo root.
3. Review the diff and **commit the `generated/` changes in the same commit as the
   schema edit** — the committed artifacts must always match the schema.

Handy targets: `make lint` (validate only), `make clean` (wipe `generated/`),
`make <target>` (rebuild one artifact — see the table below).

> **CI drift check.** CI runs `make all` and fails if `generated/` changes, proving
> the committed artifacts are in sync. **Caveat:** the OWL and SHACL Turtle output
> is not byte-stable across runs (rdflib reorders blank nodes), so a naive `git
> diff` check will flag spurious churn on `owl`/`shacl`. Either exclude those two
> from the drift check or normalise them (e.g. `rdfpipe`/canonicalisation) before
> comparing. The Python/JSON/Mermaid/Cypher outputs are deterministic.

## Generated artifacts (`make <target>`)

All land under a single `generated/` tree, except `pydantic` — see ADR-019
(`architecture/decisions/README.md`) — which lands inside the installed `hulubul`
package so it's importable. Run `make all` for the lot.

| Target | Output | Purpose |
|--------|--------|---------|
| `pydantic` | `hulubul/core/models/domain/hulubul_models.py` (outside `generated/`, per ADR-019) | Pydantic models |
| `owl` | `generated/owl/hulubul.owl.ttl` | OWL ontology |
| `shacl` | `generated/shacl/hulubul.shacl.ttl` | SHACL shapes (validation) |
| `jsonschema` | `generated/jsonschema/hulubul.schema.json` | JSON Schema |
| `erdiagram` | `generated/diagrams/hulubul.er.md` | Mermaid ER diagram (whole model) |
| `plantuml` | `generated/diagrams/hulubul.puml` | UML class diagram, whole model (PlantUML) |
| `classdiagram` | `generated/diagrams/hulubul.class.md` | **UML class diagram, whole model** (Mermaid, renders on GitHub) |
| `neo4j-constraints` | `generated/neo4j/constraints.cypher` | Neo4j constraint DDL |
| `neomodel` | `generated/neomodel/hulubul_ogm.py` | neomodel OGM classes |

Most targets call LinkML's stock `gen-*` tools. Three artifacts have no LinkML
generator, so they use custom ones in [`../scripts/`](../scripts/) (each a
`linkml.utils.generator.Generator` subclass): `classdiagram`
(whole-model Mermaid), `neo4j-constraints` (Cypher DDL) and `neomodel` (OGM).

## Class diagram (whole model)

Generated, not hand-drawn — regenerate with `make classdiagram` (Mermaid,
renders on GitHub) or `make plantuml` (authoritative PlantUML). All diagrams live
under `generated/diagrams/`:

- `generated/diagrams/hulubul.class.md` — whole-model Mermaid class diagram
- `generated/diagrams/hulubul.puml` — whole-model PlantUML UML
- `generated/diagrams/hulubul.er.md` — whole-model Mermaid ER diagram
