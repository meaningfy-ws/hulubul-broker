"""Tests for HulubulDataOperationRequestBuilder: deterministic routing-context request assembly."""

import json
from uuid import uuid4

import pytest
from lfx.schema.data import Data
from lfx.schema.message import Message

from hulubul.core.models.operational import (
    ActorContext,
    ActorRole,
    IdentityAssurance,
    InvocationSource,
    MainFlowInput,
)
from hulubul.core.models.operational.data_operations import GetRequestRoutingContextRequest
from hulubul.core.models.operational.enums import DataOperation
from hulubul.request_intake.entrypoints.langflow.components.hulubul.data_operation_request_builder import (
    HulubulDataOperationRequestBuilder,
)

FIXED_CORRELATION_ID = uuid4()
FIXED_SESSION_ID = "p1-12345678-1234-4000-8000-000000000000"
FIXED_ACTOR_ID = "urn:uuid:87654321-4321-4000-8000-000000000000"

FIXED_ENVELOPE = MainFlowInput(
    message_id=uuid4(),
    session_id=FIXED_SESSION_ID,
    actor=ActorContext(
        actor_id=FIXED_ACTOR_ID,
        display_name="Test Sender",
        actor_role=ActorRole.SENDER,
        identity_assurance=IdentityAssurance.SIMULATED,
    ),
    source=InvocationSource.API,
    message="Test message",
    correlation_id=FIXED_CORRELATION_ID,
)


def _text(message: Message) -> str:
    """Narrow Message.text (str | AsyncIterator | Iterator | None) to str for mypy."""
    assert isinstance(message.text, str)
    return message.text


@pytest.fixture
def builder() -> HulubulDataOperationRequestBuilder:
    """Create a HulubulDataOperationRequestBuilder."""
    return HulubulDataOperationRequestBuilder()


class TestDeterministicAssembly:
    """Test deterministic GetRequestRoutingContextRequest construction from a hydrated envelope."""

    def test_builds_request_from_real_envelope_instance(
        self, builder: HulubulDataOperationRequestBuilder
    ) -> None:
        """A real MainFlowInput instance (unit-test convenience shape) builds correctly."""
        builder.envelope = FIXED_ENVELOPE

        output = builder.build_output()

        assert isinstance(output, Message)
        request = GetRequestRoutingContextRequest.model_validate_json(_text(output))
        assert request.operation == DataOperation.GET_REQUEST_ROUTING_CONTEXT
        assert request.caller == "LF-00"
        assert request.session_id == FIXED_SESSION_ID
        assert request.actor_id == FIXED_ACTOR_ID
        assert request.schema_version == FIXED_ENVELOPE.schema_version
        assert request.correlation_id == str(FIXED_CORRELATION_ID)

    def test_operation_id_is_unique_per_call(
        self, builder: HulubulDataOperationRequestBuilder
    ) -> None:
        """Each call generates a fresh operation_id."""
        builder.envelope = FIXED_ENVELOPE

        first = GetRequestRoutingContextRequest.model_validate_json(_text(builder.build_output()))
        second = GetRequestRoutingContextRequest.model_validate_json(_text(builder.build_output()))

        assert first.operation_id != second.operation_id


class TestRealEdgeValueCoercion:
    """Test the actual runtime edge shapes -- not the unit-test convenience shape.

    Regression coverage: `ExecutionEnvelopeComponent.build_envelope()` returns
    `Data(data=envelope.model_dump())`, not a hydrated `MainFlowInput`
    instance. Every prior "test" of this component passed a real
    `MainFlowInput` object directly (this file didn't exist before), so this
    exact wiring was never exercised until a live LF-00 flow was actually
    built -- where it failed with `'dict' object has no attribute
    'actor_id'`.
    """

    def test_accepts_data_wrapped_native_object_dict(
        self, builder: HulubulDataOperationRequestBuilder
    ) -> None:
        """The real edge shape: Data(data=envelope.model_dump()) -- native UUID/enum objects."""
        builder.envelope = Data(data=FIXED_ENVELOPE.model_dump())

        output = builder.build_output()

        request = GetRequestRoutingContextRequest.model_validate_json(_text(output))
        assert request.session_id == FIXED_SESSION_ID
        assert request.actor_id == FIXED_ACTOR_ID

    def test_accepts_json_primitive_dict(self, builder: HulubulDataOperationRequestBuilder) -> None:
        """A dict of JSON-primitive values (string UUIDs) also coerces correctly."""
        builder.envelope = FIXED_ENVELOPE.model_dump(mode="json")

        output = builder.build_output()

        request = GetRequestRoutingContextRequest.model_validate_json(_text(output))
        assert request.session_id == FIXED_SESSION_ID
        assert request.actor_id == FIXED_ACTOR_ID

    def test_accepts_dict_with_leaked_framework_fields(
        self, builder: HulubulDataOperationRequestBuilder
    ) -> None:
        """LFX's own JSON/Data wrapper can leak its own fields (e.g. `default_value`) into `.data`.

        Regression test: confirmed live -- a real LF-00 edge value arrived as
        `JSON(text_key='text', data={...real envelope fields...,
        'default_value': ''}, default_value='')`. MainFlowInput is a strict
        model (extra_forbidden), so this extra key must be filtered out
        rather than crashing the whole graph build.
        """
        leaked = {**FIXED_ENVELOPE.model_dump(mode="json"), "default_value": ""}
        builder.envelope = leaked

        output = builder.build_output()

        request = GetRequestRoutingContextRequest.model_validate_json(_text(output))
        assert request.session_id == FIXED_SESSION_ID
        assert request.actor_id == FIXED_ACTOR_ID

    def test_accepts_message_wrapped_json_text(
        self, builder: HulubulDataOperationRequestBuilder
    ) -> None:
        """A Message wrapping the envelope's JSON text also coerces correctly."""
        builder.envelope = Message(text=FIXED_ENVELOPE.model_dump_json())

        output = builder.build_output()

        request = GetRequestRoutingContextRequest.model_validate_json(_text(output))
        assert request.session_id == FIXED_SESSION_ID
        assert request.actor_id == FIXED_ACTOR_ID

    def test_rejects_unparseable_envelope(
        self, builder: HulubulDataOperationRequestBuilder
    ) -> None:
        """An envelope that isn't a Message/Data/dict/MainFlowInput raises, not silently corrupts."""
        builder.envelope = 12345

        with pytest.raises(ValueError, match="INVALID_CONFIGURATION"):
            builder.build_output()


class TestPurity:
    """Test that construction is pure/deterministic (no I/O, no model calls)."""

    def test_output_is_json_serializable(self, builder: HulubulDataOperationRequestBuilder) -> None:
        """Output text is valid JSON with no non-JSON-native leakage."""
        builder.envelope = FIXED_ENVELOPE

        output = builder.build_output()

        parsed = json.loads(_text(output))
        assert isinstance(parsed, dict)
        assert parsed["caller"] == "LF-00"
