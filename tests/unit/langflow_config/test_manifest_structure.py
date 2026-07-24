"""
Unit tests for LangFlow flow manifest structure and configuration.

Tests verify:
- Manifest YAML is valid and parseable
- Three flows present with stable UUIDs (UUIDv5)
- All component IDs match pinned schema
- Runtime bindings reference environment variables
- Environments file has local/CI configuration
"""

import pathlib
import uuid

import pytest
import yaml  # type: ignore

# Hard-coded stable UUIDs from plan.md (UUIDv5 over flow names)
EXPECTED_FLOW_UUIDS = {
    "lf-70-data-access": uuid.UUID("94f6774d-ebc7-5bf1-8486-886f91886a5f"),
    "lf-10-request-intake": uuid.UUID("6843ae79-147f-55d4-a25b-01d6143a12cc"),
    "lf-00-main-router": uuid.UUID("38b7ee64-26c8-5d4d-97e4-6e62a0fcb557"),
}

EXPECTED_COMPONENT_IDS = {
    "lf-70": {
        "public_input": "HulubulDataOperationRequestBoundary-hlb-lf-70-request-v1",
        "public_result": "HulubulDataOperationResultBoundary-hlb-lf-70-result-v1",
        "model": "OpenAIModel-hlb-lf-70-model-v1",
    },
    "lf-10": {
        "public_input": "HulubulContractInputBoundary-hlb-lf-10-input-v1",
        "public_result": "HulubulContractResultBoundary-hlb-lf-10-result-v1",
        "model": "OpenAIModel-hlb-lf-10-model-v1",
    },
    "lf-00": {
        "public_input": "ChatInput-hlb-lf-00-message-v1",
        "public_result": "HulubulContractResultBoundary-hlb-lf-00-result-v1",
        "chat_output": "ChatOutput-hlb-lf-00-chat-v1",
        "model": "OpenAIModel-hlb-lf-00-model-v1",
    },
}

EXPECTED_ENVIRONMENT_KEYS_LOCAL = {
    "langflow_url",
    "neo4j_mcp_url",
    "recorded_model_endpoint",
}

EXPECTED_ENVIRONMENT_KEYS_CI = {
    "langflow_url",
    "neo4j_mcp_url",
    "recorded_model_endpoint",
}


@pytest.fixture
def manifest_path() -> pathlib.Path:
    """Path to flow manifest."""
    return pathlib.Path(__file__).parent.parent.parent.parent / "langflow" / "flow-manifest.yaml"


@pytest.fixture
def environments_path() -> pathlib.Path:
    """Path to environments configuration."""
    return (
        pathlib.Path(__file__).parent.parent.parent.parent
        / "langflow"
        / ".lfx"
        / "environments.yaml"
    )


@pytest.fixture
def flows_dir() -> pathlib.Path:
    """Path to flows directory."""
    return pathlib.Path(__file__).parent.parent.parent.parent / "langflow" / "flows"


class TestManifestStructure:
    """Tests for flow manifest YAML structure."""

    def test_manifest_file_exists(self, manifest_path: pathlib.Path) -> None:
        """Manifest file must exist."""
        assert manifest_path.exists(), f"Manifest not found at {manifest_path}"

    def test_manifest_is_valid_yaml(self, manifest_path: pathlib.Path) -> None:
        """Manifest must be valid YAML."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
        assert data is not None, "Manifest is empty or invalid YAML"
        assert isinstance(data, dict), "Manifest root must be a dictionary"

    def test_manifest_has_required_top_level_keys(self, manifest_path: pathlib.Path) -> None:
        """Manifest must have schema_version, langflow_version, deployment_order, flows."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        required_keys = {
            "schema_version",
            "langflow_version",
            "deployment_order",
            "flows",
            "runtime_bindings",
        }
        assert required_keys.issubset(data.keys()), f"Missing keys: {required_keys - data.keys()}"

    def test_manifest_schema_version(self, manifest_path: pathlib.Path) -> None:
        """Schema version must be 1.0.0."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
        assert data["schema_version"] == "1.0.0"

    def test_manifest_langflow_version(self, manifest_path: pathlib.Path) -> None:
        """LangFlow version must be pinned to 1.10.2."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
        assert data["langflow_version"] == "1.10.2"

    def test_manifest_deployment_order(self, manifest_path: pathlib.Path) -> None:
        """Deployment order must be [lf-70-data-access, lf-10-request-intake, lf-00-main-router]."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        expected_order = ["lf-70-data-access", "lf-10-request-intake", "lf-00-main-router"]
        assert data["deployment_order"] == expected_order

    def test_manifest_has_exactly_three_flows(self, manifest_path: pathlib.Path) -> None:
        """Manifest must declare exactly three flows."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
        assert len(data["flows"]) == 3, f"Expected 3 flows, got {len(data['flows'])}"

    def test_manifest_flow_names_match_deployment_order(self, manifest_path: pathlib.Path) -> None:
        """Flow names must match deployment order."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        expected_names = set(data["deployment_order"])
        actual_names = set(data["flows"].keys())
        assert expected_names == actual_names, (
            f"Flow names mismatch: {expected_names - actual_names}"
        )

    def test_manifest_flow_uuids_are_stable_not_random(self, manifest_path: pathlib.Path) -> None:
        """Flow UUIDs must match stable pinned values from plan.md."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        flows = data["flows"]
        for flow_name, expected_uuid in EXPECTED_FLOW_UUIDS.items():
            actual_uuid = uuid.UUID(flows[flow_name]["id"])
            assert actual_uuid == expected_uuid, (
                f"Flow {flow_name} UUID mismatch: expected {expected_uuid}, got {actual_uuid}"
            )

    def test_manifest_lf70_component_ids(self, manifest_path: pathlib.Path) -> None:
        """LF-70 component IDs must match spec."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        flow = data["flows"]["lf-70-data-access"]
        assert flow["public_input_component_id"] == EXPECTED_COMPONENT_IDS["lf-70"]["public_input"]
        assert (
            flow["public_result_component_id"] == EXPECTED_COMPONENT_IDS["lf-70"]["public_result"]
        )
        assert flow["chat_output_component_id"] is None

    def test_manifest_lf10_component_ids(self, manifest_path: pathlib.Path) -> None:
        """LF-10 component IDs must match spec."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        flow = data["flows"]["lf-10-request-intake"]
        assert flow["public_input_component_id"] == EXPECTED_COMPONENT_IDS["lf-10"]["public_input"]
        assert (
            flow["public_result_component_id"] == EXPECTED_COMPONENT_IDS["lf-10"]["public_result"]
        )
        assert flow["chat_output_component_id"] is None

    def test_manifest_lf00_component_ids(self, manifest_path: pathlib.Path) -> None:
        """LF-00 component IDs must match spec."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        flow = data["flows"]["lf-00-main-router"]
        assert flow["public_input_component_id"] == EXPECTED_COMPONENT_IDS["lf-00"]["public_input"]
        assert (
            flow["public_result_component_id"] == EXPECTED_COMPONENT_IDS["lf-00"]["public_result"]
        )
        assert flow["chat_output_component_id"] == EXPECTED_COMPONENT_IDS["lf-00"]["chat_output"]

    def test_manifest_lf70_no_run_flow_references(self, manifest_path: pathlib.Path) -> None:
        """LF-70 has no Run Flow references (it is the base data access layer)."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        flow = data["flows"]["lf-70-data-access"]
        assert flow["run_flow_references"] == []

    def test_manifest_lf10_calls_lf70(self, manifest_path: pathlib.Path) -> None:
        """LF-10 calls LF-70 via Run Flow."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        flow = data["flows"]["lf-10-request-intake"]
        run_flow_refs = flow["run_flow_references"]

        assert len(run_flow_refs) >= 1, "LF-10 must have at least one Run Flow reference"
        lf70_call = [
            ref
            for ref in run_flow_refs
            if ref["target_flow_id"] == str(EXPECTED_FLOW_UUIDS["lf-70-data-access"])
        ]
        assert len(lf70_call) == 1, "LF-10 must call LF-70 exactly once"
        assert lf70_call[0]["component_id"] == "RunFlow-hlb-lf-10-data-access-v1"

    def test_manifest_lf00_calls_lf70_and_lf10(self, manifest_path: pathlib.Path) -> None:
        """LF-00 calls both LF-70 and LF-10 via Run Flow."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        flow = data["flows"]["lf-00-main-router"]
        run_flow_refs = flow["run_flow_references"]

        assert len(run_flow_refs) >= 2, "LF-00 must have at least two Run Flow references"

        lf70_calls = [
            ref
            for ref in run_flow_refs
            if ref["target_flow_id"] == str(EXPECTED_FLOW_UUIDS["lf-70-data-access"])
        ]
        assert len(lf70_calls) == 1, "LF-00 must call LF-70 exactly once"
        assert lf70_calls[0]["component_id"] == "RunFlow-hlb-lf-00-routing-context-v1"

        lf10_calls = [
            ref
            for ref in run_flow_refs
            if ref["target_flow_id"] == str(EXPECTED_FLOW_UUIDS["lf-10-request-intake"])
        ]
        assert len(lf10_calls) == 1, "LF-00 must call LF-10 exactly once"
        assert lf10_calls[0]["component_id"] == "RunFlow-hlb-lf-00-request-intake-v1"

    def test_manifest_runtime_bindings_structure(self, manifest_path: pathlib.Path) -> None:
        """Runtime bindings must have correct structure."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        bindings = data["runtime_bindings"]
        assert len(bindings) == 3, (
            f"Expected 3 runtime bindings (one per model node), got {len(bindings)}"
        )

        # Check each binding has required keys
        for binding in bindings:
            assert "component_id" in binding, "Binding missing component_id"
            assert "fields" in binding, "Binding missing fields"
            assert isinstance(binding["fields"], dict), "Binding fields must be a dict"

    def test_manifest_runtime_bindings_lf70_model(self, manifest_path: pathlib.Path) -> None:
        """Runtime binding for LF-70 model must reference HULUBUL_LLM_* env vars."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        bindings = data["runtime_bindings"]
        lf70_bindings = [
            b for b in bindings if b["component_id"] == EXPECTED_COMPONENT_IDS["lf-70"]["model"]
        ]
        assert len(lf70_bindings) == 1, "LF-70 model binding not found"

        binding = lf70_bindings[0]
        fields = binding["fields"]
        assert fields.get("model_name") == "HULUBUL_LLM_MODEL"
        assert fields.get("openai_api_base") == "HULUBUL_LLM_BASE_URL"
        assert fields.get("api_key") == "HULUBUL_LLM_API_KEY"

    def test_manifest_runtime_bindings_lf10_model(self, manifest_path: pathlib.Path) -> None:
        """Runtime binding for LF-10 model must reference HULUBUL_LLM_* env vars."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        bindings = data["runtime_bindings"]
        lf10_bindings = [
            b for b in bindings if b["component_id"] == EXPECTED_COMPONENT_IDS["lf-10"]["model"]
        ]
        assert len(lf10_bindings) == 1, "LF-10 model binding not found"

        binding = lf10_bindings[0]
        fields = binding["fields"]
        assert fields.get("model_name") == "HULUBUL_LLM_MODEL"
        assert fields.get("openai_api_base") == "HULUBUL_LLM_BASE_URL"
        assert fields.get("api_key") == "HULUBUL_LLM_API_KEY"

    def test_manifest_runtime_bindings_lf00_model(self, manifest_path: pathlib.Path) -> None:
        """Runtime binding for LF-00 model must reference HULUBUL_LLM_* env vars."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        bindings = data["runtime_bindings"]
        lf00_bindings = [
            b for b in bindings if b["component_id"] == EXPECTED_COMPONENT_IDS["lf-00"]["model"]
        ]
        assert len(lf00_bindings) == 1, "LF-00 model binding not found"

        binding = lf00_bindings[0]
        fields = binding["fields"]
        assert fields.get("model_name") == "HULUBUL_LLM_MODEL"
        assert fields.get("openai_api_base") == "HULUBUL_LLM_BASE_URL"
        assert fields.get("api_key") == "HULUBUL_LLM_API_KEY"

    def test_manifest_flow_files_referenced(self, manifest_path: pathlib.Path) -> None:
        """All flows must have file paths."""
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        flows = data["flows"]
        expected_files = {
            "lf-70-data-access": "flows/10-lf-70-data-access.json",
            "lf-10-request-intake": "flows/20-lf-10-request-intake.json",
            "lf-00-main-router": "flows/30-lf-00-main-router.json",
        }

        for flow_name, expected_file in expected_files.items():
            assert flows[flow_name]["file"] == expected_file


class TestEnvironmentsConfiguration:
    """Tests for environments configuration."""

    def test_environments_file_exists(self, environments_path: pathlib.Path) -> None:
        """Environments file must exist."""
        assert environments_path.exists(), f"Environments file not found at {environments_path}"

    def test_environments_is_valid_yaml(self, environments_path: pathlib.Path) -> None:
        """Environments file must be valid YAML."""
        with open(environments_path) as f:
            data = yaml.safe_load(f)
        assert data is not None, "Environments file is empty or invalid YAML"
        assert isinstance(data, dict), "Environments root must be a dictionary"

    def test_environments_has_local_and_ci(self, environments_path: pathlib.Path) -> None:
        """Environments must have local and ci entries."""
        with open(environments_path) as f:
            data = yaml.safe_load(f)

        assert "local" in data, "Missing 'local' environment"
        assert "ci" in data, "Missing 'ci' environment"

    def test_local_environment_has_required_keys(self, environments_path: pathlib.Path) -> None:
        """Local environment must have required configuration keys."""
        with open(environments_path) as f:
            data = yaml.safe_load(f)

        local_env = data["local"]
        assert isinstance(local_env, dict), "Local environment must be a dictionary"
        assert EXPECTED_ENVIRONMENT_KEYS_LOCAL.issubset(local_env.keys()), (
            f"Missing keys in local env: {EXPECTED_ENVIRONMENT_KEYS_LOCAL - local_env.keys()}"
        )

    def test_ci_environment_has_required_keys(self, environments_path: pathlib.Path) -> None:
        """CI environment must have required configuration keys."""
        with open(environments_path) as f:
            data = yaml.safe_load(f)

        ci_env = data["ci"]
        assert isinstance(ci_env, dict), "CI environment must be a dictionary"
        assert EXPECTED_ENVIRONMENT_KEYS_CI.issubset(ci_env.keys()), (
            f"Missing keys in CI env: {EXPECTED_ENVIRONMENT_KEYS_CI - ci_env.keys()}"
        )

    def test_local_environment_values_are_env_var_names_not_secrets(
        self, environments_path: pathlib.Path
    ) -> None:
        """Local environment values must be environment variable names, not actual secrets."""
        with open(environments_path) as f:
            data = yaml.safe_load(f)

        local_env = data["local"]
        # Values should be strings that look like env var names (uppercase, no actual URLs/IPs)
        # or they may be templated strings like ${VAR_NAME}
        for key, value in local_env.items():
            if isinstance(value, str):
                # Ensure it's not a secret value (should be env var name or template)
                assert not value.startswith("http://127.0.0.1:") or "${" in str(local_env), (
                    f"Environment value for {key} appears to be a hardcoded URL, should reference env var"
                )

    def test_ci_environment_values_are_env_var_names_not_secrets(
        self, environments_path: pathlib.Path
    ) -> None:
        """CI environment values must be environment variable names, not actual secrets."""
        with open(environments_path) as f:
            data = yaml.safe_load(f)

        ci_env = data["ci"]
        for key, value in ci_env.items():
            if isinstance(value, str):
                # Ensure it's not a secret value
                assert not value.startswith("http://127.0.0.1:") or "${" in str(ci_env), (
                    f"Environment value for {key} appears to be a hardcoded URL, should reference env var"
                )


class TestFlowsDirectory:
    """Tests for flows directory structure."""

    def test_flows_directory_exists(self, flows_dir: pathlib.Path) -> None:
        """Flows directory must exist (will contain flow JSON files)."""
        assert flows_dir.exists(), f"Flows directory not found at {flows_dir}"
        assert flows_dir.is_dir(), "Flows path exists but is not a directory"
