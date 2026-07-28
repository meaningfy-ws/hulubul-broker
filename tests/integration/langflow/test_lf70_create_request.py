"""Integration tests for LF-70 createDeliveryRequest operation.

Tests verify:
- Successful atomic creation with fresh identifiers (request + binding in one transaction)
- created_at == updated_at from Neo4j transaction time (one authoritative timestamp)
- No caller-supplied timestamp accepted (model rejects extra fields)
- Atomicity: rollback on binding uniqueness conflict (no orphan request node)
- Truthful available subgraphs (no fabricated fields in result)

The flow is live at http://localhost:7860 (stable ID: 94f6774d-ebc7-5bf1-8486-886f91886a5f)
connected to a real Neo4j instance at localhost:7687.

LF-70 calls are restricted to caller="LF-70" (enforced by data_operation_policy.py).
Direct Neo4j assertions prove the MCP operations' side effects independently of flow output.
"""

import contextlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from hulubul.core.models.operational.data_operations import validate_data_operation_request
from hulubul.core.models.operational.enums import (
    CallerFlow,
    DataOperation,
    DataOperationOutcome,
)
from hulubul.request_intake.services.graph_identifiers import new_graph_identifiers
from tests.support.langflow_client import LangFlowClient

# LF-70 stable flow UUID (from phase1-pr-checkpoints.md task 32)
LF_70_FLOW_UUID = "94f6774d-ebc7-5bf1-8486-886f91886a5f"

# LangFlow connection
LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://localhost:7860")
LANGFLOW_API_KEY = os.getenv("LANGFLOW_API_KEY", "local-dev-key-hulubul-phase1")

# Neo4j dev instance connection (live, shared, not isolated testcontainer)
NEO4J_BOLT_URL = os.getenv("NEO4J_BOLT_URL", "bolt://localhost:7687")
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


def _read_neo4j_credentials_from_env_file() -> tuple[str, str, str]:
    """Read Neo4j credentials from infra/.env if environment vars are not set.

    Falls back to defaults if .env does not exist or values are missing.
    """
    env_file = Path(__file__).resolve().parents[3] / "infra" / ".env"
    if not env_file.exists():
        return NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

    config = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

    return (
        config.get("NEO4J_USERNAME", NEO4J_USERNAME),
        config.get("NEO4J_PASSWORD", NEO4J_PASSWORD),
        config.get("NEO4J_DATABASE", NEO4J_DATABASE),
    )


@pytest.fixture
def neo4j_driver() -> Any:
    """Create a Neo4j driver for the live dev instance.

    Connects to bolt://localhost:7687 using credentials from infra/.env.
    This is the shared Neo4j instance used by parallel agents; use unique
    synthetic identifiers in tests to avoid collisions.

    Yields the driver; caller should not assume a clean graph.
    """
    try:
        from neo4j import GraphDatabase
    except ImportError:
        pytest.skip("neo4j not installed; run: poetry install --with integration")

    username, password, database = _read_neo4j_credentials_from_env_file()

    try:
        driver = GraphDatabase.driver(
            NEO4J_BOLT_URL,
            auth=(username, password),
        )
        # Verify connection
        with driver.session(database=database) as session:
            session.run("RETURN 1")
    except Exception as e:
        pytest.skip(f"Neo4j connection failed: {e}")

    yield driver

    with contextlib.suppress(Exception):
        driver.close()


class TestLF70CreateDeliveryRequest:
    """Tests for the LF-70 createDeliveryRequest data operation."""

    def test_successful_create_with_fresh_identifiers(
        self,
        neo4j_driver: Any,
    ) -> None:
        """Test: successful atomic create with fresh synthetic identifiers.

        Verifies:
        - Request is created with expected identifiers
        - Binding is created in the same transaction
        - Request node exists in Neo4j with correct properties
        - Binding relationship exists and points to the request
        """
        # Create client with explicit API key
        langflow_client = LangFlowClient(base_url=LANGFLOW_URL, api_key=LANGFLOW_API_KEY)

        # Generate fresh identifiers (unique per test run)
        graph_ids = new_graph_identifiers(
            actor_id="test-actor-" + str(id(self))[-8:],
            receiver_stable_id=None,
            include_receiver=True,
            include_parcel=True,
            include_pickup=True,
            include_drop_off=True,
        )

        # Build the operation request with valid payload
        create_request = {
            "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
            "operation_id": f"op-{id(self)}",
            "caller": CallerFlow.LF_70.value,
            "session_id": graph_ids.request_id,  # Reuse request ID for session binding
            "actor_id": "test-actor-" + str(id(self))[-8:],
            "schema_version": "v1",
            "correlation_id": f"corr-{id(self)}",
            "identifiers": {
                "request_id": graph_ids.request_id,
                "sender_id": graph_ids.sender_id,
                "sender_agent_id": graph_ids.sender_agent_id,
                "receiver_id": graph_ids.receiver_id,
                "receiver_agent_id": graph_ids.receiver_agent_id,
                "parcel_id": graph_ids.parcel_id,
                "pickup_place_id": graph_ids.pickup_place_id,
                "drop_off_place_id": graph_ids.drop_off_place_id,
            },
            "facts": {
                "receiver_identity": "Test Receiver",
                "pickup_location": "123 Main St",
                "drop_off_location": "456 Oak Ave",
                "parcel_declared_content": "Test Parcel",
            },
        }

        # Validate the request model
        validated = validate_data_operation_request(create_request)
        assert validated.operation == DataOperation.CREATE_DELIVERY_REQUEST
        assert validated.caller == CallerFlow.LF_70.value

        # Call the flow
        response = langflow_client.run_flow_with_actor(
            flow_uuid=LF_70_FLOW_UUID,
            input_data=create_request,
            actor_id="test-actor-" + str(id(self))[-8:],
        )

        # Handle LangFlow unavailability gracefully
        if response.status_code == 500 and "Connection refused" in (response.error or ""):
            pytest.skip("LangFlow server not running")

        assert response.status_code == 200, f"Flow failed: {response.error}"
        assert response.result is not None

        result = response.result
        assert result["success"] is True
        assert result["outcome"] == DataOperationOutcome.CONFIRMED.value
        assert result["write_dispatched"] is True
        assert result["request_id"] == graph_ids.request_id
        assert result["status"] == "new"

        # CRITICAL: created_at and updated_at must be equal (same Neo4j transaction time)
        # datetime.fromisoformat() only accepts a trailing "Z" UTC designator on
        # Python 3.11+; this project targets 3.10, so normalize it to "+00:00"
        # first -- confirmed live: the Agent's real (valid RFC3339) timestamp
        # "...112000Z" raised ValueError under 3.10's stricter parser.
        created_at = datetime.fromisoformat(result["created_at"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(result["updated_at"].replace("Z", "+00:00"))
        assert created_at == updated_at, (
            f"created_at ({created_at}) must equal updated_at ({updated_at}); "
            "design requires one Neo4j transaction time for both"
        )

        # Verify Neo4j state directly

        database = _read_neo4j_credentials_from_env_file()[2]
        with neo4j_driver.session(database=database) as session:
            # Check request node exists with correct properties
            request_result = session.run(
                """
                MATCH (r:DeliveryRequest {id: $request_id})
                RETURN r.id as id, r.hasStatus as status, r.created as created_at, r.updated as updated_at
                """,
                {"request_id": graph_ids.request_id},
            )
            request_row = request_result.single()

            assert request_row is not None, f"Request node not found: {graph_ids.request_id}"
            assert request_row["status"] == "new"
            assert request_row["created_at"] == request_row["updated_at"], (
                "Neo4j's own created/updated properties must be equal, independent of "
                "the flow's reported created_at/updated_at (verifies the graph write "
                "itself, not just the Agent's report of it)"
            )

            # Verify binding exists and is unique
            binding_result = session.run(
                """
                MATCH (b:OperationalConversationBinding {sessionId: $session_id})
                    -[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
                RETURN b.sessionId as session_id, r.id as request_id
                """,
                {"session_id": graph_ids.request_id},
            )
            binding_row = binding_result.single()

            assert binding_row is not None, f"Binding not found for session: {graph_ids.request_id}"
            assert binding_row["request_id"] == graph_ids.request_id

    def test_no_caller_supplied_timestamp_accepted(
        self,
    ) -> None:
        """Test: request rejects caller-supplied created_at or updated_at.

        The model's extra='forbid' should reject created_at/updated_at in the request.
        Neo4j owns both timestamps; they cannot be supplied by the caller.
        """
        # Generate fresh identifiers
        actor_id = "test-actor-" + str(id(self))[-8:]
        graph_ids = new_graph_identifiers(
            actor_id=actor_id,
            receiver_stable_id=None,
            include_receiver=True,
        )

        # Attempt to supply created_at (should be rejected at validation)
        invalid_request = {
            "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
            "operation_id": f"op-{id(self)}",
            "caller": CallerFlow.LF_70.value,
            "session_id": graph_ids.request_id,
            "actor_id": actor_id,
            "schema_version": "v1",
            "correlation_id": f"corr-{id(self)}",
            "identifiers": {
                "request_id": graph_ids.request_id,
                "sender_id": graph_ids.sender_id,
                "sender_agent_id": graph_ids.sender_agent_id,
            },
            "facts": {
                "receiver_identity": "Test",
                "pickup_location": "Pickup",
                "drop_off_location": "Dropoff",
                "parcel_declared_content": "Content",
            },
            "created_at": "2026-01-01T00:00:00Z",  # This should cause rejection
        }

        # Validate should reject this at the model level (extra='forbid')
        with pytest.raises(ValidationError):
            validate_data_operation_request(invalid_request)

    def test_atomicity_rollback_on_binding_conflict(
        self,
        neo4j_driver: Any,
    ) -> None:
        """Test: rollback on binding uniqueness conflict (no orphan request).

        When a second createDeliveryRequest uses the same session_id (binding sessionId),
        the Neo4j constraint on OperationalConversationBinding.sessionId should reject it.
        The entire transaction (both request and binding) must roll back together.
        Verify no orphan request node is left behind.
        """
        # Create client with explicit API key
        langflow_client = LangFlowClient(base_url=LANGFLOW_URL, api_key=LANGFLOW_API_KEY)

        # Use a fixed session_id for both attempts
        actor_id = "test-actor-" + str(id(self))[-8:]
        fixed_session_id = f"sess-{id(self)}"

        # First create: success
        graph_ids_1 = new_graph_identifiers(
            actor_id=actor_id,
            receiver_stable_id=None,
            include_receiver=True,
        )

        create_request_1 = {
            "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
            "operation_id": f"op-1-{id(self)}",
            "caller": CallerFlow.LF_70.value,
            "session_id": fixed_session_id,  # FIXED session ID
            "actor_id": actor_id,
            "schema_version": "v1",
            "correlation_id": f"corr-1-{id(self)}",
            "identifiers": {
                "request_id": graph_ids_1.request_id,
                "sender_id": graph_ids_1.sender_id,
                "sender_agent_id": graph_ids_1.sender_agent_id,
            },
            "facts": {
                "receiver_identity": "Test",
                "pickup_location": "Pickup",
                "drop_off_location": "Dropoff",
                "parcel_declared_content": "Content",
            },
        }

        response_1 = langflow_client.run_flow_with_actor(
            flow_uuid=LF_70_FLOW_UUID,
            input_data=create_request_1,
            actor_id=actor_id,
        )

        if response_1.status_code == 500 and "Connection refused" in (response_1.error or ""):
            pytest.skip("LangFlow server not running")

        assert response_1.status_code == 200
        assert response_1.result is not None
        assert response_1.result["success"] is True
        first_request_id = response_1.result["request_id"]

        # Second create: same session_id, different request
        graph_ids_2 = new_graph_identifiers(
            actor_id=actor_id,
            receiver_stable_id=None,
            include_receiver=True,
        )

        create_request_2 = {
            "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
            "operation_id": f"op-2-{id(self)}",
            "caller": CallerFlow.LF_70.value,
            "session_id": fixed_session_id,  # SAME session ID (triggers conflict)
            "actor_id": actor_id,
            "schema_version": "v1",
            "correlation_id": f"corr-2-{id(self)}",
            "identifiers": {
                "request_id": graph_ids_2.request_id,
                "sender_id": graph_ids_2.sender_id,
                "sender_agent_id": graph_ids_2.sender_agent_id,
            },
            "facts": {
                "receiver_identity": "Test 2",
                "pickup_location": "Pickup 2",
                "drop_off_location": "Dropoff 2",
                "parcel_declared_content": "Content 2",
            },
        }

        response_2 = langflow_client.run_flow_with_actor(
            flow_uuid=LF_70_FLOW_UUID,
            input_data=create_request_2,
            actor_id=actor_id,
        )

        assert response_2.status_code == 200
        assert response_2.result is not None
        # Second attempt should fail (binding conflict)
        # Could be REJECTED or AMBIGUOUS depending on flow error handling
        assert (
            response_2.result["success"] is False
            or response_2.result["outcome"] != DataOperationOutcome.CONFIRMED.value
        )

        # Critical: Verify that no orphan request was created
        database = _read_neo4j_credentials_from_env_file()[2]
        with neo4j_driver.session(database=database) as session:
            # Check that the second request was NOT persisted
            orphan_check = session.run(
                """
                MATCH (r:DeliveryRequest {id: $request_id})
                RETURN r.id as id
                """,
                {"request_id": graph_ids_2.request_id},
            )
            orphan_row = orphan_check.single()

            assert orphan_row is None, (
                f"Orphan request node was created: {graph_ids_2.request_id}; "
                "transaction should have rolled back atomically"
            )

            # Verify the first binding still points to the first request
            binding_check = session.run(
                """
                MATCH (b:OperationalConversationBinding {sessionId: $session_id})
                    -[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
                RETURN r.id as request_id
                """,
                {"session_id": fixed_session_id},
            )
            binding_row = binding_check.single()
            assert binding_row is not None
            assert binding_row["request_id"] == first_request_id

    def test_truthful_available_subgraphs(
        self,
    ) -> None:
        """Test: result only contains truthful data (no fabricated fields).

        The returned snapshot must reflect only what was actually created.
        Missing optional fields must be absent or null, not fabricated.
        """
        # Create client with explicit API key
        langflow_client = LangFlowClient(base_url=LANGFLOW_URL, api_key=LANGFLOW_API_KEY)

        actor_id = "test-actor-" + str(id(self))[-8:]
        graph_ids = new_graph_identifiers(
            actor_id=actor_id,
            receiver_stable_id=None,
            include_receiver=False,  # No receiver
            include_parcel=False,  # No parcel
            include_pickup=False,  # No pickup
            include_drop_off=False,  # No dropoff
        )

        # Minimal create: only required fields (sender from actor)
        create_request = {
            "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
            "operation_id": f"op-{id(self)}",
            "caller": CallerFlow.LF_70.value,
            "session_id": graph_ids.request_id,
            "actor_id": actor_id,
            "schema_version": "v1",
            "correlation_id": f"corr-{id(self)}",
            "identifiers": {
                "request_id": graph_ids.request_id,
                "sender_id": graph_ids.sender_id,
                "sender_agent_id": graph_ids.sender_agent_id,
            },
            "facts": {},  # Sparse: no facts provided (everything is missing)
        }

        response = langflow_client.run_flow_with_actor(
            flow_uuid=LF_70_FLOW_UUID,
            input_data=create_request,
            actor_id=actor_id,
        )

        if response.status_code == 500 and "Connection refused" in (response.error or ""):
            pytest.skip("LangFlow server not running")

        assert response.status_code == 200
        assert response.result is not None
        assert response.result["success"] is True

        result = response.result

        # Verify the result is sparse (no fabricated data)
        # The snapshot should have empty or missing_fields populated
        if "result" in result and result["result"] is not None:
            snapshot = result["result"]
            # For a sparse new request with no facts, facts should be empty/sparse
            # not contain fabricated Receiver, Parcel, or Place data
            if "facts" in snapshot:
                facts = snapshot["facts"]
                # Only fields that were actually provided should be in facts
                assert "receiver_identity" not in facts or facts["receiver_identity"] is None
                assert (
                    "parcel_declared_content" not in facts
                    or facts["parcel_declared_content"] is None
                )
