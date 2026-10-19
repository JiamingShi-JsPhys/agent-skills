#!/usr/bin/env python3
"""Uninstall agent-skills from a target harness's skills directory.

Usage::

    python uninstall.py --platform all --scope user
    python uninstall.py --skill task-organizer --platform workbuddy
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))

from installer.installer_core import uninstall_skill  # noqa: E402
from installer.platform_paths import PLATFORMS, known_platforms, resolve_target_root  # noqa: E402
from installer.skill_loader import discover_skills  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Uninstall agent-skills")
    parser.add_argument("--platform", choices=list(PLATFORMS.keys()) + ["all"], default="all")
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--skill", default=None, help="Uninstall only this skill")
    args = parser.parse_args()

    skills = discover_skills(_REPO_ROOT)
    if args.skill:
        skills = [s for s in skills if s.name == args.skill]
        if not skills:
            print(f"skill not found: {args.skill}")
            return 1

    platforms = known_platforms() if args.platform == "all" else [args.platform]
    for plat in platforms:
        target_root = resolve_target_root(plat, args.scope)
        for s in skills:
            ok, msg = uninstall_skill(s.name, target_root)
            print(f"[{plat}] {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
