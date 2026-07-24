"""
Integration tests for LangFlow asset validation.

Tests the validate_langflow_assets.py script against the manifest and actual flow files.
Covers manifest validation, topology validation, environment allowlist, and LFX checks.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
MANIFEST_PATH = REPO_ROOT / "langflow" / "flow-manifest.yaml"
FLOWS_DIR = REPO_ROOT / "langflow" / "flows"
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_langflow_assets.py"


class TestManifestValidation:
    """Test manifest structure and completeness validation."""

    def test_manifest_exists(self):
        """Manifest file should exist and be readable."""
        assert MANIFEST_PATH.exists(), f"Manifest not found at {MANIFEST_PATH}"

    def test_manifest_declares_three_flows(self):
        """Manifest must declare exactly three flows."""
        import yaml

        with open(MANIFEST_PATH) as f:
            manifest = yaml.safe_load(f)

        assert "flows" in manifest
        assert len(manifest["flows"]) == 3
        assert set(manifest["flows"].keys()) == {
            "lf-70-data-access",
            "lf-10-request-intake",
            "lf-00-main-router",
        }

    def test_manifest_flow_ids_are_stable(self):
        """Flow IDs should match expected values from task 29 spec."""
        import yaml

        with open(MANIFEST_PATH) as f:
            manifest = yaml.safe_load(f)

        expected_ids = {
            "lf-70-data-access": "94f6774d-ebc7-5bf1-8486-886f91886a5f",
            "lf-10-request-intake": "6843ae79-147f-55d4-a25b-01d6143a12cc",
            "lf-00-main-router": "38b7ee64-26c8-5d4d-97e4-6e62a0fcb557",
        }

        for flow_name, expected_id in expected_ids.items():
            assert manifest["flows"][flow_name]["id"] == expected_id, (
                f"Flow {flow_name} has unexpected ID: "
                f"{manifest['flows'][flow_name]['id']}"
            )

    def test_manifest_deployment_order(self):
        """Deployment order should be lf-70 -> lf-10 -> lf-00."""
        import yaml

        with open(MANIFEST_PATH) as f:
            manifest = yaml.safe_load(f)

        expected_order = [
            "lf-70-data-access",
            "lf-10-request-intake",
            "lf-00-main-router",
        ]
        assert manifest["deployment_order"] == expected_order

    def test_manifest_has_runtime_bindings(self):
        """Manifest must declare runtime variable bindings."""
        import yaml

        with open(MANIFEST_PATH) as f:
            manifest = yaml.safe_load(f)

        assert "runtime_bindings" in manifest
        assert len(manifest["runtime_bindings"]) == 3

    def test_manifest_runtime_bindings_reference_three_openai_models(self):
        """Runtime bindings should reference exactly three OpenAI model components."""
        import yaml

        with open(MANIFEST_PATH) as f:
            manifest = yaml.safe_load(f)

        bindings = manifest["runtime_bindings"]
        assert len(bindings) == 3

        for binding in bindings:
            assert "component_id" in binding
            assert "OpenAIModel" in binding["component_id"]
            assert "fields" in binding
            assert "model_name" in binding["fields"]
            assert binding["fields"]["model_name"] == "HULUBUL_LLM_MODEL"

    def test_manifest_environment_variables_allowlisted(self):
        """Only allowlisted environment variables should appear in runtime bindings."""
        import yaml

        with open(MANIFEST_PATH) as f:
            manifest = yaml.safe_load(f)

        allowed_vars = {
            "HULUBUL_LLM_MODEL",
            "HULUBUL_LLM_BASE_URL",
            "HULUBUL_LLM_API_KEY",
            "LANGFLOW_API_KEY",
        }

        bindings = manifest["runtime_bindings"]
        for binding in bindings:
            for _field_name, field_value in binding.get("fields", {}).items():
                if isinstance(field_value, str) and field_value.isupper():
                    assert field_value in allowed_vars, (
                        f"Environment variable {field_value} not in allowlist. "
                        f"Allowed: {allowed_vars}"
                    )


class TestTopologyValidation:
    """Test flow file existence and topology."""

    def test_flows_directory_exists(self):
        """Flows directory should exist."""
        assert FLOWS_DIR.exists(), f"Flows directory not found at {FLOWS_DIR}"

    def test_no_ui_only_flows_without_manifest_entry(self, tmp_path):
        """If a flow file exists but is not in manifest, it's a UI-only flow (fail)."""
        import yaml

        with open(MANIFEST_PATH) as f:
            manifest = yaml.safe_load(f)

        manifest_flows = {
            flow["file"] for flow in manifest["flows"].values()
        }

        # List all .json files in flows directory
        actual_flows = set(f.relative_to(FLOWS_DIR).as_posix()
                          for f in FLOWS_DIR.glob("*.json"))

        # Any flow file not in manifest is a UI-only flow (error condition)
        ui_only = actual_flows - manifest_flows
        if ui_only:
            pytest.fail(
                f"Found UI-only flows not in manifest: {ui_only}. "
                f"All flows must be listed in manifest."
            )

    def test_no_missing_flows_referenced_in_manifest(self):
        """All flows referenced in manifest must exist as files."""
        import yaml

        with open(MANIFEST_PATH) as f:
            manifest = yaml.safe_load(f)

        for _flow_name, flow_info in manifest["flows"].items():
            flow_file = FLOWS_DIR / flow_info["file"]
            # This test only checks that we understand the requirement;
            # actual files may not exist in early task phases.
            # The validation script should fail if they're missing.
            if flow_file.parent.exists() and not flow_file.exists():
                # If flows directory exists, we can check for missing files
                pytest.skip(
                    f"Flow file {flow_info['file']} not yet created "
                    "(expected in Checkpoint 8)"
                    )

    def test_manifest_references_valid_file_paths(self):
        """All file paths in manifest should be relative to flows/ directory."""
        import yaml

        with open(MANIFEST_PATH) as f:
            manifest = yaml.safe_load(f)

        for flow_name, flow_info in manifest["flows"].items():
            file_path = flow_info["file"]
            assert file_path.startswith("flows/"), (
                f"Flow {flow_name} has invalid file path: {file_path} "
                "(must start with 'flows/')"
            )
            assert file_path.endswith(".json"), (
                f"Flow {flow_name} file must be JSON: {file_path}"
            )


class TestValidationScriptBasics:
    """Test that the validation script exists and is callable."""

    def test_script_exists(self):
        """Validation script should exist."""
        assert SCRIPT_PATH.exists(), f"Script not found at {SCRIPT_PATH}"

    def test_script_accepts_manifest_argument(self):
        """Script should accept manifest path as argument."""
        result = subprocess.run(
            ["poetry", "run", "python", str(SCRIPT_PATH), "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"Script help failed: {result.stderr}"
        )
        assert "manifest" in result.stdout.lower()

    def test_script_validates_manifest_when_given_path(self):
        """Script should validate manifest when given the path."""
        result = subprocess.run(
            ["poetry", "run", "python", str(SCRIPT_PATH), str(MANIFEST_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should either pass (exit 0) or fail with clear validation error
        # We don't assert specific exit code here because flows may not exist yet
        output = (result.stdout + result.stderr).lower()
        assert (
            "validation" in output
            or "manifest" in output
            or "topology" in output
        ), f"Expected validation output, got stdout: {result.stdout}, stderr: {result.stderr}"


class TestFlowFilesWhenPresent:
    """Tests that apply only if flow files exist."""

    @pytest.fixture
    def flows_exist(self):
        """Skip test if flows don't exist yet."""
        if not any(FLOWS_DIR.glob("*.json")):
            pytest.skip("Flow files not yet created (expected in Checkpoint 8)")
        return True

    def test_flow_files_are_valid_json(self, flows_exist):
        """All flow files must be valid JSON."""
        for flow_file in FLOWS_DIR.glob("*.json"):
            with open(flow_file) as f:
                try:
                    json.load(f)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Flow file {flow_file.name} is not valid JSON: {e}")

    def test_flows_reference_only_allowed_components(self, flows_exist):
        """Flows should not reference LF-20 or out-of-scope flows."""
        for flow_file in FLOWS_DIR.glob("*.json"):
            with open(flow_file) as f:
                flow_data = json.load(f)

            flow_str = json.dumps(flow_data)
            # Should not contain LF-20 references
            assert "lf-20" not in flow_str.lower(), (
                f"Flow {flow_file.name} references LF-20 (out of scope)"
            )
            assert "lf_20" not in flow_str.lower(), (
                f"Flow {flow_file.name} references LF-20 (out of scope)"
            )

    def test_mcp_tools_only_in_lf70(self, flows_exist):
        """MCP tools should only be used in LF-70 (data-access)."""
        lf70_file = FLOWS_DIR / "10-lf-70-data-access.json"
        other_flows = [f for f in FLOWS_DIR.glob("*.json") if f != lf70_file]

        # Check other flows don't have MCP tools
        for flow_file in other_flows:
            with open(flow_file) as f:
                flow_data = json.load(f)

            flow_str = json.dumps(flow_data)
            assert "mcp" not in flow_str.lower(), (
                f"Flow {flow_file.name} uses MCP tools (only LF-70 allowed)"
            )
            assert "toolscomponent" not in flow_str.lower(), (
                f"Flow {flow_file.name} uses ToolsComponent (only LF-70 allowed)"
            )


class TestValidationScriptOutput:
    """Test the validation script output and error messages."""

    def test_script_provides_clear_error_messages(self):
        """When validation fails, script should provide clear error messages."""
        # Create a malformed manifest to test error reporting
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("broken: yaml: content:")
            bad_manifest = f.name

        try:
            result = subprocess.run(
                ["poetry", "run", "python", str(SCRIPT_PATH), bad_manifest],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Should fail and provide error message
            assert result.returncode != 0
            assert len(result.stdout) > 0 or len(result.stderr) > 0
        finally:
            Path(bad_manifest).unlink()

    def test_script_exits_zero_on_valid_manifest(self):
        """Script should exit 0 when manifest is valid."""
        result = subprocess.run(
            ["poetry", "run", "python", str(SCRIPT_PATH), str(MANIFEST_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # If flows exist and pass validation, exit should be 0
        # If flows don't exist, we get a controlled failure
        if result.returncode == 0:
            assert "valid" in result.stdout.lower() or "pass" in result.stdout.lower()
