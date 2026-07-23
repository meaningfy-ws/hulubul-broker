#!/usr/bin/env python3
"""neomodel OGM generator, built on the LinkML ``Generator`` infrastructure.

Subclasses ``linkml.utils.generator.Generator`` (like ``gen_neo4j_constraints``)
so it reuses schema loading, import resolution, ``SchemaView`` and the shared
``gen-*`` CLI. Renders neomodel ``StructuredNode`` classes with a Jinja2 template.

Mapping to neomodel:
  * non-abstract class          -> ``StructuredNode`` subclass (label = class name)
  * abstract class              -> skipped (never instantiated; concrete subclasses
    carry their full induced slot set, so each is standalone — no Python inheritance,
    mirroring the flat per-label mapping used for the Neo4j constraints)
  * identifier slot             -> ``StringProperty(unique_index=True, required=True)``
  * scalar slot                 -> typed ``*Property`` (``required=True`` if required)
  * enum slot                   -> ``StringProperty(choices=...)``
  * multivalued scalar/enum     -> ``ArrayProperty(<inner>)``
  * object-valued slot          -> ``RelationshipTo(target, 'REL_NAME', cardinality=...)``

Divergence from the linkml-store mapping: neomodel has no inlining, so value objects
(e.g. GeoCoordinates, no id) also become StructuredNodes and are reached by a
relationship rather than embedded. Noted in the generated header.

Usage:  python scripts/gen_neomodel.py model/linkml/hulubul.yaml
   or:  gen-neomodel model/linkml/hulubul.yaml   (once installed)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

import click
from jinja2 import Template
from linkml.utils.generator import Generator, shared_arguments  # type: ignore[import-untyped]
from linkml_runtime.linkml_model import SlotDefinition  # type: ignore[import-untyped]

# LinkML scalar range -> neomodel property class.
NEOMODEL_PROP = {
    "string": "StringProperty",
    "uri": "StringProperty",
    "uriorcurie": "StringProperty",
    "curie": "StringProperty",
    "ncname": "StringProperty",
    "time": "StringProperty",  # neomodel has no time-only property
    "integer": "IntegerProperty",
    "float": "FloatProperty",
    "double": "FloatProperty",
    "decimal": "FloatProperty",
    "boolean": "BooleanProperty",
    "date": "DateProperty",
    "datetime": "DateTimeProperty",
}

_TEMPLATE = Template(
    '''"""neomodel OGM classes generated from {{ schema_name }}.

DO NOT EDIT — regenerate with `make neomodel`.
Value objects (no identifier) are modelled as StructuredNodes reached by a
relationship: neomodel has no inlining.
"""
from neomodel import (
    StructuredNode,
    StringProperty, IntegerProperty, FloatProperty, BooleanProperty,
    DateProperty, DateTimeProperty, ArrayProperty,
    RelationshipTo, ZeroOrMore, ZeroOrOne, OneOrMore, One,
)


{% for c in classes %}
class {{ c.name }}(StructuredNode):
    """{{ c.doc }}"""
{% for line in c.lines %}
    {{ line }}
{% endfor %}
{% if not c.lines %}
    pass
{% endif %}


{% endfor %}''',
    trim_blocks=True,
    lstrip_blocks=True,
)


def _rel_name(slot_name: str) -> str:
    """camelCase slot -> UPPER_SNAKE relationship type (providesService -> PROVIDES_SERVICE)."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", slot_name).upper()


def _cardinality(required: bool, multivalued: bool) -> str:
    if multivalued:
        return "OneOrMore" if required else "ZeroOrMore"
    return "One" if required else "ZeroOrOne"


@dataclass
class NeomodelGenerator(Generator):  # type: ignore[misc]
    """Generate neomodel OGM classes for the LinkML entity/value-object classes."""

    generatorname: ClassVar[str] = "gen-neomodel"
    generatorversion: ClassVar[str] = "1.0.0"
    valid_formats: ClassVar[list[str]] = ["python"]
    file_extension: ClassVar[str] = "py"
    uses_schemaloader: ClassVar[bool] = False

    def _choices_arg(self, enum_name: str) -> str:
        pv = self.schemaview.get_enum(enum_name).permissible_values
        pairs = ", ".join(f"({v!r}, {v!r})" for v in pv)
        return f"choices=({pairs},)"

    def _property_line(self, slot: SlotDefinition, id_name: str | None) -> str:
        name = slot.name
        if name == id_name:
            return f"{name} = StringProperty(unique_index=True, required=True)"

        is_enum = slot.range in self.schemaview.all_enums()
        base = "StringProperty" if is_enum else NEOMODEL_PROP.get(slot.range, "StringProperty")
        inner_args = [self._choices_arg(slot.range)] if is_enum else []

        if slot.multivalued:
            inner = f"{base}({', '.join(inner_args)})"
            outer = ", required=True" if slot.required else ""
            return f"{name} = ArrayProperty({inner}{outer})"

        args = list(inner_args)
        if slot.required:
            args.append("required=True")
        return f"{name} = {base}({', '.join(args)})"

    def _relationship_line(self, slot: SlotDefinition) -> str:
        card = _cardinality(bool(slot.required), bool(slot.multivalued))
        return (
            f"{slot.name} = RelationshipTo('{slot.range}', "
            f"'{_rel_name(slot.name)}', cardinality={card})"
        )

    def _class_dict(self, class_name: str) -> dict[str, str | list[str]]:
        sv = self.schemaview
        class_names = set(sv.all_classes())
        id_slot = sv.get_identifier_slot(class_name)
        id_name = id_slot.name if id_slot else None

        lines = []
        for slot in sv.class_induced_slots(class_name):
            if slot.range in class_names:
                lines.append(self._relationship_line(slot))
            else:
                lines.append(self._property_line(slot, id_name))

        doc = " ".join((sv.get_class(class_name).description or class_name).split())
        return {"name": class_name, "doc": doc, "lines": lines}

    def serialize(self, **kwargs: Any) -> str:
        sv = self.schemaview
        classes = [
            self._class_dict(cn) for cn in sorted(sv.all_classes()) if not sv.get_class(cn).abstract
        ]
        return _TEMPLATE.render(schema_name=self.schema.name, classes=classes)


@shared_arguments(NeomodelGenerator)  # type: ignore[misc]
@click.command(name="gen-neomodel")
@click.version_option(NeomodelGenerator.generatorversion, "-V", "--version")
def cli(yamlfile: str, **kwargs: Any) -> None:
    """Generate neomodel OGM classes from a LinkML schema."""
    gen = NeomodelGenerator(yamlfile, **kwargs)
    print(gen.serialize())


if __name__ == "__main__":
    cli()
