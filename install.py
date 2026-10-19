#!/usr/bin/env python3
"""Cross-platform command-line installer for agent-skills.

Works without packaging: it discovers skills at the repository root and
under ``skills/``, checks declared dependencies, and copies the selected
skill folders into the target harness's skills directory.

Usage::

    python install.py --list
    python install.py --platform all --scope user
    python install.py --skill task-organizer --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the ``installer`` package importable when this file is run directly.
_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))

from installer.installer_core import check_dependencies, install_skill  # noqa: E402
from installer.platform_paths import PLATFORMS, known_platforms, resolve_target_root  # noqa: E402
from installer.skill_loader import discover_skills  # noqa: E402


def _check_deps(meta, platform_ok: bool) -> bool:
    ok, msgs = check_dependencies(meta, verbose=True)
    for m in msgs:
        print(f"    {m}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Install agent-skills")
    parser.add_argument("--platform", choices=list(PLATFORMS.keys()) + ["all"], default="all")
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--skill", default=None, help="Install only this skill")
    parser.add_argument("--force", action="store_true", help="Overwrite existing installs")
    parser.add_argument("--dry-run", action="store_true", help="Report without touching the filesystem")
    parser.add_argument("--list", action="store_true", help="List available skills and exit")
    args = parser.parse_args()

    skills = discover_skills(_REPO_ROOT)
    if not skills:
        print("No skills found at repo root or under skills/.")
        return 1

    if args.list:
        print("Available skills:")
        for s in skills:
            print(f"  - {s.summary_line()}")
        return 0

    selected = skills
    if args.skill:
        selected = [s for s in skills if s.name == args.skill]
        if not selected:
            print(f"skill not found: {args.skill}")
            return 1

    print("agent-skills installer")
    print(f"   scope={args.scope}  dry_run={args.dry_run}  force={args.force}\n")

    # Dependency check (once per skill).
    print("Checking dependencies...")
    for s in selected:
        print(f"[{s.name}]")
        _check_deps(s, True)
    print()

    platforms = known_platforms() if args.platform == "all" else [args.platform]
    for plat in platforms:
        target_root = resolve_target_root(plat, args.scope)
        print(f"Platform: {plat} -> {target_root}")
        for s in selected:
            ok, msg = install_skill(s, target_root, force=args.force, dry_run=args.dry_run)
            print(f"  {msg}")
        print()

    print("Done. Restart your AI tools to load the skills." if not args.dry_run else "Dry run complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
