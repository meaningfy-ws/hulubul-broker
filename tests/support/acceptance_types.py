"""Value objects for acceptance test contexts and graph snapshots."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextGraphSnapshot:
    """Immutable snapshot of graph state for a conversation session.

    Captures session binding count, active request count, request IDs, and status values
    at a point in time.
    """

    session_id: str
    binding_count: int
    request_count: int
    request_ids: frozenset[str]
    statuses: frozenset[str | None]

    def __post_init__(self) -> None:
        """Validate snapshot invariants."""
        if self.binding_count < 0:
            raise ValueError("binding_count cannot be negative")
        if self.request_count < 0:
            raise ValueError("request_count cannot be negative")
        if self.binding_count == 0 and self.request_count > 0:
            raise ValueError("Cannot have requests without a binding")


@dataclass(frozen=True)
class ContextFactoryResult:
    """Result of a context factory: isolated namespace and snapshot."""

    namespace: str
    snapshot: ContextGraphSnapshot

    def __post_init__(self) -> None:
        """Validate that namespace is non-empty."""
        if not self.namespace:
            raise ValueError("namespace must be non-empty")
