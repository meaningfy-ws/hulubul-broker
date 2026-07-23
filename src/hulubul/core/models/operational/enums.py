"""Operational vocabulary and semantic enumerations."""

from enum import Enum

__all__ = [
    "ActorRole",
    "BindingState",
    "CallerFlow",
    "DataOperation",
    "DataOperationOutcome",
    "DependencyKind",
    "ErrorCategory",
    "ErrorCode",
    "ErrorEscalation",
    "FailureKind",
    "IdentityAssurance",
    "IntakeField",
    "IntakeOutcome",
    "InvocationSource",
    "RequestStatus",
    "RetryAction",
    "RouterOutcome",
    "RouterTarget",
    "RoutingReason",
    "RoutingStage",
]


class RequestStatus(str, Enum):
    """Request lifecycle status."""

    NEW = "new"
    NEEDS_CLARIFICATION = "needsClarification"
    COMPLETE = "complete"
    OPTIONS_PROPOSED = "optionsProposed"
    WAITING_RESPONSE = "waitingResponse"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PICK_UP_PLANNED = "pickUpPlanned"
    PICKED_UP = "pickedUp"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


POST_INTAKE_STATUSES = (
    RequestStatus.OPTIONS_PROPOSED,
    RequestStatus.WAITING_RESPONSE,
    RequestStatus.ACCEPTED,
    RequestStatus.REJECTED,
    RequestStatus.PICK_UP_PLANNED,
    RequestStatus.PICKED_UP,
    RequestStatus.DELIVERED,
    RequestStatus.CANCELLED,
)


class IntakeField(str, Enum):
    """Required fields for intake."""

    RECEIVER_IDENTITY = "receiver_identity"
    PICKUP_LOCATION = "pickup_location"
    DROP_OFF_LOCATION = "drop_off_location"
    PARCEL_DECLARED_CONTENT = "parcel_declared_content"
    PREFERRED_PERIOD = "preferred_period"


class DataOperation(str, Enum):
    """Data operation types."""

    GET_REQUEST_ROUTING_CONTEXT = "getRequestRoutingContext"
    CREATE_DELIVERY_REQUEST = "createDeliveryRequest"
    READ_DELIVERY_REQUEST = "readDeliveryRequest"
    UPDATE_DELIVERY_REQUEST = "updateDeliveryRequest"
    SET_REQUEST_STATUS = "setRequestStatus"


class ErrorCode(str, Enum):
    """Operational error codes."""

    INVALID_INPUT = "INVALID_INPUT"
    INVALID_CONTRACT = "INVALID_CONTRACT"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    BINDING_REQUEST_MISMATCH = "BINDING_REQUEST_MISMATCH"
    GRAPH_CONTEXT_INCONSISTENT = "GRAPH_CONTEXT_INCONSISTENT"
    UNSUPPORTED_PHASE1_STATUS = "UNSUPPORTED_PHASE1_STATUS"
    UNSUPPORTED_REQUEST_STATUS = "UNSUPPORTED_REQUEST_STATUS"
    INVALID_EXPECTED_STATUS = "INVALID_EXPECTED_STATUS"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"
    AFFECTED_RECORD_COUNT_MISMATCH = "AFFECTED_RECORD_COUNT_MISMATCH"
    MODEL_TRANSIENT_FAILURE = "MODEL_TRANSIENT_FAILURE"
    MODEL_AUTHENTICATION_FAILURE = "MODEL_AUTHENTICATION_FAILURE"
    MALFORMED_AGENT_RESULT = "MALFORMED_AGENT_RESULT"
    MCP_READ_TRANSIENT_FAILURE = "MCP_READ_TRANSIENT_FAILURE"
    MCP_WRITE_AMBIGUOUS = "MCP_WRITE_AMBIGUOUS"
    MCP_AUTHENTICATION_FAILURE = "MCP_AUTHENTICATION_FAILURE"
    MCP_OPERATION_FAILURE = "MCP_OPERATION_FAILURE"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"


class ActorRole(str, Enum):
    """Actor role."""

    SENDER = "sender"


class IdentityAssurance(str, Enum):
    """Identity assurance level."""

    SIMULATED = "simulated"


class InvocationSource(str, Enum):
    """Flow invocation source."""

    API = "api"
    PLAYGROUND = "playground"


class BindingState(str, Enum):
    """Binding state."""

    ABSENT = "absent"
    BOUND = "bound"
    INCONSISTENT = "inconsistent"


class RoutingStage(str, Enum):
    """Request routing stage."""

    INTAKE = "intake"
    COMPLETE = "complete"
    CLOSED = "closed"
    UNSUPPORTED = "unsupported"
    FAILURE = "failure"


class RouterOutcome(str, Enum):
    """Router decision outcome."""

    ROUTED = "routed"
    INFORMATIONAL = "informational"
    FAILURE = "failure"


class RouterTarget(str, Enum):
    """Router target."""

    INTAKE = "intake"
    NONE = "none"


class RoutingReason(str, Enum):
    """Reason for routing decision."""

    NO_BINDING = "noBinding"
    INTAKE_IN_PROGRESS = "intakeInProgress"
    INTAKE_COMPLETE = "intakeComplete"
    REQUEST_CLOSED = "requestClosed"
    UNSUPPORTED_STATUS = "unsupportedStatus"
    INVALID_CONTEXT = "invalidContext"
    LOOKUP_FAILED = "lookupFailed"


class IntakeOutcome(str, Enum):
    """Intake operation outcome."""

    CLARIFICATION_REQUIRED = "clarificationRequired"
    REQUEST_COMPLETE = "requestComplete"
    FAILURE = "failure"


class DataOperationOutcome(str, Enum):
    """Data operation result outcome."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"


class CallerFlow(str, Enum):
    """Caller flow identifier."""

    LF_00 = "LF-00"
    LF_10 = "LF-10"
    LF_70 = "LF-70"


class ErrorCategory(str, Enum):
    """Error category for logging."""

    INPUT = "input"
    CONTRACT = "contract"
    AUTHORIZATION = "authorization"
    STATE = "state"
    CONCURRENCY = "concurrency"
    DEPENDENCY = "dependency"
    INTERNAL = "internal"


class ErrorEscalation(str, Enum):
    """Error escalation level."""

    NONE = "none"
    HARD_GATE_FAILURE = "hard-gate failure"
    MANUAL_AMBIGUOUS_WRITE_GRAPH_INSPECTION = "manual ambiguous-write graph inspection"


class DependencyKind(str, Enum):
    """Dependency kind."""

    MODEL = "model"
    MCP_READ = "mcpRead"
    MCP_WRITE = "mcpWrite"


class FailureKind(str, Enum):
    """Failure kind for retry classification."""

    TIMEOUT = "timeout"
    CONNECTION = "connection"
    PROTOCOL = "protocol"
    HTTP_STATUS = "httpStatus"
    MALFORMED_RESULT = "malformedResult"
    NEO4J_TRANSIENT = "neo4jTransient"
    SERVICE_UNAVAILABLE = "serviceUnavailable"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    UNSUPPORTED_OPERATION = "unsupportedOperation"
    CYPHER_CLIENT = "cypherClient"
    CYPHER_SYNTAX = "cypherSyntax"
    CONSTRAINT = "constraint"
    AFFECTED_COUNT = "affectedCount"


class RetryAction(str, Enum):
    """Retry decision action."""

    RETRY = "retry"
    REPAIR_RAW_RESULT = "repairRawResult"
    FAIL = "fail"
