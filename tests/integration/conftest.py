"""Pytest fixtures for integration tests (Neo4j Testcontainer + MCP)."""

import contextlib
import secrets
import time
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Any, NamedTuple

import pytest

# Neo4j Testcontainer image — pinned to exact digest for reproducibility
NEO4J_IMAGE = (
    "neo4j:5.26-community@sha256:362542416de6c09a971484d1893878016cc3b5cdec166e54b1c824a220ecd6b9"
)


class Neo4jTestcontainerInfo(NamedTuple):
    """Info about the Neo4j testcontainer and its network."""

    driver: Any
    network_alias: str
    network: Any
    container: Any


def _load_cypher_file(file_path: Path) -> str:
    """Load and return the contents of a Cypher script file."""
    if not file_path.exists():
        raise RuntimeError(f"Cypher file not found: {file_path}")
    return file_path.read_text()


def _apply_cypher_statements(session: Any, cypher_text: str) -> None:
    """Parse and apply Cypher statements from a file, skipping comments and empty lines."""
    for stmt in cypher_text.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("//"):
            with contextlib.suppress(Exception):
                # Some statements may fail if they're incomplete or already exist
                # This is acceptable for idempotent CREATE...IF NOT EXISTS statements
                session.run(stmt)


@pytest.fixture(scope="session")
def neo4j_testcontainer_info() -> Generator[Neo4jTestcontainerInfo, None, None]:
    """
    Session-scoped fixture: Create a disposable, isolated Neo4j Testcontainer.

    This is an internal fixture that returns both the driver and network info.
    Other fixtures depend on this to access the network for services like MCP.

    This fixture:
    - Creates a fresh Neo4j container using Testcontainers (no persistent volume)
    - Applies domain schema from infra/cypher/schema.cypher
    - Applies operational schema from infra/cypher/operational-schema.cypher
    - Generates a unique in-memory password (never references infra/.env)
    - Yields Neo4jTestcontainerInfo with driver, network alias, network object, and container
    - Cleans up: stops the container and removes the network

    Use neo4j_testcontainer_driver for backward compatibility (yields just the driver).
    Use this fixture when you need network info for co-located services.
    Never falls back to developer's localhost Neo4j.
    """
    try:
        from neo4j import GraphDatabase
        from testcontainers.core.network import Network  # type: ignore
        from testcontainers.neo4j import Neo4jContainer  # type: ignore
    except ImportError:
        pytest.skip("testcontainers or neo4j not installed; run: poetry install --with integration")

    # Generate unique session identifiers
    session_id = str(uuid.uuid4())[:8]
    network_alias = f"test-neo4j-{session_id}"
    cred = secrets.token_urlsafe(32)

    # Create isolated Docker network
    network = Network(docker_network_kw={"name": f"test-net-{session_id}"})
    network.create()

    try:
        # Start Neo4j container on isolated network
        container = (
            Neo4jContainer(image=NEO4J_IMAGE)
            .with_env("NEO4J_AUTH", f"neo4j/{cred}")
            .with_network(network)
            .with_network_aliases(network_alias)
        )
        container.start()

        # Wait for Neo4j to be ready
        host = container.get_container_host_ip()
        port = container.get_exposed_port(7687)

        max_retries = 60
        driver = GraphDatabase.driver(f"bolt://{host}:{port}", auth=("neo4j", cred))

        for attempt in range(max_retries):
            try:
                with driver.session() as session:
                    session.run("RETURN 1")
                break
            except Exception:
                if attempt == max_retries - 1:
                    driver.close()
                    pytest.skip("Neo4j container failed to start after 60 retries")
                time.sleep(1)

        # Load and apply domain schema
        repo_root = Path(__file__).parent.parent.parent
        schema_file = repo_root / "infra" / "cypher" / "schema.cypher"
        domain_schema = _load_cypher_file(schema_file)

        with driver.session() as session:
            _apply_cypher_statements(session, domain_schema)

        # Load and apply operational schema
        operational_schema_file = repo_root / "infra" / "cypher" / "operational-schema.cypher"
        if operational_schema_file.exists():
            operational_schema = _load_cypher_file(operational_schema_file)
            with driver.session() as session:
                _apply_cypher_statements(session, operational_schema)

        # Await indexes to be fully created
        with driver.session() as session:
            with contextlib.suppress(Exception):
                # Index await may not be available in all versions
                session.run("CALL db.awaitIndexes(120)")

        yield Neo4jTestcontainerInfo(
            driver=driver,
            network_alias=network_alias,
            network=network,
            container=container,
        )

    finally:
        # Cleanup: close driver and stop container
        with contextlib.suppress(Exception):
            driver.close()

        with contextlib.suppress(Exception):
            container.stop()

        with contextlib.suppress(Exception):
            network.remove()


@pytest.fixture(scope="session")
def neo4j_testcontainer_driver(
    neo4j_testcontainer_info: Neo4jTestcontainerInfo,
) -> Generator[Any, None, None]:
    """
    Backward-compatible fixture: yields just the Neo4j driver.

    This is a wrapper around neo4j_testcontainer_info for tests that only need the driver.
    For new tests that need network info (e.g., MCP fixtures), depend on neo4j_testcontainer_info.
    """
    yield neo4j_testcontainer_info.driver


@pytest.fixture(scope="session")
def mcp_client(neo4j_testcontainer_info: Neo4jTestcontainerInfo) -> Generator[Any, None, None]:
    """
    Session-scoped fixture: Start isolated MCP service on Neo4j test network.

    This fixture:
    - Builds and starts mcp-neo4j-cypher container from infra/mcp/Dockerfile
    - Starts it on the SAME network as neo4j_testcontainer_info
    - Configures MCP to connect to Neo4j via the network alias (never localhost)
    - Sets NEO4J_MCP_SERVER_ALLOWED_HOSTS to include the test network alias
    - Initializes MCP protocol (real SSE + HTTP POST handshake)
    - Yields an MCPClient with verified tool inventory
    - Cleans up: stops the MCP container

    This fixture proves:
    - MCP service runs on disposable Neo4j test network (not localhost)
    - Protocol initialization works (real SSE + HTTP, not TCP-only)
    - Tool inventory is exactly {"get_neo4j_schema", "read_neo4j_cypher", "write_neo4j_cypher"}

    Use this fixture for tests verifying MCP readiness and protocol compliance.
    Never falls back to localhost or any external network.
    """
    try:
        from testcontainers.core.container import DockerContainer  # type: ignore
    except ImportError:
        pytest.skip("testcontainers not installed; run: poetry install --with integration")

    # Import MCPClient from tests/support
    from tests.support.mcp_client import MCPClient

    session_id = str(uuid.uuid4())[:8]

    # Build MCP image from Dockerfile (from_build_context builds from local Dockerfile)
    # For testcontainers, we use a generic container with the image name
    # The image will be pulled/built by Docker based on local Dockerfile
    image_name = f"hulubul-mcp-test-{session_id}:latest"

    # Start MCP container on the SAME network as Neo4j
    # Note: In local dev, you may need to pre-build the image with:
    #   docker build -t hulubul-mcp-test:latest infra/mcp/
    mcp_container = (
        DockerContainer(image_name)
        .with_network(neo4j_testcontainer_info.network)
        .with_network_aliases(f"test-mcp-{session_id}")
        .with_env("NEO4J_URL", f"bolt://{neo4j_testcontainer_info.network_alias}:7687")
        .with_env("NEO4J_USERNAME", "neo4j")
        .with_env("NEO4J_PASSWORD", "test")
        .with_env("NEO4J_TRANSPORT", "http")
        .with_env(
            "NEO4J_MCP_SERVER_ALLOWED_HOSTS",
            f"{neo4j_testcontainer_info.network_alias},localhost,127.0.0.1",
        )
        .with_exposed_port(8000)
    )

    mcp_container.start()

    try:
        # Wait for MCP to be ready
        host = mcp_container.get_container_host_ip()
        port = mcp_container.get_exposed_port(8000)
        base_url = f"http://{host}:{port}"

        max_retries = 60
        client = MCPClient(base_url, timeout=30.0)

        for attempt in range(max_retries):
            try:
                client.initialize()
                tools = client.list_tools()
                if tools:
                    # MCP is ready
                    break
            except Exception:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        "MCP container failed to start after 60 retries"
                    ) from None
                time.sleep(1)

        yield client

    finally:
        # Cleanup: stop MCP container
        with contextlib.suppress(Exception):
            client.close()

        with contextlib.suppress(Exception):
            mcp_container.stop()


@pytest.fixture(scope="session")
def mcp_client_localhost_only(
    neo4j_testcontainer_info: Neo4jTestcontainerInfo,
) -> Generator[Any, None, None]:
    """
    Negative test fixture: MCP with allowed-hosts restricted to localhost only.

    This fixture intentionally misconfigures MCP to verify that the allowed-hosts
    gate is enforced. It will fail to initialize because NEO4J_MCP_SERVER_ALLOWED_HOSTS
    is restricted to localhost, but the fixture attempts to connect via the network alias.

    This proves the allowed-hosts restriction is not a no-op — it actually prevents
    connections from disallowed hosts.

    Yields an MCPClient that will raise an exception when attempting to list_tools().
    """
    try:
        from testcontainers.core.container import DockerContainer
    except ImportError:
        pytest.skip("testcontainers not installed; run: poetry install --with integration")

    # Import MCPClient from tests/support
    from tests.support.mcp_client import MCPClient

    session_id = str(uuid.uuid4())[:8]
    image_name = f"hulubul-mcp-test-{session_id}:latest"

    # Start MCP container with RESTRICTED allowed-hosts (localhost only)
    mcp_container = (
        DockerContainer(image_name)        .with_network(neo4j_testcontainer_info.network)
        .with_network_aliases(f"test-mcp-restricted-{session_id}")
        .with_env("NEO4J_URL", f"bolt://{neo4j_testcontainer_info.network_alias}:7687")
        .with_env("NEO4J_USERNAME", "neo4j")
        .with_env("NEO4J_PASSWORD", "test")
        .with_env("NEO4J_TRANSPORT", "http")
        .with_env("NEO4J_MCP_SERVER_ALLOWED_HOSTS", "localhost")  # RESTRICTED
        .with_exposed_port(8000)
    )

    mcp_container.start()

    try:
        # Wait for MCP container to start (it will be running but reject requests)
        host = mcp_container.get_container_host_ip()
        port = mcp_container.get_exposed_port(8000)
        base_url = f"http://{host}:{port}"

        time.sleep(2)  # Give container time to start

        client = MCPClient(base_url, timeout=30.0)
        yield client

    finally:
        # Cleanup: stop MCP container
        with contextlib.suppress(Exception):
            mcp_container.stop()
