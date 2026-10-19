"""Installer package for agent-skills.

Modules
-------
- :mod:`platform_paths` -- (platform, scope) -> target directory mapping.
- :mod:`skill_loader`   -- skill discovery + SKILL.md frontmatter loading.
- :mod:`installer_core` -- GUI-agnostic install / uninstall / verify logic.
- :mod:`installer_gui`  -- tkinter frontend (the double-click target).
"""

from .platform_paths import PLATFORMS, known_platforms, resolve_target_root
from .skill_loader import SkillMeta, discover_skills, load_skill_meta
from .installer_core import (
    check_dependencies,
    install_skill,
    uninstall_skill,
    verify_install,
)

__all__ = [
    "PLATFORMS",
    "known_platforms",
    "resolve_target_root",
    "SkillMeta",
    "discover_skills",
    "load_skill_meta",
    "check_dependencies",
    "install_skill",
    "uninstall_skill",
    "verify_install",
]

__version__ = "1.0.0"
