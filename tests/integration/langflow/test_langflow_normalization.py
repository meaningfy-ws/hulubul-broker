"""Integration tests for LangFlow flow normalization."""

import hashlib
import json
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest


@pytest.fixture
def sample_langflow_flow() -> dict[str, Any]:
    """Sample LangFlow 1.10.2 export format with unsorted keys and varied formatting."""
    return {
        "data": {
            "nodes": [
                {
                    "id": "node1-id",
                    "type": "ChatInput",
                    "data": {"outputs": [{"name": "text", "type": "str"}]},
                    "position": [100, 100],
                },
                {
                    "id": "node2-id",
                    "type": "OpenAIModel",
                    "data": {
                        "model_name": "gpt-4",
                        "api_key": "REDACTED-TEST-API-KEY",
                        "temperature": 0,
                    },
                    "position": [300, 100],
                },
            ],
            "edges": [
                {
                    "source": "node1-id",
                    "target": "node2-id",
                    "sourceHandle": "text",
                    "targetHandle": "text_input",
                }
            ],
        },
        "name": "Test Flow",
        "description": "A test flow",
    }


@pytest.fixture
def sample_flow_with_env_vars() -> dict[str, Any]:
    """Sample flow with hardcoded LLM credentials that should be replaced."""
    return {
        "data": {
            "nodes": [
                {
                    "id": "OpenAIModel-hlb-lf-00-model-v1",
                    "type": "OpenAIModel",
                    "data": {
                        "model_name": "gpt-4",
                        "openai_api_base": "https://api.openai.com/v1",
                        "api_key": "REDACTED-TEST-API-KEY-LONG",
                    },
                    "position": [300, 100],
                },
            ],
            "edges": [],
        },
        "name": "LLM Flow",
    }


@pytest.fixture
def manifest_yaml() -> str:
    """Load flow-manifest.yaml runtime bindings."""
    return dedent("""
        runtime_bindings:
          - component_id: OpenAIModel-hlb-lf-00-model-v1
            fields:
              model_name: HULUBUL_LLM_MODEL
              openai_api_base: HULUBUL_LLM_BASE_URL
              api_key: HULUBUL_LLM_API_KEY
    """).strip()


def test_normalize_preserves_node_edge_order(sample_langflow_flow: dict[str, Any]) -> None:
    """Test that normalization preserves node/edge array order."""
    from scripts.normalize_langflow_flows import normalize_flow_json

    normalized = normalize_flow_json(sample_langflow_flow)

    # Verify order is preserved
    assert [n["id"] for n in normalized["data"]["nodes"]] == ["node1-id", "node2-id"]
    assert normalized["data"]["edges"][0]["source"] == "node1-id"


def test_normalize_sorts_keys_at_each_level(sample_langflow_flow: dict[str, Any]) -> None:
    """Test that all JSON keys are sorted alphabetically at each level."""
    from scripts.normalize_langflow_flows import normalize_flow_json

    normalized = normalize_flow_json(sample_langflow_flow)

    def verify_keys_sorted(obj: Any, path: str = "") -> None:
        """Recursively verify all dict keys are sorted."""
        if isinstance(obj, dict):
            keys = list(obj.keys())
            sorted_keys = sorted(keys)
            assert keys == sorted_keys, f"Keys not sorted at {path}: {keys}"
            for key, value in obj.items():
                verify_keys_sorted(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                verify_keys_sorted(item, f"{path}[{idx}]")

    verify_keys_sorted(normalized)


def test_normalize_idempotent(sample_langflow_flow: dict[str, Any]) -> None:
    """Test that normalizing twice produces identical output (idempotence)."""
    from scripts.normalize_langflow_flows import normalize_flow_json

    first_pass = normalize_flow_json(sample_langflow_flow)
    second_pass = normalize_flow_json(first_pass)

    first_json = json.dumps(first_pass, sort_keys=True, indent=2)
    second_json = json.dumps(second_pass, sort_keys=True, indent=2)

    assert first_json == second_json, "Normalization is not idempotent"

    # Also verify SHA-256 hashes are identical
    first_hash = hashlib.sha256(first_json.encode()).hexdigest()
    second_hash = hashlib.sha256(second_json.encode()).hexdigest()
    assert first_hash == second_hash


def test_normalize_uses_2_space_indentation(sample_langflow_flow: dict[str, Any]) -> None:
    """Test that normalized JSON uses 2-space indentation."""
    from scripts.normalize_langflow_flows import normalize_to_json_string

    json_string = normalize_to_json_string(sample_langflow_flow)

    # Check for 2-space indentation (lines starting with exactly 2, 4, 6 spaces)
    lines = json_string.split("\n")
    for line in lines:
        if line and line[0] == " ":
            spaces = len(line) - len(line.lstrip())
            # Each indent level should be exactly 2 spaces
            assert spaces % 2 == 0, f"Indentation not multiple of 2: {line!r}"


def test_normalize_uses_lf_line_endings(sample_langflow_flow: dict[str, Any]) -> None:
    """Test that normalized JSON uses LF line endings."""
    from scripts.normalize_langflow_flows import normalize_to_json_string

    json_string = normalize_to_json_string(sample_langflow_flow)

    # Should contain LF, not CRLF
    assert "\r\n" not in json_string, "JSON uses CRLF instead of LF"
    assert "\n" in json_string, "JSON should contain LF line endings"


@pytest.mark.parametrize(
    "input_json,expected_model_name,expected_base_url,expected_api_key",
    [
        pytest.param(
            {
                "data": {
                    "nodes": [
                        {
                            "id": "OpenAIModel-hlb-lf-00-model-v1",
                            "data": {
                                "model_name": "gpt-4",
                                "openai_api_base": "https://api.openai.com/v1",
                                "api_key": "REDACTED-TEST-API-KEY-LONG",
                            },
                        }
                    ],
                    "edges": [],
                }
            },
            "{{ HULUBUL_LLM_MODEL }}",
            "{{ HULUBUL_LLM_BASE_URL }}",
            "{{ HULUBUL_LLM_API_KEY }}",
            id="replaces_openai_credentials",
        ),
    ],
)
def test_restore_manifest_variables(
    sample_flow_with_env_vars: dict[str, Any],
    input_json: dict[str, Any],
    expected_model_name: str,
    expected_base_url: str,
    expected_api_key: str,
) -> None:
    """Test that manifest-allowlisted variable names are restored."""
    from scripts.normalize_langflow_flows import normalize_flow_json_with_manifest

    manifest_bindings = {
        "OpenAIModel-hlb-lf-00-model-v1": {
            "model_name": "HULUBUL_LLM_MODEL",
            "openai_api_base": "HULUBUL_LLM_BASE_URL",
            "api_key": "HULUBUL_LLM_API_KEY",
        }
    }

    normalized = normalize_flow_json_with_manifest(input_json, manifest_bindings)

    # Verify the hardcoded values are replaced with variable references
    model_node = normalized["data"]["nodes"][0]
    assert model_node["data"]["model_name"] == expected_model_name
    assert model_node["data"]["openai_api_base"] == expected_base_url
    assert model_node["data"]["api_key"] == expected_api_key


def test_reject_undeclared_runtime_variable(sample_flow_with_env_vars: dict[str, Any]) -> None:
    """Restoring a variable name outside the approved allowlist must raise."""
    from scripts.normalize_langflow_flows import (
        NormalizationError,
        normalize_flow_json_with_manifest,
    )

    manifest_bindings = {
        "OpenAIModel-hlb-lf-00-model-v1": {
            "api_key": "ARBITRARY_UNDECLARED_SECRET",
        }
    }

    with pytest.raises(NormalizationError, match="undeclared runtime variable"):
        normalize_flow_json_with_manifest(sample_flow_with_env_vars, manifest_bindings)


def test_check_mode_detects_idempotence() -> None:
    """Test that --check mode correctly detects idempotence."""
    from scripts.normalize_langflow_flows import check_file_idempotence

    with tempfile.TemporaryDirectory() as tmpdir:
        flow_path = Path(tmpdir) / "test_flow.json"

        # Create an unsorted flow
        unsorted_flow = {
            "z_field": "last",
            "a_field": "first",
            "data": {"nodes": [], "edges": []},
        }

        flow_path.write_text(json.dumps(unsorted_flow, indent=2))

        # First check should detect it's not normalized
        is_normalized = check_file_idempotence(flow_path)
        assert not is_normalized

        # Now write the normalized version
        from scripts.normalize_langflow_flows import normalize_to_json_string

        normalized_str = normalize_to_json_string(unsorted_flow)
        flow_path.write_text(normalized_str)

        # Second check should pass
        is_normalized = check_file_idempotence(flow_path)
        assert is_normalized


def test_cli_check_flag_with_file() -> None:
    """Test CLI --check flag functionality."""
    import sys

    from scripts.normalize_langflow_flows import main

    with tempfile.TemporaryDirectory() as tmpdir:
        flow_path = Path(tmpdir) / "test_flow.json"

        # Create an unnormalized flow
        unsorted_flow = {
            "z_field": "last",
            "a_field": "first",
            "data": {"nodes": [], "edges": []},
        }

        flow_path.write_text(json.dumps(unsorted_flow, indent=2))

        # Run with --check flag (should exit non-zero for un-normalized file)
        old_argv = sys.argv
        try:
            sys.argv = ["normalize_langflow_flows.py", "--check", str(flow_path)]
            exit_code = main()
            # Unnormalized file should return non-zero
            assert exit_code != 0
        finally:
            sys.argv = old_argv


def test_cli_output_flag() -> None:
    """Test CLI --output flag to write normalized flows to directory."""
    import sys

    from scripts.normalize_langflow_flows import main

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / "output"

        input_path.mkdir()
        output_path.mkdir()

        flow_file = input_path / "test_flow.json"
        unsorted_flow = {"z": 1, "a": 2, "data": {"nodes": [], "edges": []}}
        flow_file.write_text(json.dumps(unsorted_flow))

        old_argv = sys.argv
        try:
            sys.argv = [
                "normalize_langflow_flows.py",
                "--output",
                str(output_path),
                str(flow_file),
            ]
            exit_code = main()
            assert exit_code == 0

            # Verify normalized file was written
            output_file = output_path / "test_flow.json"
            assert output_file.exists()

            # Verify it's normalized
            written_content = output_file.read_text()
            written_json = json.loads(written_content)
            keys = list(written_json.keys())
            assert keys == sorted(keys), "Output file is not normalized"
        finally:
            sys.argv = old_argv
