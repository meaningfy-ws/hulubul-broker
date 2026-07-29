"""Data operation request builder component for LF-00 routing context prefetch.

Constructs deterministic GetRequestRoutingContextRequest for the mandatory routing context prefetch.
Pure deterministic component (no I/O, no LLM) — wires between execution envelope and LF-70 Run Flow.
"""

import json
from typing import Any
from uuid import uuid4

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput
from lfx.schema.message import Message
from lfx.template.field.base import Output

from hulubul.core.models.operational import MainFlowInput
from hulubul.core.models.operational.data_operations import GetRequestRoutingContextRequest
from hulubul.core.models.operational.enums import DataOperation

__all__ = ["HulubulDataOperationRequestBuilder"]


class HulubulDataOperationRequestBuilder(Component):
    """Build deterministic GetRequestRoutingContextRequest.

    Takes the validated MainFlowInput envelope from execution boundary and
    constructs the operation request for LF-70's mandatory routing-context
    prefetch.

    Inputs:
    - envelope: MainFlowInput from ExecutionEnvelopeComponent

    Outputs:
    - request: Message containing JSON string (GetRequestRoutingContextRequest) for LF-70
    """

    display_name = "Data Operation Request Builder (Routing Context)"
    description = (
        "Build GetRequestRoutingContextRequest for routing context prefetch. "
        "Pure deterministic assembly from envelope metadata."
    )
    icon = "package"
    name = "HulubulDataOperationRequestBuilder"

    inputs = [  # noqa: RUF012
        HandleInput(  # type: ignore[call-arg]
            name="envelope",
            display_name="Execution Envelope",
            info="MainFlowInput from ExecutionEnvelopeComponent",
            input_types=["Data", "JSON"],
            required=True,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="Data Operation Request",
            name="request",
            type_=Message,
            method="build_output",
        ),
    ]

    @staticmethod
    def _coerce_envelope(value: Any) -> MainFlowInput:
        """Coerce the incoming envelope edge value into a real MainFlowInput.

        `ExecutionEnvelopeComponent.build_envelope()` returns
        `Data(data=envelope.model_dump())` -- a dict, not a hydrated
        `MainFlowInput` instance, and its `.actor` is itself a plain nested
        dict (`.actor.actor_id` fails with `'dict' object has no attribute
        'actor_id'`), discovered only when actually building a live LF-00
        flow, not by any prior unit test (existing tests passed a real
        `MainFlowInput` instance directly). Route through
        `model_validate_json` so strict-model UUID/enum coercion applies
        regardless of whether the dict holds native objects or JSON
        primitives (`default=str` handles both).

        `isinstance(value, Message)` must be checked before the generic
        `hasattr(value, "data")` branch: `Message` also exposes a `.data`
        attribute (its own field dict -- `sender`, `session_id`, `duration`,
        etc.), which is not the envelope payload at all; the actual JSON
        lives in `.text`.
        """
        if isinstance(value, MainFlowInput):
            return value
        if isinstance(value, Message):
            if not isinstance(value.text, str):
                msg = "INVALID_CONFIGURATION: envelope Message has no text content"
                raise ValueError(msg)
            return MainFlowInput.model_validate_json(value.text)
        candidate = value.data if hasattr(value, "data") else value
        if isinstance(candidate, str):
            return MainFlowInput.model_validate_json(candidate)
        if isinstance(candidate, dict):
            # LFX's own JSON/Data wrapper classes can leak their OWN fields
            # (e.g. `default_value`) into `.data` at some points in the
            # pipeline -- confirmed live: a real edge value arrived as
            # `JSON(text_key='text', data={...real envelope fields...,
            # 'default_value': ''}, default_value='')`. MainFlowInput is a
            # strict model (extra_forbidden), so pass through only the keys
            # it actually declares rather than patching around one specific
            # framework-injected key.
            filtered = {k: v for k, v in candidate.items() if k in MainFlowInput.model_fields}
            return MainFlowInput.model_validate_json(json.dumps(filtered, default=str))
        msg = f"INVALID_CONFIGURATION: envelope has unexpected type {type(value)!r}"
        raise ValueError(msg)

    def build_output(self) -> Message:
        """Construct GetRequestRoutingContextRequest.

        Returns Message containing JSON string (GetRequestRoutingContextRequest) for LF-70.
        """
        envelope = self._coerce_envelope(self.envelope)

        # Construct the operation request deterministically
        request = GetRequestRoutingContextRequest(
            operation=DataOperation.GET_REQUEST_ROUTING_CONTEXT,
            operation_id=str(uuid4()),
            caller="LF-00",
            session_id=str(envelope.session_id),
            actor_id=str(envelope.actor.actor_id),
            schema_version=envelope.schema_version,
            correlation_id=str(envelope.correlation_id),
        )

        # Return as Message with JSON text
        return Message(text=request.model_dump_json())
