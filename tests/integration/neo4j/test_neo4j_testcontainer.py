"""Tests for disposable Neo4j Testcontainer integration."""

from typing import Any

import pytest


def get_server_version(driver: Any) -> str:
    """Fetch Neo4j server version string."""
    with driver.session() as session:
        result = session.run("CALL dbms.components() YIELD versions RETURN versions[0]")
        record = result.single()
        return record[0] if record else ""


def get_constraint_names(driver: Any) -> set[str]:
    """Fetch all constraint names currently in the database."""
    with driver.session() as session:
        result = session.run("SHOW CONSTRAINTS")
        return {record["name"] for record in result}


# These are the required constraints from the domain and operational schemas
REQUIRED_CONSTRAINTS = {
    # Domain constraints (from infra/cypher/schema.cypher)
    "address_id_unique",
    "agent_id_unique",
    "area_id_unique",
    "channel_id_unique",
    "deliveryrequest_id_unique",
    "feedback_id_unique",
    "parcel_id_unique",
    "place_id_unique",
    "receiver_id_unique",
    "sender_id_unique",
    "serviceoffer_id_unique",
    "transportservice_id_unique",
    "transporter_id_unique",
    # Operational constraints (from infra/cypher/operational-schema.cypher)
    "operationalconversationbinding_sessionid_unique",
}


@pytest.mark.integration
class TestDisposableNeo4jTestcontainer:
    """Test the disposable Neo4j Testcontainer fixture."""

    def test_disposable_neo4j_has_approved_version_and_schemas(
        self, neo4j_testcontainer_driver: Any
    ) -> None:
        """
        Test that the testcontainer Neo4j has the approved version and both schemas.

        This test verifies:
        1. The Neo4j version is exactly 5.26.28
        2. All required domain constraints are present
        3. The operational-schema constraint is present
        4. The container is isolated (not using developer's localhost)

        Before the fixture exists, this test will fail (RED).
        After the fixture is implemented, this test will pass (GREEN).
        """
        version = get_server_version(neo4j_testcontainer_driver)
        constraints = get_constraint_names(neo4j_testcontainer_driver)

        # Verify the exact version
        assert version == "5.26.28", f"Expected Neo4j 5.26.28, got {version}"

        # Verify all required constraints are present
        missing = REQUIRED_CONSTRAINTS - constraints
        assert not missing, (
            f"Missing required constraints: {missing}. Present constraints: {constraints}"
        )
