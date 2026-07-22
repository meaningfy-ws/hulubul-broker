"""Static tests for the local pre-commit secret-scan hook wiring."""
from __future__ import annotations

import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = REPO_ROOT / "scripts" / "git-hooks" / "pre-commit"


def test_pre_commit_hook_exists_and_is_executable():
    assert HOOK_PATH.is_file()
    mode = HOOK_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, "pre-commit hook must be executable"


def test_pre_commit_hook_invokes_the_secret_scanner():
    body = HOOK_PATH.read_text()

    assert "check_committed_secrets.py" in body
    assert body.startswith("#!/usr/bin/env bash")


def test_makefile_installs_hook_via_git_common_dir():
    body = (REPO_ROOT / "Makefile").read_text()

    assert "install-git-hooks:" in body
    assert "scripts/git-hooks/pre-commit" in body
    assert "git rev-parse --git-common-dir" in body
