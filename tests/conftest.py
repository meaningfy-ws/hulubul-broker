"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add src directory to Python path BEFORE any imports
repo_root = Path(__file__).parent.parent
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Verify import works
from hulubul.core.models.operational.base import StrictModel  # noqa: E402, F401


def pytest_configure(config):
    """Pytest hook called before test collection."""
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
