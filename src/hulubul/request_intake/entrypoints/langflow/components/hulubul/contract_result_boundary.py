"""Contract result boundary component: validates and serializes contract results.

Split from the former contract_boundary.py (which held three components)
because LangFlow's directory-based custom component loader registers exactly
one component per file, named after the file -- extra classes in the same
file are silently dropped from the sidebar palette. See
router_input_boundary.py and intake_input_boundary.py for the other two.
"""

import json
from typing import Any
from uuid import uuid4

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput
from lfx.schema.data import JSON
from lfx.schema.message import Message
from lfx.template.field.base import Output
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

__all__ = ["CONTRACT_TYPES", "ContractResultBoundaryComponent"]

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


class ContractResultBoundaryComponent(Component):
    """Validates and serializes contract results (OperationalError, RouterResult, IntakeResult).

    Uses registry-driven conversion for all 11 ContractKind values. Validates/type-translates
    only declared LFX Data/JSON values. Catches validation/type failures → INVALID_CONTRACT.
    Unexpected programming errors remain exceptions.
    """

    display_name = "Contract Result Boundary"
    description = "Validates and serializes a contract result against all 11 ContractKind types."
    icon = "shield-check"
    name = "HulubulContractResultBoundary"

    inputs = [  # noqa: RUF012
        HandleInput(  # type: ignore[call-arg]
            name="value",
            display_name="Contract Value",
            info="The contract value to validate (Data/JSON, never free text).",
            input_types=["Data", "JSON"],
            required=True,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="Message", name="response", type_=Message, method="build_output"
        ),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the ContractResultBoundaryComponent."""
        super().__init__(**kwargs)

    def build_output(self) -> Message:
        """LFX-facing output: validate self.value.

        Always returns Message (even for errors, wrapping the JSON error as
        message text) so LFX registers a single declared output type. A
        `Message | JSON` return annotation here makes LFX register
        `output_types=["JSON", "Message"]`, which the frontend's connection
        check treats as a strict subset requirement against a Message-only
        target -- silently rejecting every edge into this output.
        """
        value = self.value
        if hasattr(value, "data"):
            value = value.data
        result = self.validate_contract_value(value)
        if isinstance(result, Message):
            return result
        return Message(text=json.dumps(result.data))

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
                        data = instance.model_dump(mode="json")
                    else:
                        data = dict(instance)
                    return JSON(data=data)
                # Handle BaseModel classes
                elif isinstance(model_type, type) and issubclass(model_type, BaseModel):
                    instance = model_type.model_validate(value)
                    # Success: return as JSON
                    return JSON(data=instance.model_dump(mode="json"))
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

        return JSON(data=error.model_dump(mode="json"))
