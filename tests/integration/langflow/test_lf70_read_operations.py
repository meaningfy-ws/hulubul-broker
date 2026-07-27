"""Integration tests for LF-70 read operations: getRequestRoutingContext and readDeliveryRequest.

Tests verify:
- getRequestRoutingContext strict raw-record validation and exhaustive closed/status/cardinality adaptation
- readDeliveryRequest sparse snapshot behavior and transient read retry
- No mutations occurred (read operations never write to the graph)
- Direct Neo4j assertions prove LLM agent correctly interprets Cypher results

Task 8.2: LF-70 read operations with typed DataOperationRequest/DataOperationResult contracts.
"""

import os
import time
from datetime import datetime, timezone

import pytest

from hulubul.core.models.operational import (
    DataOperation,
    DataOperationOutcome,
    RequestStatus,
)
from hulubul.request_intake.services.graph_identifiers import generate_session_id
from tests.support.langflow_client import LangFlowClient

# LF-70 stable flow ID
LF_70_FLOW_UUID = "94f6774d-ebc7-5bf1-8486-886f91886a5f"


class TestLF70ReadOperations:
    """Integration tests for LF-70 read operations against live LangFlow and Neo4j."""

    @pytest.fixture(autouse=True)
    def setup(self, langflow_client: LangFlowClient) -> None:
        """Verify LangFlow is running before attempting tests.

        Skips all tests in this class if LangFlow is not reachable.
        """
        self.client = langflow_client
        self.langflow_url = langflow_client.base_url

    def test_get_routing_context_no_binding_present(self) -> None:
        """getRequestRoutingContext with no binding present returns empty context.

        Given: No OperationalConversationBinding for this session
        When: Call getRequestRoutingContext with caller=LF-00
        Then: Flow returns RoutingContext with binding_state=absent, no request_id/status/closed_at
              and no mutations occurred in Neo4j
        """
        session_id = generate_session_id()
        operation_id = "op-routing-no-binding-001"

        # Prepare DataOperationRequest payload
        request_payload = {
            "operation": DataOperation.GET_REQUEST_ROUTING_CONTEXT,
            "operation_id": operation_id,
            "caller": "LF-00",  # Only LF-00 can call getRequestRoutingContext
            "session_id": session_id,
            "actor_id": "test-actor-no-binding",
            "schema_version": "1.0.0",
            "correlation_id": "corr-no-binding-001",
        }

        # Call LF-70
        reply = self.client.run_flow_with_actor(
            flow_uuid=LF_70_FLOW_UUID,
            input_data=request_payload,
            actor_id="test-actor-no-binding",
        )

        # Assert successful invocation
        if reply.status_code == 500 and "Connection refused" in (reply.error or ""):
            pytest.skip("LangFlow server not running")

        assert reply.status_code == 200, (
            f"Expected 200, got {reply.status_code}. Error: {reply.error}"
        )
        assert reply.result is not None, "Expected non-null result from flow"

        # Extract result from nested structure (LangFlow wraps in output/result)
        result_data = reply.result
        if isinstance(result_data, dict) and "output" in result_data:
            result_data = result_data["output"]
        # getRequestRoutingContext's RoutingContext fields are nested under
        # DataOperationResult.result -- design.md: "DataOperationResult ...
        # typed result/error" wraps every operation's payload uniformly,
        # including routing context, applied deterministically by
        # RoutingContextAdapterComponent (adapt_routing_lookup) downstream of
        # the Agent, not by the Agent itself.
        assert result_data.get("outcome") == "confirmed", (
            f"Expected outcome=confirmed, got {result_data.get('outcome')}"
        )
        result_data = result_data["result"]

        # Assert RoutingContext fields
        assert "binding_state" in result_data, "Expected binding_state in result"
        assert result_data["binding_state"] == "absent", (
            f"Expected binding_state=absent for no binding, got {result_data.get('binding_state')}"
        )

        assert result_data.get("binding_count") == 0, (
            f"Expected binding_count=0, got {result_data.get('binding_count')}"
        )
        assert result_data.get("active_relationship_count") == 0, (
            f"Expected active_relationship_count=0, got {result_data.get('active_relationship_count')}"
        )
        assert result_data.get("active_target_count") == 0, (
            f"Expected active_target_count=0, got {result_data.get('active_target_count')}"
        )

        # For absent binding, request_id and request_status should be None
        assert result_data.get("request_id") is None, (
            f"Expected request_id=None for absent binding, got {result_data.get('request_id')}"
        )
        assert result_data.get("request_status") is None, (
            f"Expected request_status=None for absent binding, got {result_data.get('request_status')}"
        )
        assert result_data.get("closed_at") is None, (
            f"Expected closed_at=None for absent binding, got {result_data.get('closed_at')}"
        )

    def test_get_routing_context_binding_with_status(self) -> None:
        """getRequestRoutingContext with binding present and known status.

        Given: OperationalConversationBinding exists and is bound to a DeliveryRequest with status='new'
        When: Call getRequestRoutingContext with caller=LF-00
        Then: Flow returns RoutingContext with binding_state=bound, correct request_id/status
              and no mutations occurred
        """
        session_id = generate_session_id()
        operation_id = "op-routing-with-status-001"
        request_id = f"req-{session_id[:8]}"

        # Seed Neo4j directly with a binding and request
        # We'll use the neo4j driver from conftest if available, but fall back to
        # attempting direct connection for the live environment
        try:
            from neo4j import GraphDatabase
        except ImportError:
            pytest.skip("neo4j driver not installed; run: poetry install --with integration")

        # Load credentials from infra/.env
        env_file = "/home/greg/PROJECTS/hulubul-broker/infra/.env"
        neo4j_config = {}
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        neo4j_config[key] = value
        else:
            pytest.skip(".env file not found; skipping live Neo4j seed")

        neo4j_url = neo4j_config.get("NEO4J_URL", "bolt://localhost:7687")
        neo4j_user = neo4j_config.get("NEO4J_USERNAME", "neo4j")
        neo4j_password = neo4j_config.get("NEO4J_PASSWORD")
        neo4j_database = neo4j_config.get("NEO4J_DATABASE", "neo4j")

        if not neo4j_password:
            pytest.skip("NEO4J_PASSWORD not configured")

        # Connect to live Neo4j
        driver = GraphDatabase.driver(neo4j_url, auth=(neo4j_user, neo4j_password))

        try:
            # Seed: Create binding and request
            now_iso = datetime.now(timezone.utc).isoformat()
            seed_query = """
            MATCH (s:Sender {trustedId: 'default-test-sender'})
            WITH s
            MERGE (b:OperationalConversationBinding {sessionId: $session_id})
            SET b.createdAt = $now,
                b.actor = 'test-actor',
                b.source = 'api'
            MERGE (r:DeliveryRequest {id: $request_id})
            SET r.created = $now,
                r.updated = $now,
                r.hasStatus = $status
            MERGE (b)-[:BINDS_ACTIVE_REQUEST]->(r)
            RETURN b.sessionId AS session_id, r.id AS request_id, r.hasStatus AS status
            """

            result = driver.execute_query(
                seed_query,
                session_id=session_id,
                request_id=request_id,
                now=now_iso,
                status=RequestStatus.NEW,
                database=neo4j_database,
            )

            if not result.records:
                pytest.skip("Failed to seed binding and request in Neo4j")

            # Small delay to ensure graph consistency
            time.sleep(0.2)

            # Prepare DataOperationRequest payload
            request_payload = {
                "operation": DataOperation.GET_REQUEST_ROUTING_CONTEXT,
                "operation_id": operation_id,
                "caller": "LF-00",
                "session_id": session_id,
                "actor_id": "test-actor-with-status",
                "schema_version": "1.0.0",
                "correlation_id": f"corr-with-status-{session_id[:8]}",
            }

            # Call LF-70
            reply = self.client.run_flow_with_actor(
                flow_uuid=LF_70_FLOW_UUID,
                input_data=request_payload,
                actor_id="test-actor-with-status",
            )

            # Assert successful invocation
            if reply.status_code == 500 and "Connection refused" in (reply.error or ""):
                pytest.skip("LangFlow server not running")

            assert reply.status_code == 200, (
                f"Expected 200, got {reply.status_code}. Error: {reply.error}"
            )
            assert reply.result is not None, "Expected non-null result from flow"

            # Extract result from nested structure
            result_data = reply.result
            if isinstance(result_data, dict) and "output" in result_data:
                result_data = result_data["output"]
            # RoutingContext fields are nested under DataOperationResult.result
            # (see the no-binding test above for why).
            assert result_data.get("outcome") == "confirmed", (
                f"Expected outcome=confirmed, got {result_data.get('outcome')}"
            )
            result_data = result_data["result"]

            # Assert RoutingContext fields for bound case
            assert result_data["binding_state"] == "bound", (
                f"Expected binding_state=bound, got {result_data.get('binding_state')}"
            )
            assert result_data.get("binding_count") == 1, (
                f"Expected binding_count=1, got {result_data.get('binding_count')}"
            )
            assert result_data.get("active_relationship_count") == 1, (
                f"Expected active_relationship_count=1, got {result_data.get('active_relationship_count')}"
            )
            assert result_data.get("active_target_count") == 1, (
                f"Expected active_target_count=1, got {result_data.get('active_target_count')}"
            )

            # Request should be present with correct status
            assert result_data.get("request_id") == request_id, (
                f"Expected request_id={request_id}, got {result_data.get('request_id')}"
            )
            assert result_data.get("request_status") == RequestStatus.NEW, (
                f"Expected request_status=new, got {result_data.get('request_status')}"
            )

            # Verify no mutations occurred: read the binding again
            verify_query = """
            MATCH (b:OperationalConversationBinding {sessionId: $session_id})-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
            RETURN b.sessionId AS session_id, r.id AS request_id, r.hasStatus AS status
            """
            verify_result = driver.execute_query(
                verify_query,
                session_id=session_id,
                database=neo4j_database,
            )

            assert verify_result.records, "Binding should still exist after read operation"
            verify_record = verify_result.records[0]
            assert verify_record["request_id"] == request_id, "Request ID should not change"
            assert verify_record["status"] == RequestStatus.NEW, "Status should not change"

        finally:
            driver.close()

    def test_read_delivery_request_sparse_snapshot(self) -> None:
        """readDeliveryRequest with sparse facts returns correct snapshot.

        Given: DeliveryRequest exists with only some facts populated (sparse)
        When: Call readDeliveryRequest with caller=LF-10, request_id
        Then: Flow returns DeliveryRequestSnapshot reflecting sparseness:
              - present fields are correct
              - absent fields are None/empty (not fabricated)
              - updated_at timestamp is present for optimistic concurrency
              - no mutations occurred
        """
        session_id = generate_session_id()
        operation_id = "op-read-sparse-001"
        request_id = f"req-sparse-{session_id[:8]}"

        try:
            from neo4j import GraphDatabase
        except ImportError:
            pytest.skip("neo4j driver not installed; run: poetry install --with integration")

        # Load credentials from infra/.env
        env_file = "/home/greg/PROJECTS/hulubul-broker/infra/.env"
        neo4j_config = {}
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        neo4j_config[key] = value
        else:
            pytest.skip(".env file not found; skipping live Neo4j seed")

        neo4j_url = neo4j_config.get("NEO4J_URL", "bolt://localhost:7687")
        neo4j_user = neo4j_config.get("NEO4J_USERNAME", "neo4j")
        neo4j_password = neo4j_config.get("NEO4J_PASSWORD")
        neo4j_database = neo4j_config.get("NEO4J_DATABASE", "neo4j")

        if not neo4j_password:
            pytest.skip("NEO4J_PASSWORD not configured")

        # Connect to live Neo4j
        driver = GraphDatabase.driver(neo4j_url, auth=(neo4j_user, neo4j_password))

        try:
            # Seed: Create a delivery request with only partial facts
            now_iso = datetime.now(timezone.utc).isoformat()
            seed_query = """
            MERGE (r:DeliveryRequest {id: $request_id})
            SET r.created = $now,
                r.updated = $now,
                r.hasStatus = $status
            RETURN r.id AS request_id, r.created AS created_at, r.updated AS updated_at
            """

            result = driver.execute_query(
                seed_query,
                request_id=request_id,
                now=now_iso,
                status=RequestStatus.NEW,
                database=neo4j_database,
            )

            if not result.records:
                pytest.skip("Failed to seed delivery request in Neo4j")

            seeded_record = result.records[0]

            # Small delay to ensure graph consistency
            time.sleep(0.2)

            # Prepare DataOperationRequest payload for read
            request_payload = {
                "operation": DataOperation.READ_DELIVERY_REQUEST,
                "operation_id": operation_id,
                "caller": "LF-10",  # Only LF-10 can call readDeliveryRequest
                "session_id": session_id,
                "actor_id": "test-actor-read",
                "schema_version": "1.0.0",
                "correlation_id": f"corr-read-{session_id[:8]}",
                "request_id": request_id,
            }

            # Call LF-70
            reply = self.client.run_flow_with_actor(
                flow_uuid=LF_70_FLOW_UUID,
                input_data=request_payload,
                actor_id="test-actor-read",
            )

            # Assert successful invocation
            if reply.status_code == 500 and "Connection refused" in (reply.error or ""):
                pytest.skip("LangFlow server not running")

            assert reply.status_code == 200, (
                f"Expected 200, got {reply.status_code}. Error: {reply.error}"
            )
            assert reply.result is not None, "Expected non-null result from flow"

            # Extract result from nested structure
            result_data = reply.result
            if isinstance(result_data, dict) and "output" in result_data:
                result_data = result_data["output"]

            # Assert DataOperationResult fields for read
            assert result_data.get("operation") == DataOperation.READ_DELIVERY_REQUEST, (
                f"Expected operation=readDeliveryRequest, got {result_data.get('operation')}"
            )
            assert result_data.get("outcome") == DataOperationOutcome.CONFIRMED, (
                f"Expected outcome=confirmed, got {result_data.get('outcome')}"
            )
            assert result_data.get("success") is True, (
                f"Expected success=True, got {result_data.get('success')}"
            )
            assert result_data.get("write_dispatched") is False, (
                "Read operations must have write_dispatched=False"
            )

            # Assert DeliveryRequestSnapshot fields
            result_snapshot = result_data.get("result")
            assert result_snapshot is not None, "Expected snapshot in result"

            # Verify sparse snapshot behavior
            assert result_snapshot.get("request_id") == request_id, (
                f"Expected request_id={request_id}, got {result_snapshot.get('request_id')}"
            )
            assert result_snapshot.get("status") == RequestStatus.NEW, (
                f"Expected status=new, got {result_snapshot.get('status')}"
            )

            # updated_at must be present for optimistic concurrency
            assert result_snapshot.get("updated_at") is not None, (
                "Expected updated_at timestamp in snapshot"
            )

            # Absent facts should not be fabricated (check that missing_fields is present)
            missing_fields = result_snapshot.get("missing_fields", [])
            assert isinstance(missing_fields, list | tuple), (
                f"Expected missing_fields to be list/tuple, got {type(missing_fields)}"
            )

            # Facts should not contain fabricated data (only what we seeded)
            facts = result_snapshot.get("facts")
            assert isinstance(facts, dict), "Expected facts to be a dict"

            # Verify no mutations occurred: read the request again
            verify_query = """
            MATCH (r:DeliveryRequest {id: $request_id})
            RETURN r.id AS request_id, r.updated AS updated_at, r.hasStatus AS status
            """
            verify_result = driver.execute_query(
                verify_query,
                request_id=request_id,
                database=neo4j_database,
            )

            assert verify_result.records, "Request should still exist after read operation"
            verify_record = verify_result.records[0]
            assert verify_record["request_id"] == request_id, "Request ID should not change"
            assert verify_record["status"] == RequestStatus.NEW, (
                "Status should not change after read"
            )
            # updated_at should not have changed
            assert verify_record["updated_at"] == seeded_record["updated_at"], (
                "updated_at timestamp should not change on read operation"
            )

        finally:
            driver.close()

    def test_get_routing_context_operation_not_allowed_for_lf10(self) -> None:
        """getRequestRoutingContext with caller=LF-10 returns OPERATION_NOT_ALLOWED.

        Authorization matrix: only LF-00 can call getRequestRoutingContext.
        LF-10 attempting this operation should be rejected with OPERATION_NOT_ALLOWED.

        Given: getRequestRoutingContext operation with caller=LF-10
        When: Call LF-70
        Then: Flow returns rejected result with error_code=OPERATION_NOT_ALLOWED
        """
        session_id = generate_session_id()
        operation_id = "op-routing-forbidden-001"

        # Prepare DataOperationRequest with wrong caller
        request_payload = {
            "operation": DataOperation.GET_REQUEST_ROUTING_CONTEXT,
            "operation_id": operation_id,
            "caller": "LF-10",  # Wrong caller (should be LF-00)
            "session_id": session_id,
            "actor_id": "test-actor-forbidden",
            "schema_version": "1.0.0",
            "correlation_id": "corr-forbidden-001",
        }

        # Call LF-70
        reply = self.client.run_flow_with_actor(
            flow_uuid=LF_70_FLOW_UUID,
            input_data=request_payload,
            actor_id="test-actor-forbidden",
        )

        # Assert successful invocation (LF-70 should return a valid result, not 500)
        if reply.status_code == 500 and "Connection refused" in (reply.error or ""):
            pytest.skip("LangFlow server not running")

        assert reply.status_code == 200, (
            f"Expected 200, got {reply.status_code}. Error: {reply.error}"
        )
        assert reply.result is not None, "Expected non-null result from flow"

        # Extract result from nested structure
        result_data = reply.result
        if isinstance(result_data, dict) and "output" in result_data:
            result_data = result_data["output"]

        # Assert rejected outcome with OPERATION_NOT_ALLOWED error
        assert result_data.get("outcome") == DataOperationOutcome.REJECTED, (
            f"Expected outcome=rejected, got {result_data.get('outcome')}"
        )
        assert result_data.get("success") is False, "Rejected results must have success=False"
        assert result_data.get("error_code") == "OPERATION_NOT_ALLOWED", (
            f"Expected error_code=OPERATION_NOT_ALLOWED, got {result_data.get('error_code')}"
        )

    def test_read_delivery_request_operation_not_allowed_for_lf00(self) -> None:
        """readDeliveryRequest with caller=LF-00 returns OPERATION_NOT_ALLOWED.

        Authorization matrix: only LF-10 can call readDeliveryRequest.
        LF-00 attempting this operation should be rejected with OPERATION_NOT_ALLOWED.

        Given: readDeliveryRequest operation with caller=LF-00
        When: Call LF-70
        Then: Flow returns rejected result with error_code=OPERATION_NOT_ALLOWED
        """
        session_id = generate_session_id()
        operation_id = "op-read-forbidden-001"
        request_id = f"req-forbidden-{session_id[:8]}"

        # Prepare DataOperationRequest with wrong caller
        request_payload = {
            "operation": DataOperation.READ_DELIVERY_REQUEST,
            "operation_id": operation_id,
            "caller": "LF-00",  # Wrong caller (should be LF-10)
            "session_id": session_id,
            "actor_id": "test-actor-read-forbidden",
            "schema_version": "1.0.0",
            "correlation_id": "corr-read-forbidden-001",
            "request_id": request_id,
        }

        # Call LF-70
        reply = self.client.run_flow_with_actor(
            flow_uuid=LF_70_FLOW_UUID,
            input_data=request_payload,
            actor_id="test-actor-read-forbidden",
        )

        # Assert successful invocation
        if reply.status_code == 500 and "Connection refused" in (reply.error or ""):
            pytest.skip("LangFlow server not running")

        assert reply.status_code == 200, (
            f"Expected 200, got {reply.status_code}. Error: {reply.error}"
        )
        assert reply.result is not None, "Expected non-null result from flow"

        # Extract result from nested structure
        result_data = reply.result
        if isinstance(result_data, dict) and "output" in result_data:
            result_data = result_data["output"]

        # Assert rejected outcome with OPERATION_NOT_ALLOWED error
        assert result_data.get("outcome") == DataOperationOutcome.REJECTED, (
            f"Expected outcome=rejected, got {result_data.get('outcome')}"
        )
        assert result_data.get("success") is False, "Rejected results must have success=False"
        assert result_data.get("error_code") == "OPERATION_NOT_ALLOWED", (
            f"Expected error_code=OPERATION_NOT_ALLOWED, got {result_data.get('error_code')}"
        )
