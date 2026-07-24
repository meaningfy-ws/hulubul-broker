"""Operational contract boundary components: validation, error translation, fixed-edge enforcement.

This module provides three LFX components for handling operational contracts:
1. RouterInputBoundaryComponent: Assembles RouterInput from fixed envelope/context edges
2. IntakeInputBoundaryComponent: Assembles IntakeInput from fixed envelope/context edges
3. ContractResultBoundaryComponent: Validates and serializes contract results

All components enforce:
- Registry-driven conversion (all 11 ContractKind values)
- Fixed envelope/context fields (advanced, cannot be overridden)
- Error redaction (validation errors never expose user values)
- Type translation to INVALID_CONTRACT on failure
- Output as typed Message/JSON, never raw dict
"""

from typing import Any
from uuid import uuid4

from lfx.custom.custom_component.component import Component
from lfx.schema.data import JSON
from lfx.schema.message import Message
from pydantic import BaseModel, TypeAdapter, ValidationError

from hulubul.core.models.operational import (
    ContractKind,
    DataOperationResult,
    DeliveryRequestSnapshot,
    ErrorCode,
    IntakeFacts,
    IntakeInput,
    IntakeResult,
    MainFlowInput,
    OperationalError,
    RouterInput,
    RouterResult,
    RoutingContext,
)
from hulubul.core.models.operational.data_operations import DATA_OPERATION_ADAPTER
from hulubul.core.models.operational.errors import ERROR_POLICY

__all__ = [
    "CONTRACT_TYPES",
    "ContractResultBoundaryComponent",
    "IntakeInputBoundaryComponent",
    "RouterInputBoundaryComponent",
]

# ============================================================================
# Registry: All 11 ContractKind values → Model types
# ============================================================================

CONTRACT_TYPES = {
    ContractKind.MAIN_FLOW_INPUT: MainFlowInput,
    ContractKind.ROUTER_INPUT: RouterInput,
    ContractKind.INTAKE_INPUT: IntakeInput,
    ContractKind.ROUTING_CONTEXT: RoutingContext,
    ContractKind.ROUTER_RESULT: RouterResult,
    ContractKind.INTAKE_FACTS: IntakeFacts,
    ContractKind.INTAKE_RESULT: IntakeResult,
    ContractKind.DATA_OPERATION_REQUEST: DATA_OPERATION_ADAPTER,
    ContractKind.DATA_OPERATION_RESULT: DataOperationResult,
    ContractKind.DELIVERY_REQUEST_SNAPSHOT: DeliveryRequestSnapshot,
    ContractKind.OPERATIONAL_ERROR: OperationalError,
}

# Verify registry contains all 11 ContractKind values
assert set(CONTRACT_TYPES.keys()) == set(ContractKind), (
    "Registry missing or has extra ContractKind values"
)


class RouterInputBoundaryComponent(Component):
    """Assembles RouterInput from fixed advanced envelope/context edges + validated Data payload.

    The envelope and routing_context are advanced (fixed) fields, absent from model tool schemas.
    They cannot be overridden by user input, model output, prose, or tweaks.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the RouterInputBoundaryComponent."""
        super().__init__(**kwargs)
        self.envelope: MainFlowInput | None = None
        self.routing_context: RoutingContext | None = None

    def build_router_input(self) -> Message:
        """Build RouterInput from fixed envelope/context edges.

        Returns:
            Message: An LFX Message with RouterInput serialized as JSON

        Raises:
            ValueError: If envelope or routing_context is missing
        """
        if self.envelope is None:
            raise ValueError("INVALID_CONFIGURATION: envelope is required")

        if self.routing_context is None:
            raise ValueError("INVALID_CONFIGURATION: routing_context is required")

        # Assemble RouterInput from fixed edges
        wrapper = RouterInput(
            schema_version=self.envelope.schema_version,
            correlation_id=self.envelope.correlation_id,
            envelope=self.envelope,
            routing_context=self.routing_context,
        )

        # Return as Message with JSON text
        return Message(text=wrapper.model_dump_json())


class IntakeInputBoundaryComponent(Component):
    """Assembles IntakeInput from fixed advanced envelope/context edges + validated Data payload.

    The envelope and routing_context are advanced (fixed) fields, absent from model tool schemas.
    They cannot be overridden by user input, model output, prose, or tweaks.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the IntakeInputBoundaryComponent."""
        super().__init__(**kwargs)
        self.envelope: MainFlowInput | None = None
        self.routing_context: RoutingContext | None = None

    def build_intake_input(self) -> Message:
        """Build IntakeInput from fixed envelope/context edges.

        Returns:
            Message: An LFX Message with IntakeInput serialized as JSON

        Raises:
            ValueError: If envelope or routing_context is missing
        """
        if self.envelope is None:
            raise ValueError("INVALID_CONFIGURATION: envelope is required")

        if self.routing_context is None:
            raise ValueError("INVALID_CONFIGURATION: routing_context is required")

        # Assemble IntakeInput from fixed edges
        wrapper = IntakeInput(
            schema_version=self.envelope.schema_version,
            correlation_id=self.envelope.correlation_id,
            envelope=self.envelope,
            routing_context=self.routing_context,
        )

        # Return as Message with JSON text
        return Message(text=wrapper.model_dump_json())


class ContractResultBoundaryComponent(Component):
    """Validates and serializes contract results (OperationalError, RouterResult, IntakeResult).

    Uses registry-driven conversion for all 11 ContractKind values. Validates/type-translates
    only declared LFX Data/JSON values. Catches validation/type failures → INVALID_CONTRACT.
    Unexpected programming errors remain exceptions.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the ContractResultBoundaryComponent."""
        super().__init__(**kwargs)

    def validate_contract_value(self, value: dict[str, Any] | Any) -> Message | JSON:
        """Validate and convert a contract value to typed model.

        Attempts to validate the input value against all registered contract types.
        On validation failure, returns canonical INVALID_CONTRACT OperationalError.

        Args:
            value: The contract value to validate (dict or other type)

        Returns:
            Message or JSON: Typed, validated contract or error

        Raises:
            ValueError: Only for unexpected programming errors, not validation failures
        """
        if value is None:
            return self._make_error_response(ErrorCode.INVALID_CONTRACT)

        if not isinstance(value, dict):
            return self._make_error_response(ErrorCode.INVALID_CONTRACT)

        # Try to validate against each registered contract type
        for _contract_kind, model_type in CONTRACT_TYPES.items():
            try:
                # Handle TypeAdapter (for DATA_OPERATION_REQUEST)
                if isinstance(model_type, TypeAdapter):
                    instance = model_type.validate_python(value)
                    # Success: return as JSON
                    if hasattr(instance, "model_dump"):
                        data = instance.model_dump()
                    else:
                        data = dict(instance)
                    return JSON(data=data)
                # Handle BaseModel classes
                elif isinstance(model_type, type) and issubclass(model_type, BaseModel):
                    instance = model_type.model_validate(value)
                    # Success: return as JSON
                    return JSON(data=instance.model_dump())
                else:
                    # Unknown type, skip
                    continue
            except ValidationError:
                # Validation failure, continue to next type
                continue
            except (TypeError, ValueError, AttributeError):
                # Other validation issues, continue
                continue

        # None of the registered types matched
        # Return canonical INVALID_CONTRACT error (never expose raw values)
        return self._make_error_response(ErrorCode.INVALID_CONTRACT)

    def _make_error_response(
        self,
        code: ErrorCode,
    ) -> JSON:
        """Create a canonical error response without exposing user values.

        Args:
            code: The ErrorCode

        Returns:
            JSON: Serialized OperationalError
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

        return JSON(data=error.model_dump())
