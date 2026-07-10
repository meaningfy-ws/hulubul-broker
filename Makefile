# Deterministic generation from the Hulubul LinkML model.
# Generation runs outside the LLM path — never hand-edit a generated file.
# Requires linkml installed:  pip install linkml  (or: uv pip install linkml)

SCHEMA := model/linkml/hulubul.yaml
GEN    := model/generated

.PHONY: all lint pydantic owl shacl jsonschema erdiagram docs neo4j neo4j-constraints clean

# Every artifact lands under a single tree: $(GEN)/<target>/...
all: lint pydantic owl shacl jsonschema erdiagram docs neo4j-constraints

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

# Human-readable Markdown docs (one file per class/slot/enum + index).
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
# NO neomodel generator — the native path above is linkml-store. To emit neomodel
# StructuredNode/StructuredRel classes you'd add a custom Jinja generator; not
# provided here. Ask if you want it built.
neo4j:
	@echo "Load instances with linkml-store: linkml-store ... insert --schema $(SCHEMA)"
	@echo "No neomodel generator exists in LinkML — see Makefile comment."

# Neo4j constraint DDL for the enforceable subset (identifier -> uniqueness;
# required/typed scalars -> existence/type on Enterprise). Custom generator built
# on linkml.utils.generator.Generator — see scripts/gen_neo4j_constraints.py.
neo4j-constraints:
	mkdir -p $(GEN)/neo4j && python scripts/gen_neo4j_constraints.py $(SCHEMA) > $(GEN)/neo4j/constraints.cypher

clean:
	rm -rf $(GEN)
