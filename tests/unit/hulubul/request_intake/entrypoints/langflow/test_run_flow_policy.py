"""Tests for the cross-flow RunFlow tool-boundary policy."""

import copy
from typing import Any

import pytest

from hulubul.request_intake.entrypoints.langflow.run_flow_policy import (
    UNRESTRICTED_INPUT_TYPE,
    deepcopy_outputs_with_fallback,
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


class _Unpicklable:
    """Stand-in for a live object `copy.deepcopy` cannot handle (e.g. an
    `asyncio.Task`), without depending on asyncio internals in the test."""

    def __deepcopy__(self, memo: dict[int, Any]) -> "_Unpicklable":
        msg = "cannot pickle '_Unpicklable' object"
        raise TypeError(msg)


class TestDeepcopyOutputsWithFallback:
    """Per-tool-call copy of a component's cached outputs."""

    def test_deepcopyable_values_are_deep_copied(self) -> None:
        outputs_map = {"response": {"nested": ["value"]}}

        copied, fell_back = deepcopy_outputs_with_fallback(outputs_map, {})

        assert copied == outputs_map
        assert copied["response"] is not outputs_map["response"]
        assert fell_back == []

    def test_unpicklable_value_falls_back_to_shared_reference(self) -> None:
        """A cached `component_as_tool` wrapper carrying a live asyncio.Task."""
        unpicklable = _Unpicklable()
        outputs_map = {"component_as_tool": unpicklable}

        copied, fell_back = deepcopy_outputs_with_fallback(outputs_map, {})

        assert copied["component_as_tool"] is unpicklable
        assert fell_back == ["component_as_tool"]

    def test_mixed_map_only_reports_the_entries_that_failed(self) -> None:
        unpicklable = _Unpicklable()
        outputs_map = {
            "HulubulContractResultBoundary-hlb-lf-10-result-v1~response": {"value": 1},
            "component_as_tool": unpicklable,
        }

        copied, fell_back = deepcopy_outputs_with_fallback(outputs_map, {})

        assert copied["HulubulContractResultBoundary-hlb-lf-10-result-v1~response"] == {"value": 1}
        assert (
            copied["HulubulContractResultBoundary-hlb-lf-10-result-v1~response"]
            is not outputs_map["HulubulContractResultBoundary-hlb-lf-10-result-v1~response"]
        )
        assert copied["component_as_tool"] is unpicklable
        assert fell_back == ["component_as_tool"]

    def test_empty_map_yields_no_result_and_no_fallback(self) -> None:
        assert deepcopy_outputs_with_fallback({}, {}) == ({}, [])

    def test_memo_is_shared_with_the_caller_deepcopy(self) -> None:
        """A shared `memo` resolves reference cycles consistently across calls."""
        shared_value = {"marker": "shared"}
        outputs_map = {"first": shared_value, "second": shared_value}
        memo: dict[int, Any] = {}

        copied, fell_back = deepcopy_outputs_with_fallback(outputs_map, memo)

        assert fell_back == []
        assert copied["first"] is copied["second"]
        assert copied["first"] is not shared_value

    def test_source_map_is_not_mutated(self) -> None:
        unpicklable = _Unpicklable()
        outputs_map = {"component_as_tool": unpicklable, "response": {"value": 1}}
        original = copy.copy(outputs_map)

        deepcopy_outputs_with_fallback(outputs_map, {})

        assert outputs_map == original
