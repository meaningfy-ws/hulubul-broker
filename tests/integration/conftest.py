"""Pytest fixtures for integration tests (Neo4j Testcontainer)."""

import contextlib
import secrets
import time
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

# Neo4j Testcontainer image — pinned to exact digest for reproducibility
NEO4J_IMAGE = (
    "neo4j:5.26-community@sha256:362542416de6c09a971484d1893878016cc3b5cdec166e54b1c824a220ecd6b9"
)


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
def neo4j_testcontainer_driver() -> Generator[Any, None, None]:
    """
    Session-scoped fixture: Create a disposable, isolated Neo4j Testcontainer.

    This fixture:
    - Creates a fresh Neo4j container using Testcontainers (no persistent volume)
    - Applies domain schema from infra/cypher/schema.cypher
    - Applies operational schema from infra/cypher/operational-schema.cypher
    - Generates a unique in-memory password (never references infra/.env)
    - Yields a Neo4j driver connected to the container
    - Cleans up: stops the container and removes the network

    Use this fixture for tests that need a clean, isolated Neo4j instance.
    Never falls back to developer's localhost Neo4j.
    """
    try:
        from neo4j import GraphDatabase
        from testcontainers.core.network import Network
        from testcontainers.neo4j import Neo4jContainer
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

        yield driver

    finally:
        # Cleanup: close driver and stop container
        with contextlib.suppress(Exception):
            driver.close()

        with contextlib.suppress(Exception):
            container.stop()

        with contextlib.suppress(Exception):
            network.remove()
