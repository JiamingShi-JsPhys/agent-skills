"""Root-level pytest configuration.

Ensures the ``installer`` package is importable from the repository root
so that :mod:`tests.test_installer` can exercise it regardless of the
current working directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# The repository root is the discovery source for the installer.
__all__ = ["_REPO_ROOT"]
