"""Tests for the Hulubul Run Flow component's two overrides.

The point of these tests is that they run against the *real* ``lfx`` machinery
the overrides exist to protect: the schema builder that crashes on a raw
connection-field label, and the payload builder that omits the input category.
"""

import asyncio
from typing import Any

import pytest
from lfx.components.flow_controls.run_flow import RunFlowComponent
from lfx.io.schema import create_input_schema_from_dict
from lfx.schema.dotdict import dotdict

from hulubul.request_intake.entrypoints.langflow.components.hulubul.run_flow import (
    HulubulRunFlowComponent,
)

CONNECTION_FIELD_TYPE = "other"
FLOW_TWEAK_PARAM_KEY = "flow_tweak_data"
BOUNDARY_VERTEX_ID = "HulubulDataOperationRequestBoundary-hlb-lf-70-request-v1"


def _field(name: str, field_type: str) -> dotdict:
    return dotdict(
        {
            "name": name,
            "display_name": name.replace("_", " ").title(),
            "info": f"{name} field",
            "type": field_type,
            "input_types": ["Data", "JSON"],
            "required": False,
            "is_list": False,
            "tool_mode": True,
            "value": "",
        }
    )


def _component() -> HulubulRunFlowComponent:
    """A component instance without LangFlow's full construction machinery.

    ``Component.__init__`` needs a vertex, a graph and service registrations
    that only exist inside a running server; both overrides under test read
    nothing but their arguments and ``flow_name_selected``.
    """
    component = object.__new__(HulubulRunFlowComponent)
    component.flow_name_selected = "lf-10-request-intake"
    return component


class TestComponentIdentity:
    """What the flow JSON and the component palette bind to."""

    def test_registered_name_is_stable(self) -> None:
        """`data.type` in every swapped flow node must match this exactly."""
        assert HulubulRunFlowComponent.name == "HulubulRunFlow"

    def test_templates_are_detached_from_the_builtin_component(self) -> None:
        assert HulubulRunFlowComponent.inputs is not RunFlowComponent.inputs
        assert HulubulRunFlowComponent.outputs is not RunFlowComponent.outputs

    def test_input_names_match_the_builtin_component(self) -> None:
        """Detaching the templates must not drift from upstream's inputs."""
        assert [i.name for i in HulubulRunFlowComponent.inputs] == [
            i.name for i in RunFlowComponent.inputs
        ]


class TestGetRequiredData:
    """Build-time: which target-flow fields reach the tool schema."""

    @pytest.fixture
    def boundary_fields(self) -> list[dotdict]:
        """LF-10's input boundary once `advanced=False` exposes its handles."""
        return [
            _field("envelope", CONNECTION_FIELD_TYPE),
            _field("routing_context", CONNECTION_FIELD_TYPE),
            _field("input_value", "str"),
            _field("contract_kind", "str"),
        ]

    @pytest.fixture
    def patched_super(
        self, monkeypatch: pytest.MonkeyPatch, boundary_fields: list[dotdict]
    ) -> None:
        async def fake_get_required_data(_self: Any) -> tuple[str, list[dotdict]]:
            return "LF-10 Request Intake", boundary_fields

        monkeypatch.setattr(RunFlowComponent, "get_required_data", fake_get_required_data)

    def test_connection_fields_are_withheld_from_the_tool_schema(self, patched_super: None) -> None:
        result = asyncio.run(_component().get_required_data())

        assert result is not None
        flow_description, fields = result
        assert flow_description == "LF-10 Request Intake"
        assert [field["name"] for field in fields] == ["input_value", "contract_kind"]

    def test_schema_builds_where_the_stock_component_crashes(
        self, patched_super: None, boundary_fields: list[dotdict]
    ) -> None:
        """The actual regression: `name 'other' is not defined` at build time."""
        with pytest.raises(Exception, match="other"):
            create_input_schema_from_dict(inputs=boundary_fields, param_key=FLOW_TWEAK_PARAM_KEY)

        result = asyncio.run(_component().get_required_data())
        assert result is not None
        _, fields = result

        model = create_input_schema_from_dict(inputs=fields, param_key=FLOW_TWEAK_PARAM_KEY)

        schema = model.model_json_schema()
        inner = schema["$defs"]["InnerModel"]["properties"]
        assert set(inner) == {"input_value", "contract_kind"}

    def test_fields_are_dotdicts_as_the_toolkit_expects(self, patched_super: None) -> None:
        result = asyncio.run(_component().get_required_data())

        assert result is not None
        _, fields = result
        assert all(isinstance(field, dotdict) for field in fields)
        assert fields[0].name == "input_value"

    def test_source_fields_are_left_untouched(
        self, patched_super: None, boundary_fields: list[dotdict]
    ) -> None:
        asyncio.run(_component().get_required_data())

        assert [field["type"] for field in boundary_fields] == [
            CONNECTION_FIELD_TYPE,
            CONNECTION_FIELD_TYPE,
            "str",
            "str",
        ]

    def test_absent_target_flow_stays_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def no_flow_selected(_self: Any) -> None:
            return None

        monkeypatch.setattr(RunFlowComponent, "get_required_data", no_flow_selected)

        assert asyncio.run(_component().get_required_data()) is None


class TestBuildInputsFromIoputs:
    """Run time: whether a payload aimed at a custom boundary actually lands."""

    def test_payload_is_forced_to_the_unrestricted_category(self) -> None:
        payloads = _component()._build_inputs_from_ioputs(
            {BOUNDARY_VERTEX_ID: {"input_value": '{"operation":"readDeliveryRequest"}'}}
        )

        assert payloads == [
            {
                "components": [BOUNDARY_VERTEX_ID],
                "input_value": '{"operation":"readDeliveryRequest"}',
                "type": "any",
            }
        ]

    def test_model_supplied_category_cannot_reintroduce_the_filter(self) -> None:
        """Injection must not depend on a prompt telling the model to send `any`."""
        payloads = _component()._build_inputs_from_ioputs(
            {BOUNDARY_VERTEX_ID: {"input_value": "payload", "type": "chat"}}
        )

        assert payloads[0]["type"] == "any"

    def test_vertex_without_an_input_value_is_still_skipped(self) -> None:
        """Upstream's own filtering stays intact -- only the category changes."""
        payloads = _component()._build_inputs_from_ioputs(
            {BOUNDARY_VERTEX_ID: {"contract_kind": "intake"}}
        )

        assert payloads == []

    def test_no_ioputs_yields_no_payloads(self) -> None:
        assert _component()._build_inputs_from_ioputs({}) == []
