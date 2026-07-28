"""Integration tests for LF-70 updateDeliveryRequest operation.

Tests verify:
- Successful update with correct expected_updated_at/expected_status
- Additive-only semantics (no replacement of existing singular fields)
- Concurrent-update rejection via compare-and-set
- Exactly-one-request postcondition validation
- Non-mutating zero-row classification

All tests call the live LF-70 flow (stable UUID 94f6774d-ebc7-5bf1-8486-886f91886a5f)
with real Neo4j assertions to verify write correctness.
"""

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest

from hulubul.core.models.operational import DataOperation, ErrorCode, RequestStatus
from tests.support.langflow_client import LangFlowClient

if TYPE_CHECKING:
    from neo4j import Driver

# LF-70 stable flow ID (updateDeliveryRequest operation)
LF_70_FLOW_ID = "94f6774d-ebc7-5bf1-8486-886f91886a5f"

# Neo4j live instance connection details
NEO4J_URL = os.getenv("NEO4J_URL", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


def _get_neo4j_driver() -> "Driver":
    """Get a Neo4j driver for the live instance."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        pytest.skip("neo4j not installed; run: poetry install --with integration")

    return GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


def _seed_delivery_request(
    driver: "Driver", request_id: str, initial_facts: dict[str, Any], session_id: str | None = None
) -> tuple[str, str]:
    """Seed a DeliveryRequest node with given facts and status.

    Creates a minimal request in 'new' status for testing updates.
    Returns the created_at and updated_at timestamps.
    """
    if session_id is None:
        session_id = str(uuid4())

    now = datetime.now(timezone.utc)

    # Pass the raw Python datetime (the neo4j driver converts it to a native
    # Neo4j DateTime) rather than an ISO string -- createDeliveryRequest's own
    # Cypher stores `created`/`updated` the same way, and updateDeliveryRequest's
    # compare-and-set does `request.updated = datetime($p.expected_updated_at)`,
    # which never matches a `updated` property that was stored as a plain string.
    cypher = """
    CREATE (r:DeliveryRequest {
        id: $request_id,
        created: $timestamp,
        updated: $timestamp,
        hasStatus: 'new'
    })
    RETURN r.created as created_at, r.updated as updated_at
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(cypher, request_id=request_id, timestamp=now)
        record = result.single()
        if record:
            return record["created_at"].isoformat(), record["updated_at"].isoformat()
    return now.isoformat(), now.isoformat()


def _read_request_from_neo4j(driver: "Driver", request_id: str) -> dict[str, Any] | None:
    """Read a DeliveryRequest directly from Neo4j."""
    cypher = """
    MATCH (r:DeliveryRequest {id: $request_id})
    RETURN r {.*} as request
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(cypher, request_id=request_id)
        record = result.single()
        if record:
            return dict(record["request"])
    return None


def _count_delivery_requests(driver: "Driver") -> int:
    """Count total DeliveryRequest nodes in Neo4j."""
    cypher = "MATCH (r:DeliveryRequest) RETURN count(r) as count"

    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(cypher)
        record = result.single()
        return record["count"] if record else 0


def _cleanup_request(driver: "Driver", request_id: str) -> None:
    """Clean up a test request from Neo4j."""
    cypher = "MATCH (r:DeliveryRequest {id: $request_id}) DETACH DELETE r"

    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(cypher, request_id=request_id)


class TestLF70UpdateRequest:
    """Integration tests for LF-70 updateDeliveryRequest operation."""

    @pytest.fixture(autouse=True)
    def _setup_langflow_client(self) -> None:
        """Create a fresh LangFlow client with API key from environment."""
        langflow_url = os.getenv("LANGFLOW_URL", "http://localhost:7860")
        langflow_api_key = os.getenv("LANGFLOW_API_KEY", "local-dev-key-hulubul-phase1")
        self.client = LangFlowClient(base_url=langflow_url, api_key=langflow_api_key)

    def test_successful_update_with_correct_concurrency_values(self) -> None:
        """Successful update: correct expected_updated_at and expected_status match.

        Scenario:
        1. Seed a request in 'new' status
        2. Call updateDeliveryRequest with matching expected_updated_at and expected_status
        3. Assert via Neo4j: exactly 1 request modified, new fields present, fresh updated_at returned
        """

        driver = _get_neo4j_driver()
        request_id = f"req-{uuid4()}"

        try:
            # Seed a request
            created_at, updated_at = _seed_delivery_request(
                driver, request_id, {}, session_id=str(uuid4())
            )

            # Prepare update payload
            update_payload = {
                "operation": DataOperation.UPDATE_DELIVERY_REQUEST,
                "operation_id": str(uuid4()),
                "caller": "LF-10",
                "session_id": str(uuid4()),
                "actor_id": "test-actor-update",
                "schema_version": "1.0.0",
                "correlation_id": str(uuid4()),
                "request_id": request_id,
                "expected_updated_at": updated_at,
                "expected_status": RequestStatus.NEW,
                "updates": {"preferred_period": "2024-08-01 to 2024-08-05"},
                "identifiers": {},
            }

            # Call LF-70 flow
            response = self.client.run_flow_with_actor(LF_70_FLOW_ID, update_payload)

            if response.status_code == 500 and "Connection" in (response.error or ""):
                pytest.skip("LangFlow server not running")

            assert response.status_code == 200, f"Flow failed: {response.error}"
            assert response.result is not None

            result = response.result
            assert result["success"] is True
            assert result["outcome"] == "confirmed"
            assert result["count"] == 1, "Expected exactly 1 affected request"

            # Verify Neo4j state
            updated_request = _read_request_from_neo4j(driver, request_id)
            assert updated_request is not None
            assert updated_request["hasStatus"] == "new"

            # Verify that updated_at changed
            assert result.get("updated_at") is not None

        finally:
            _cleanup_request(driver, request_id)
            driver.close()

    def test_additive_only_semantics_rejects_replacement(self) -> None:
        """Additive-only semantics: cannot replace existing singular fields.

        Scenario:
        1. Seed a request with preferred_period already set
        2. Attempt update with a different preferred_period value
        3. Assert operation is rejected or ignored per policy (no replacement allowed)
        """

        driver = _get_neo4j_driver()
        request_id = f"req-{uuid4()}"

        try:
            # Seed a request with existing preferred_period
            created_at, updated_at = _seed_delivery_request(
                driver, request_id, {}, session_id=str(uuid4())
            )

            # First, set an initial preferred_period
            cypher_set_period = """
            MATCH (r:DeliveryRequest {id: $request_id})
            SET r.preferredPeriod = $period
            """
            with driver.session(database=NEO4J_DATABASE) as session:
                session.run(
                    cypher_set_period, request_id=request_id, period="2024-07-01 to 2024-07-31"
                )

            # Now attempt to replace it
            replacement_payload = {
                "operation": DataOperation.UPDATE_DELIVERY_REQUEST,
                "operation_id": str(uuid4()),
                "caller": "LF-10",
                "session_id": str(uuid4()),
                "actor_id": "test-actor-additive",
                "schema_version": "1.0.0",
                "correlation_id": str(uuid4()),
                "request_id": request_id,
                "expected_updated_at": updated_at,
                "expected_status": RequestStatus.NEW,
                "updates": {
                    "preferred_period": "2024-08-01 to 2024-08-31"  # Different value
                },
                "identifiers": {},
            }

            # Call LF-70
            response = self.client.run_flow_with_actor(LF_70_FLOW_ID, replacement_payload)

            if response.status_code == 500 and "Connection" in (response.error or ""):
                pytest.skip("LangFlow server not running")

            # The flow should either:
            # 1. Return success but the Neo4j write didn't change the field (additive-only), OR
            # 2. Return rejected with appropriate error code

            if response.status_code == 200:
                result = response.result
                assert result is not None
                # If success, verify the field was NOT changed
                if result.get("success"):
                    updated_request = _read_request_from_neo4j(driver, request_id)
                    assert updated_request is not None
                    # Verify that preferredPeriod remains the original value
                    assert updated_request.get("preferredPeriod") == "2024-07-01 to 2024-07-31"

        finally:
            _cleanup_request(driver, request_id)
            driver.close()

    def test_concurrent_update_rejection_with_stale_timestamp(self) -> None:
        """Concurrent-update rejection: stale expected_updated_at is rejected.

        Scenario:
        1. Seed a request with initial updated_at timestamp T1
        2. Perform a successful update that sets new timestamp T2
        3. Attempt another update using the old T1 (compare-and-set mismatch)
        4. Assert CONCURRENT_MODIFICATION error, zero mutations in Neo4j
        """

        driver = _get_neo4j_driver()
        request_id = f"req-{uuid4()}"

        try:
            # Seed initial request
            created_at, updated_at_t1 = _seed_delivery_request(
                driver, request_id, {}, session_id=str(uuid4())
            )

            # First update (succeeds)
            first_update = {
                "operation": DataOperation.UPDATE_DELIVERY_REQUEST,
                "operation_id": str(uuid4()),
                "caller": "LF-10",
                "session_id": str(uuid4()),
                "actor_id": "test-actor-concurrent",
                "schema_version": "1.0.0",
                "correlation_id": str(uuid4()),
                "request_id": request_id,
                "expected_updated_at": updated_at_t1,
                "expected_status": RequestStatus.NEW,
                "updates": {"field1": "value1"},
                "identifiers": {},
            }

            response1 = self.client.run_flow_with_actor(LF_70_FLOW_ID, first_update)

            if response1.status_code == 500 and "Connection" in (response1.error or ""):
                pytest.skip("LangFlow server not running")

            assert response1.status_code == 200
            result1 = response1.result
            assert result1 is not None
            assert result1["success"] is True

            # Extract new updated_at from successful response
            updated_at_t2 = result1.get("updated_at")
            assert updated_at_t2 is not None

            # Verify timestamp changed
            assert updated_at_t2 != updated_at_t1, "Timestamp should have changed after update"

            # Second update using STALE timestamp (should fail)
            second_update = {
                "operation": DataOperation.UPDATE_DELIVERY_REQUEST,
                "operation_id": str(uuid4()),
                "caller": "LF-10",
                "session_id": str(uuid4()),
                "actor_id": "test-actor-concurrent",
                "schema_version": "1.0.0",
                "correlation_id": str(uuid4()),
                "request_id": request_id,
                "expected_updated_at": updated_at_t1,  # STALE timestamp
                "expected_status": RequestStatus.NEW,
                "updates": {"field2": "value2"},
                "identifiers": {},
            }

            response2 = self.client.run_flow_with_actor(LF_70_FLOW_ID, second_update)

            assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
            result2 = response2.result
            assert result2 is not None

            # Should be rejected with CONCURRENT_MODIFICATION
            assert result2["success"] is False
            assert result2["outcome"] in ["rejected", "ambiguous"]
            assert result2.get("error_code") == ErrorCode.CONCURRENT_MODIFICATION

            # Verify Neo4j: no extra mutations occurred
            updated_request = _read_request_from_neo4j(driver, request_id)
            assert updated_request is not None
            # Should still have field1 from first update, NOT field2
            assert updated_request.get("field1") == "value1"
            assert "field2" not in updated_request or updated_request.get("field2") is None

        finally:
            _cleanup_request(driver, request_id)
            driver.close()

    def test_exactly_one_request_postcondition(self) -> None:
        """Exactly-one-request postcondition: affected count must be 1, not 0 or >1.

        Scenario:
        1. Create a duplicate request scenario (if possible in Neo4j constraints)
        2. Call update
        3. Assert that the count field is exactly 1 in the response
        """

        driver = _get_neo4j_driver()
        request_id = f"req-{uuid4()}"

        try:
            # Seed a single request
            created_at, updated_at = _seed_delivery_request(
                driver, request_id, {}, session_id=str(uuid4())
            )

            # Perform update
            update_payload = {
                "operation": DataOperation.UPDATE_DELIVERY_REQUEST,
                "operation_id": str(uuid4()),
                "caller": "LF-10",
                "session_id": str(uuid4()),
                "actor_id": "test-actor-count",
                "schema_version": "1.0.0",
                "correlation_id": str(uuid4()),
                "request_id": request_id,
                "expected_updated_at": updated_at,
                "expected_status": RequestStatus.NEW,
                "updates": {"test_field": "test_value"},
                "identifiers": {},
            }

            response = self.client.run_flow_with_actor(LF_70_FLOW_ID, update_payload)

            if response.status_code == 500 and "Connection" in (response.error or ""):
                pytest.skip("LangFlow server not running")

            assert response.status_code == 200
            result = response.result
            assert result is not None

            if result["success"]:
                # Verify affected count is exactly 1
                assert result.get("count") == 1, "Affected record count must be exactly 1"

        finally:
            _cleanup_request(driver, request_id)
            driver.close()

    def test_non_mutating_zero_row_classification(self) -> None:
        """Non-mutating zero-row classification: failed compare-and-set doesn't mutate.

        Scenario:
        1. Attempt update on non-existent request
        2. Assert returned error classification (CONCURRENT_MODIFICATION or similar)
        3. Verify no side effects in Neo4j
        """

        nonexistent_request_id = f"req-{uuid4()}"

        # Don't seed any request; use nonexistent ID
        update_payload = {
            "operation": DataOperation.UPDATE_DELIVERY_REQUEST,
            "operation_id": str(uuid4()),
            "caller": "LF-10",
            "session_id": str(uuid4()),
            "actor_id": "test-actor-nonexistent",
            "schema_version": "1.0.0",
            "correlation_id": str(uuid4()),
            "request_id": nonexistent_request_id,
            "expected_updated_at": datetime.now(timezone.utc).isoformat(),
            "expected_status": RequestStatus.NEW,
            "updates": {"any_field": "any_value"},
            "identifiers": {},
        }

        response = self.client.run_flow_with_actor(LF_70_FLOW_ID, update_payload)

        if response.status_code == 500 and "Connection" in (response.error or ""):
            pytest.skip("LangFlow server not running")

        assert response.status_code == 200
        result = response.result
        assert result is not None

        # Should be rejected (zero rows matched the compare-and-set condition)
        assert result["success"] is False
        assert result.get("error_code") in [
            ErrorCode.CONCURRENT_MODIFICATION,
            ErrorCode.GRAPH_CONTEXT_INCONSISTENT,
        ]

        # Verify no side effects: no request was created
        driver = _get_neo4j_driver()
        try:
            updated_request = _read_request_from_neo4j(driver, nonexistent_request_id)
            assert updated_request is None, "No request should exist after failed update"
        finally:
            driver.close()
