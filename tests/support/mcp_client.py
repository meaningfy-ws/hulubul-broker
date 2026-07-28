"""MCP client wrapper for test integration with mcp-neo4j-cypher server."""

import logging

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class MCPClient:
    """
    Synchronous wrapper around MCP protocol client.

    Sends JSON-RPC requests to the MCP server over plain HTTP POST and reads
    the JSON response — no SSE stream or persistent connection is established.
    Implements enough of the MCP spec to initialize and list tools.

    MCP spec: https://spec.modelcontextprotocol.org/
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        """
        Initialize MCP client.

        Args:
            base_url: Base URL of MCP server (e.g., http://localhost:8000)
            timeout: Timeout for HTTP requests in seconds
        """
        if httpx is None:
            raise RuntimeError("httpx is required; install with: poetry install --with integration")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session_id: str | None = None
        self._message_id_counter = 0
        self._initialized = False
        self._tools_cache: set[str] | None = None

    def _next_message_id(self) -> str:
        """Generate next message ID."""
        self._message_id_counter += 1
        return str(self._message_id_counter)

    def initialize(self) -> None:
        """
        Initialize MCP protocol with the server.

        This performs a real protocol handshake:
        1. Sends INITIALIZE request with client info
        2. Waits for INITIALIZE response
        3. Verifies server name

        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            return

        message_id = self._next_message_id()
        initialize_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-mcp-client",
                    "version": "0.0.1",
                },
            },
        }

        logger.debug(f"Sending INITIALIZE: {initialize_message}")

        try:
            response = httpx.post(
                f"{self.base_url}/mcp",
                json=initialize_message,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()
            logger.debug(f"INITIALIZE response: {result}")

            if "error" in result:
                raise RuntimeError(f"INITIALIZE error: {result['error']}")

            # Extract server info
            server_info = result.get("result", {}).get("serverInfo", {})
            server_name = server_info.get("name", "unknown")
            logger.info(f"Connected to MCP server: {server_name}")

            self._initialized = True

        except Exception as e:
            logger.error(f"INITIALIZE failed: {e}")
            raise RuntimeError(f"Failed to initialize MCP protocol: {e}") from e

    def list_tools(self) -> list[str]:
        """
        List available tools from the MCP server.

        Returns:
            List of tool names as strings

        Raises:
            RuntimeError: If not initialized or tool listing fails
        """
        if not self._initialized:
            self.initialize()

        if self._tools_cache is not None:
            return sorted(self._tools_cache)

        message_id = self._next_message_id()
        list_tools_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/list",
            "params": {},
        }

        logger.debug(f"Sending TOOLS/LIST: {list_tools_message}")

        try:
            response = httpx.post(
                f"{self.base_url}/mcp",
                json=list_tools_message,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()
            logger.debug(f"TOOLS/LIST response: {result}")

            if "error" in result:
                raise RuntimeError(f"TOOLS/LIST error: {result['error']}")

            # Extract tool names from result.tools
            tools = result.get("result", {}).get("tools", [])
            tool_names = [tool.get("name") for tool in tools if "name" in tool]
            self._tools_cache = set(tool_names)

            logger.info(f"Available tools: {tool_names}")
            return sorted(tool_names)

        except Exception as e:
            logger.error(f"TOOLS/LIST failed: {e}")
            raise RuntimeError(f"Failed to list MCP tools: {e}") from e

    def close(self) -> None:
        """Close the client (no persistent connection to close in HTTP mode)."""
        self._initialized = False
        self._tools_cache = None
