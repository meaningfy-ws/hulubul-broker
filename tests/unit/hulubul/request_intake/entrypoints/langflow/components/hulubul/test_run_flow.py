"""Tests for the Hulubul Run Flow component's overrides.

The point of these tests is that they run against the *real* ``lfx`` machinery
the overrides exist to protect: the schema builder that crashes on a raw
connection-field label, the payload builder that omits the input category, and
the per-tool-call component copy that used to lose the agent's arguments.
"""

import asyncio
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from lfx.components.flow_controls.run_flow import RunFlowComponent
from lfx.io.schema import create_input_schema_from_dict
from lfx.schema.dotdict import dotdict
from lfx.template.field.base import Output

from hulubul.request_intake.entrypoints.langflow.components.hulubul.run_flow import (
    HulubulRunFlowComponent,
)

CONNECTION_FIELD_TYPE = "other"
FLOW_TWEAK_PARAM_KEY = "flow_tweak_data"
BOUNDARY_VERTEX_ID = "HulubulDataOperationRequestBoundary-hlb-lf-70-request-v1"
RESULT_VERTEX_ID = "HulubulDataOperationResultBoundary-hlb-lf-70-result-v1"


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


class TestToolArgumentDelivery:
    """Run time: whether an agent's tool arguments reach the run that uses them.

    ``ComponentToolkit`` copies the component per tool call, applies the
    agent's arguments to the copy, then re-resolves the output method on the
    copy by ``output_method.__name__``. Stock RunFlow breaks that twice over,
    so the sub-flow ran against the original component and saw no arguments
    at all. These tests reproduce that exact sequence.
    """

    @staticmethod
    def _with_flow_output(
        vertex_id: str = RESULT_VERTEX_ID,
    ) -> tuple[HulubulRunFlowComponent, str]:
        """A component carrying one dynamic flow output, as a live node does."""
        component = HulubulRunFlowComponent(_id="test-run-flow")  # type: ignore[no-untyped-call]
        method_name = component._register_flow_output_method(
            vertex_id=vertex_id, output_name="response"
        )
        output = Output(
            name=f"{vertex_id}~response",
            display_name="Result",
            method=method_name,
            types=["JSON"],
        )
        component._outputs_map[output.name] = output
        component.outputs = [output]
        return component, method_name

    def test_resolver_name_matches_the_attribute_it_is_published_under(self) -> None:
        component, method_name = self._with_flow_output()

        assert getattr(component, method_name).__name__ == method_name

    def test_registration_still_reports_the_upstream_method_name(self) -> None:
        _, method_name = self._with_flow_output()

        assert method_name == (
            "_resolve_flow_output__HulubulDataOperationResultBoundary_hlb_lf_70_result_v1__response"
        )

    def test_each_registration_owns_its_own_closure(self) -> None:
        """Renaming one resolver must not rename another."""
        component = HulubulRunFlowComponent(_id="test-run-flow")  # type: ignore[no-untyped-call]

        first = component._register_flow_output_method(vertex_id="alpha", output_name="response")
        second = component._register_flow_output_method(vertex_id="beta", output_name="response")

        assert first != second
        assert getattr(component, first).__name__ == first
        assert getattr(component, second).__name__ == second

    def test_copy_carries_the_resolver(self) -> None:
        """Component.__deepcopy__ rebuilds the instance and drops dynamic attrs."""
        component, method_name = self._with_flow_output()

        duplicate = deepcopy(component)

        assert hasattr(duplicate, method_name)

    def test_toolkit_lookup_lands_on_the_copy_not_the_original(self) -> None:
        """The exact lookup ComponentToolkit._build_output_*_function performs."""
        component, method_name = self._with_flow_output()
        assert component.outputs[0].method == method_name
        output_method = getattr(component, method_name)

        duplicate = deepcopy(component)
        resolved = getattr(duplicate, output_method.__name__, output_method)

        assert resolved.__self__ is duplicate

    def test_arguments_applied_to_the_copy_reach_the_sub_flow_run(self) -> None:
        """End to end over the real toolkit sequence: copy, set, resolve, build."""
        component, method_name = self._with_flow_output()
        assert component.outputs[0].method == method_name
        output_method = getattr(component, method_name)

        duplicate = deepcopy(component)
        duplicate.set(  # type: ignore[no-untyped-call]
            flow_tweak_data={
                f"{BOUNDARY_VERTEX_ID}~input_value": '{"operation":"readDeliveryRequest"}'
            }
        )
        executing = getattr(duplicate, output_method.__name__, output_method).__self__

        inputs = executing._build_inputs(executing._build_flow_tweak_data())

        assert inputs == [
            {
                "components": [BOUNDARY_VERTEX_ID],
                "input_value": '{"operation":"readDeliveryRequest"}',
                "type": "any",
            }
        ]


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


class TestDeepcopySurvivesAnUnpicklableCachedOutput:
    """The live failure: a cached `component_as_tool` output's `.value`
    carrying a live `asyncio.Task`, nested inside it exactly as captured from
    the running system (`Output.value[0].callbacks[0].tracer._flush_task`) --
    LangFlow's own tracing service. Confirmed live only on a flow build
    started through the streaming endpoint the Playground UI uses -- never on
    a plain synchronous run, and never reproducible via a direct API call
    regardless of session ID format.
    """

    @staticmethod
    def _finished_task() -> "asyncio.Task[None]":
        async def _noop() -> None:
            return None

        async def _make() -> "asyncio.Task[None]":
            task = asyncio.ensure_future(_noop())
            await task
            return task

        return asyncio.run(_make())

    @classmethod
    def _component_as_tool_output(cls) -> Output:
        """A `component_as_tool` output shaped like the one captured live:
        `Output.value[0].callbacks[0].tracer._flush_task` holds the task."""
        tracer = SimpleNamespace(_flush_task=cls._finished_task())
        callback = SimpleNamespace(tracer=tracer)
        tool_wrapper = SimpleNamespace(callbacks=[callback])
        return Output(
            name="component_as_tool",
            display_name="Toolset",
            method="to_toolkit",
            types=["Tool"],
            value=[tool_wrapper],
        )

    @staticmethod
    def _component_with_flow_output() -> tuple[HulubulRunFlowComponent, str]:
        component = HulubulRunFlowComponent(_id="test-run-flow")  # type: ignore[no-untyped-call]
        method_name = component._register_flow_output_method(
            vertex_id=RESULT_VERTEX_ID, output_name="response"
        )
        output = Output(
            name=f"{RESULT_VERTEX_ID}~response",
            display_name="Result",
            method=method_name,
            types=["JSON"],
        )
        component._outputs_map[output.name] = output
        component.outputs = [output]
        return component, method_name

    def test_deepcopy_does_not_raise_when_a_cached_output_holds_a_task(self) -> None:
        component, _ = self._component_with_flow_output()
        tool_output = self._component_as_tool_output()
        component._outputs_map["component_as_tool"] = tool_output

        duplicate = deepcopy(component)  # must not raise TypeError

        assert duplicate._outputs_map["component_as_tool"] is tool_output

    def test_other_cached_outputs_are_still_deep_copied_independently(self) -> None:
        """The fallback must stay scoped to the one entry that fails, not
        silently degrade the whole `_outputs_map` to a shallow copy."""
        component, _ = self._component_with_flow_output()
        component._outputs_map["component_as_tool"] = self._component_as_tool_output()

        duplicate = deepcopy(component)

        vertex_output_name = f"{RESULT_VERTEX_ID}~response"
        assert (
            duplicate._outputs_map[vertex_output_name]
            is not (component._outputs_map[vertex_output_name])
        )

    def test_dynamic_resolver_still_works_alongside_the_unpicklable_output(self) -> None:
        """The pre-existing tool-argument-delivery fix must not regress."""
        component, method_name = self._component_with_flow_output()
        component._outputs_map["component_as_tool"] = self._component_as_tool_output()

        duplicate = deepcopy(component)

        assert hasattr(duplicate, method_name)
        assert getattr(duplicate, method_name).__self__ is duplicate

    def test_original_component_is_left_usable_after_the_copy(self) -> None:
        """Detaching `_outputs_map` for the base copy must restore it on self."""
        component, _ = self._component_with_flow_output()
        tool_output = self._component_as_tool_output()
        component._outputs_map["component_as_tool"] = tool_output

        deepcopy(component)

        assert component._outputs_map["component_as_tool"] is tool_output

    def test_without_an_unpicklable_output_deepcopy_is_unaffected(self) -> None:
        """No behavior change on the ordinary path most tool calls take."""
        component, method_name = self._component_with_flow_output()

        duplicate = deepcopy(component)

        assert hasattr(duplicate, method_name)
        vertex_output_name = f"{RESULT_VERTEX_ID}~response"
        assert (
            duplicate._outputs_map[vertex_output_name]
            is not (component._outputs_map[vertex_output_name])
        )
