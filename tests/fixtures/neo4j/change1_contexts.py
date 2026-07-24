"""Isolated context factories for Change 1 graph fixtures.

Provides factory functions for all 11 RequestStatus values and edge cases
(unknown/null status, closed precedence, sparse/complete requests, duplicates,
missing targets, concurrent snapshots).

Each factory creates isolated namespace and returns ContextFactoryResult.
All Neo4j operations use parameterized queries (no string interpolation).
"""

import uuid
from collections.abc import Callable

from neo4j import Driver

from hulubul.core.models.operational.enums import RequestStatus
from tests.support.acceptance_types import ContextFactoryResult
from tests.support.graph_probe import GraphProbe


def _create_binding_and_sparse_request(
    driver: Driver, session_id: str, status: str | None = None
) -> tuple[str, str]:
    """Create an OperationalConversationBinding and minimal DeliveryRequest.

    Args:
        driver: Neo4j driver instance.
        session_id: Unique session identifier for the binding.
        status: Optional status value to set on the request.

    Returns:
        Tuple of (binding_node_id, request_id).
    """
    session = driver.session()
    try:
        request_id = str(uuid.uuid4())
        query = """
        CREATE (b:OperationalConversationBinding {sessionId: $session_id})
        CREATE (r:DeliveryRequest {id: $request_id, created: datetime(), hasStatus: $status})
        CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r)
        RETURN b, r.id AS request_id
        """
        result = session.run(query, session_id=session_id, request_id=request_id, status=status)
        record = result.single()
        return record.get("b"), record.get("request_id")
    finally:
        session.close()


def _create_binding_and_complete_request(
    driver: Driver, session_id: str, status: str | None = None
) -> tuple[str, str]:
    """Create an OperationalConversationBinding and complete DeliveryRequest with related nodes.

    Args:
        driver: Neo4j driver instance.
        session_id: Unique session identifier for the binding.
        status: Optional status value to set on the request.

    Returns:
        Tuple of (binding_node_id, request_id).
    """
    session = driver.session()
    try:
        request_id = str(uuid.uuid4())
        receiver_agent_id = str(uuid.uuid4())
        parcel_id = str(uuid.uuid4())
        pickup_place_id = str(uuid.uuid4())
        dropoff_place_id = str(uuid.uuid4())

        query = """
        CREATE (b:OperationalConversationBinding {sessionId: $session_id})
        CREATE (r:DeliveryRequest {
            id: $request_id,
            created: datetime(),
            updated: datetime(),
            hasStatus: $status,
            preferredPeriod: "2025-12-31"
        })
        CREATE (receiver:Receiver {id: $receiver_id})
        CREATE (agent:Agent {id: $receiver_agent_id, identifier: "receiver-123", name: "Receiver Agent"})
        CREATE (r)-[:HAS_RECEIVER]->(receiver)-[:PLAYED_BY]->(agent)
        CREATE (parcel:Parcel {id: $parcel_id, declaredContent: "Electronics"})
        CREATE (r)-[:HAS_DELIVERY_ITEM]->(parcel)
        CREATE (pickup:Place {id: $pickup_place_id, name: "Pickup Location", hasType: "address"})
        CREATE (r)-[:HAS_PICK_UP_LOCATION]->(pickup)
        CREATE (dropoff:Place {id: $dropoff_place_id, name: "Drop-off Location", hasType: "address"})
        CREATE (r)-[:HAS_DROP_OFF_LOCATION]->(dropoff)
        CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r)
        RETURN b, r.id AS request_id
        """
        result = session.run(
            query,
            session_id=session_id,
            request_id=request_id,
            status=status,
            receiver_id=str(uuid.uuid4()),
            receiver_agent_id=receiver_agent_id,
            parcel_id=parcel_id,
            pickup_place_id=pickup_place_id,
            dropoff_place_id=dropoff_place_id,
        )
        record = result.single()
        return record.get("b"), record.get("request_id")
    finally:
        session.close()


def create_sparse_request(driver: Driver, session_id: str) -> str:
    """Factory: Create sparse DeliveryRequest in OperationalConversationBinding.

    Minimal fields only (id, created, status).

    Args:
        driver: Neo4j driver instance.
        session_id: Unique session identifier.

    Returns:
        Request ID for assertions.
    """
    _, request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.NEW.value
    )
    return request_id


def create_complete_request(driver: Driver, session_id: str) -> str:
    """Factory: Create complete DeliveryRequest with all related nodes.

    Args:
        driver: Neo4j driver instance.
        session_id: Unique session identifier.

    Returns:
        Request ID for assertions.
    """
    _, request_id = _create_binding_and_complete_request(
        driver, session_id, status=RequestStatus.COMPLETE.value
    )
    return request_id


def create_unknown_status_request(driver: Driver, session_id: str) -> str:
    """Factory: Create DeliveryRequest with unknown (non-enum) status value.

    Args:
        driver: Neo4j driver instance.
        session_id: Unique session identifier.

    Returns:
        Request ID for assertions.
    """
    _, request_id = _create_binding_and_sparse_request(driver, session_id, status="unknown_status")
    return request_id


def create_null_status_request(driver: Driver, session_id: str) -> str:
    """Factory: Create DeliveryRequest with NULL status value.

    Args:
        driver: Neo4j driver instance.
        session_id: Unique session identifier.

    Returns:
        Request ID for assertions.
    """
    _, request_id = _create_binding_and_sparse_request(driver, session_id, status=None)
    return request_id


def create_closed_precedence_request(driver: Driver, session_id: str) -> str:
    """Factory: Create DeliveryRequest with closed status (precedence over other statuses).

    Args:
        driver: Neo4j driver instance.
        session_id: Unique session identifier.

    Returns:
        Request ID for assertions.
    """
    _, request_id = _create_binding_and_sparse_request(driver, session_id, status="closed")
    return request_id


def create_missing_target_binding(driver: Driver, session_id: str) -> str:
    """Factory: Create OperationalConversationBinding with NO BINDS_ACTIVE_REQUEST relationship.

    Binding exists but is not linked to any request.

    Args:
        driver: Neo4j driver instance.
        session_id: Unique session identifier.

    Returns:
        Binding session ID for assertions.
    """
    session = driver.session()
    try:
        query = """
        CREATE (b:OperationalConversationBinding {sessionId: $session_id})
        RETURN b
        """
        session.run(query, session_id=session_id)
        return session_id
    finally:
        session.close()


def create_duplicate_active_request_rels(driver: Driver, session_id: str) -> str:
    """Factory: Create binding with TWO BINDS_ACTIVE_REQUEST rels to SAME request.

    One binding, one request, but two relationships pointing to it (edge case).

    Args:
        driver: Neo4j driver instance.
        session_id: Unique session identifier.

    Returns:
        Request ID for assertions.
    """
    session = driver.session()
    try:
        request_id = str(uuid.uuid4())
        query = """
        CREATE (b:OperationalConversationBinding {sessionId: $session_id})
        CREATE (r:DeliveryRequest {id: $request_id, created: datetime(), hasStatus: $status})
        CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r)
        CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r)
        RETURN r.id AS request_id
        """
        result = session.run(query, session_id=session_id, request_id=request_id, status="new")
        record = result.single()
        return record.get("request_id")
    finally:
        session.close()


def create_duplicate_active_targets(driver: Driver, session_id: str) -> list[str]:
    """Factory: Create binding with TWO BINDS_ACTIVE_REQUEST rels to DIFFERENT requests.

    One binding, two distinct requests, each with a BINDS_ACTIVE_REQUEST relationship (edge case).

    Args:
        driver: Neo4j driver instance.
        session_id: Unique session identifier.

    Returns:
        List of request IDs for assertions.
    """
    session = driver.session()
    try:
        request_id_1 = str(uuid.uuid4())
        request_id_2 = str(uuid.uuid4())
        query = """
        CREATE (b:OperationalConversationBinding {sessionId: $session_id})
        CREATE (r1:DeliveryRequest {id: $request_id_1, created: datetime(), hasStatus: $status})
        CREATE (r2:DeliveryRequest {id: $request_id_2, created: datetime(), hasStatus: $status})
        CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r1)
        CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r2)
        RETURN r1.id AS id1, r2.id AS id2
        """
        result = session.run(
            query,
            session_id=session_id,
            request_id_1=request_id_1,
            request_id_2=request_id_2,
            status="new",
        )
        record = result.single()
        return [record.get("id1"), record.get("id2")]
    finally:
        session.close()


def create_concurrent_snapshots(driver: Driver, session_ids: list[str]) -> list[list[str]]:
    """Factory: Create multiple concurrent bindings, each with its own requests.

    Simulates multiple simultaneous sessions, each with distinct requests.

    Args:
        driver: Neo4j driver instance.
        session_ids: List of unique session identifiers.

    Returns:
        List of request ID lists (one per session_id).
    """
    results = []
    for session_id in session_ids:
        request_id = create_sparse_request(driver, session_id)
        results.append([request_id])
    return results


def create_orphan_request(driver: Driver, namespace: str) -> str:
    """Factory: Create DeliveryRequest NOT bound to any OperationalConversationBinding.

    Orphaned request (for orphan detection testing).

    Args:
        driver: Neo4j driver instance.
        namespace: Scope identifier (unused for orphans, but part of interface).

    Returns:
        Request ID for assertions.
    """
    session = driver.session()
    try:
        request_id = str(uuid.uuid4())
        query = """
        CREATE (r:DeliveryRequest {id: $request_id, created: datetime(), hasStatus: $status})
        RETURN r.id AS request_id
        """
        result = session.run(query, request_id=request_id, status="new")
        record = result.single()
        return record.get("request_id")
    finally:
        session.close()


# ============================================================================
# Factory Functions for Each of the 11 RequestStatus Values
# ============================================================================


def _factory_new(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.NEW."""
    session_id = f"status-new-{uuid.uuid4()}"
    request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.NEW.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"new-{request_id}", snapshot=snapshot)


def _factory_needs_clarification(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.NEEDS_CLARIFICATION."""
    session_id = f"status-needs-clarification-{uuid.uuid4()}"
    request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.NEEDS_CLARIFICATION.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"needsClarification-{request_id}", snapshot=snapshot)


def _factory_complete(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.COMPLETE."""
    session_id = f"status-complete-{uuid.uuid4()}"
    request_id = _create_binding_and_complete_request(
        driver, session_id, status=RequestStatus.COMPLETE.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"complete-{request_id}", snapshot=snapshot)


def _factory_options_proposed(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.OPTIONS_PROPOSED."""
    session_id = f"status-options-proposed-{uuid.uuid4()}"
    request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.OPTIONS_PROPOSED.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"optionsProposed-{request_id}", snapshot=snapshot)


def _factory_waiting_response(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.WAITING_RESPONSE."""
    session_id = f"status-waiting-response-{uuid.uuid4()}"
    request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.WAITING_RESPONSE.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"waitingResponse-{request_id}", snapshot=snapshot)


def _factory_accepted(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.ACCEPTED."""
    session_id = f"status-accepted-{uuid.uuid4()}"
    request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.ACCEPTED.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"accepted-{request_id}", snapshot=snapshot)


def _factory_rejected(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.REJECTED."""
    session_id = f"status-rejected-{uuid.uuid4()}"
    request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.REJECTED.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"rejected-{request_id}", snapshot=snapshot)


def _factory_pick_up_planned(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.PICK_UP_PLANNED."""
    session_id = f"status-pick-up-planned-{uuid.uuid4()}"
    request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.PICK_UP_PLANNED.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"pickUpPlanned-{request_id}", snapshot=snapshot)


def _factory_picked_up(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.PICKED_UP."""
    session_id = f"status-picked-up-{uuid.uuid4()}"
    request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.PICKED_UP.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"pickedUp-{request_id}", snapshot=snapshot)


def _factory_delivered(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.DELIVERED."""
    session_id = f"status-delivered-{uuid.uuid4()}"
    request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.DELIVERED.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"delivered-{request_id}", snapshot=snapshot)


def _factory_cancelled(driver: Driver) -> ContextFactoryResult:
    """Factory for RequestStatus.CANCELLED."""
    session_id = f"status-cancelled-{uuid.uuid4()}"
    request_id = _create_binding_and_sparse_request(
        driver, session_id, status=RequestStatus.CANCELLED.value
    )[1]
    probe = GraphProbe(driver)
    snapshot = probe.snapshot_for_session(session_id)
    return ContextFactoryResult(namespace=f"cancelled-{request_id}", snapshot=snapshot)


# ============================================================================
# Status Context Factories Registry
# ============================================================================

STATUS_CONTEXT_FACTORIES: dict[RequestStatus, Callable[[Driver], ContextFactoryResult]] = {
    RequestStatus.NEW: _factory_new,
    RequestStatus.NEEDS_CLARIFICATION: _factory_needs_clarification,
    RequestStatus.COMPLETE: _factory_complete,
    RequestStatus.OPTIONS_PROPOSED: _factory_options_proposed,
    RequestStatus.WAITING_RESPONSE: _factory_waiting_response,
    RequestStatus.ACCEPTED: _factory_accepted,
    RequestStatus.REJECTED: _factory_rejected,
    RequestStatus.PICK_UP_PLANNED: _factory_pick_up_planned,
    RequestStatus.PICKED_UP: _factory_picked_up,
    RequestStatus.DELIVERED: _factory_delivered,
    RequestStatus.CANCELLED: _factory_cancelled,
}
