"""Platform-specific install path mapping for agent-skills.

Each supported AI-tool harness keeps its skills under a well-known
directory. This module maps a (platform, scope) pair to that directory so
the installer core can copy skills to the right place without any
platform-specific path logic leaking into the GUI or core modules.

Pure standard library.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

__all__ = [
    "PLATFORMS",
    "resolve_target_root",
]


def _plat_map() -> Dict[str, Dict[str, str]]:
    """Return the platform -> {scope -> relative path} mapping.

    ``"user"`` is relative to the OS home directory; ``"project"`` is
    relative to the current working directory (the repo root when the
    user runs the installer from there).
    """
    home = "~"
    return {
        "workbuddy": {
            "user": f"{home}/.workbuddy/skills",
            "project": ".workbuddy/skills",
        },
        "claude": {
            "user": f"{home}/.claude/skills",
            "project": ".claude/skills",
        },
        "codex": {
            "user": f"{home}/.codex/skills",
            "project": ".agents/skills",
        },
        "dsh": {
            "user": f"{home}/.dsh/skills",
            "project": ".dsh/skills",
        },
    }


#: Public read-only view of the mapping (built lazily so ``~`` is the
#: literal string, not an expanded path).
PLATFORMS: Dict[str, Dict[str, str]] = _plat_map()


def resolve_target_root(platform: str, scope: str) -> Path:
    """Resolve a (platform, scope) pair to an absolute ``Path``.

    Parameters
    ----------
    platform:
        One of the keys in :data:`PLATFORMS`.
    scope:
        ``"user"`` or ``"project"``.

    Returns
    -------
    Path
        An absolute path. User scope is expanded from ``~``; project scope
        is anchored at the current working directory.

    Raises
    ------
    KeyError
        If the platform or scope is unknown.
    """
    mapping = PLATFORMS.get(platform)
    if mapping is None:
        raise KeyError(f"unknown platform '{platform}'")
    if scope not in mapping:
        raise KeyError(f"unknown scope '{scope}' for platform '{platform}'")
    raw = mapping[scope]
    if raw.startswith("~"):
        return Path(raw).expanduser()
    # Project scope: anchor at the CWD.
    return Path.cwd() / raw


def known_platforms() -> Tuple[str, ...]:
    """All supported platform names, in stable order."""
    return tuple(PLATFORMS.keys())
