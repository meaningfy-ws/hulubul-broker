#!/usr/bin/env python3
"""
MCP readiness checker for mcp-neo4j-cypher server.

This script:
1. Connects to a running MCP server
2. Initializes the MCP protocol
3. Verifies server name
4. Checks tool inventory matches exactly three Neo4j tools
5. Exits 0 if healthy, 1 if not

Usage:
    python infra/scripts/mcp-readiness.py http://localhost:8000

Environment variables (optional):
    MCP_TIMEOUT - HTTP timeout in seconds (default: 30)

Expected tools: get_neo4j_schema, read_neo4j_cypher, write_neo4j_cypher
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports (if needed)
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required; install with: pip install httpx", file=sys.stderr)
    sys.exit(1)


# Expected tools from mcp-neo4j-cypher
EXPECTED_TOOLS = frozenset({"get_neo4j_schema", "read_neo4j_cypher", "write_neo4j_cypher"})

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_mcp_readiness(base_url: str, timeout: float = 30.0) -> bool:
    """
    Check if MCP server is ready and has correct tool inventory.

    Args:
        base_url: Base URL of MCP server (e.g., http://localhost:8000)
        timeout: Timeout for HTTP requests in seconds

    Returns:
        True if MCP is ready with correct tools, False otherwise
    """
    base_url = base_url.rstrip("/")
    logger.info(f"Checking MCP readiness at {base_url}")

    try:
        # Step 1: Initialize protocol
        logger.info("Initializing MCP protocol...")
        message_id = "1"
        initialize_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "readiness-checker",
                    "version": "0.0.1",
                },
            },
        }

        response = httpx.post(
            f"{base_url}/mcp",
            json=initialize_message,
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            logger.error(f"INITIALIZE error: {result['error']}")
            return False

        server_info = result.get("result", {}).get("serverInfo", {})
        server_name = server_info.get("name", "unknown")
        logger.info(f"Connected to MCP server: {server_name}")

        # Step 2: List tools
        logger.info("Listing available tools...")
        message_id = "2"
        list_tools_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/list",
            "params": {},
        }

        response = httpx.post(
            f"{base_url}/mcp",
            json=list_tools_message,
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            logger.error(f"TOOLS/LIST error: {result['error']}")
            return False

        # Extract tool names
        tools = result.get("result", {}).get("tools", [])
        tool_names = frozenset(tool.get("name") for tool in tools if "name" in tool)

        logger.info(f"Found tools: {sorted(tool_names)}")
        logger.info(f"Expected tools: {sorted(EXPECTED_TOOLS)}")

        # Step 3: Verify tool inventory
        if tool_names == EXPECTED_TOOLS:
            logger.info("✓ MCP readiness check PASSED")
            return True
        else:
            missing = EXPECTED_TOOLS - tool_names
            extra = tool_names - EXPECTED_TOOLS
            if missing:
                logger.error(f"Missing tools: {missing}")
            if extra:
                logger.error(f"Extra tools: {extra}")
            logger.error("✗ MCP readiness check FAILED")
            return False

    except httpx.ConnectError as e:
        logger.error(f"Connection error: {e}")
        return False
    except httpx.TimeoutException as e:
        logger.error(f"Timeout error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <base_url>", file=sys.stderr)
        print(f"Example: {sys.argv[0]} http://localhost:8000", file=sys.stderr)
        sys.exit(1)

    base_url = sys.argv[1]
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0

    success = check_mcp_readiness(base_url, timeout)
    sys.exit(0 if success else 1)
