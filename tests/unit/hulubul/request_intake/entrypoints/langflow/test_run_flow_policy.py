"""Tests for the cross-flow RunFlow tool-boundary policy."""

from typing import Any

import pytest

from hulubul.request_intake.entrypoints.langflow.run_flow_policy import (
    UNRESTRICTED_INPUT_TYPE,
    excluded_field_names,
    select_model_callable_fields,
    with_unrestricted_input_type,
)

CONNECTION_FIELD_TYPE = "other"


def _field(name: str, field_type: Any) -> dict[str, Any]:
    """A target-flow field as `RunFlowBaseComponent.get_new_fields` emits it."""
    return {
        "name": name,
        "display_name": name.replace("_", " ").title(),
        "type": field_type,
        "input_types": ["Data", "JSON"],
        "required": False,
        "is_list": False,
        "tool_mode": True,
        "value": "",
    }


class TestSelectModelCallableFields:
    """Which target-flow fields may be offered to a model as tool arguments."""

    def test_connection_field_is_withheld(self) -> None:
        """A HandleInput serializes as `other` -- edge-fed, never model-authored."""
        fields = [_field("envelope", CONNECTION_FIELD_TYPE)]

        assert select_model_callable_fields(fields) == []

    def test_unmappable_type_is_withheld_rather_than_raising(self) -> None:
        """An unfamiliar target field must not make the calling flow unbuildable."""
        fields = [_field("mystery", "SomeFutureFieldType")]

        assert select_model_callable_fields(fields) == []

    @pytest.mark.parametrize("field_type", [None, 42, {"nested": "label"}, ["str"]])
    def test_non_string_type_is_withheld(self, field_type: Any) -> None:
        fields = [_field("weird", field_type)]

        assert select_model_callable_fields(fields) == []

    @pytest.mark.parametrize(
        ("serialized_type", "expected_annotation"),
        [
            ("str", "str"),
            ("int", "int"),
            ("float", "float"),
            ("bool", "bool"),
            ("boolean", "bool"),
            ("dict", "dict"),
            ("NestedDict", "dict"),
            ("table", "dict"),
            ("code", "str"),
            ("file", "str"),
            ("prompt", "str"),
            ("mustache", "str"),
            ("query", "str"),
            ("tab", "str"),
        ],
    )
    def test_safe_type_is_normalized_to_a_resolvable_annotation(
        self, serialized_type: str, expected_annotation: str
    ) -> None:
        fields = [_field("input_value", serialized_type)]

        selected = select_model_callable_fields(fields)

        assert [f["type"] for f in selected] == [expected_annotation]

    def test_remaining_field_metadata_is_preserved(self) -> None:
        fields = [_field("input_value", "str")]

        (selected,) = select_model_callable_fields(fields)

        assert selected["name"] == "input_value"
        assert selected["display_name"] == "Input Value"
        assert selected["input_types"] == ["Data", "JSON"]
        assert selected["required"] is False

    def test_source_fields_are_not_mutated(self) -> None:
        """The caller's graph metadata is shared state -- copy, never edit."""
        fields = [_field("input_value", "boolean"), _field("envelope", CONNECTION_FIELD_TYPE)]

        select_model_callable_fields(fields)

        assert [f["type"] for f in fields] == ["boolean", CONNECTION_FIELD_TYPE]

    def test_mixed_boundary_keeps_only_the_public_field(self) -> None:
        """The shape of LF-10's boundary once `advanced=False` exposes its handles."""
        fields = [
            _field("envelope", CONNECTION_FIELD_TYPE),
            _field("routing_context", CONNECTION_FIELD_TYPE),
            _field("input_value", "str"),
            _field("contract_kind", "str"),
        ]

        selected = select_model_callable_fields(fields)

        assert [f["name"] for f in selected] == ["input_value", "contract_kind"]

    def test_no_fields_yields_no_selection(self) -> None:
        assert select_model_callable_fields([]) == []


class TestExcludedFieldNames:
    """What the component reports as withheld."""

    def test_lists_only_the_withheld_fields(self) -> None:
        fields = [
            _field("envelope", CONNECTION_FIELD_TYPE),
            _field("input_value", "str"),
            _field("mystery", "SomeFutureFieldType"),
        ]

        assert excluded_field_names(fields) == ["envelope", "mystery"]

    def test_unnamed_field_gets_a_placeholder(self) -> None:
        assert excluded_field_names([{"type": CONNECTION_FIELD_TYPE}]) == ["<unnamed>"]

    def test_nothing_withheld_when_every_field_is_safe(self) -> None:
        assert excluded_field_names([_field("input_value", "str")]) == []


class TestWithUnrestrictedInputType:
    """Runtime payload category, which decides whether injection lands at all."""

    def test_missing_category_is_supplied(self) -> None:
        payloads = [{"components": ["boundary-id"], "input_value": '{"operation":"read"}'}]

        assert with_unrestricted_input_type(payloads) == [
            {
                "components": ["boundary-id"],
                "input_value": '{"operation":"read"}',
                "type": UNRESTRICTED_INPUT_TYPE,
            }
        ]

    def test_chat_category_is_overridden(self) -> None:
        """`chat` is exactly the value that makes _set_inputs drop the payload."""
        payloads = [{"components": ["boundary-id"], "input_value": "payload", "type": "chat"}]

        assert with_unrestricted_input_type(payloads)[0]["type"] == UNRESTRICTED_INPUT_TYPE

    def test_source_payloads_are_not_mutated(self) -> None:
        payloads = [{"components": ["boundary-id"], "input_value": "payload", "type": "chat"}]

        with_unrestricted_input_type(payloads)

        assert payloads[0]["type"] == "chat"

    def test_every_payload_is_covered(self) -> None:
        payloads = [
            {"components": ["first"], "input_value": "a"},
            {"components": ["second"], "input_value": "b", "type": "text"},
        ]

        assert [p["type"] for p in with_unrestricted_input_type(payloads)] == [
            UNRESTRICTED_INPUT_TYPE,
            UNRESTRICTED_INPUT_TYPE,
        ]

    def test_no_payloads_yields_no_result(self) -> None:
        assert with_unrestricted_input_type([]) == []
