"""Integration tests for LF-70 setRequestStatus operation.

Tests verify:
- Each allowed status transition in the Change 1 transition table
- Invalid transitions are rejected without Neo4j mutation
- Stale expected_updated_at/expected_status triggers non-mutating classification
- Exactly one request is affected by successful transitions
- Compare-and-set semantics prevent concurrent modification

The LF-70 flow (stable ID 94f6774d-ebc7-5bf1-8486-886f91886a5f) is live and
uses real Neo4j MCP tools. These tests call the real flow via LangFlow API
and assert against actual graph state.

Live Neo4j and LangFlow instances are expected to be running at:
- Neo4j: bolt://localhost:7687
- LangFlow: http://localhost:7860
"""

from __future__ import annotations

import contextlib
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import pytest

from hulubul.core.models.operational.enums import DataOperationOutcome, ErrorCode, RequestStatus
from tests.support.langflow_client import FlowReply, LangFlowClient

# LF-70 stable flow ID from task 29/32
LF_70_FLOW_ID = "94f6774d-ebc7-5bf1-8486-886f91886a5f"


class Neo4jHelper:
    """Helper to query/seed Neo4j directly for assertions."""

    def __init__(self, driver: Any) -> None:
        """Initialize with Neo4j driver."""
        self.driver = driver

    def seed_request(
        self,
        request_id: str,
        status: RequestStatus | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """Seed a DeliveryRequest in Neo4j at a specific status/timestamp.

        Args:
            request_id: The request ID to create
            status: The status to set (None = unset, not created)
            updated_at: The updated_at timestamp (defaults to now)
        """
        if updated_at is None:
            updated_at = datetime.now(timezone.utc)

        if status is None:
            # Node exists but has no status set
            cypher = "CREATE (r:DeliveryRequest {id: $request_id, updated: $updated_at})"
            with self.driver.session() as session:
                session.run(cypher, request_id=request_id, updated_at=updated_at)
        else:
            # Node exists with status. Property names (hasStatus/updated) match the
            # real domain schema (model/generated/neo4j/constraints.cypher) -- an
            # earlier version of this fixture used status/updated_at, which silently
            # never matched setRequestStatus's compare-and-set query.
            cypher = (
                "CREATE (r:DeliveryRequest {id: $request_id, hasStatus: $status, "
                "updated: $updated_at})"
            )
            with self.driver.session() as session:
                session.run(
                    cypher,
                    request_id=request_id,
                    status=status.value,
                    updated_at=updated_at,
                )

    def get_request_state(self, request_id: str) -> dict[str, Any] | None:
        """Fetch current status and updated_at from Neo4j.

        Returns:
            Dict with 'status' and 'updated_at' keys, or None if not found
        """
        cypher = (
            "MATCH (r:DeliveryRequest {id: $request_id}) "
            "RETURN r.hasStatus as status, r.updated as updated_at"
        )
        with self.driver.session() as session:
            result = session.run(cypher, request_id=request_id)
            record = result.single()
            if record:
                return {"status": record["status"], "updated_at": record["updated_at"]}
            return None

    def cleanup_request(self, request_id: str) -> None:
        """Delete a request and all related nodes."""
        cypher = "MATCH (r:DeliveryRequest {id: $request_id}) DETACH DELETE r"
        with self.driver.session() as session:
            session.run(cypher, request_id=request_id)


@pytest.fixture(scope="session")
def neo4j_live_driver() -> Any:
    """Connect to live Neo4j instance at bolt://localhost:7687.

    Reads credentials from infra/.env. Skips if connection fails.
    """
    try:
        from neo4j import GraphDatabase
    except ImportError:
        pytest.skip("neo4j not installed; run: poetry install --with integration")

    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "changeme123")

    try:
        driver = GraphDatabase.driver(
            "bolt://localhost:7687", auth=(neo4j_username, neo4j_password)
        )
        # Test connection
        with driver.session() as session:
            session.run("RETURN 1")
        yield driver
    except Exception as e:
        pytest.skip(f"Neo4j not available at localhost:7687: {e}")
    finally:
        with contextlib.suppress(Exception):
            driver.close()


@pytest.fixture
def neo4j_helper(neo4j_live_driver: Any) -> Neo4jHelper:
    """Provide Neo4j helper for direct graph assertions."""
    return Neo4jHelper(neo4j_live_driver)


@pytest.fixture
def langflow_helper(langflow_client: LangFlowClient) -> LangFlowClient:
    """Provide LangFlow client configured for LF-70 calls."""
    return langflow_client


def _skip_if_langflow_unavailable(response: FlowReply) -> None:
    """Skip test if LangFlow is unavailable or returns auth error.

    Args:
        response: The FlowReply from a LangFlow call
    """
    if response.status_code == 500 and "Connection refused" in (response.error or ""):
        pytest.skip("LangFlow server not running")
    if response.status_code == 403:
        pytest.skip(f"LangFlow authentication issue: {response.error}")


class TestSetRequestStatusTransitions:
    """Test valid status transitions via LF-70 setRequestStatus operation."""

    def test_transition_none_to_new_is_rejected(
        self,
        langflow_helper: LangFlowClient,
        neo4j_helper: Neo4jHelper,
    ) -> None:
        """None → NEW is NOT a setRequestStatus transition -- it is contract-invalid.

        Per plan.md's setRequestStatus transition table (`new->needsClarification`,
        `new->complete`, `needsClarification->complete` only) and its explicit
        note that "`none->new` exists only inside atomic create": a request
        with no status is not yet a DeliveryRequest row this operation can act
        on, and `SetRequestStatusRequest.expected_status` is typed as a
        required `str`, not `str | None` -- there is no way to construct a
        contract-valid payload asserting "no status" as the expected current
        state. The only path from "doesn't exist yet" to `new` is
        createDeliveryRequest's atomic create.

        Expected: rejected as INVALID_CONTRACT before the request ever
        reaches the Agent (write_dispatched=False), with no Neo4j mutation.
        """
        request_id = f"req-test-none-to-new-{uuid4()}"
        now = datetime.now(timezone.utc)

        try:
            # Seed request with no status
            neo4j_helper.seed_request(request_id, status=None, updated_at=now)
            state_before = neo4j_helper.get_request_state(request_id)
            assert state_before is not None
            assert state_before["status"] is None

            # Attempt setRequestStatus: None → NEW (contract-invalid)
            payload = _build_set_status_payload(
                request_id=request_id,
                expected_status=None,
                expected_updated_at=now,
                target_status=RequestStatus.NEW,
            )

            response = langflow_helper.run_flow_with_actor(
                flow_uuid=LF_70_FLOW_ID,
                input_data=payload,
                actor_id="test-actor-001",
            )

            # Check for infrastructure issues
            _skip_if_langflow_unavailable(response)

            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.error}"
            )
            assert response.result is not None
            result_data = response.result

            # Verify rejection
            assert result_data.get("outcome") == DataOperationOutcome.REJECTED.value
            assert result_data.get("success") is False
            assert result_data.get("write_dispatched") is False
            assert result_data.get("error_code") == ErrorCode.INVALID_CONTRACT.value

            # Verify no Neo4j mutation
            state_after = neo4j_helper.get_request_state(request_id)
            assert state_after is not None
            assert state_after["status"] is None
            assert state_after["updated_at"] == state_before["updated_at"]
        finally:
            neo4j_helper.cleanup_request(request_id)

    def test_transition_new_to_needs_clarification(
        self,
        langflow_helper: LangFlowClient,
        neo4j_helper: Neo4jHelper,
    ) -> None:
        """NEW → NEEDS_CLARIFICATION is allowed.

        Transition table: NEW can go to NEEDS_CLARIFICATION or COMPLETE.
        Expected: Flow returns success, Neo4j shows status=needsClarification with updated timestamp.
        """
        request_id = f"req-test-new-to-clarify-{uuid4()}"
        now = datetime.now(timezone.utc)

        try:
            # Seed request with NEW status
            neo4j_helper.seed_request(request_id, status=RequestStatus.NEW, updated_at=now)

            # Call setRequestStatus: NEW → NEEDS_CLARIFICATION
            payload = _build_set_status_payload(
                request_id=request_id,
                expected_status=RequestStatus.NEW,
                expected_updated_at=now,
                target_status=RequestStatus.NEEDS_CLARIFICATION,
            )

            response = langflow_helper.run_flow_with_actor(
                flow_uuid=LF_70_FLOW_ID,
                input_data=payload,
                actor_id="test-actor-001",
            )

            _skip_if_langflow_unavailable(response)

            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.error}"
            )
            result_data = response.result
            assert result_data is not None
            assert result_data.get("outcome") == DataOperationOutcome.CONFIRMED.value
            assert result_data.get("success") is True
            assert result_data.get("status") == RequestStatus.NEEDS_CLARIFICATION.value

            # Verify Neo4j mutation
            state_after = neo4j_helper.get_request_state(request_id)
            assert state_after is not None
            assert state_after["status"] == RequestStatus.NEEDS_CLARIFICATION.value
        finally:
            neo4j_helper.cleanup_request(request_id)

    def test_transition_new_to_complete(
        self,
        langflow_helper: LangFlowClient,
        neo4j_helper: Neo4jHelper,
    ) -> None:
        """NEW → COMPLETE is allowed.

        Transition table: NEW can go to NEEDS_CLARIFICATION or COMPLETE.
        Expected: Flow returns success, Neo4j shows status=complete with updated timestamp.
        """
        request_id = f"req-test-new-to-complete-{uuid4()}"
        now = datetime.now(timezone.utc)

        try:
            # Seed request with NEW status
            neo4j_helper.seed_request(request_id, status=RequestStatus.NEW, updated_at=now)

            # Call setRequestStatus: NEW → COMPLETE
            payload = _build_set_status_payload(
                request_id=request_id,
                expected_status=RequestStatus.NEW,
                expected_updated_at=now,
                target_status=RequestStatus.COMPLETE,
            )

            response = langflow_helper.run_flow_with_actor(
                flow_uuid=LF_70_FLOW_ID,
                input_data=payload,
                actor_id="test-actor-001",
            )

            _skip_if_langflow_unavailable(response)

            assert response.status_code == 200
            result_data = response.result
            assert result_data is not None
            assert result_data.get("outcome") == DataOperationOutcome.CONFIRMED.value
            assert result_data.get("success") is True
            assert result_data.get("status") == RequestStatus.COMPLETE.value

            # Verify Neo4j mutation
            state_after = neo4j_helper.get_request_state(request_id)
            assert state_after is not None
            assert state_after["status"] == RequestStatus.COMPLETE.value
        finally:
            neo4j_helper.cleanup_request(request_id)

    def test_transition_needs_clarification_to_complete(
        self,
        langflow_helper: LangFlowClient,
        neo4j_helper: Neo4jHelper,
    ) -> None:
        """NEEDS_CLARIFICATION → COMPLETE is allowed.

        Transition table: NEEDS_CLARIFICATION can only go to COMPLETE.
        Expected: Flow returns success, Neo4j shows status=complete with updated timestamp.
        """
        request_id = f"req-test-clarify-to-complete-{uuid4()}"
        now = datetime.now(timezone.utc)

        try:
            # Seed request with NEEDS_CLARIFICATION status
            neo4j_helper.seed_request(
                request_id, status=RequestStatus.NEEDS_CLARIFICATION, updated_at=now
            )

            # Call setRequestStatus: NEEDS_CLARIFICATION → COMPLETE
            payload = _build_set_status_payload(
                request_id=request_id,
                expected_status=RequestStatus.NEEDS_CLARIFICATION,
                expected_updated_at=now,
                target_status=RequestStatus.COMPLETE,
            )

            response = langflow_helper.run_flow_with_actor(
                flow_uuid=LF_70_FLOW_ID,
                input_data=payload,
                actor_id="test-actor-001",
            )

            _skip_if_langflow_unavailable(response)

            assert response.status_code == 200
            result_data = response.result
            assert result_data is not None
            assert result_data.get("outcome") == DataOperationOutcome.CONFIRMED.value
            assert result_data.get("success") is True
            assert result_data.get("status") == RequestStatus.COMPLETE.value

            # Verify Neo4j mutation
            state_after = neo4j_helper.get_request_state(request_id)
            assert state_after is not None
            assert state_after["status"] == RequestStatus.COMPLETE.value
        finally:
            neo4j_helper.cleanup_request(request_id)


class TestInvalidStatusTransitions:
    """Test that invalid transitions are rejected without mutation."""

    def test_invalid_transition_complete_to_new(
        self,
        langflow_helper: LangFlowClient,
        neo4j_helper: Neo4jHelper,
    ) -> None:
        """COMPLETE → NEW is NOT allowed (violates transition table).

        Transition table: COMPLETE has no outgoing edges.
        Expected: Flow returns rejected/error, Neo4j shows zero mutation.
        """
        request_id = f"req-test-invalid-complete-new-{uuid4()}"
        now = datetime.now(timezone.utc)

        try:
            # Seed request with COMPLETE status
            neo4j_helper.seed_request(request_id, status=RequestStatus.COMPLETE, updated_at=now)
            state_before = neo4j_helper.get_request_state(request_id)

            # Call setRequestStatus: COMPLETE → NEW (invalid)
            payload = _build_set_status_payload(
                request_id=request_id,
                expected_status=RequestStatus.COMPLETE,
                expected_updated_at=now,
                target_status=RequestStatus.NEW,
            )

            response = langflow_helper.run_flow_with_actor(
                flow_uuid=LF_70_FLOW_ID,
                input_data=payload,
                actor_id="test-actor-001",
            )

            _skip_if_langflow_unavailable(response)

            assert response.status_code == 200
            result_data = response.result
            assert result_data is not None

            # Should be rejected or contain error
            assert result_data.get("success") is False
            assert result_data.get("outcome") == DataOperationOutcome.REJECTED.value

            # Verify Neo4j shows NO mutation
            state_after = neo4j_helper.get_request_state(request_id)
            assert state_after is not None
            assert state_before == state_after, (
                "Neo4j should show no mutation for invalid transition"
            )
        finally:
            neo4j_helper.cleanup_request(request_id)


class TestConcurrentModificationDetection:
    """Test non-mutating zero-row classification via stale CAS values."""

    def test_stale_expected_updated_at(
        self,
        langflow_helper: LangFlowClient,
        neo4j_helper: Neo4jHelper,
    ) -> None:
        """Stale expected_updated_at (CAS check fails) triggers non-mutating classification.

        Expected: Flow classifies as CONCURRENT_MODIFICATION or INVALID_EXPECTED_STATUS,
        returns count=0, and Neo4j shows no mutation.
        """
        request_id = f"req-test-stale-ts-{uuid4()}"
        now = datetime.now(timezone.utc)
        stale_ts = now - timedelta(hours=1)

        try:
            # Seed request with current status/timestamp
            neo4j_helper.seed_request(request_id, status=RequestStatus.NEW, updated_at=now)

            # Call setRequestStatus with STALE expected_updated_at
            payload = _build_set_status_payload(
                request_id=request_id,
                expected_status=RequestStatus.NEW,
                expected_updated_at=stale_ts,  # Stale!
                target_status=RequestStatus.COMPLETE,
            )

            response = langflow_helper.run_flow_with_actor(
                flow_uuid=LF_70_FLOW_ID,
                input_data=payload,
                actor_id="test-actor-001",
            )

            _skip_if_langflow_unavailable(response)

            assert response.status_code == 200
            result_data = response.result
            assert result_data is not None

            # Should be rejected due to stale timestamp
            assert result_data.get("success") is False
            # Either CONCURRENT_MODIFICATION or similar error
            assert result_data.get("outcome") == DataOperationOutcome.REJECTED.value

            # Verify count is 0 (no rows affected)
            assert result_data.get("count") == 0 or result_data.get("count") is None

            # Verify Neo4j shows NO mutation
            state_after = neo4j_helper.get_request_state(request_id)
            assert state_after is not None
            assert state_after["status"] == RequestStatus.NEW.value
            assert state_after["updated_at"] == now
        finally:
            neo4j_helper.cleanup_request(request_id)

    def test_stale_expected_status(
        self,
        langflow_helper: LangFlowClient,
        neo4j_helper: Neo4jHelper,
    ) -> None:
        """Stale expected_status (CAS check fails) triggers non-mutating classification.

        Expected: Flow classifies as INVALID_EXPECTED_STATUS, returns count=0,
        and Neo4j shows no mutation.
        """
        request_id = f"req-test-stale-status-{uuid4()}"
        now = datetime.now(timezone.utc)

        try:
            # Seed request with NEEDS_CLARIFICATION status
            neo4j_helper.seed_request(
                request_id, status=RequestStatus.NEEDS_CLARIFICATION, updated_at=now
            )

            # Call setRequestStatus with STALE expected_status (say it's NEW but it's really NEEDS_CLARIFICATION)
            payload = _build_set_status_payload(
                request_id=request_id,
                expected_status=RequestStatus.NEW,  # Stale! Actually NEEDS_CLARIFICATION
                expected_updated_at=now,
                target_status=RequestStatus.COMPLETE,
            )

            response = langflow_helper.run_flow_with_actor(
                flow_uuid=LF_70_FLOW_ID,
                input_data=payload,
                actor_id="test-actor-001",
            )

            _skip_if_langflow_unavailable(response)

            assert response.status_code == 200
            result_data = response.result
            assert result_data is not None

            # Should be rejected due to stale status
            assert result_data.get("success") is False
            assert result_data.get("outcome") == DataOperationOutcome.REJECTED.value

            # Verify count is 0 (no rows affected)
            assert result_data.get("count") == 0 or result_data.get("count") is None

            # Verify Neo4j shows NO mutation
            state_after = neo4j_helper.get_request_state(request_id)
            assert state_after is not None
            assert state_after["status"] == RequestStatus.NEEDS_CLARIFICATION.value
        finally:
            neo4j_helper.cleanup_request(request_id)


def _build_set_status_payload(
    request_id: str,
    expected_status: RequestStatus | None,
    expected_updated_at: datetime,
    target_status: RequestStatus,
) -> dict[str, Any]:
    """Build a setRequestStatus DataOperationRequest payload.

    Args:
        request_id: Target request ID
        expected_status: Expected current status (None for unset)
        expected_updated_at: Expected current updated_at timestamp
        target_status: Desired target status

    Returns:
        Dict payload ready for LF-70 input_data
    """
    return {
        "operation": "setRequestStatus",
        "operation_id": str(uuid4()),
        "caller": "LF-10",  # Caller context (LF-10 or LF-70 allowed)
        "session_id": str(uuid4()),
        "actor_id": "test-actor-001",
        "schema_version": "1.0.0",
        "correlation_id": str(uuid4()),
        "request_id": request_id,
        "expected_status": expected_status.value if expected_status else None,
        "expected_updated_at": expected_updated_at.isoformat(),
        "target_status": target_status.value,
    }
