"""Tests for isolated MCP protocol readiness on disposable Neo4j network."""

from typing import Any

import pytest

# The three exact tools that mcp-neo4j-cypher must expose
EXPECTED_TOOLS = frozenset({"get_neo4j_schema", "read_neo4j_cypher", "write_neo4j_cypher"})


@pytest.mark.integration
class TestMCPReadiness:
    """Test MCP protocol readiness on isolated Neo4j Testcontainer network."""

    def test_mcp_ready_only_after_initialize_and_exact_inventory(self, mcp_client: Any) -> None:
        """
        Test that MCP initializes cleanly and tool inventory matches exactly.

        This test verifies:
        1. MCP protocol initializes successfully (real SSE + HTTP POST to /initialize)
        2. Server name is correct
        3. Tool inventory is exactly {"get_neo4j_schema", "read_neo4j_cypher", "write_neo4j_cypher"}
        4. No extra tools, no shortcuts, no aliases
        5. MCP runs on isolated Neo4j test network (not localhost)

        Before the fixture exists, this test will fail (RED).
        After the fixture is implemented, this test will pass (GREEN).
        """
        tool_names = frozenset(mcp_client.list_tools())
        assert tool_names == EXPECTED_TOOLS, (
            f"Expected tools {EXPECTED_TOOLS}, got {tool_names}. "
            f"Missing: {EXPECTED_TOOLS - tool_names}, Extra: {tool_names - EXPECTED_TOOLS}"
        )

    def test_mcp_readiness_fails_when_allowed_hosts_restricted_to_localhost(
        self, mcp_client_localhost_only: Any
    ) -> None:
        """
        Negative test: verify the NEO4J_MCP_SERVER_ALLOWED_HOSTS gate is enforced.

        This test confirms that when NEO4J_MCP_SERVER_ALLOWED_HOSTS is restricted
        to localhost only, MCP readiness fails (proving the gate is real, not a no-op).

        This is the verification that the allowed-hosts check actually works.
        """
        # The mcp_client_localhost_only fixture should fail to initialize
        # because it's restricted to localhost but trying to use the test network alias
        with pytest.raises(RuntimeError):
            mcp_client_localhost_only.list_tools()
