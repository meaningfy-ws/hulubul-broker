"""Retry policy classification and decision service for request intake.

Per plan Task 14 and DEC-015 (design.md), this module answers two questions
for any controlled failure: what kind of failure is it (``classify_failure``),
and what should happen next (``retry_action`` / ``should_retry`` /
``max_retries``). The decision matrix is exhaustive over
``FailureKind`` -- every variant is explicitly mapped, with no wildcard or
default branch.

Three outcomes exist, per DEC-015:

- **Retryable (transient):** timeouts, connection/protocol failures, HTTP
  status failures, and Neo4j/service-unavailable transients get exactly one
  retry after a fixed delay owned by the caller.
- **Non-retryable (permanent):** authentication, validation, unsupported
  operations, Cypher client/syntax errors, constraint violations, and
  affected-record mismatches never retry.
- **Tool-less repair:** a malformed structured result gets exactly one
  repair attempt against the existing raw output. This is never a replay of
  a dispatched write -- the write-capable action itself is never rerun.

This module is pure: no I/O, no retry loop, no delay/sleep. Callers (the
LangFlow retry-decision component and higher layers) own the actual attempt
loop, the fixed delay, and -- critically -- the prohibition on replaying a
dispatched write; this service only classifies failures and states the
per-kind policy.

``classify_failure`` accepts either a raw exception surfaced by an adapter
call, or an already-built ``OperationalError``. Because an ``OperationalError``
already represents a *finalized* contract, only codes that are unambiguously
and unconditionally non-retryable (e.g. authentication failures) are
reclassified from it; codes that represent an already-exhausted retry cycle
(e.g. ``MODEL_TRANSIENT_FAILURE``) intentionally raise ``ValueError`` rather
than being reinterpreted as "still retryable", which would violate the
one-retry-only rule.
"""

from __future__ import annotations

from hulubul.core.models.operational.enums import ErrorCode, FailureKind, RetryAction
from hulubul.core.models.operational.errors import OperationalError

__all__ = [
    "RETRY_ACTION_BY_FAILURE_KIND",
    "classify_failure",
    "max_retries",
    "retry_action",
    "should_retry",
]

# Transient: eligible for exactly one retry after a fixed delay.
_TRANSIENT_FAILURE_KINDS: tuple[FailureKind, ...] = (
    FailureKind.TIMEOUT,
    FailureKind.CONNECTION,
    FailureKind.PROTOCOL,
    FailureKind.HTTP_STATUS,
    FailureKind.NEO4J_TRANSIENT,
    FailureKind.SERVICE_UNAVAILABLE,
)

# Tool-less repair: one repair attempt against the existing raw result, never
# a replay of a dispatched write.
_TOOL_LESS_REPAIR_FAILURE_KINDS: tuple[FailureKind, ...] = (FailureKind.MALFORMED_RESULT,)

# Permanent: never retried.
_PERMANENT_FAILURE_KINDS: tuple[FailureKind, ...] = (
    FailureKind.AUTHENTICATION,
    FailureKind.VALIDATION,
    FailureKind.UNSUPPORTED_OPERATION,
    FailureKind.CYPHER_CLIENT,
    FailureKind.CYPHER_SYNTAX,
    FailureKind.CONSTRAINT,
    FailureKind.AFFECTED_COUNT,
)

RETRY_ACTION_BY_FAILURE_KIND: dict[FailureKind, RetryAction] = {
    **{kind: RetryAction.RETRY for kind in _TRANSIENT_FAILURE_KINDS},
    **{kind: RetryAction.REPAIR_RAW_RESULT for kind in _TOOL_LESS_REPAIR_FAILURE_KINDS},
    **{kind: RetryAction.FAIL for kind in _PERMANENT_FAILURE_KINDS},
}
"""Exhaustive FailureKind -> RetryAction matrix; every FailureKind is present."""

_MAX_ATTEMPTS_BY_RETRY_ACTION: dict[RetryAction, int] = {
    RetryAction.RETRY: 1,
    RetryAction.REPAIR_RAW_RESULT: 1,
    RetryAction.FAIL: 0,
}

# Explicit, order-independent exception-type registry (OSError subclasses are
# siblings, so isinstance checks below never shadow one another).
_EXCEPTION_TYPE_TO_FAILURE_KIND: tuple[tuple[type[Exception], FailureKind], ...] = (
    (TimeoutError, FailureKind.TIMEOUT),
    (ConnectionError, FailureKind.CONNECTION),
    (PermissionError, FailureKind.AUTHENTICATION),
    (ValueError, FailureKind.VALIDATION),
)

# Only codes that are unconditionally non-retryable, regardless of when in
# the retry lifecycle they occur, are safe to reclassify from an
# OperationalError. Codes that represent an already-exhausted retry/repair
# cycle (e.g. MODEL_TRANSIENT_FAILURE, MCP_READ_TRANSIENT_FAILURE,
# MALFORMED_AGENT_RESULT) are deliberately excluded.
_OPERATIONAL_ERROR_CODE_TO_FAILURE_KIND: dict[ErrorCode, FailureKind] = {
    ErrorCode.MODEL_AUTHENTICATION_FAILURE: FailureKind.AUTHENTICATION,
    ErrorCode.MCP_AUTHENTICATION_FAILURE: FailureKind.AUTHENTICATION,
}


def classify_failure(error: Exception | OperationalError) -> FailureKind:
    """Classify a raw failure into a FailureKind for retry decisioning.

    Raises ``ValueError`` for any input this policy does not recognize,
    rather than guessing -- a wrong classification could unsafely retry (or
    unsafely refuse to retry) a real failure.
    """
    if isinstance(error, OperationalError):
        try:
            return _OPERATIONAL_ERROR_CODE_TO_FAILURE_KIND[error.code]
        except KeyError:
            raise ValueError(
                f"No FailureKind classification for OperationalError code {error.code!r}"
            ) from None

    for exception_type, failure_kind in _EXCEPTION_TYPE_TO_FAILURE_KIND:
        if isinstance(error, exception_type):
            return failure_kind

    raise ValueError(f"No FailureKind classification for exception type {type(error)!r}")


def retry_action(failure_kind: FailureKind) -> RetryAction:
    """Return the retry action for a failure kind (exhaustive, no default)."""
    return RETRY_ACTION_BY_FAILURE_KIND[failure_kind]


def should_retry(failure_kind: FailureKind) -> bool:
    """Report whether a failure kind warrants another attempt.

    True for transient failures (another network/model/read attempt) and for
    the malformed-result tool-less repair; false for every permanent
    failure kind.
    """
    return retry_action(failure_kind) is not RetryAction.FAIL


def max_retries(failure_kind: FailureKind) -> int:
    """Return the maximum further attempts for a failure kind.

    0 means no retry. 1 means either one retry (transient) or one tool-less
    repair attempt (malformed result) -- never a replay of a dispatched
    write, which callers must enforce independently of this classification.
    """
    return _MAX_ATTEMPTS_BY_RETRY_ACTION[retry_action(failure_kind)]
