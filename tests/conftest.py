"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Add src directory to Python path BEFORE any imports
repo_root = Path(__file__).parent.parent
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Verify import works
from hulubul.core.models.operational.base import StrictModel  # noqa: E402, F401


def pytest_configure(config: pytest.Config) -> None:
    """Pytest hook called before test collection."""
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


# ============================================================================
# Neo4j Integration Test Fixtures
# ============================================================================


def _load_neo4j_env() -> dict[str, str]:
    """Load Neo4j credentials from infra/.env."""
    env_file = repo_root / "infra" / ".env"
    if not env_file.exists():
        raise RuntimeError(
            f"Missing {env_file}. Run: cp infra/.env.example infra/.env"
        )

    env = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key, val = line.split("=", 1)
                    env[key.strip()] = val.strip()
    return env


@pytest.fixture(scope="session")
def neo4j_env() -> dict[str, str]:
    """Load Neo4j environment from infra/.env."""
    return _load_neo4j_env()


@pytest.fixture(scope="session")
def neo4j_driver(neo4j_env):
    """Create a Neo4j driver connected to the running container."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        pytest.skip("neo4j driver not installed; run: poetry install --with integration")

    uri = "bolt://localhost:7687"
    username = neo4j_env.get("NEO4J_USERNAME", "neo4j")
    cred = neo4j_env.get("NEO4J_PASSWORD")

    if not cred:
        pytest.skip("NEO4J_PASSWORD not set in infra/.env")

    driver = GraphDatabase.driver(uri, auth=(username, cred))

    # Wait for Neo4j to be ready
    max_retries = 60
    for attempt in range(max_retries):
        try:
            with driver.session() as session:
                session.run("RETURN 1")
            break
        except Exception:
            if attempt == max_retries - 1:
                driver.close()
                pytest.skip("Neo4j not ready after 60 attempts")
            import time
            time.sleep(1)

    yield driver
    driver.close()


@pytest.fixture(scope="function")
def neo4j_session_with_schema(neo4j_driver):
    """
    Fixture that provides a Neo4j session with domain and operational schemas applied.

    Creates a fresh session, applies the domain schema from infra/cypher/schema.cypher,
    then applies the operational schema from infra/cypher/operational-schema.cypher (if it exists),
    and yields the session for test use. Cleans up after the test.
    """
    session = neo4j_driver.session()

    # Read and apply domain schema
    schema_file = repo_root / "infra" / "cypher" / "schema.cypher"
    if not schema_file.exists():
        raise RuntimeError(f"Schema file not found: {schema_file}")

    with open(schema_file) as f:
        schema = f.read()

    # Apply domain schema statements
    for stmt in schema.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("//"):
            try:
                session.run(stmt)
            except Exception:
                # Some statements may fail if they're comments or incomplete
                pass

    # Read and apply operational schema if it exists
    operational_schema_file = repo_root / "infra" / "cypher" / "operational-schema.cypher"
    if operational_schema_file.exists():
        with open(operational_schema_file) as f:
            operational_schema = f.read()

        # Apply operational schema statements
        for stmt in operational_schema.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("//"):
                try:
                    session.run(stmt)
                except Exception:
                    # Some statements may fail if they're comments or incomplete
                    pass

    yield session

    # Clean up: delete all nodes and relationships
    try:
        session.run("MATCH (n) DETACH DELETE n")
    except Exception:
        pass
    finally:
        session.close()
