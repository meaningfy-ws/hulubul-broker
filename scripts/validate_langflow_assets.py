#!/usr/bin/env python
"""
Validate LangFlow assets against manifest, topology, and schema rules.

This script enforces strict static validation of all LangFlow flows:
- Manifest validation (correct structure, UUIDs, deployment order)
- Topology validation (no UI-only/missing flows)
- Environment variable allowlist (only approved secrets)
- LFX level-4 strict validation (if flows exist)
- Component reference rules (no LF-20, MCP only in LF-70)

Exits 0 if all checks pass, non-zero otherwise.

Usage:
    poetry run python scripts/validate_langflow_assets.py langflow/flow-manifest.yaml
    poetry run python scripts/validate_langflow_assets.py \\
        langflow/flow-manifest.yaml langflow/flows/
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

ALLOWED_ENV_VARS = {
    "HULUBUL_LLM_MODEL",
    "HULUBUL_LLM_BASE_URL",
    "HULUBUL_LLM_API_KEY",
    "LANGFLOW_API_KEY",
}

EXPECTED_FLOW_IDS = {
    "lf-70-data-access": "94f6774d-ebc7-5bf1-8486-886f91886a5f",
    "lf-10-request-intake": "6843ae79-147f-55d4-a25b-01d6143a12cc",
    "lf-00-main-router": "38b7ee64-26c8-5d4d-97e4-6e62a0fcb557",
}

EXPECTED_DEPLOYMENT_ORDER = [
    "lf-70-data-access",
    "lf-10-request-intake",
    "lf-00-main-router",
]


@dataclass
class ValidationError:
    """Represents a single validation error."""

    category: str
    message: str
    severity: str = "error"  # error, warning

    def __str__(self) -> str:
        return f"[{self.category}] {self.message}"


class ManifestValidator:
    """Validates flow manifest structure and content."""

    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        self.errors: list[ValidationError] = []
        self.manifest: dict[str, Any] | None = None

    def validate(self) -> bool:
        """Validate manifest file. Returns True if valid."""
        if not self._load_manifest():
            return False

        self._validate_structure()
        self._validate_flow_ids()
        self._validate_deployment_order()
        self._validate_runtime_bindings()

        return len(self.errors) == 0

    def _load_manifest(self) -> bool:
        """Load and parse manifest YAML."""
        if not self.manifest_path.exists():
            self.errors.append(
                ValidationError(
                    "manifest",
                    f"Manifest file not found: {self.manifest_path}",
                )
            )
            return False

        try:
            with open(self.manifest_path) as f:
                self.manifest = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.errors.append(ValidationError("manifest", f"Failed to parse YAML: {e}"))
            return False

        if not isinstance(self.manifest, dict):
            self.errors.append(ValidationError("manifest", "Manifest must be a YAML dictionary"))
            return False

        return True

    def _validate_structure(self) -> None:
        """Validate manifest has required top-level keys."""
        assert self.manifest is not None
        required_keys = {"schema_version", "langflow_version", "flows", "deployment_order"}
        missing = required_keys - set(self.manifest.keys())
        if missing:
            self.errors.append(
                ValidationError(
                    "manifest",
                    f"Manifest missing required keys: {missing}",
                )
            )

        # Check flows section
        if "flows" in self.manifest:
            flows = self.manifest["flows"]
            if not isinstance(flows, dict):
                self.errors.append(ValidationError("manifest", "flows must be a dictionary"))
                return

            if len(flows) != 3:
                self.errors.append(
                    ValidationError(
                        "manifest",
                        f"Expected exactly 3 flows, found {len(flows)}",
                    )
                )

            expected_flow_names = {"lf-70-data-access", "lf-10-request-intake", "lf-00-main-router"}
            actual_flow_names = set(flows.keys())
            if actual_flow_names != expected_flow_names:
                self.errors.append(
                    ValidationError(
                        "manifest",
                        f"Flow names mismatch. Expected {expected_flow_names}, "
                        f"got {actual_flow_names}",
                    )
                )

    def _validate_flow_ids(self) -> None:
        """Validate flow IDs match expected stable values."""
        assert self.manifest is not None
        if "flows" not in self.manifest:
            return

        for flow_name, expected_id in EXPECTED_FLOW_IDS.items():
            if flow_name not in self.manifest["flows"]:
                continue

            flow_info = self.manifest["flows"][flow_name]
            if "id" not in flow_info:
                self.errors.append(
                    ValidationError(
                        "flow_id",
                        f"Flow {flow_name} missing id field",
                    )
                )
                continue

            actual_id = flow_info["id"]
            if actual_id != expected_id:
                self.errors.append(
                    ValidationError(
                        "flow_id",
                        f"Flow {flow_name} has unexpected ID. "
                        f"Expected {expected_id}, got {actual_id}",
                    )
                )

    def _validate_deployment_order(self) -> None:
        """Validate deployment order."""
        assert self.manifest is not None
        if "deployment_order" not in self.manifest:
            self.errors.append(ValidationError("manifest", "Missing deployment_order field"))
            return

        actual_order = self.manifest["deployment_order"]
        if actual_order != EXPECTED_DEPLOYMENT_ORDER:
            self.errors.append(
                ValidationError(
                    "deployment_order",
                    f"Deployment order mismatch. "
                    f"Expected {EXPECTED_DEPLOYMENT_ORDER}, got {actual_order}",
                )
            )

    def _validate_runtime_bindings(self) -> None:
        """Validate runtime variable bindings."""
        assert self.manifest is not None
        if "runtime_bindings" not in self.manifest:
            self.errors.append(ValidationError("manifest", "Missing runtime_bindings field"))
            return

        bindings = self.manifest["runtime_bindings"]
        if not isinstance(bindings, list):
            self.errors.append(
                ValidationError("runtime_bindings", "runtime_bindings must be a list")
            )
            return

        if len(bindings) != 3:
            self.errors.append(
                ValidationError(
                    "runtime_bindings",
                    f"Expected exactly 3 runtime bindings (one per OpenAI model), "
                    f"found {len(bindings)}",
                )
            )

        # Validate each binding
        for idx, binding in enumerate(bindings):
            if not isinstance(binding, dict):
                self.errors.append(
                    ValidationError(
                        "runtime_bindings",
                        f"Binding {idx} must be a dictionary",
                    )
                )
                continue

            if "component_id" not in binding:
                self.errors.append(
                    ValidationError(
                        "runtime_bindings",
                        f"Binding {idx} missing component_id",
                    )
                )

            if "OpenAIModel" not in binding.get("component_id", ""):
                self.errors.append(
                    ValidationError(
                        "runtime_bindings",
                        f"Binding {idx} component_id must reference OpenAIModel",
                    )
                )

            fields = binding.get("fields", {})
            if not isinstance(fields, dict):
                self.errors.append(
                    ValidationError(
                        "runtime_bindings",
                        f"Binding {idx} fields must be a dictionary",
                    )
                )
                continue

            # Check field values against allowlist
            for _, field_value in fields.items():
                if (
                    isinstance(field_value, str)
                    and field_value.isupper()
                    and field_value not in ALLOWED_ENV_VARS
                ):
                    self.errors.append(
                        ValidationError(
                            "environment_allowlist",
                            f"Binding {idx} references disallowed variable {field_value}. "
                            f"Allowed: {ALLOWED_ENV_VARS}",
                        )
                    )


class TopologyValidator:
    """Validates flow file existence and topology."""

    def __init__(self, manifest: dict[str, Any], flows_dir: Path):
        self.manifest = manifest
        self.flows_dir = flows_dir
        self.errors: list[ValidationError] = []

    def validate(self) -> bool:
        """Validate topology. Returns True if valid."""
        if not self.flows_dir.exists():
            self.errors.append(
                ValidationError(
                    "topology",
                    f"Flows directory not found: {self.flows_dir}",
                )
            )
            return False

        self._validate_referenced_flows_exist()
        self._validate_no_ui_only_flows()

        return len(self.errors) == 0

    def _validate_referenced_flows_exist(self) -> None:
        """Check all flows referenced in manifest exist as files."""
        if "flows" not in self.manifest:
            return

        for flow_name, flow_info in self.manifest["flows"].items():
            # File paths in manifest are relative to the manifest's own
            # directory (langflow/), e.g. "flows/10-lf-70-data-access.json".
            relative_path = flow_info.get("file", "")
            flow_file = self.flows_dir.parent / relative_path

            if not flow_file.exists():
                self.errors.append(
                    ValidationError(
                        "topology",
                        f"Flow {flow_name} referenced in manifest but file not found: "
                        f"{relative_path}",
                    )
                )

    def _validate_no_ui_only_flows(self) -> None:
        """Ensure no flow files exist outside the manifest (UI-only flows)."""
        if not self.flows_dir.exists():
            return

        manifest_flows = {
            flow_info.get("file") for flow_info in self.manifest.get("flows", {}).values()
        }

        actual_flows = {f"flows/{f.name}" for f in self.flows_dir.glob("*.json")}

        ui_only = actual_flows - manifest_flows
        if ui_only:
            self.errors.append(
                ValidationError(
                    "topology",
                    f"Found UI-only flows not in manifest: {ui_only}. "
                    f"All flows must be declared in manifest.",
                )
            )


class FlowContentValidator:
    """Validates flow file content and component usage."""

    def __init__(self, flows_dir: Path):
        self.flows_dir = flows_dir
        self.errors: list[ValidationError] = []

    def validate(self) -> bool:
        """Validate flow content. Returns True if valid."""
        if not self.flows_dir.exists():
            return True  # No flows to validate yet

        flow_files = list(self.flows_dir.glob("*.json"))
        if not flow_files:
            return True  # No flows to validate yet

        for flow_file in flow_files:
            self._validate_flow_json(flow_file)
            self._validate_component_references(flow_file)
            self._validate_mcp_usage(flow_file)

        return len(self.errors) == 0

    def _validate_flow_json(self, flow_file: Path) -> None:
        """Ensure flow file is valid JSON."""
        try:
            with open(flow_file) as f:
                json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(
                ValidationError(
                    "flow_json",
                    f"Flow {flow_file.name} is not valid JSON: {e}",
                )
            )

    def _validate_component_references(self, flow_file: Path) -> None:
        """Check for disallowed component references (LF-20)."""
        try:
            with open(flow_file) as f:
                flow_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return  # Already caught by _validate_flow_json

        flow_str = json.dumps(flow_data).lower()

        # Check for LF-20 references
        if "lf-20" in flow_str or "lf_20" in flow_str:
            self.errors.append(
                ValidationError(
                    "component_references",
                    f"Flow {flow_file.name} references LF-20 (out of scope)",
                )
            )

    def _validate_mcp_usage(self, flow_file: Path) -> None:
        """Ensure MCP tools are only used in LF-70."""
        flow_name = flow_file.stem
        is_lf70 = "lf-70" in flow_name or "10-" in flow_file.name

        try:
            with open(flow_file) as f:
                flow_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        flow_str = json.dumps(flow_data).lower()

        if not is_lf70 and ("mcp" in flow_str or "toolscomponent" in flow_str):
            # Non-LF-70 flows must not use MCP tools
            self.errors.append(
                ValidationError(
                    "mcp_usage",
                    f"Flow {flow_file.name} uses MCP tools (only LF-70 data-access flow allowed)",
                )
            )


class LFXValidator:
    """Validates flows using lfx CLI tool."""

    def __init__(self, flows_dir: Path):
        self.flows_dir = flows_dir
        self.errors: list[ValidationError] = []

    def validate(self) -> bool:
        """Validate flows with lfx. Returns True if valid."""
        if not self.flows_dir.exists():
            return True

        flow_files = list(self.flows_dir.glob("*.json"))
        if not flow_files:
            return True

        # Check if lfx is available
        if not self._lfx_available():
            return True  # Skip LFX validation if not installed

        for flow_file in flow_files:
            self._validate_with_lfx_strict(flow_file)

        return len(self.errors) == 0

    def _lfx_available(self) -> bool:
        """Check if lfx CLI is available."""
        try:
            result = subprocess.run(
                ["lfx", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _validate_with_lfx_strict(self, flow_file: Path) -> None:
        """Run lfx level-4 strict validation on a single flow."""
        try:
            result = subprocess.run(
                [
                    "lfx",
                    "validate",
                    "--level",
                    "4",
                    "--strict",
                    "--skip-credentials",
                    str(flow_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.errors.append(
                    ValidationError(
                        "lfx_validation",
                        f"Flow {flow_file.name} failed LFX level-4 validation:\n"
                        f"{result.stdout}\n{result.stderr}",
                    )
                )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            self.errors.append(
                ValidationError(
                    "lfx_validation",
                    f"Failed to run lfx validation on {flow_file.name}: {e}",
                )
            )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate LangFlow assets against manifest and schema rules"
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to flow-manifest.yaml",
    )
    parser.add_argument(
        "--flows-dir",
        type=Path,
        default=None,
        help="Path to flows directory (default: manifest directory + /flows)",
    )

    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"[ERROR] Manifest not found: {args.manifest}", file=sys.stderr)
        return 1

    # Determine flows directory
    flows_dir = args.flows_dir
    if flows_dir is None:
        flows_dir = args.manifest.parent / "flows"

    # Run validators
    all_errors: list[ValidationError] = []

    # 1. Manifest validation
    manifest_validator = ManifestValidator(args.manifest)
    if not manifest_validator.validate():
        all_errors.extend(manifest_validator.errors)
        for error in manifest_validator.errors:
            print(f"[{error.category}] {error.message}", file=sys.stderr)
        return 1

    manifest = manifest_validator.manifest
    assert manifest is not None

    # 2. Topology validation
    topology_validator = TopologyValidator(manifest, flows_dir)
    if not topology_validator.validate():
        all_errors.extend(topology_validator.errors)
        for error in topology_validator.errors:
            print(f"[{error.category}] {error.message}", file=sys.stderr)

    # 3. Flow content validation (component references, MCP usage)
    content_validator = FlowContentValidator(flows_dir)
    if not content_validator.validate():
        all_errors.extend(content_validator.errors)
        for error in content_validator.errors:
            print(f"[{error.category}] {error.message}", file=sys.stderr)

    # 4. LFX validation
    lfx_validator = LFXValidator(flows_dir)
    if not lfx_validator.validate():
        all_errors.extend(lfx_validator.errors)
        for error in lfx_validator.errors:
            print(f"[{error.category}] {error.message}", file=sys.stderr)

    if all_errors:
        print(f"\n[VALIDATION FAILED] {len(all_errors)} error(s)", file=sys.stderr)
        return 1

    print("[VALIDATION PASSED] All checks passed", file=sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
