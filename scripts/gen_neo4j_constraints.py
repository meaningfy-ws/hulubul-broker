#!/usr/bin/env python3
"""Neo4j constraint generator, built on the LinkML ``Generator`` infrastructure.

Subclasses ``linkml.utils.generator.Generator`` so it reuses the standard schema
loading, import resolution, ``SchemaView`` access, and the shared ``gen-*`` CLI
(``--format``, ``--stacktrace``, version handling) — identical in shape to
``gen-owl`` / ``gen-shacl``.

Emits only the constraints Neo4j can actually enforce, derived unambiguously
from LinkML (SHACL is a poor source — it has no uniqueness):

  identifier slot        -> uniqueness constraint      (Community)
  required scalar/enum   -> existence constraint       (Enterprise)
  typed scalar/enum      -> property-type constraint   (Enterprise)

Mapping rules (mirror the linkml-store Neo4j mapping documented in the Makefile):
  * entity class   = concrete class with an ``id`` (identifier) slot -> :Label node
  * value object   = class without an identifier -> inlined, NOT a node -> skipped
  * abstract class = never instantiated -> skipped (concrete subclasses carry
    their own inherited ``id`` and get constraints individually)
  * object-valued slot (range is a class) -> a relationship, not a node property
    -> skipped
  * multivalued scalar -> ambiguous storage in Neo4j -> skipped

Usage:  python model/gen/gen_neo4j_constraints.py model/linkml/hulubul.yaml
   or:  gen-neo4j-constraints model/linkml/hulubul.yaml   (once installed)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import click
from linkml.utils.generator import Generator, shared_arguments  # type: ignore[import-untyped]

# LinkML scalar range -> Neo4j property type (for `IS :: <TYPE>` constraints).
NEO4J_TYPES = {
    "string": "STRING",
    "uriorcurie": "STRING",
    "uri": "STRING",
    "curie": "STRING",
    "ncname": "STRING",
    "integer": "INTEGER",
    "float": "FLOAT",
    "double": "FLOAT",
    "decimal": "FLOAT",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "datetime": "DATETIME",
    "time": "LOCAL_TIME",
}


@dataclass
class Neo4jConstraintGenerator(Generator):  # type: ignore[misc]
    """Generate Neo4j constraint DDL (Cypher) for the enforceable LinkML subset."""

    generatorname: ClassVar[str] = "gen-neo4j-constraints"
    generatorversion: ClassVar[str] = "1.0.0"
    valid_formats: ClassVar[list[str]] = ["cypher"]
    file_extension: ClassVar[str] = "cypher"
    uses_schemaloader: ClassVar[bool] = False  # we drive everything through self.schemaview

    def _is_entity(self, class_name: str) -> bool:
        """A class becomes a Neo4j node iff it is concrete and has an identifier."""
        cls = self.schemaview.get_class(class_name)
        return not cls.abstract and self.schemaview.get_identifier_slot(class_name) is not None

    @staticmethod
    def _neo4j_type(range_: str | None) -> str:
        """Neo4j property type for a scalar/enum range (enums store as STRING)."""
        return NEO4J_TYPES.get(range_ or "string", "STRING")

    def _class_constraints(self, class_name: str) -> list[str]:
        sv = self.schemaview
        label = class_name
        id_slot = sv.get_identifier_slot(class_name)
        class_names = set(sv.all_classes())

        out = [f"// ---- {label} " + "-" * max(0, 68 - len(label))]

        # Identifier -> uniqueness (Community). NODE KEY (unique+exists) is the
        # Enterprise upgrade; noted rather than emitted so this runs on Community.
        p = id_slot.name
        out.append(
            f"CREATE CONSTRAINT {label.lower()}_{p}_unique IF NOT EXISTS\n"
            f"FOR (n:`{label}`) REQUIRE n.`{p}` IS UNIQUE;"
            "  // NODE KEY on Enterprise"
        )

        for slot in sv.class_induced_slots(class_name):
            if slot.name == id_slot.name:
                continue
            if slot.range in class_names:  # object-valued -> relationship
                continue
            if slot.multivalued:  # ambiguous storage -> skip
                continue
            p = slot.name
            if slot.required:
                out.append(
                    f"CREATE CONSTRAINT {label.lower()}_{p}_exists IF NOT EXISTS\n"
                    f"FOR (n:`{label}`) REQUIRE n.`{p}` IS NOT NULL;"
                    "  // Enterprise"
                )
            out.append(
                f"CREATE CONSTRAINT {label.lower()}_{p}_type IF NOT EXISTS\n"
                f"FOR (n:`{label}`) REQUIRE n.`{p}` IS :: {self._neo4j_type(slot.range)};"
                "  // Enterprise"
            )
        return out

    def serialize(self, **kwargs) -> str:
        sv = self.schemaview
        header = [
            f"// Neo4j constraints generated from {self.schema.name}",
            "// DO NOT EDIT — regenerate with `make neo4j-constraints`.",
            "// Uniqueness runs on Community Edition; existence/type need Enterprise.",
            "",
        ]
        body = [
            "\n".join(self._class_constraints(cn))
            for cn in sorted(sv.all_classes())
            if self._is_entity(cn)
        ]
        return "\n".join(header) + "\n\n".join(body) + "\n"


@shared_arguments(Neo4jConstraintGenerator)
@click.command(name="gen-neo4j-constraints")
@click.version_option(Neo4jConstraintGenerator.generatorversion, "-V", "--version")
def cli(yamlfile, **kwargs):
    """Generate Neo4j constraint DDL from a LinkML schema."""
    gen = Neo4jConstraintGenerator(yamlfile, **kwargs)
    print(gen.serialize())


if __name__ == "__main__":
    cli()
