#!/usr/bin/env python3
"""
Normalize LangFlow 1.10.2 flow JSON exports to canonical format.

This script ensures deterministic JSON output with:
- Sorted keys at each level (for stable diffs)
- Preserved node/edge array order (logical flow topology unchanged)
- Normalized indentation (2 spaces) and line endings (LF)
- Optional restoration of manifest-allowlisted environment variables
- Idempotence verification (same input always produces same output)

Exit codes:
  0: Success (normalization passed or idempotent)
  1: File error or invalid JSON
  2: Idempotence check failed (file changed after normalization)
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

# The only environment variable names ever allowed to be restored into a
# `load_from_db=true` field. Declaring a binding for any other name in
# flow-manifest.yaml is a normalization-time error, not a silent pass-through.
ALLOWED_RUNTIME_VARIABLE_NAMES = frozenset(
    {
        "HULUBUL_LLM_MODEL",
        "HULUBUL_LLM_BASE_URL",
        "HULUBUL_LLM_API_KEY",
    }
)


class NormalizationError(Exception):
    """Raised when normalization would restore an undeclared runtime variable."""


def sort_dict_keys(obj: Any, preserve_arrays: bool = True) -> Any:
    """
    Recursively sort dictionary keys while preserving array order.

    Args:
        obj: The object to process (dict, list, or scalar)
        preserve_arrays: If True, preserve array order; if False, sort array contents

    Returns:
        The object with sorted keys at each level
    """
    if isinstance(obj, dict):
        # Sort all dictionary keys
        result: dict[str, Any] = {}
        for k, v in sorted(obj.items()):
            result[k] = sort_dict_keys(v, preserve_arrays)
        return result
    if isinstance(obj, list) and preserve_arrays:
        # Preserve array order but recursively sort contents
        return [sort_dict_keys(item, preserve_arrays) for item in obj]
    # Return scalars unchanged
    return obj


def normalize_flow_json(flow: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a LangFlow JSON object to canonical format.

    Ensures:
    - Keys are sorted alphabetically at each level
    - Node/edge arrays preserve their order (logical topology)
    - Idempotent (running twice produces identical result)

    Args:
        flow: Parsed LangFlow JSON dictionary

    Returns:
        Normalized flow dictionary
    """
    # Sort all keys while preserving array order
    result = sort_dict_keys(flow, preserve_arrays=True)
    assert isinstance(result, dict)
    return result


def normalize_flow_json_with_manifest(
    flow: dict[str, Any],
    manifest_bindings: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """
    Normalize flow and restore manifest-allowlisted environment variable names.

    Args:
        flow: Parsed LangFlow JSON dictionary
        manifest_bindings: Dict mapping component_id -> field -> env_var_name

    Returns:
        Normalized flow with restored variable names

    Raises:
        NormalizationError: If a binding references a variable name outside
            ``ALLOWED_RUNTIME_VARIABLE_NAMES``.
    """
    normalized = normalize_flow_json(flow)

    # Restore environment variables for allowlisted components
    if "data" in normalized and "nodes" in normalized["data"]:
        for node in normalized["data"]["nodes"]:
            node_id = node.get("id")
            if node_id in manifest_bindings:
                bindings = manifest_bindings[node_id]
                if "data" in node:
                    for field, env_var_name in bindings.items():
                        if env_var_name not in ALLOWED_RUNTIME_VARIABLE_NAMES:
                            raise NormalizationError(
                                f"undeclared runtime variable reference: "
                                f"{env_var_name!r} on {node_id}.{field}"
                            )
                        if field in node["data"]:
                            # Replace hardcoded value with environment variable reference
                            node["data"][field] = f"{{{{ {env_var_name} }}}}"

    return normalized


def normalize_to_json_string(flow: dict[str, Any]) -> str:
    """
    Convert normalized flow dictionary to JSON string with canonical formatting.

    Ensures:
    - 2-space indentation
    - LF line endings (not CRLF)
    - Trailing newline

    Args:
        flow: Normalized flow dictionary

    Returns:
        JSON string with canonical formatting
    """
    # Convert to JSON with sorted keys and 2-space indentation
    json_str = json.dumps(flow, indent=2, ensure_ascii=False, sort_keys=True)

    # Ensure LF line endings (strip any CRLF and normalize to LF)
    json_str = json_str.replace("\r\n", "\n")

    # Ensure trailing newline
    if not json_str.endswith("\n"):
        json_str += "\n"

    return json_str


def check_file_idempotence(file_path: Path) -> bool:
    """
    Check if a flow JSON file is idempotent (normalizing produces same content).

    Args:
        file_path: Path to the flow JSON file

    Returns:
        True if file is idempotent, False if normalization would change it
    """
    # Read original file
    original_content = file_path.read_text(encoding="utf-8")
    original_hash = hashlib.sha256(original_content.encode()).hexdigest()

    # Parse and re-normalize
    flow = json.loads(original_content)
    normalized_flow = normalize_flow_json(flow)
    normalized_content = normalize_to_json_string(normalized_flow)
    normalized_hash = hashlib.sha256(normalized_content.encode()).hexdigest()

    # Check if idempotent
    return original_hash == normalized_hash


def normalize_file(
    file_path: Path,
    output_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> bool:
    """
    Normalize a single flow JSON file.

    Args:
        file_path: Path to the flow JSON file
        output_dir: Optional output directory to write normalized file
        manifest_path: Optional path to flow-manifest.yaml for variable restoration

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read and parse the flow
        original_content = file_path.read_text(encoding="utf-8")
        flow = json.loads(original_content)

        # Normalize the flow
        normalized_flow = normalize_flow_json(flow)

        # Restore manifest variables if available
        if manifest_path:
            manifest_bindings = load_manifest_bindings(manifest_path)
            normalized_flow = normalize_flow_json_with_manifest(
                normalized_flow,
                manifest_bindings,
            )

        # Convert to canonical JSON string
        normalized_content = normalize_to_json_string(normalized_flow)

        # Write to output location
        if output_dir:
            output_file = output_dir / file_path.name
            output_file.write_text(normalized_content, encoding="utf-8")
        else:
            file_path.write_text(normalized_content, encoding="utf-8")

        return True

    except (json.JSONDecodeError, OSError) as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return False


def load_manifest_bindings(manifest_path: Path) -> dict[str, dict[str, str]]:
    """
    Load runtime bindings from flow-manifest.yaml.

    Args:
        manifest_path: Path to flow-manifest.yaml

    Returns:
        Dict mapping component_id -> field -> env_var_name
    """
    try:
        import yaml  # type: ignore[import-untyped]

        manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        bindings: dict[str, dict[str, str]] = {}

        if isinstance(manifest_data, dict) and "runtime_bindings" in manifest_data:
            for binding in manifest_data["runtime_bindings"]:
                if isinstance(binding, dict):
                    component_id = binding.get("component_id")
                    fields = binding.get("fields", {})
                    if component_id and isinstance(fields, dict):
                        bindings[component_id] = fields

        return bindings

    except (ImportError, Exception) as e:
        print(
            f"Warning: Could not load manifest bindings from {manifest_path}: {e}",
            file=sys.stderr,
        )
        return {}


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Normalize LangFlow 1.10.2 flow JSON exports to canonical format.",
        epilog="Exit codes: 0=success, 1=error, 2=idempotence check failed",
    )

    parser.add_argument(
        "flows",
        nargs="*",
        type=Path,
        help="Flow JSON files to normalize (glob patterns supported)",
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify idempotence without modifying files (exit code 2 if not idempotent)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for normalized flows (if not specified, normalize in place)",
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("langflow/flow-manifest.yaml"),
        help="Path to flow-manifest.yaml for variable restoration",
    )

    args = parser.parse_args()

    # Expand glob patterns if needed
    flow_files: list[Path] = []
    for flow_arg in args.flows:
        if "*" in str(flow_arg):
            flow_files.extend(Path(".").glob(str(flow_arg)))
        else:
            flow_files.append(flow_arg)

    if not flow_files:
        print("No flow files specified", file=sys.stderr)
        return 1

    # Validate output directory if specified
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)

    # Check if manifest exists and is readable
    manifest_path = None
    if args.manifest.exists():
        manifest_path = args.manifest

    # Process each file
    failed_files = []
    not_idempotent_files = []

    for flow_file in flow_files:
        if not flow_file.exists():
            print(f"File not found: {flow_file}", file=sys.stderr)
            failed_files.append(flow_file)
            continue

        if args.check:
            # Check idempotence without modifying
            if check_file_idempotence(flow_file):
                print(f"✓ {flow_file.name} is idempotent")
            else:
                print(f"✗ {flow_file.name} is NOT idempotent", file=sys.stderr)
                not_idempotent_files.append(flow_file)
        else:
            # Normalize and possibly restore manifest variables
            if normalize_file(flow_file, args.output, manifest_path):
                print(f"✓ Normalized {flow_file.name}")
            else:
                failed_files.append(flow_file)

    # Determine exit code
    if failed_files:
        print(
            f"Failed to process {len(failed_files)} file(s)",
            file=sys.stderr,
        )
        return 1

    if not_idempotent_files:
        print(
            f"{len(not_idempotent_files)} file(s) are not idempotent",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
