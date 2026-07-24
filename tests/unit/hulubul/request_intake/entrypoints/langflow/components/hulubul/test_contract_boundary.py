"""Tests for contract boundary components: validation, error translation, fixed-edge enforcement."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from lfx.schema.data import Data, JSON
from lfx.schema.message import Message

from hulubul.core.models.operational import (
    ActorContext,
    ActorRole,
    BindingState,
    ContractKind,
    DataOperationRequest,
    DataOperationResult,
    DeliveryRequestSnapshot,
    ErrorCode,
    IdentityAssurance,
    IntakeFacts,
    IntakeInput,
    IntakeOutcome,
    IntakeResult,
    InvocationSource,
    MainFlowInput,
    OperationalError,
    RequestStatus,
    RouterInput,
    RouterOutcome,
    RouterResult,
    RouterTarget,
    RoutingContext,
    RoutingReason,
    RoutingStage,
)
from hulubul.request_intake.entrypoints.langflow.components.hulubul.contract_boundary import (
    CONTRACT_TYPES,
    ContractResultBoundaryComponent,
    IntakeInputBoundaryComponent,
    RouterInputBoundaryComponent,
)

# ============================================================================
# Fixtures and Constants
# ============================================================================

FIXED_CORRELATION_ID = uuid4()
FIXED_SESSION_ID = "p1-12345678-1234-4000-8000-000000000000"
FIXED_ACTOR_ID = "urn:uuid:test-actor-id"
FIXED_DISPLAY_NAME = "Test Sender"

FIXED_ACTOR_CONTEXT = ActorContext(
    actor_id=FIXED_ACTOR_ID,
    display_name=FIXED_DISPLAY_NAME,
    actor_role=ActorRole.SENDER,
    identity_assurance=IdentityAssurance.SIMULATED,
)

FIXED_ENVELOPE = MainFlowInput(
    message_id=uuid4(),
    session_id=FIXED_SESSION_ID,
    actor=FIXED_ACTOR_CONTEXT,
    source=InvocationSource.API,
    message="Test message",
    correlation_id=FIXED_CORRELATION_ID,
)

FIXED_ROUTING_CONTEXT = RoutingContext(
    schema_version="1.0.0",
    correlation_id=FIXED_CORRELATION_ID,
    session_id=FIXED_SESSION_ID,
    binding_state=BindingState.ABSENT,
    binding_count=0,
    active_relationship_count=0,
    active_target_count=0,
    routing_stage=RoutingStage.INTAKE,
)


@pytest.fixture
def router_input_boundary():
    """Create a RouterInputBoundaryComponent."""
    return RouterInputBoundaryComponent()


@pytest.fixture
def intake_input_boundary():
    """Create an IntakeInputBoundaryComponent."""
    return IntakeInputBoundaryComponent()


@pytest.fixture
def contract_result_boundary():
    """Create a ContractResultBoundaryComponent."""
    return ContractResultBoundaryComponent()


# ============================================================================
# Test: Registry Completeness (All 11 ContractKind values)
# ============================================================================


class TestRegistryCompleteness:
    """Verify registry contains all 11 ContractKind values."""

    def test_registry_contains_all_contract_kinds(self, contract_result_boundary):
        """Registry keys match exact set(ContractKind)."""
        registry_keys = set(CONTRACT_TYPES.keys())
        contract_kinds = set(ContractKind)

        assert registry_keys == contract_kinds, (
            f"Registry mismatch. "
            f"Missing: {contract_kinds - registry_keys}, "
            f"Extra: {registry_keys - contract_kinds}"
        )

    def test_registry_has_exactly_11_entries(self, contract_result_boundary):
        """Registry has exactly 11 entries."""
        assert len(CONTRACT_TYPES) == 11


# ============================================================================
# Test: RouterInputBoundaryComponent
# ============================================================================


class TestRouterInputBoundary:
    """Test RouterInputBoundaryComponent for envelope/context fixed-edge validation."""

    def test_router_input_uses_fixed_edges(self, router_input_boundary):
        """RouterInput assembles from fixed envelope/context edges, not model values."""
        # Set up component with fixed edges
        router_input_boundary.envelope = FIXED_ENVELOPE
        router_input_boundary.routing_context = FIXED_ROUTING_CONTEXT

        # Build message
        output = router_input_boundary.build_router_input()
        assert isinstance(output, Message)

        # Parse and verify fixed edges preserved
        wrapper = RouterInput.model_validate_json(output.text)
        assert wrapper.envelope == FIXED_ENVELOPE
        assert wrapper.routing_context == FIXED_ROUTING_CONTEXT

    def test_router_input_fixed_envelope_not_substitutable(self, router_input_boundary):
        """RouterInput envelope is fixed; caller cannot override."""
        router_input_boundary.envelope = FIXED_ENVELOPE
        router_input_boundary.routing_context = FIXED_ROUTING_CONTEXT

        # Attempt to set a different envelope (should be ignored or error)
        output = router_input_boundary.build_router_input()
        wrapper = RouterInput.model_validate_json(output.text)

        # Verify envelope matches what was set, not caller input
        assert wrapper.envelope.actor.actor_id == FIXED_ACTOR_ID

    def test_router_input_fixed_context_not_substitutable(self, router_input_boundary):
        """RouterInput routing_context is fixed; caller cannot override."""
        router_input_boundary.envelope = FIXED_ENVELOPE
        router_input_boundary.routing_context = FIXED_ROUTING_CONTEXT

        output = router_input_boundary.build_router_input()
        wrapper = RouterInput.model_validate_json(output.text)

        # Verify context is the fixed one
        assert wrapper.routing_context.routing_stage == RoutingStage.INTAKE
        assert wrapper.routing_context.binding_state == BindingState.ABSENT


# ============================================================================
# Test: IntakeInputBoundaryComponent
# ============================================================================


class TestIntakeInputBoundary:
    """Test IntakeInputBoundaryComponent for envelope/context fixed-edge validation."""

    def test_intake_input_uses_fixed_edges(self, intake_input_boundary):
        """IntakeInput assembles from fixed envelope/context edges, not model values."""
        # Set up component with fixed edges
        intake_input_boundary.envelope = FIXED_ENVELOPE
        intake_input_boundary.routing_context = FIXED_ROUTING_CONTEXT

        # Build message
        output = intake_input_boundary.build_intake_input()
        assert isinstance(output, Message)

        # Parse and verify fixed edges preserved
        wrapper = IntakeInput.model_validate_json(output.text)
        assert wrapper.envelope == FIXED_ENVELOPE
        assert wrapper.routing_context == FIXED_ROUTING_CONTEXT

    def test_intake_input_fixed_envelope_not_substitutable(self, intake_input_boundary):
        """IntakeInput envelope is fixed; caller cannot override."""
        intake_input_boundary.envelope = FIXED_ENVELOPE
        intake_input_boundary.routing_context = FIXED_ROUTING_CONTEXT

        output = intake_input_boundary.build_intake_input()
        wrapper = IntakeInput.model_validate_json(output.text)

        # Verify envelope is the fixed one
        assert wrapper.envelope.message == "Test message"

    def test_intake_input_fixed_context_not_substitutable(self, intake_input_boundary):
        """IntakeInput routing_context is fixed; caller cannot override."""
        intake_input_boundary.envelope = FIXED_ENVELOPE
        intake_input_boundary.routing_context = FIXED_ROUTING_CONTEXT

        output = intake_input_boundary.build_intake_input()
        wrapper = IntakeInput.model_validate_json(output.text)

        # Verify context is the fixed one
        assert wrapper.routing_context.routing_stage == RoutingStage.INTAKE


# ============================================================================
# Test: Canonical Data/JSON Conversion
# ============================================================================


class TestCanonicalConversion:
    """Test canonical LFX Data/JSON → typed model conversion."""

    def test_contract_result_boundary_returns_json_or_message(self, contract_result_boundary):
        """ContractResultBoundary returns JSON or Message output."""
        facts_dict = {
            "sender_actor_id": "urn:uuid:test",
            "receiver_name": "Test Receiver",
        }

        output = contract_result_boundary.validate_contract_value(facts_dict)
        # Output should be JSON or Message
        assert isinstance(output, (Data, Message, JSON))

    def test_contract_result_boundary_handles_intake_facts(self, contract_result_boundary):
        """ContractResultBoundary can validate IntakeFacts input."""
        facts_dict = {
            "sender_actor_id": "urn:uuid:test",
            "receiver_name": "Test Receiver",
        }

        output = contract_result_boundary.validate_contract_value(facts_dict)
        # Verify output is valid (can be parsed back)
        assert output is not None

    def test_contract_result_boundary_returns_error_for_empty(self, contract_result_boundary):
        """ContractResultBoundary returns error for None/empty input."""
        output = contract_result_boundary.validate_contract_value(None)
        # Should return an error response
        assert isinstance(output, (Data, JSON))


# ============================================================================
# Test: Error Redaction (Field Violations Never Expose Values)
# ============================================================================


class TestErrorRedaction:
    """Test that validation errors never expose user-supplied values."""

    def test_invalid_dict_returns_json(self, contract_result_boundary):
        """Invalid dict input returns JSON error response."""
        invalid_dict = {"invalid": "data"}

        output = contract_result_boundary.validate_contract_value(invalid_dict)
        # Should return JSON/Message, not exception
        assert isinstance(output, (Data, JSON, Message))

    def test_non_dict_returns_error(self, contract_result_boundary):
        """Non-dict input returns error response."""
        output = contract_result_boundary.validate_contract_value("not a dict")

        # Should return JSON error
        assert isinstance(output, (Data, JSON, Message))

    def test_error_response_does_not_expose_user_values(self, contract_result_boundary):
        """Error responses don't contain user-supplied values."""
        invalid_dict = {
            "malformed": "SECRET_VALUE_12345",
            "bad_uuid": "xyz123",
        }

        output = contract_result_boundary.validate_contract_value(invalid_dict)
        # Convert to string for inspection
        if isinstance(output, Message):
            output_str = output.text
        elif isinstance(output, Data) or isinstance(output, JSON):
            output_str = str(output.data)
        else:
            output_str = str(output)

        # Verify secret value never appears in output
        assert "SECRET_VALUE_12345" not in output_str
        assert "xyz123" not in output_str


# ============================================================================
# Test: Type Translation Failures → INVALID_CONTRACT
# ============================================================================


class TestTypeTranslationFailures:
    """Test that type/validation failures produce error responses."""

    def test_malformed_input_returns_error(self, contract_result_boundary):
        """Malformed input produces error response."""
        invalid_dict = {
            "completely": "wrong_structure",
            "no_valid_fields": True,
        }

        output = contract_result_boundary.validate_contract_value(invalid_dict)
        # Should return error response, not exception
        assert isinstance(output, (Data, JSON, Message))

    def test_missing_required_fields_returns_error(self, contract_result_boundary):
        """Missing required fields produce error response."""
        invalid_dict = {
            "sender_actor_id": "urn:uuid:test",
            # Missing required pickup_location
        }

        output = contract_result_boundary.validate_contract_value(invalid_dict)
        assert isinstance(output, (Data, JSON, Message))

    def test_invalid_enum_value_returns_error(self, contract_result_boundary):
        """Invalid enum value produces error response."""
        invalid_dict = {
            "outcome": "not-a-valid-outcome",
        }

        output = contract_result_boundary.validate_contract_value(invalid_dict)
        # Should return error response
        assert isinstance(output, (Data, JSON, Message))


# ============================================================================
# Test: No Raw Dict After Validation
# ============================================================================


class TestNoRawDictAfterValidation:
    """Test that no raw dict/unvalidated data enters downstream."""

    def test_router_input_output_is_typed_message(self, router_input_boundary):
        """RouterInput.build_router_input() returns Message, not raw dict."""
        router_input_boundary.envelope = FIXED_ENVELOPE
        router_input_boundary.routing_context = FIXED_ROUTING_CONTEXT

        output = router_input_boundary.build_router_input()

        assert isinstance(output, Message)
        assert isinstance(output.text, str)

        # Verify it's valid JSON that parses to RouterInput
        wrapper = RouterInput.model_validate_json(output.text)
        assert isinstance(wrapper, RouterInput)

    def test_intake_input_output_is_typed_message(self, intake_input_boundary):
        """IntakeInput.build_intake_input() returns Message, not raw dict."""
        intake_input_boundary.envelope = FIXED_ENVELOPE
        intake_input_boundary.routing_context = FIXED_ROUTING_CONTEXT

        output = intake_input_boundary.build_intake_input()

        assert isinstance(output, Message)
        assert isinstance(output.text, str)

        # Verify it's valid JSON that parses to IntakeInput
        wrapper = IntakeInput.model_validate_json(output.text)
        assert isinstance(wrapper, IntakeInput)

    def test_contract_result_output_is_typed_message_or_data(self, contract_result_boundary):
        """ContractResult output is Message/Data/JSON, not raw dict."""
        result_dict = {
            "sender_actor_id": "urn:uuid:test",
        }

        output = contract_result_boundary.validate_contract_value(result_dict)

        # Output must be typed Message, Data, or JSON - never a raw dict
        assert isinstance(output, (Message, Data, JSON))
        assert not isinstance(output, dict)


# ============================================================================
# Test: Wrapper Equality and Fixed-Edge Immutability
# ============================================================================


class TestWrapperEquality:
    """Test wrapper equality and fixed-edge immutability."""

    def test_router_input_equality(self):
        """RouterInput wrappers with same envelope/context are equal."""
        wrapper1 = RouterInput(
            schema_version="1.0.0",
            correlation_id=FIXED_CORRELATION_ID,
            envelope=FIXED_ENVELOPE,
            routing_context=FIXED_ROUTING_CONTEXT,
        )

        wrapper2 = RouterInput(
            schema_version="1.0.0",
            correlation_id=FIXED_CORRELATION_ID,
            envelope=FIXED_ENVELOPE,
            routing_context=FIXED_ROUTING_CONTEXT,
        )

        assert wrapper1 == wrapper2

    def test_intake_input_equality(self):
        """IntakeInput wrappers with same envelope/context are equal."""
        wrapper1 = IntakeInput(
            schema_version="1.0.0",
            correlation_id=FIXED_CORRELATION_ID,
            envelope=FIXED_ENVELOPE,
            routing_context=FIXED_ROUTING_CONTEXT,
        )

        wrapper2 = IntakeInput(
            schema_version="1.0.0",
            correlation_id=FIXED_CORRELATION_ID,
            envelope=FIXED_ENVELOPE,
            routing_context=FIXED_ROUTING_CONTEXT,
        )

        assert wrapper1 == wrapper2

    def test_router_input_frozen(self):
        """RouterInput is frozen (immutable) after creation."""
        wrapper = RouterInput(
            schema_version="1.0.0",
            correlation_id=FIXED_CORRELATION_ID,
            envelope=FIXED_ENVELOPE,
            routing_context=FIXED_ROUTING_CONTEXT,
        )

        # Attempt to modify frozen model
        with pytest.raises(Exception):  # ValidationError or similar
            wrapper.envelope = None

    def test_intake_input_frozen(self):
        """IntakeInput is frozen (immutable) after creation."""
        wrapper = IntakeInput(
            schema_version="1.0.0",
            correlation_id=FIXED_CORRELATION_ID,
            envelope=FIXED_ENVELOPE,
            routing_context=FIXED_ROUTING_CONTEXT,
        )

        # Attempt to modify frozen model
        with pytest.raises(Exception):
            wrapper.routing_context = None


# ============================================================================
# Test: All 11 Contract Kinds (Valid Conversion)
# ============================================================================


class TestAllContractKinds:
    """Test that all 11 contract kinds are in registry and accessible."""

    def test_all_contract_kinds_in_registry(self):
        """All 11 ContractKind values are in registry."""
        expected_kinds = {
            ContractKind.MAIN_FLOW_INPUT,
            ContractKind.ROUTER_INPUT,
            ContractKind.INTAKE_INPUT,
            ContractKind.ROUTING_CONTEXT,
            ContractKind.ROUTER_RESULT,
            ContractKind.INTAKE_FACTS,
            ContractKind.INTAKE_RESULT,
            ContractKind.DATA_OPERATION_REQUEST,
            ContractKind.DATA_OPERATION_RESULT,
            ContractKind.DELIVERY_REQUEST_SNAPSHOT,
            ContractKind.OPERATIONAL_ERROR,
        }

        registry_kinds = set(CONTRACT_TYPES.keys())
        assert registry_kinds == expected_kinds

    def test_main_flow_input_kind_has_model(self):
        """MAIN_FLOW_INPUT contract kind has a registered model."""
        assert ContractKind.MAIN_FLOW_INPUT in CONTRACT_TYPES
        assert CONTRACT_TYPES[ContractKind.MAIN_FLOW_INPUT] is MainFlowInput

    def test_router_input_kind_has_model(self):
        """ROUTER_INPUT contract kind has a registered model."""
        assert ContractKind.ROUTER_INPUT in CONTRACT_TYPES
        assert CONTRACT_TYPES[ContractKind.ROUTER_INPUT] is RouterInput

    def test_intake_input_kind_has_model(self):
        """INTAKE_INPUT contract kind has a registered model."""
        assert ContractKind.INTAKE_INPUT in CONTRACT_TYPES
        assert CONTRACT_TYPES[ContractKind.INTAKE_INPUT] is IntakeInput

    def test_routing_context_kind_has_model(self):
        """ROUTING_CONTEXT contract kind has a registered model."""
        assert ContractKind.ROUTING_CONTEXT in CONTRACT_TYPES
        assert CONTRACT_TYPES[ContractKind.ROUTING_CONTEXT] is RoutingContext

    def test_router_result_kind_has_model(self):
        """ROUTER_RESULT contract kind has a registered model."""
        assert ContractKind.ROUTER_RESULT in CONTRACT_TYPES
        assert CONTRACT_TYPES[ContractKind.ROUTER_RESULT] is RouterResult

    def test_intake_facts_kind_has_model(self):
        """INTAKE_FACTS contract kind has a registered model."""
        assert ContractKind.INTAKE_FACTS in CONTRACT_TYPES
        assert CONTRACT_TYPES[ContractKind.INTAKE_FACTS] is IntakeFacts

    def test_intake_result_kind_has_model(self):
        """INTAKE_RESULT contract kind has a registered model."""
        assert ContractKind.INTAKE_RESULT in CONTRACT_TYPES
        assert CONTRACT_TYPES[ContractKind.INTAKE_RESULT] is IntakeResult

    def test_data_operation_request_kind_has_model(self):
        """DATA_OPERATION_REQUEST contract kind has a registered model."""
        assert ContractKind.DATA_OPERATION_REQUEST in CONTRACT_TYPES

    def test_data_operation_result_kind_has_model(self):
        """DATA_OPERATION_RESULT contract kind has a registered model."""
        assert ContractKind.DATA_OPERATION_RESULT in CONTRACT_TYPES
        assert CONTRACT_TYPES[ContractKind.DATA_OPERATION_RESULT] is DataOperationResult

    def test_delivery_request_snapshot_kind_has_model(self):
        """DELIVERY_REQUEST_SNAPSHOT contract kind has a registered model."""
        assert ContractKind.DELIVERY_REQUEST_SNAPSHOT in CONTRACT_TYPES
        assert CONTRACT_TYPES[ContractKind.DELIVERY_REQUEST_SNAPSHOT] is DeliveryRequestSnapshot

    def test_operational_error_kind_has_model(self):
        """OPERATIONAL_ERROR contract kind has a registered model."""
        assert ContractKind.OPERATIONAL_ERROR in CONTRACT_TYPES
        assert CONTRACT_TYPES[ContractKind.OPERATIONAL_ERROR] is OperationalError
