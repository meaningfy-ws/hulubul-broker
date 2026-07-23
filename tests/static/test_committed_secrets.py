"""Static tests for the committed-secrets scanner.

These tests never assert on a real credential value: fixtures use a
synthetic token, and the scanner's own contract (``SecretFinding``) is
designed to carry only a path and a rule id, never the matched value.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.check_committed_secrets import SecretFinding, scan_tracked_files

RULE_ID_CREDENTIAL_PATTERN = "credential-pattern"


def _init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)


def run_scan_on_tracked_fixture(tmp_path: Path, secret_value: str) -> SecretFinding:
    """Commit a single tracked file assigning ``secret_value`` and scan it.

    Returns the single finding produced, so tests can assert on its shape.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    tracked_file = repo / "tracked.txt"
    tracked_file.write_text(f"HULUBUL_LLM_API_KEY={secret_value}\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add tracked fixture"], cwd=repo, check=True)

    findings = scan_tracked_files(repo)
    assert len(findings) == 1
    return findings[0]


def test_secret_scan_reports_path_and_rule_without_matching_value(tmp_path):
    finding = run_scan_on_tracked_fixture(tmp_path, "synthetic-provider-token")

    assert finding.path.endswith("tracked.txt")
    assert finding.rule_id == RULE_ID_CREDENTIAL_PATTERN
    assert "synthetic-provider-token" not in repr(finding)


def test_secret_scan_ignores_empty_and_placeholder_values(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    tracked_file = repo / "tracked.txt"
    tracked_file.write_text(
        "HULUBUL_LLM_API_KEY=\nPOSTGRES_PASSWORD=changeme\nNEO4J_PASSWORD=changeme123\n"
    )
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add safe fixture"], cwd=repo, check=True)

    findings = scan_tracked_files(repo)

    assert findings == ()


def test_safe_langflow_example_file_produces_no_findings():
    findings = scan_tracked_files(Path(__file__).resolve().parents[2])

    assert findings == ()
