# Deterministic generation from the Hulubul LinkML model.
# Generation runs outside the LLM path — never hand-edit a generated file.
# Requires linkml installed:  pip install linkml  (or: uv pip install linkml)

SCHEMA := model/linkml/hulubul.yaml
GEN    := model/generated

.PHONY: all lint pydantic owl shacl jsonschema erdiagram plantuml classdiagram classdiagram-full docs neo4j neo4j-constraints neomodel clean

# Every artifact lands under a single tree: $(GEN)/<target>/...
all: lint pydantic owl shacl jsonschema erdiagram plantuml classdiagram classdiagram-full docs neo4j-constraints neomodel

lint:
	linkml-lint -c .linkmllint.yaml $(SCHEMA)

# Pydantic classes (the "possibly generate pydantic" target).
pydantic:
	mkdir -p $(GEN)/pydantic && gen-pydantic $(SCHEMA) > $(GEN)/pydantic/hulubul_models.py

# Ontology + constraints. Every class/slot carries an explicit hlb: URI, so the
# OWL/SHACL come out complete even though the shipped targets are Python/Neo4j.
owl:
	mkdir -p $(GEN)/owl && gen-owl $(SCHEMA) > $(GEN)/owl/hulubul.owl.ttl

shacl:
	mkdir -p $(GEN)/shacl && gen-shacl $(SCHEMA) > $(GEN)/shacl/hulubul.shacl.ttl

jsonschema:
	mkdir -p $(GEN)/jsonschema && gen-json-schema $(SCHEMA) > $(GEN)/jsonschema/hulubul.schema.json

erdiagram:
	mkdir -p $(GEN)/erdiagram && gen-erdiagram $(SCHEMA) > $(GEN)/erdiagram/hulubul.er.md

# UML class diagram (PlantUML) — the .puml renders via any PlantUML tool/plugin.
plantuml:
	mkdir -p $(GEN)/plantuml && gen-plantuml $(SCHEMA) > $(GEN)/plantuml/hulubul.puml

# UML class diagrams as Mermaid (one per class; render natively on GitHub).
classdiagram:
	mkdir -p $(GEN)/classdiagram && gen-mermaid-class-diagram -d $(GEN)/classdiagram $(SCHEMA)

# Whole-model UML class diagram as a single Mermaid .md (renders on GitHub).
# Custom generator — LinkML only emits per-class; see scripts/gen_mermaid_classdiagram.py.
classdiagram-full:
	mkdir -p $(GEN)/classdiagram && python scripts/gen_mermaid_classdiagram.py $(SCHEMA) > $(GEN)/classdiagram/hulubul.full.md

# Human-readable Markdown docs (one file per class/slot/enum + index), each page
# embedding a Mermaid class diagram of the element.
docs:
	mkdir -p $(GEN)/docs && gen-doc -d $(GEN)/docs $(SCHEMA)

# Neo4j is loaded via linkml-store, not a codegen target:
#   https://linkml.io/linkml-store/how-to/Use-Neo4j.html
# Entity classes carry `id` (identifier) -> Neo4j nodes; object-valued slots are
# `inlined: false` -> Neo4j relationships. Value objects (GeoCoordinates) have no
# id and are embedded. Example load:
#   linkml-store -d neo4j://localhost:7687 insert -i data.yaml --schema $(SCHEMA)
#
# neomodel (https://neomodel.readthedocs.io) is a separate Neo4j OGM. LinkML ships
# no neomodel generator, so we provide one: scripts/gen_neomodel.py (Generator
# subclass + Jinja2 template) — see the `neomodel` target below.
neo4j:
	@echo "Load instances with linkml-store: linkml-store ... insert --schema $(SCHEMA)"
	@echo "No neomodel generator exists in LinkML — see Makefile comment."

# Neo4j constraint DDL for the enforceable subset (identifier -> uniqueness;
# required/typed scalars -> existence/type on Enterprise). Custom generator built
# on linkml.utils.generator.Generator — see scripts/gen_neo4j_constraints.py.
neo4j-constraints:
	mkdir -p $(GEN)/neo4j && python scripts/gen_neo4j_constraints.py $(SCHEMA) > $(GEN)/neo4j/constraints.cypher

# neomodel OGM classes (StructuredNode + RelationshipTo). Custom generator built
# on linkml.utils.generator.Generator + Jinja2 — see scripts/gen_neomodel.py.
neomodel:
	mkdir -p $(GEN)/neomodel && python scripts/gen_neomodel.py $(SCHEMA) > $(GEN)/neomodel/hulubul_ogm.py

clean:
	rm -rf $(GEN)
