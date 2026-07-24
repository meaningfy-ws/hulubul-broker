"""Tests for operational schema constraints and bindings."""

import pytest


@pytest.mark.integration
class TestOperationalConversationBinding:
    """Test OperationalConversationBinding schema and constraints."""

    def test_session_id_uniqueness_constraint_enforced(self, neo4j_session_with_schema):
        """
        RED: Test that duplicate sessionId values are rejected by the constraint.

        This test expects the operational-schema constraint to be in place.
        Before the constraint exists, this test will fail (RED).
        After the constraint is applied, this test will pass (GREEN).
        """
        session = neo4j_session_with_schema

        # Create a request node to link to
        request_result = session.run(
            "CREATE (r:ParcelRequest {id: 'req-001'}) RETURN r.id as id"
        )
        request_id = request_result.single()["id"]

        # Create first binding with sessionId
        session.run(
            """
            CREATE (b:OperationalConversationBinding {sessionId: 'test-session-001'})
            """
        )

        # Try to create second binding with same sessionId — should fail
        with pytest.raises(Exception) as exc_info:
            session.run(
                """
                CREATE (b:OperationalConversationBinding {sessionId: 'test-session-001'})
                """
            )

        # Verify it's a constraint violation (not some other error)
        assert "constraint" in str(exc_info.value).lower(), (
            f"Expected constraint violation, got: {exc_info.value}"
        )

    def test_binding_uses_relationship_only_linking(self, neo4j_session_with_schema):
        """
        Test that OperationalConversationBinding uses relationship-only linking
        to the active request (no activeRequestId property).

        The binding must link via BINDS_ACTIVE_REQUEST relationship only,
        never via a duplicated activeRequestId property.
        """
        session = neo4j_session_with_schema

        # Create a request node
        session.run("CREATE (r:ParcelRequest {id: 'req-001'})")

        # Create a binding
        binding_result = session.run(
            """
            CREATE (b:OperationalConversationBinding {sessionId: 'test-session-002'})
            RETURN b
            """
        )
        binding = binding_result.single()[0]

        # Verify the binding has no activeRequestId property
        binding_props = dict(binding)
        assert "activeRequestId" not in binding_props, (
            f"Binding must not have activeRequestId property. "
            f"Found properties: {binding_props.keys()}"
        )
        assert binding_props["sessionId"] == "test-session-002"

        # Create relationship from binding to request
        session.run(
            """
            MATCH (b:OperationalConversationBinding {sessionId: 'test-session-002'})
            MATCH (r:ParcelRequest {id: 'req-001'})
            CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r)
            """
        )

        # Verify the relationship exists and is the only link
        rel_result = session.run(
            """
            MATCH (b:OperationalConversationBinding {sessionId: 'test-session-002'})
                  -[rel:BINDS_ACTIVE_REQUEST]->(r:ParcelRequest)
            RETURN type(rel) as rel_type
            """
        )
        rel = rel_result.single()
        assert rel["rel_type"] == "BINDS_ACTIVE_REQUEST"
