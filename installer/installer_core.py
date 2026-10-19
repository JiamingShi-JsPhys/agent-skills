"""Installer core: dependency check + skill copy to a target root.

The core is GUI-agnostic so it can be driven from the tkinter frontend,
from ``install.py`` (command line), or directly from tests.

Pure standard library.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple

from .skill_loader import SkillMeta

__all__ = [
    "check_dependencies",
    "install_skill",
    "uninstall_skill",
    "verify_install",
    "INSTALL_MANIFEST",
    "keep_paths_for",
]

# Progress hook signature: ``(done_files, total_files, current_file_name)``.
ProgressFn = Optional[Callable[[int, int, str], None]]

# ---------------------------------------------------------------------------
# Install manifest -- what an installed skill copy actually contains
# ---------------------------------------------------------------------------
# The installed copy is deliberately LEAN: SKILL.md (the agent-facing
# contract), the code, and the files the skill's own docs/code reference at
# runtime.  Repo-only material -- README, CHANGELOG, AUTHORS, LICENSE,
# CONTRIBUTING, tests, packaging metadata (pyproject/requirements), example
# configs nobody loads -- stays in the repository and the source archive.
# A user's ``.workbuddy/skills`` folder should hold what runs, not what
# develops.
#
# Entries are relative POSIX paths (files or directories) inside the skill
# directory.  Keep in sync with:
#   * the inline copy in ``installer_gui.py`` (frozen builds are
#     self-contained and cannot import this module),
#   * ``$InstallManifest`` in ``install-web.ps1`` (no-Python route),
#   * the bundle staging in ``build_installers.py``.
# ``tests/test_installer.py`` fails when any of the four drift apart.
INSTALL_MANIFEST: Dict[str, List[str]] = {
    # init writes its own .task-organizer.yml template and builds the
    # broadcast index inline, so assets/ ships in the repo only.
    "task-organizer": ["SKILL.md", "scripts"],
    # The MCP server (mcp_server/) is an optional extra interface that
    # SKILL.md does not contract; it ships in the source archive only.
    "formula-validator": ["SKILL.md", "scripts"],
    # SKILL.md's usage examples run against config.example.yaml verbatim.
    "multi-dim-manager": [
        "SKILL.md", "scripts", "config.example.yaml",
    ],
    # R scripts are invoked at runtime by r_runner; SKILL.md's examples run
    # against config/examples/*.yaml.  config/schema.yaml is loaded by
    # nothing (documentation only) and stays in the repo.
    "longitudinal-analysis": [
        "SKILL.md", "src", "R", "config/examples",
    ],
    "conflict-detector": ["SKILL.md", "src", "config/examples"],
    "document-evolution-tracker": [
        "SKILL.md", "src", "config/examples",
    ],
    # Lean runtime copy: the CLI reads a user-supplied config; the bundled
    # config.yaml template + assets/ examples stay in the source archive.
    "video-tracker": ["SKILL.md", "scripts"],
    # Standalone pure-stdlib skill: SKILL.md + the scanner code (src/) + the
    # human-readable reference library (references/). No config/ or scripts/.
    "ai-trace-remover": ["SKILL.md", "src", "references"],
}

# VCS / cache noise: never copied, even under a kept directory.
_NOISE_NAMES = frozenset({".git", "__pycache__", ".pytest_cache", ".mypy_cache"})


def keep_paths_for(skill_name: str) -> Optional[List[str]]:
    """Runtime keep-list for ``skill_name`` (None = copy everything)."""
    return INSTALL_MANIFEST.get(skill_name)


def _keep_ignore(root: Path, keep: List[str]):
    """Build a ``copytree`` ignore function keeping exactly ``keep``.

    ``keep`` entries are relative POSIX paths of files or directories.  A
    directory is kept when it is (an ancestor of) a kept path; every other
    entry is ignored.  The filter is path-aware at EVERY directory level
    (an earlier "top-level names only" variant silently emptied kept
    subdirectories, because copytree re-applies the filter per level).
    """
    keep_set = {p.replace("\\", "/").strip("/") for p in keep if p.strip()}
    root_resolved = Path(root).resolve()

    def _ignore(src, names):
        try:
            rel = Path(src).resolve().relative_to(root_resolved)
        except ValueError:
            return []  # outside the skill root: keep everything
        prefix = "" if rel == Path(".") else rel.as_posix() + "/"
        ignored = []
        for n in names:
            if n in _NOISE_NAMES:
                ignored.append(n)
                continue
            rp = prefix + n
            if rp in keep_set:
                continue
            if any(k.startswith(rp + "/") for k in keep_set):
                continue  # ancestor directory of a kept path
            if any(rp.startswith(k + "/") for k in keep_set):
                continue  # inside an explicitly kept directory: keep all
            ignored.append(n)
        return ignored

    return _ignore


def check_dependencies(meta: SkillMeta, verbose: bool = True) -> Tuple[bool, List[str]]:
    """Check the Python version and pip deps declared in ``meta``.

    Returns ``(ok, messages)`` where ``messages`` is a list of human-readable
    lines. ``ok`` is True only when every *required* dependency is present.
    """
    msgs: List[str] = []
    ok = True
    deps = meta.dependencies or {}

    py_req = deps.get("python")
    if py_req:
        m = re.match(r">=(\d+)\.(\d+)", py_req)
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
            if sys.version_info < (major, minor):
                msgs.append(f"ERROR: Python {py_req} required, found {sys.version.split()[0]}")
                ok = False
            else:
                msgs.append(f"OK: Python {sys.version.split()[0]}")

    for spec in deps.get("pip", []) or []:
        pkg = spec.split(">=")[0].split("==")[0].strip().replace("-", "_")
        try:
            __import__(pkg)
            msgs.append(f"OK: {spec}")
        except ImportError:
            msgs.append(f"WARN: {spec} not installed (run: pip install {spec})")
            # Soft warning: a missing optional dep does not block install.
    return ok, msgs


def _iter_skill_files(root: Path, ignore_fn) -> Iterator[Path]:
    """Yield the files ``copytree`` would copy, honouring the same ignore.

    Walks with the identical ignore filter as the real copy so the progress
    total matches the file count exactly.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        skipped = set(ignore_fn(dirpath, list(dirnames) + list(filenames)))
        dirnames[:] = [d for d in dirnames if d not in skipped]
        for name in filenames:
            if name not in skipped:
                yield Path(dirpath) / name


def install_skill(
    meta: SkillMeta,
    target_root: Path,
    force: bool = False,
    dry_run: bool = False,
    keep: Optional[List[str]] = None,
    progress: ProgressFn = None,
) -> Tuple[bool, str]:
    """Copy a skill into ``target_root / meta.name``.

    Parameters
    ----------
    meta:
        The skill to install.
    target_root:
        Destination root (one platform+scope resolved path).
    force:
        Overwrite an existing install instead of skipping.
    dry_run:
        Report what *would* happen without touching the filesystem.
    keep:
        Optional relative-path whitelist (see ``INSTALL_MANIFEST``); when
        given, ONLY these files/directories are installed -- a lean
        runtime copy.  Default (None): copy everything except VCS/cache
        noise.
    progress:
        Optional hook called after each copied file as
        ``progress(done, total, current_file_name)``.  Exceptions raised by
        the hook are swallowed -- a progress display must never break the
        install itself.

    Returns
    -------
    (installed, message)
    """
    dst = target_root / meta.name
    if dst.exists():
        if not force:
            return False, f"SKIP: {dst} already exists (use --force to overwrite)"
        if dry_run:
            return True, f"OVERWRITE: would overwrite {dst}"
        shutil.rmtree(dst)

    if dry_run:
        return True, f"INSTALL: would install to {dst}"

    dst.parent.mkdir(parents=True, exist_ok=True)

    if keep is not None:
        _ignore = _keep_ignore(meta.directory, keep)
    else:
        def _ignore(_src, names):
            return [n for n in names if n in _NOISE_NAMES]

    total = sum(1 for _ in _iter_skill_files(meta.directory, _ignore))
    state = {"done": 0}

    def _copy_function(src, dst, **_kwargs):
        # Swallow copytree's optional keyword args (e.g. follow_symlinks);
        # skills are plain file trees, so copy2's default is correct.
        shutil.copy2(src, dst)
        state["done"] += 1
        if progress is not None:
            try:
                progress(state["done"], total, Path(src).name)
            except Exception:
                pass

    shutil.copytree(
        meta.directory,
        dst,
        ignore=_ignore,
        dirs_exist_ok=True,
        copy_function=_copy_function,
    )
    if progress is not None and total:
        # Final tick so a determinate bar always reaches 100% even if the
        # last file carried no size update.
        try:
            progress(total, total, "")
        except Exception:
            pass
    return True, f"OK: installed {dst}"


def uninstall_skill(meta_name: str, target_root: Path) -> Tuple[bool, str]:
    """Remove ``target_root / meta_name`` if present."""
    dst = target_root / meta_name
    if not dst.exists():
        return False, f"NOT FOUND: {dst}"
    shutil.rmtree(dst)
    return True, f"Removed {dst}"


def verify_install(meta: SkillMeta, target_root: Path) -> Tuple[bool, str]:
    """Check that a skill was fully copied (SKILL.md always required)."""
    dst = target_root / meta.name
    if not (dst / "SKILL.md").exists():
        return False, f"ERROR: {meta.name} missing SKILL.md at {dst}"
    return True, f"OK: {meta.name}"
