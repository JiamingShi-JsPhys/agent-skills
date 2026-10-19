#!/usr/bin/env python3
"""Verify that agent-skills are fully installed in a target harness.

Usage::

    python verify.py --platform all --scope user
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))

from installer.installer_core import verify_install  # noqa: E402
from installer.platform_paths import PLATFORMS, known_platforms, resolve_target_root  # noqa: E402
from installer.skill_loader import discover_skills  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify agent-skills installation")
    parser.add_argument("--platform", choices=list(PLATFORMS.keys()) + ["all"], default="all")
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--skill", default=None, help="Verify only this skill")
    args = parser.parse_args()

    skills = discover_skills(_REPO_ROOT)
    if args.skill:
        skills = [s for s in skills if s.name == args.skill]

    platforms = known_platforms() if args.platform == "all" else [args.platform]
    all_ok = True
    for plat in platforms:
        target_root = resolve_target_root(plat, args.scope)
        print(f"Platform: {plat} -> {target_root}")
        for s in skills:
            ok, msg = verify_install(s, target_root)
            print(f"  {msg}")
            all_ok = all_ok and ok
        print()
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
