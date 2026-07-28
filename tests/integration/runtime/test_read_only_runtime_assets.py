"""
Test that tracked assets are mounted read-only and LangFlow starter projects are disabled.

This test verifies:
- Application and LangFlow assets are mounted read-only to prevent accidental mutation
- Database/configuration volumes remain writable for runtime state
- Starter projects are disabled to prevent unwanted auto-creation
- Custom components path is configured for importing application code
"""

from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMPOSE_FILE = PROJECT_ROOT / "infra" / "docker-compose.yaml"


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    """Load docker-compose.yaml and return services dict."""
    with open(COMPOSE_FILE) as f:
        compose_data = yaml.safe_load(f)
    return compose_data  # type: ignore[no-any-return]


class TestReadOnlyMounts:
    """Verify that source code mounts are read-only."""

    def test_langflow_source_mounted_read_only(self, compose: dict[str, Any]) -> None:
        """Verify langflow/ directory is mounted read-only."""
        langflow_service = compose["services"]["langflow"]
        volumes = langflow_service.get("volumes", [])

        # Check for langflow read-only mount (./langflow:/app/hulubul-langflow:ro)
        read_only_mounts = [v for v in volumes if isinstance(v, str) and ":ro" in v]
        langflow_ro = [v for v in read_only_mounts if "langflow:" in v or "hulubul-langflow" in v]

        assert langflow_ro, f"langflow/ must be mounted read-only. Current volumes: {volumes}"

    def test_src_mounted_read_only(self, compose: dict[str, Any]) -> None:
        """Verify src/ directory is mounted read-only."""
        langflow_service = compose["services"]["langflow"]
        volumes = langflow_service.get("volumes", [])

        # Check for src read-only mount (./src:/app/src:ro)
        read_only_mounts = [v for v in volumes if isinstance(v, str) and ":ro" in v]
        src_ro = [v for v in read_only_mounts if "/app/src:ro" in v]

        assert src_ro, f"src/ must be mounted read-only at /app/src:ro. Current volumes: {volumes}"

    def test_langflow_data_volume_writable(self, compose: dict[str, Any]) -> None:
        """Verify langflow-data volume (runtime state) is writable (no :ro)."""
        langflow_service = compose["services"]["langflow"]
        volumes = langflow_service.get("volumes", [])

        # Check that langflow-data volume is NOT read-only
        langflow_data_vols = [v for v in volumes if "langflow-data" in str(v)]
        assert langflow_data_vols, "langflow-data volume must be mounted for runtime state"

        for vol in langflow_data_vols:
            assert not str(vol).endswith(":ro"), (
                f"langflow-data volume must be writable (no :ro suffix). Got: {vol}"
            )


class TestStarterProjectsDisabled:
    """Verify that LangFlow starter projects are disabled."""

    def test_create_starter_projects_disabled(self, compose: dict[str, Any]) -> None:
        """Verify LANGFLOW_CREATE_STARTER_PROJECTS is false."""
        langflow_service = compose["services"]["langflow"]
        env = langflow_service.get("environment", {})

        assert "LANGFLOW_CREATE_STARTER_PROJECTS" in env, (
            "LANGFLOW_CREATE_STARTER_PROJECTS must be set in environment"
        )
        assert env["LANGFLOW_CREATE_STARTER_PROJECTS"] == "false", (
            f"LANGFLOW_CREATE_STARTER_PROJECTS must be 'false', got {env.get('LANGFLOW_CREATE_STARTER_PROJECTS')}"
        )

    def test_update_starter_projects_disabled(self, compose: dict[str, Any]) -> None:
        """Verify LANGFLOW_UPDATE_STARTER_PROJECTS is false."""
        langflow_service = compose["services"]["langflow"]
        env = langflow_service.get("environment", {})

        assert "LANGFLOW_UPDATE_STARTER_PROJECTS" in env, (
            "LANGFLOW_UPDATE_STARTER_PROJECTS must be set in environment"
        )
        assert env["LANGFLOW_UPDATE_STARTER_PROJECTS"] == "false", (
            f"LANGFLOW_UPDATE_STARTER_PROJECTS must be 'false', got {env.get('LANGFLOW_UPDATE_STARTER_PROJECTS')}"
        )


class TestCustomComponentsConfiguration:
    """Verify that custom components path and PYTHONPATH are configured."""

    def test_pythonpath_configured(self, compose: dict[str, Any]) -> None:
        """Verify PYTHONPATH includes /app/src for custom components."""
        langflow_service = compose["services"]["langflow"]
        env = langflow_service.get("environment", {})

        assert "PYTHONPATH" in env, "PYTHONPATH must be set in environment for custom components"
        assert env["PYTHONPATH"] == "/app/src", (
            f"PYTHONPATH must be '/app/src', got {env.get('PYTHONPATH')}"
        )

    def test_components_path_configured(self, compose: dict[str, Any]) -> None:
        """Verify LANGFLOW_COMPONENTS_PATH is set to custom components directory."""
        langflow_service = compose["services"]["langflow"]
        env = langflow_service.get("environment", {})

        assert "LANGFLOW_COMPONENTS_PATH" in env, (
            "LANGFLOW_COMPONENTS_PATH must be set in environment"
        )
        assert env["LANGFLOW_COMPONENTS_PATH"] == "/app/custom_components", (
            f"LANGFLOW_COMPONENTS_PATH must be '/app/custom_components', got {env.get('LANGFLOW_COMPONENTS_PATH')}"
        )


class TestDatabaseVolumesWritable:
    """Verify that database volumes remain writable."""

    def test_postgres_volume_writable(self, compose: dict[str, Any]) -> None:
        """Verify postgres volume is NOT read-only."""
        postgres_service = compose["services"]["postgres"]
        volumes = postgres_service.get("volumes", [])

        # Check that no postgres volume is read-only
        for vol in volumes:
            assert not str(vol).endswith(":ro"), (
                f"PostgreSQL volume must be writable (no :ro suffix). Got: {vol}"
            )

    def test_neo4j_volume_writable(self, compose: dict[str, Any]) -> None:
        """Verify neo4j volume is NOT read-only."""
        neo4j_service = compose["services"]["neo4j"]
        volumes = neo4j_service.get("volumes", [])

        # Check that no neo4j volume is read-only
        for vol in volumes:
            assert not str(vol).endswith(":ro"), (
                f"Neo4j volume must be writable (no :ro suffix). Got: {vol}"
            )
