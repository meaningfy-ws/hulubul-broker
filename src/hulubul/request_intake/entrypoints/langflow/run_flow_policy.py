"""Policy for LangFlow's cross-flow ``RunFlow`` boundary.

Stock ``RunFlow`` (``lfx==1.10.2``) has two defects on the path a caller flow
uses to invoke a target flow. Both are fixed by ``HulubulRunFlowComponent``,
which delegates the decisions to the pure functions in this module.

Build time -- ``lfx/io/schema.py::create_input_schema_from_dict()`` passes each
target-flow field's *serialized* type label straight to Pydantic as a type
annotation. Scalar labels ("str", "bool") happen to survive because they name
real Python builtins; every other label is an unresolvable forward reference
and ``model_rebuild()`` dies. ``HandleInput`` (connection) fields serialize as
``"other"``, so a single non-advanced handle field on a target flow's input
boundary makes the *caller* flow unbuildable with ``name 'other' is not
defined``. See :func:`select_model_callable_fields`.

Run time -- ``lfx/helpers/flow.py::run_flow()`` defaults each input's category
to ``"chat"``, and ``Graph._set_inputs()`` then silently skips any target
vertex whose component type is not ``ChatInput``. A payload aimed at a custom
boundary component therefore never lands and the boundary rejects an empty
``input_value``. See :func:`with_unrestricted_input_type`.

This module is deliberately free of ``lfx``/``langflow`` imports so the policy
stays unit-testable without a LangFlow server installation; it speaks plain
mappings, and the component re-wraps the results in ``dotdict``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Final

__all__ = [
    "CONNECTION_ONLY_FIELD_TYPES",
    "FIELD_NAME_KEY",
    "FIELD_TYPE_KEY",
    "INPUT_TYPE_KEY",
    "SCHEMA_SAFE_FIELD_TYPES",
    "UNRESTRICTED_INPUT_TYPE",
    "excluded_field_names",
    "select_model_callable_fields",
    "with_unrestricted_input_type",
]

FIELD_NAME_KEY: Final = "name"
FIELD_TYPE_KEY: Final = "type"
INPUT_TYPE_KEY: Final = "type"

UNKNOWN_FIELD_NAME: Final = "<unnamed>"

#: LangFlow's placeholder label for "this field is a connection; its real type
#: lives in ``input_types``". Such fields are fed by a graph edge, never by a
#: model-authored tool argument, so they are excluded from the tool schema
#: rather than mapped to some stand-in annotation. Mapping them to ``str``
#: would silence the build-time crash but would also invite an agent to
#: fabricate values for trusted context (an envelope, a routing context) that
#: must only ever arrive over a fixed edge.
CONNECTION_ONLY_FIELD_TYPES: Final[frozenset[str]] = frozenset({"other"})

#: Serialized field labels that may be exposed as tool arguments, mapped to the
#: annotation label ``create_input_schema_from_dict()`` can resolve. Values stay
#: strings rather than Python type objects so the same table keeps working
#: against the stricter label deserializer in later ``lfx`` releases.
SCHEMA_SAFE_FIELD_TYPES: Final[Mapping[str, str]] = {
    "str": "str",
    "int": "int",
    "float": "float",
    "bool": "bool",
    "boolean": "bool",
    "dict": "dict",
    "NestedDict": "dict",
    "table": "dict",
    "code": "str",
    "file": "str",
    "prompt": "str",
    "mustache": "str",
    "query": "str",
    "tab": "str",
}

#: Input category that disables ``Graph._set_inputs()``'s ChatInput/TextInput
#: class filter. Safe to force here because every payload built by ``RunFlow``
#: already names its exact target vertex, so widening the category cannot
#: broadcast a value to unrelated input components.
UNRESTRICTED_INPUT_TYPE: Final = "any"


def _schema_safe_type(field: Mapping[str, Any]) -> str | None:
    """Return the schema-safe annotation label for a field, or ``None``.

    ``None`` means "do not expose this field as a tool argument": either it is
    a connection-only field, or its serialized label has no annotation we can
    render faithfully.
    """
    raw_type = field.get(FIELD_TYPE_KEY)
    if not isinstance(raw_type, str) or raw_type in CONNECTION_ONLY_FIELD_TYPES:
        return None
    return SCHEMA_SAFE_FIELD_TYPES.get(raw_type)


def select_model_callable_fields(
    fields: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return the target-flow fields that may become model-callable arguments.

    Each returned field is a *copy* whose ``type`` carries a schema-safe
    annotation label; the caller's graph metadata is never mutated. Fields that
    cannot be exposed are dropped rather than raising: an unfamiliar field on a
    target flow must not make the calling flow unbuildable, and dropping fails
    in the safe direction (the model simply cannot supply that argument).
    """
    selected: list[dict[str, Any]] = []
    for field in fields:
        annotation = _schema_safe_type(field)
        if annotation is None:
            continue
        exposed = dict(field)
        exposed[FIELD_TYPE_KEY] = annotation
        selected.append(exposed)
    return selected


def excluded_field_names(fields: Iterable[Mapping[str, Any]]) -> list[str]:
    """Return the names of fields :func:`select_model_callable_fields` drops.

    Kept separate so the component can report what it withheld without the
    policy itself having to know about logging.
    """
    return [
        str(field.get(FIELD_NAME_KEY, UNKNOWN_FIELD_NAME))
        for field in fields
        if _schema_safe_type(field) is None
    ]


def with_unrestricted_input_type(
    payloads: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return copies of ``payloads`` forced to the unrestricted input category.

    Overrides any category already present: a caller-supplied ``"chat"`` is
    exactly the value that makes ``Graph._set_inputs()`` drop the payload for a
    custom boundary component.
    """
    return [{**payload, INPUT_TYPE_KEY: UNRESTRICTED_INPUT_TYPE} for payload in payloads]
