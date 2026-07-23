"""Root pytest conftest.

Its only purpose is to anchor pytest's rootdir at the repository root so
test modules under ``tests/`` can import top-level packages such as
``scripts`` (namespace package, no ``__init__.py``) and the application
package under ``src/hulubul/``.
"""
import sys
from pathlib import Path

# Add src to sys.path so hulubul can be imported
_src_path = Path(__file__).parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))
