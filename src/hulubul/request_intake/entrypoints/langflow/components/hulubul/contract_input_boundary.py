"""Contract input boundary component: unified entry point for intake and router inputs.

Consolidates IntakeInputBoundaryComponent and RouterInputBoundaryComponent into
a single, generic component that handles both:
1. Structured integration path: fixed `envelope` and `routing_context` edges
   (for LF-00/LF-10 upstream integration)
2. Direct API invocation path: `input_value` MessageTextInput with JSON text
   (for Run API testing)

The `contract_kind` dropdown selects which wrapper type to build (intake or
router). If fixed edges are provided, they take precedence. If only
`input_value` is provided, it is parsed and validated as the selected contract
kind.

Split from the former contract_boundary.py (which held three components)
because LangFlow's directory-based custom component loader registers exactly
one component per file, named after the file -- extra classes in the same
file are silently dropped from the sidebar palette.
"""

import json
from typing import Any
from uuid import uuid4

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DropdownInput, HandleInput, MessageTextInput
from lfx.schema.message import Message
from lfx.template.field.base import Output
from pydantic import BaseModel, ValidationError

from hulubul.core.models.operational import (
    IntakeInput,
    MainFlowInput,
    OperationalError,
    RouterInput,
    RoutingContext,
)
from hulubul.core.models.operational.enums import ErrorCode
from hulubul.core.models.operational.errors import ERROR_POLICY

__all__ = ["ContractInputBoundaryComponent"]


class ContractInputBoundaryComponent(Component):
    """Unified public entry point for intake and router inputs.

    Supports two integration paths:
    1. Structured edges: fixed `envelope` and `routing_context` (for LF-00/LF-10 upstream flows)
    2. Direct API: literal JSON text via `input_value` (for Run API invocation)

    The `contract_kind` selector determines which wrapper type to assemble (intake or router).
    Fixed edges take precedence when supplied; otherwise, `input_value` is used.
    """

    display_name = "Contract Input Boundary"
    description = "Public entry point for intake and router inputs via fixed edges or direct JSON."
    icon = "shield-check"
    name = "HulubulContractInputBoundary"

    inputs = [  # noqa: RUF012
        HandleInput(  # type: ignore[call-arg]
            name="envelope",
            display_name="Envelope",
            info=(
                "Fixed MainFlowInput envelope (not model-editable -- excluded "
                "from the model-callable tool schema via fixed-edge wiring, "
                "not via `advanced`). Required if using fixed-edge path.\n\n"
                "Deliberately NOT `advanced=True`: LangFlow's frontend treats "
                "an incoming edge into an `advanced` field as invalid and "
                "silently strips it while loading/saving the graph -- "
                "`advanced` is UI-only metadata (which section a field shows "
                "under) and has no effect on trust, read-only-ness, or "
                "model-editability; using it for a field that participates "
                "in the normal data path caused this exact edge to be "
                "dropped for real when a canvas was saved while that warning "
                "showed. See DEV/reports/advanced-field-in-langflow.md."
            ),
            input_types=["Data", "JSON"],
            advanced=False,
            required=False,
        ),
        HandleInput(  # type: ignore[call-arg]
            name="routing_context",
            display_name="Routing Context",
            info=(
                "Fixed RoutingContext (not model-editable -- excluded from "
                "the model-callable tool schema via fixed-edge wiring, not "
                "via `advanced`). Required if using fixed-edge path.\n\n"
                "Deliberately NOT `advanced=True`: see the `envelope` "
                "field's docstring above for why."
            ),
            input_types=["Data", "JSON"],
            advanced=False,
            required=False,
        ),
        MessageTextInput(  # type: ignore[call-arg]
            name="input_value",
            display_name="Direct Input",
            info=(
                "Typed contract input (JSON text) for direct API invocation or "
                "edge-supplied data. MessageTextInput rather than HandleInput: "
                "HandleInput fields are edge-only in LangFlow (they never read "
                "their own literal value), which made direct invocation unreachable "
                "via the plain Run API. MessageTextInput accepts both literal "
                "values and real edges."
            ),
            required=False,
        ),
        DropdownInput(  # type: ignore[call-arg]
            name="contract_kind",
            display_name="Contract Kind",
            info=("Type of input to build: 'intake' for IntakeInput, 'router' for RouterInput."),
            options=["intake", "router"],
            value="intake",
            required=True,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="Message", name="response", type_=Message, method="build_output"
        ),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the ContractInputBoundaryComponent.

        Deliberately does NOT pre-assign any declared input field here.
        LangFlow's `Component.set_attributes()` treats a name that is already
        in `self.__dict__` but not in `self._attributes` as a reserved-word
        collision the moment a differing runtime value is injected via a real
        edge -- confirmed for `input_value` (loud crash: "defines an input
        parameter named 'input_value' that is a reserved word") and, it turns
        out, for `envelope`/`routing_context` too, just silently: the edge
        into the field gets dropped instead of raising, discovered only when
        an actual LF-00 flow round-tripped through the API with fewer edges
        than were sent. Let the framework's own declarative default (each
        input's own `value=`) populate every field instead.
        """
        super().__init__(**kwargs)

    def build_output(self) -> Message:
        """Build intake or router input from fixed edges or direct JSON.

        Priority:
        1. If both envelope and routing_context are supplied, assemble from fixed edges
        2. Otherwise, parse and validate input_value as JSON

        Returns:
            Message: JSON-serialized IntakeInput or RouterInput

        Raises:
            ValueError: If neither path is available or if required fields are missing
        """
        # Path 1: Fixed edges (structured integration from LF-00/LF-10 upstream).
        # Truthy, not `is not None`: an unwired HandleInput field's framework
        # default is `""` (empty string), not `None`, once these fields are no
        # longer explicitly pre-assigned in `__init__` (see its docstring).
        if self.envelope and self.routing_context:
            return self._build_from_fixed_edges()

        # Path 2: Direct JSON input (Run API invocation)
        if self.input_value:
            return self._build_from_input_value()

        # Neither path available
        return self._make_error_response(ErrorCode.INVALID_CONTRACT)

    @staticmethod
    def _coerce_model(value: Any, model_cls: type[BaseModel]) -> Any:
        """Coerce a Data/Message/dict/already-hydrated-model edge value into `model_cls`.

        A real edge value from another component can arrive as either a
        JSON-primitive dict (string UUIDs, string enum values -- e.g.
        `.model_dump(mode="json")` output) or a dict of already-native
        instances (e.g. `ExecutionEnvelopeComponent.build_envelope()` returns
        `Data(data=envelope.model_dump())` -- note: no `mode="json"`, so its
        `actor_id`/`message_id`/`correlation_id` are real `UUID` objects, not
        strings). This project's contracts are strict-typed and reject the
        first shape via ordinary python-mode construction (a UUID/enum field
        must already be a native instance) -- only `model_validate_json`
        applies the standard JSON coercion rules; `default=str` in the
        dump makes that same call handle the second shape too. Values
        already an instance of `model_cls` (e.g. a real object passed
        directly in a unit test) pass through unchanged; anything
        unparseable is returned as-is and left for the caller's own
        validation/error path to reject.

        `isinstance(value, Message)` is checked before the generic
        `hasattr(value, "data")` branch: `Message` also exposes a `.data`
        attribute (its own field dict -- `sender`, `session_id`, `duration`,
        etc.), which is not the wrapped payload at all; the actual JSON
        lives in `.text`.
        """
        if isinstance(value, model_cls):
            return value
        if isinstance(value, Message):
            if not isinstance(value.text, str):
                return value
            try:
                return model_cls.model_validate_json(value.text)
            except (ValidationError, TypeError):
                return value
        candidate = value.data if hasattr(value, "data") else value
        try:
            if isinstance(candidate, str):
                return model_cls.model_validate_json(candidate)
            if isinstance(candidate, dict):
                # LFX's own JSON/Data wrapper classes can leak their OWN
                # fields (e.g. `default_value`) into `.data` at some points
                # in the pipeline -- confirmed live against a real LF-00
                # edge value. `model_cls` is strict (extra_forbidden), so
                # pass through only the keys it actually declares.
                filtered = {k: v for k, v in candidate.items() if k in model_cls.model_fields}
                return model_cls.model_validate_json(json.dumps(filtered, default=str))
        except (ValidationError, TypeError):
            return value
        return value

    @staticmethod
    def _unwrap_routing_context(value: Any) -> Any:
        """Unwrap a DataOperationResult-shaped routing_context edge value.

        LF-00's mandatory context-prefetch feeds this boundary the raw
        `DataOperationResult` returned by LF-70's `getRequestRoutingContext`
        operation (RoutingContext lives at `.result`, already fully adapted
        by LF-70's own RoutingContextAdapterComponent) -- not a bare
        RoutingContext directly. LF-10 has no such predecessor and always
        supplies a bare RoutingContext. Detect the DataOperationResult shape
        (its `outcome`/`result` keys are not RoutingContext fields) and
        unwrap it; pass anything else through unchanged so a bare
        RoutingContext (dict or model instance) still works as before.

        `isinstance(value, Message)` must be checked before the generic
        `hasattr(value, "data")` branch (same ordering bug already fixed in
        `_coerce_model`): confirmed live -- the real `RunFlow` context-
        prefetch output arrives as a `Message` wrapping the full
        `DataOperationResult` JSON text, not a `Data`/`JSON` object. Without
        this check the unwrap silently no-ops (a `Message`'s own `.data` is
        its OWN field dict, not the payload), and `_coerce_model` then tries
        to validate the entire `DataOperationResult` as a bare
        `RoutingContext` and fails with `INVALID_CONTRACT` -- with no
        exception ever logged, since the failure is "successfully" caught by
        `_build_from_fixed_edges`'s own error handling. This was silently
        breaking every LF-00 request regardless of RoutingContext content.

        A second, independent wrapping layer was found live on top of that:
        `RunFlow` in non-tool mode surfaces a sub-flow component's output by
        forwarding LangFlow's own internal per-output artifact record --
        `{"repr": <str>, "raw": <actual payload>, "type": <str>}` -- as the
        `Data`/`Message` content, rather than the bare payload. `_unwrap_one_layer`
        peels exactly that shape off (recognised by having `raw`/`type` keys
        without `outcome`/`result` of its own) before the `outcome`/`result`
        check runs, so a payload that never went through `RunFlow` (e.g. LF-10
        feeding a bare `RoutingContext`, or a direct `DataOperationResult`
        with no `RunFlow` hop) is unaffected.
        """

        def _unwrap_one_layer(candidate: Any) -> Any:
            if (
                isinstance(candidate, dict)
                and "raw" in candidate
                and "type" in candidate
                and "outcome" not in candidate
            ):
                return candidate["raw"]
            return candidate

        if isinstance(value, Message) and isinstance(value.text, str):
            try:
                parsed = json.loads(value.text)
            except json.JSONDecodeError:
                return value
            parsed = _unwrap_one_layer(parsed)
            if isinstance(parsed, dict) and "outcome" in parsed and "result" in parsed:
                return parsed["result"]
            return value
        candidate = value.data if hasattr(value, "data") else value
        candidate = _unwrap_one_layer(candidate)
        if isinstance(candidate, dict) and "outcome" in candidate and "result" in candidate:
            return candidate["result"]
        return value

    def _build_from_fixed_edges(self) -> Message:
        """Assemble input from fixed envelope/routing_context edges.

        Returns:
            Message: Serialized IntakeInput or RouterInput, as selected by contract_kind

        Raises:
            ValueError: If envelope or routing_context is None
        """
        if self.envelope is None:
            raise ValueError("INVALID_CONFIGURATION: envelope is required")
        if self.routing_context is None:
            raise ValueError("INVALID_CONFIGURATION: routing_context is required")

        envelope = self._coerce_model(self.envelope, MainFlowInput)
        routing_context = self._coerce_model(
            self._unwrap_routing_context(self.routing_context), RoutingContext
        )

        try:
            wrapper: IntakeInput | RouterInput
            if self.contract_kind == "router":
                wrapper = RouterInput(
                    schema_version=envelope.schema_version,
                    correlation_id=envelope.correlation_id,
                    envelope=envelope,
                    routing_context=routing_context,
                )
            else:  # default to "intake"
                wrapper = IntakeInput(
                    schema_version=envelope.schema_version,
                    correlation_id=envelope.correlation_id,
                    envelope=envelope,
                    routing_context=routing_context,
                )

            return Message(text=wrapper.model_dump_json())

        except (ValidationError, TypeError, AttributeError):
            return self._make_error_response(ErrorCode.INVALID_CONTRACT)

    def _build_from_input_value(self) -> Message:
        """Parse and validate input_value as JSON, then assemble the selected contract type.

        Returns:
            Message: Serialized IntakeInput or RouterInput, as selected by contract_kind
        """
        raw_value = self.input_value
        if isinstance(raw_value, Message):
            raw_value = raw_value.text

        if not raw_value or (isinstance(raw_value, str) and not raw_value.strip()):
            return self._make_error_response(ErrorCode.INVALID_CONTRACT)

        try:
            # Parse JSON and validate as selected type
            parsed_input: IntakeInput | RouterInput
            if self.contract_kind == "router":
                if isinstance(raw_value, str):
                    parsed_input = RouterInput.model_validate_json(raw_value)
                else:
                    # JSON-mode validation for non-string dicts: a dict from
                    # an edge or variable binding is shaped as JSON primitives
                    # (string UUIDs in correlation_id, string source enums, etc.),
                    # not native instances. Though currently unreachable (input_value
                    # is always a string or Message in live flows), this is the
                    # correct pattern if the else branch is ever exercised.
                    # Same rationale as DataOperationResultBoundary and
                    # DataAccessAgentComponent.
                    value_json = json.dumps(raw_value, default=str)
                    parsed_input = RouterInput.model_validate_json(value_json)
            else:  # default to "intake"
                if isinstance(raw_value, str):
                    parsed_input = IntakeInput.model_validate_json(raw_value)
                else:
                    # JSON-mode validation for non-string dicts: same rationale
                    # as RouterInput case above.
                    value_json = json.dumps(raw_value, default=str)
                    parsed_input = IntakeInput.model_validate_json(value_json)

            return Message(text=parsed_input.model_dump_json())

        except (ValidationError, json.JSONDecodeError, TypeError):
            return self._make_error_response(ErrorCode.INVALID_CONTRACT)

    def _make_error_response(self, code: ErrorCode) -> Message:
        """Create a canonical error response without exposing user values.

        Args:
            code: The ErrorCode

        Returns:
            Message: Serialized OperationalError
        """
        policy = ERROR_POLICY[code]
        error = OperationalError(
            schema_version="1.0.0",
            code=code,
            correlation_id=uuid4(),
            category=policy.category,
            message=policy.safe_message,
            retryable=policy.retryable,
        )

        return Message(text=error.model_dump_json())
