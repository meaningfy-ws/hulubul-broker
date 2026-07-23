"""Static tests for the GitHub Actions CI workflow definition.

These tests parse ``.github/workflows/ci.yaml`` and assert on its structure
directly, so the "CI calls Make targets only, nothing inlined" contract is
enforced by a test rather than by convention. PyYAML is available here as a
transitive dependency of ``linkml`` (a base, non-optional Poetry dependency),
so no additional test dependency is required to parse the workflow file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yaml"


class _Workflow:
    """Thin read-only view over a parsed GitHub Actions workflow document."""

    def __init__(self, document: dict[str, Any]):
        self._document = document

    def project_commands(self, job_name: str) -> tuple[str, ...]:
        """Return the ``make ...`` commands a job invokes, in step order.

        Only commands that build/verify the project (``make ...``) count;
        environment-bootstrap steps (checkout, setup-python, installing
        Poetry via pipx) are deliberately excluded, so this asserts the "Make
        targets only" contract without hard-coding bootstrap step names.
        """
        steps = self._document["jobs"][job_name]["steps"]
        commands = (step["run"].strip() for step in steps if "run" in step)
        return tuple(command for command in commands if command.startswith("make "))


@pytest.fixture
def workflow() -> _Workflow:
    document = yaml.safe_load(WORKFLOW_PATH.read_text())
    return _Workflow(document)


def test_hard_ci_calls_make_targets_only(workflow):
    assert workflow.project_commands("static-quality") == ("make install", "make ci-static")
