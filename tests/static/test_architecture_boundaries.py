"""
Subprocess-based architecture boundary tests.

These tests run in isolated Python processes to verify that importing certain
modules does NOT load forbidden dependencies (e.g., lfx, langflow).

This ensures that core models and services remain framework-agnostic and can
be imported safely without triggering heavy external dependencies.
"""

import subprocess
import sys
from pathlib import Path


def run_python_isolated(code: str) -> str:
    """
    Execute Python code in an isolated subprocess.

    Returns stdout stripped of whitespace.
    Raises CalledProcessError if subprocess fails.
    """
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
        check=True,
    )
    return result.stdout.strip()


class TestCoreModelsNoLfx:
    """Verify core.models does not load lfx or langflow."""

    def test_core_models_operational_does_not_load_lfx(self) -> None:
        """Importing core.models.operational must not load lfx."""
        code = """
import sys
import hulubul.core.models.operational
print('lfx' in sys.modules)
"""
        output = run_python_isolated(code)
        assert output == "False", f"lfx was loaded when importing core.models.operational: {output}"

    def test_core_models_operational_does_not_load_langflow(self) -> None:
        """Importing core.models.operational must not load langflow."""
        code = """
import sys
import hulubul.core.models.operational
print('langflow' in sys.modules)
"""
        output = run_python_isolated(code)
        assert output == "False", (
            f"langflow was loaded when importing core.models.operational: {output}"
        )

    def test_core_models_package_does_not_load_lfx(self) -> None:
        """Importing core.models package must not load lfx."""
        code = """
import sys
import hulubul.core.models
print('lfx' in sys.modules)
"""
        output = run_python_isolated(code)
        assert output == "False", f"lfx was loaded when importing core.models: {output}"

    def test_core_models_package_does_not_load_langflow(self) -> None:
        """Importing core.models package must not load langflow."""
        code = """
import sys
import hulubul.core.models
print('langflow' in sys.modules)
"""
        output = run_python_isolated(code)
        assert output == "False", f"langflow was loaded when importing core.models: {output}"


class TestRequestIntakeServicesNoLfx:
    """Verify request_intake.services does not load lfx or langflow."""

    def test_request_intake_services_does_not_load_lfx(self) -> None:
        """Importing request_intake.services must not load lfx."""
        code = """
import sys
import hulubul.request_intake.services
print('lfx' in sys.modules)
"""
        output = run_python_isolated(code)
        assert output == "False", f"lfx was loaded when importing request_intake.services: {output}"

    def test_request_intake_services_does_not_load_langflow(self) -> None:
        """Importing request_intake.services must not load langflow."""
        code = """
import sys
import hulubul.request_intake.services
print('langflow' in sys.modules)
"""
        output = run_python_isolated(code)
        assert output == "False", (
            f"langflow was loaded when importing request_intake.services: {output}"
        )
