"""The native installer window (tkinter, standard-installer layout).

Launch paths
------------
* **Source (repo mode)** -- run the installer from the repo root and it
  discovers all skills under ``repo_root/`` (and ``repo_root/skills/``).
* **Frozen (PyInstaller onefile)** -- each per-skill installer is built by
  baking its single skill in as data (see ``build_installers.py``).  On
  startup the frozen binary extracts that skill from ``sys._MEIPASS`` to a
  temp dir; the window header then shows that one skill's title and
  description, fixed -- there is nothing to pick.

UI layout (mimics a generic installer wizard)
---------------------------------------------
* **Header band** -- the package title (skill name + version) only.
  The long frontmatter description is intentionally omitted from the
  window (it adds no value here and overflows the fixed-size layout).
* **"Install to"** -- a **multi-select** checklist of harness frameworks
  by full name, sorted alphabetically (Claude Code, DeepSeek Harness,
  OpenAI Codex, WorkBuddy).  Tick several to install into all of them at
  once.  Each entry shows the directory it would install into for the
  current scope on a second line.  Nothing is preselected: the window
  opens with no framework ticked and no scope chosen, and Install stays
  disabled until the user picks at least one framework and a scope.
* **Scope** -- *user* scope installs into your home folder
  (``~/.workbuddy/skills`` etc.), so every project of that harness can
  use the skill; *project* scope installs into one task folder, visible
  to that project only.  In project scope the installer scans the
  machine for existing task folders (repositories, harness project
  roots) and offers them in a dropdown -- the field stays editable and a
  "Browse..." button picks any other folder.
* **Install** -- a progress bar plus a step-by-step status line
  ("Checking dependencies...", "Copying files to ...", "Verifying...")
  exactly like a standard installer, then a success line with the final
  paths and an "Open folder" button.

Frozen-build notes
------------------
A PyInstaller one-file build must bundle three things for tkinter to work:
``_tkinter.pyd`` (auto-collected), ``tcl86t.dll`` + ``tk86t.dll`` (resolved
by PyInstaller's tcl/tk hook via PATH -- in a conda env they live in
``Library/bin``, which is only on PATH when the env is activated), and the
``tcl8.6`` / ``tk8.6`` script libraries (auto-collected by the same hook).
``build_installers.py`` puts ``Library/bin`` on PATH for the build so the
DLLs get collected; the runtime hook then points ``TCL_LIBRARY`` /
``TK_LIBRARY`` at the bundled script dirs.  :func:`_prep_tcl_tk_env` is a
belt-and-braces fallback that does the same in case the runtime hook did
not run.

CLI fallback
------------
``--cli`` installs without a window (for scripting or headless use);
``--check`` verifies that the bundled tkinter can initialise and exits
non-zero if not, which is what the build smoke test uses.

Pure standard library only.
"""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__all__ = ["InstallerGUI", "main"]


def _is_frozen() -> bool:
    """True when running under PyInstaller (``sys.frozen`` set)."""
    return bool(getattr(sys, "frozen", False))


# ---------------------------------------------------------------------------
# Skill discovery (inline of installer.skill_loader)
# ---------------------------------------------------------------------------

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class SkillMeta:
    """Metadata for a single installable skill."""

    name: str
    directory: Path
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    license: str = "MIT"
    entry: str = ""
    dependencies: Dict = field(default_factory=dict)
    platforms: List[str] = field(
        default_factory=lambda: ["workbuddy", "claude", "codex", "dsh"]
    )

    @property
    def has_skill_md(self) -> bool:
        return (self.directory / "SKILL.md").exists()

    def summary_line(self) -> str:
        desc = self.description.split(".")[0] + "." if self.description else ""
        return f"{self.name} v{self.version} -- {desc}"


def _read_frontmatter(skill_md: Path) -> Dict[str, str]:
    """Pull top-level scalars out of a SKILL.md frontmatter block.

    Handles both flat frontmatter (``version: 1.0.0`` at top level, as in
    the test fixtures) and nested metadata blocks (``version`` under an
    indented ``metadata:`` key, as in the real skill files).  Reads both
    top-level ``description`` and keys nested under ``metadata:``.
    """
    out: Dict[str, str] = {}
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return out

    # Top-level ``description`` key
    m = re.search(r"^description:\s*(.*)$", text, re.MULTILINE)
    out["description"] = m.group(1).strip().strip('"').strip("'") if m else ""

    # For version / author / license / entry: first check the whole text
    # for top-level keys (flat layout), then fall back to the metadata
    # block (nested layout).
    def _top_or_meta(key: str, meta_key: str | None = None) -> str:
        meta_key = meta_key or key
        # 1) Top-level (flat)
        m = re.search(rf"^{key}:\s*(.*)$", text, re.MULTILINE)
        if m:
            return m.group(1).strip().strip('"').strip("'")
        # 2) Indented key under metadata: (nested)
        mb = re.search(
            r"^metadata:\s*$\n((?:[ \t]+[^\n]*\n)+)", text, re.MULTILINE
        )
        block = mb.group(1) if mb else ""
        m2 = re.search(rf"^\s+{meta_key}:\s*(.*)$", block, re.MULTILINE)
        if m2:
            return m2.group(1).strip().strip('"').strip("'")
        return ""

    out["version"] = _top_or_meta("version")
    out["author"] = _top_or_meta("author")
    out["license"] = _top_or_meta("license")
    # entry maps to entry_point in the nested layout
    out["entry"] = _top_or_meta("entry", "entry_point")
    return out


def _synthesize_meta(skill_dir: Path) -> SkillMeta:
    fm = _read_frontmatter(skill_dir / "SKILL.md")
    return SkillMeta(
        name=skill_dir.name,
        directory=skill_dir,
        version=fm.get("version") or "0.0.0",
        description=fm.get("description", ""),
        author=fm.get("author") or "Jiaming Shi",
        license=fm.get("license") or "MIT",
        entry=fm.get("entry", ""),
    )


def _load_skill_meta(skill_dir: Path) -> SkillMeta:
    skill_dir = Path(skill_dir)
    if not (skill_dir / "SKILL.md").exists():
        raise FileNotFoundError(f"not a skill directory (no SKILL.md): {skill_dir}")
    skill_json = skill_dir / "skill.json"
    if skill_json.exists():
        raw = json.loads(skill_json.read_text(encoding="utf-8"))
        return SkillMeta(
            name=str(raw.get("name", skill_dir.name)),
            directory=skill_dir,
            version=str(raw.get("version", "0.0.0")),
            description=str(raw.get("description", "")),
            author=str(raw.get("author", "Jiaming Shi")),
            license=str(raw.get("license", "MIT")),
            entry=str(raw.get("entry", "")),
            dependencies=dict(raw.get("dependencies", {}) or {}),
            platforms=list(raw.get("platforms", ["workbuddy", "claude", "codex", "dsh"])),
        )
    return _synthesize_meta(skill_dir)


def _is_skill_dir(entry: Path) -> bool:
    return entry.is_dir() and (entry / "SKILL.md").exists()


def discover_skills(repo_root: Path) -> List[SkillMeta]:
    """Discover installable skills across both repo layouts."""
    repo_root = Path(repo_root)
    found: Dict[str, SkillMeta] = {}
    for entry in sorted(repo_root.iterdir()):
        if _is_skill_dir(entry):
            meta = _load_skill_meta(entry)
            found.setdefault(meta.name, meta)
    skills_dir = repo_root / "skills"
    if skills_dir.is_dir():
        for entry in sorted(skills_dir.iterdir()):
            if _is_skill_dir(entry):
                meta = _load_skill_meta(entry)
                if meta.name not in found:
                    found[meta.name] = meta
    return sorted(found.values(), key=lambda m: m.name)


# ---------------------------------------------------------------------------
# Platform paths (inline of installer.platform_paths)
# ---------------------------------------------------------------------------


def _plat_map() -> Dict[str, Dict[str, str]]:
    home = "~"
    return {
        "workbuddy": {"user": f"{home}/.workbuddy/skills", "project": ".workbuddy/skills"},
        "claude": {"user": f"{home}/.claude/skills", "project": ".claude/skills"},
        "codex": {"user": f"{home}/.codex/skills", "project": ".agents/skills"},
        "dsh": {"user": f"{home}/.dsh/skills", "project": ".dsh/skills"},
    }


PLATFORMS: Dict[str, Dict[str, str]] = _plat_map()


def resolve_target_root(platform: str, scope: str) -> Path:
    mapping = PLATFORMS.get(platform)
    if mapping is None:
        raise KeyError(f"unknown platform '{platform}'")
    if scope not in mapping:
        raise KeyError(f"unknown scope '{scope}' for platform '{platform}'")
    raw = mapping[scope]
    if raw.startswith("~"):
        return Path(raw).expanduser()
    return Path.cwd() / raw


def known_platforms() -> Tuple[str, ...]:
    return tuple(PLATFORMS.keys())


# Display names (full product names, as requested) + alphabetical ordering
# for the harness checklist.  Ordered by the displayed label, not the key.
_PLATFORM_LABELS: Dict[str, str] = {
    "claude": "Claude Code",
    "codex": "OpenAI Codex",
    "dsh": "DeepSeek Harness",
    "workbuddy": "WorkBuddy",
}
_PLATFORM_ORDER: Tuple[str, ...] = tuple(
    key for key, _ in sorted(_PLATFORM_LABELS.items(), key=lambda kv: kv[1])
)

# ---------------------------------------------------------------------------
# Project-folder discovery (project scope)
# ---------------------------------------------------------------------------

# A folder counts as a task/project folder when it carries one of these
# markers: a git repo, a harness project root, or a task-organizer config.
_PROJECT_MARKERS: Tuple[str, ...] = (
    ".git",
    ".workbuddy",
    ".claude",
    ".codex",
    ".dsh",
    ".agents",
    ".task-organizer.yml",
)

# Top-level home entries that are never task folders.
_HOME_SKIP: frozenset = frozenset(
    {
        "AppData",
        "Application Data",
        "Cookies",
        "Local Settings",
        "My Documents",
        "NetHood",
        "PrintHood",
        "Recent",
        "SendTo",
        "Start Menu",
        "Templates",
    }
)


def discover_project_folders(
    roots: Optional[List[Path]] = None, limit: int = 25
) -> List[str]:
    """Scan likely locations for existing task / project folders.

    Looks one level deep inside ``~/Desktop``, ``~/Documents`` and the
    home directory itself for folders that carry a project marker (a git
    repo, a harness project root, or a task-organizer config).  Returns
    the most recently modified matches, newest first.  Pure standard
    library; never raises on unreadable directories.
    """
    if roots is None:
        try:
            home = Path.home()
        except Exception:
            return []
        roots = [home / "Desktop", home / "Documents", home]
    found: Dict[str, float] = {}
    for root in roots:
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        for entry in entries:
            try:
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                if entry.name in _HOME_SKIP:
                    continue
                if not any((entry / marker).exists() for marker in _PROJECT_MARKERS):
                    continue
                found[str(entry)] = entry.stat().st_mtime
            except OSError:
                continue
    ordered = sorted(found.items(), key=lambda kv: kv[1], reverse=True)
    return [path for path, _ in ordered[:limit]]


# ---------------------------------------------------------------------------
# Installer core (inline of installer.installer_core)
# ---------------------------------------------------------------------------


def check_dependencies(meta: SkillMeta, verbose: bool = True) -> Tuple[bool, List[str]]:
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
    return ok, msgs


# ---------------------------------------------------------------------------
# Install manifest (inline copy -- frozen builds must stay self-contained)
# ---------------------------------------------------------------------------
# Mirrors ``INSTALL_MANIFEST`` in ``installer/installer_core.py``; a root
# test fails when the two drift apart.  The installed copy is deliberately
# lean: SKILL.md + code + runtime-referenced files only.  README, CHANGELOG,
# tests and packaging metadata stay in the repository / source archive.
INSTALL_MANIFEST = {
    "task-organizer": ["SKILL.md", "scripts"],
    "formula-validator": ["SKILL.md", "scripts"],
    "multi-dim-manager": [
        "SKILL.md", "scripts", "config.example.yaml",
    ],
    "longitudinal-analysis": [
        "SKILL.md", "src", "R", "config/examples",
    ],
    "conflict-detector": ["SKILL.md", "src", "config/examples"],
    "document-evolution-tracker": [
        "SKILL.md", "src", "config/examples",
    ],
    "video-tracker": ["SKILL.md", "scripts"],
    # Standalone pure-stdlib skill: SKILL.md + src + references.
    "ai-trace-remover": ["SKILL.md", "src", "references"],
}

_NOISE_NAMES = frozenset({".git", "__pycache__", ".pytest_cache", ".mypy_cache"})


def keep_paths_for(skill_name: str):
    """Runtime keep-list for ``skill_name`` (None = copy everything)."""
    return INSTALL_MANIFEST.get(skill_name)


def _keep_ignore(root, keep):
    """Build a ``copytree`` ignore function keeping exactly ``keep``.

    Path-aware at every directory level (see installer_core._keep_ignore);
    the naive "names not in whitelist" variant empties kept subdirectories
    because copytree re-applies the filter per level.
    """
    keep_set = {p.replace("\\", "/").strip("/") for p in keep if p.strip()}
    root_resolved = Path(root).resolve()

    def _ignore(src, names):
        try:
            rel = Path(src).resolve().relative_to(root_resolved)
        except ValueError:
            return []
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


def _iter_skill_files(root: Path, ignore_fn) -> List[Path]:
    """Files ``copytree`` would copy, honouring the same ignore filter.

    Lets the progress total match the real copy exactly.
    """
    out: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        skipped = set(ignore_fn(dirpath, list(dirnames) + list(filenames)))
        dirnames[:] = [d for d in dirnames if d not in skipped]
        for name in filenames:
            if name not in skipped:
                out.append(Path(dirpath) / name)
    return out


def install_skill(
    meta: SkillMeta,
    target_root: Path,
    force: bool = False,
    dry_run: bool = False,
    keep: Optional[List[str]] = None,
    progress=None,
) -> Tuple[bool, str]:
    """Copy a skill into ``target_root / meta.name``.

    ``keep`` is an optional relative-path whitelist (see INSTALL_MANIFEST):
    only those files/directories are installed -- a lean runtime copy.
    ``progress`` (optional) is called after each copied file as
    ``progress(done, total, current_file_name)``; exceptions from the hook
    are swallowed so a progress display can never break the install.
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

    total = len(_iter_skill_files(meta.directory, _ignore))
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
        # Final tick so a determinate bar always reaches 100%.
        try:
            progress(total, total, "")
        except Exception:
            pass
    return True, f"OK: installed {dst}"


def verify_install(meta: SkillMeta, target_root: Path) -> Tuple[bool, str]:
    dst = target_root / meta.name
    if not (dst / "SKILL.md").exists():
        return False, f"ERROR: {meta.name} missing SKILL.md at {dst}"
    return True, f"OK: {meta.name}"


# ---------------------------------------------------------------------------
# Bundled skill extraction (frozen mode)
# ---------------------------------------------------------------------------


def _frontmatter_name(skill_md: Path) -> Optional[str]:
    """Read the top-level ``name:`` key from a SKILL.md frontmatter block."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"^name:\s*(.*)$", text, re.MULTILINE)
    if not m:
        return None
    name = m.group(1).strip().strip('"').strip("'")
    return name or None


def _bundled_skill_root() -> Optional[Path]:
    """Extract the single skill baked into a frozen installer to a temp dir.

    The staged skill tree is bundled as ``_BUNDLED_SKILL`` (a container
    directory created by PyInstaller ``--add-data``).  Depending on how the
    source archive is laid out the container either holds the skill directly
    (``_BUNDLED_SKILL/SKILL.md``) or one skill subdirectory
    (``_BUNDLED_SKILL/<skill>/SKILL.md``).

    Returns a **repository-shaped** temp directory: ``<tmp>/<skill-name>/``
    holding the skill tree, where ``<skill-name>`` is the real name from the
    SKILL.md frontmatter.  ``discover_skills()`` scans a repository root
    (``root/*`` and ``root/skills/*``) and takes the skill name from the
    *directory* name, so returning the skill directory itself would make it
    discover nothing (and returning the raw container would name the skill
    ``_BUNDLED_SKILL``).
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    bundle_dir = Path(meipass) / "_BUNDLED_SKILL"
    if not bundle_dir.is_dir():
        return None
    # Locate the skill root inside the container.
    skill_src = bundle_dir
    if not (skill_src / "SKILL.md").exists():
        for child in sorted(bundle_dir.iterdir()):
            if child.is_dir() and (child / "SKILL.md").exists():
                skill_src = child
                break
        else:
            return None
    # The real skill name comes from the frontmatter (authoritative), with
    # the source directory name as fallback.
    name = _frontmatter_name(skill_src / "SKILL.md") or skill_src.name
    if not name:
        return None
    out = Path(tempfile.mkdtemp(prefix="js_agent_skills_skill_"))
    shutil.copytree(skill_src, out / name)
    return out


def _bundled_skill_name() -> Optional[str]:
    """The single skill name this frozen installer was built for."""
    root = _bundled_skill_root()
    if root is None:
        return None
    try:
        skills = discover_skills(root)
        return skills[0].name if skills else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# tkinter bootstrap
# ---------------------------------------------------------------------------


def _prep_tcl_tk_env() -> None:
    """Point TCL_LIBRARY / TK_LIBRARY at the bundled tcl/tk script dirs.

    PyInstaller's tkinter runtime hook normally does this (it looks for
    ``_tcl_data`` / ``_tk_data`` inside ``sys._MEIPASS``); this is the same
    logic as a fallback, in case the hook did not run.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    for var, sub in (("TCL_LIBRARY", "_tcl_data"), ("TK_LIBRARY", "_tk_data")):
        if var not in os.environ:
            p = Path(meipass) / sub
            if p.is_dir():
                os.environ[var] = str(p)


def _tk():
    """Import tkinter (after the tcl/tk env is prepared)."""
    _prep_tcl_tk_env()
    import tkinter  # noqa: F401

    return tkinter


# ---------------------------------------------------------------------------
# The installer window
# ---------------------------------------------------------------------------


class InstallerGUI:
    """A standard-installer-style window: fixed header (title + description),
    multi-select harness framework checklist (full names, alphabetical),
    scope choice, a discovered task-folder picker for project scope, and a
    progress display while installing.  Nothing is preselected -- the user
    must tick at least one framework and pick a scope before Install
    enables."""

    def __init__(self, root, repo_root: Path, skill_name: Optional[str] = None) -> None:
        # ``root`` is accepted for API compatibility; the real Tk root is
        # created in :meth:`run` (or reused when the caller passes one).
        self._root_arg = root
        self.tk = None
        self.repo_root = Path(repo_root)
        self.skills = discover_skills(self.repo_root)
        if skill_name:
            self.skills = [s for s in self.skills if s.name == skill_name] or self.skills
        if not self.skills:
            raise SystemExit(
                "No skill discovered. Run the installer from the repository "
                "root, or use a per-skill installer binary."
            )

        # No presets: the window opens with nothing selected; the user
        # ticks the framework(s) and the scope explicitly.
        self.platform = ""
        self.scope = ""
        self.project_dir = Path.cwd()

        self._busy = False
        self._last_target: Optional[Path] = None
        self._q: "queue.Queue" = queue.Queue()
        # Main-thread snapshot of the user's choices, filled by
        # _start_install right before the worker thread launches.  The
        # worker must never read Tk variables directly (RuntimeError:
        # "main thread is not in main loop").
        self._install_plan: Optional[dict] = None
        # Completion summary dialog (created by _finish_ok, destroyed by
        # _finish_close).  None until the install finishes.
        self._finish_dialog = None
        self._finish_finish_btn = None
        # Exact skill directory "Open folder" reveals (set with the dialog).
        self._finish_open_dir: Optional[Path] = None

    # ------------------------------------------------------------------
    # selection helpers
    # ------------------------------------------------------------------
    @property
    def meta(self) -> SkillMeta:
        return self.skills[0]

    def _skill(self) -> SkillMeta:
        # Source mode with several skills: follow the skill combobox.
        if self.tk and getattr(self, "_skill_var", None) is not None and len(self.skills) > 1:
            name = self._skill_var.get()
            for s in self.skills:
                if s.name == name:
                    return s
        return self.meta

    def _selected_platforms(self) -> List[str]:
        """Frameworks ticked in the checklist (empty until the user picks)."""
        if not self.tk:
            return [self.platform] if self.platform else []
        return [k for k in _PLATFORM_ORDER if self._platform_vars[k].get()]

    def _current_scope(self) -> str:
        return self._scope_var.get() if self.tk else self.scope

    def _target_for_platform(self, platform: str, scope: Optional[str] = None) -> Path:
        """Install target for one framework under the given scope."""
        scope = scope if scope is not None else self._current_scope()
        if scope == "user":
            return resolve_target_root(platform, "user")
        if scope == "project":
            return self.project_dir / PLATFORMS[platform]["project"]
        raise KeyError(f"no scope selected: {scope!r}")

    def _target(self) -> Path:
        """Resolve the install target for the first selected framework."""
        plats = self._selected_platforms()
        if not plats:
            raise KeyError("no framework selected")
        return self._target_for_platform(plats[0])

    # ------------------------------------------------------------------
    # window construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        tk = self.tk
        from tkinter import ttk

        root = self.root
        meta = self._skill()
        root.title(f"Setup - {meta.name} v{meta.version}")
        root.geometry("640x720")
        root.minsize(580, 620)

        # Selection state.  Nothing is preselected: the window opens with
        # no framework ticked and no scope chosen; Install stays disabled
        # until the user picks at least one framework and a scope.
        self._platform_vars: Dict[str, object] = {
            key: tk.BooleanVar(value=False) for key in _PLATFORM_ORDER
        }
        self._scope_var = tk.StringVar(value="")

        # --- header band: the package title (skill name + version) only.
        #     The full frontmatter description is a long agent contract and
        #     is intentionally NOT shown here (it adds no value in the
        #     installer window and overflows the fixed-size layout). ---------
        band = tk.Frame(root, bg="#f2f4f7", padx=18, pady=14)
        band.pack(fill="x")
        self._title_label = tk.Label(
            band,
            text=f"{meta.name}  v{meta.version}",
            font=("Segoe UI", 15, "bold"),
            bg="#f2f4f7",
            anchor="w",
        )
        self._title_label.pack(fill="x")

        # --- body ---------------------------------------------------------
        body = ttk.Frame(root, padding=16)
        body.pack(fill="both", expand=True)

        # skill picker (source mode with several skills; frozen has exactly one)
        if len(self.skills) > 1:
            ttk.Label(body, text="Skill:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
            names = [s.name for s in self.skills]
            self._skill_var = tk.StringVar(value=names[0])
            ttk.Combobox(
                body, textvariable=self._skill_var, values=names,
                state="readonly", width=48,
            ).pack(anchor="w", pady=(2, 10))
            self._skill_var.trace_add("write", lambda *_a: self._refresh_header())

        ttk.Label(
            body,
            text="Install to (harness framework - tick one or more):",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        pf = ttk.LabelFrame(body, text="Target framework")
        pf.pack(fill="x", pady=(4, 12))
        # One row per framework: the checkbutton carries the full name, a
        # second line underneath shows the resolved target path.
        self._platform_checks: Dict[str, Tuple[object, object]] = {}
        for key in _PLATFORM_ORDER:
            row = ttk.Frame(pf)
            row.pack(fill="x", padx=10, pady=(5, 0))
            cb = ttk.Checkbutton(
                row,
                text=_PLATFORM_LABELS[key],
                variable=self._platform_vars[key],
                command=self._refresh_state,
            )
            cb.pack(anchor="w")
            path_lbl = ttk.Label(
                row, text="", foreground="#555", font=("Segoe UI", 9)
            )
            path_lbl.pack(anchor="w", padx=(26, 0))
            self._platform_checks[key] = (cb, path_lbl)

        ttk.Label(body, text="Scope:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(4, 0))
        sf = ttk.LabelFrame(body, text="Where the skill is installed")
        sf.pack(fill="x", pady=(4, 12))
        ttk.Radiobutton(
            sf,
            text="User - install to your home folder.\n"
                 "Every project of the selected framework(s) can use the skill.",
            variable=self._scope_var,
            value="user",
            command=self._refresh_state,
        ).pack(anchor="w", padx=10, pady=(6, 2))
        ttk.Radiobutton(
            sf,
            text="Project - install into a single task folder.\n"
                 "Only that project sees the skill.",
            variable=self._scope_var,
            value="project",
            command=self._refresh_state,
        ).pack(anchor="w", padx=10, pady=(0, 6))

        # Project folder picker: shown only in project scope.  The dropdown
        # lists task folders detected on this machine; the field stays
        # editable and Browse picks any other folder.
        self._project_row = ttk.Frame(sf)
        ttk.Label(
            self._project_row,
            text="Task folder (detected on this machine - or type any path):",
            font=("Segoe UI", 9),
            foreground="#444",
        ).pack(anchor="w")
        prow = ttk.Frame(self._project_row)
        prow.pack(fill="x", pady=(4, 0))
        self._project_entry = ttk.Combobox(
            prow, values=discover_project_folders(), width=54
        )
        self._project_entry.pack(side="left")
        self._project_entry.bind(
            "<<ComboboxSelected>>", lambda _e: self._commit_project_entry()
        )
        self._project_entry.bind("<Return>", lambda _e: self._commit_project_entry())
        self._project_entry.bind(
            "<FocusOut>", lambda _e: self._commit_project_entry()
        )
        ttk.Button(
            prow, text="Browse...", command=self._browse, width=12
        ).pack(side="left", padx=(8, 0))
        self._target_summary = ttk.Label(
            self._project_row, text="", foreground="#555", font=("Segoe UI", 9),
            wraplength=520, justify="left",
        )
        self._target_summary.pack(anchor="w", pady=(6, 0))

        # --- progress + status (shown during install) ---------------------
        # Determinate 0-100: the worker reports per-file progress, so the
        # bar behaves like a standard downloader (never an aimless spinner).
        self._progress = ttk.Progressbar(
            body, mode="determinate", maximum=100, length=560
        )
        self._status_var = tk.StringVar(value="")
        status = ttk.Label(
            body, textvariable=self._status_var, wraplength=560,
            foreground="#333", justify="left",
        )
        status.pack(anchor="w", pady=(12, 0))
        # Keep the *widget* reference: pack(before=...) needs a sibling
        # widget, and passing the StringVar here raises a TclError that
        # silently kills the install click (see _start_install).
        self._status_label = status

        # --- buttons ------------------------------------------------------
        bf = ttk.Frame(root, padding=(16, 0, 16, 16))
        bf.pack(fill="x")
        self._install_btn = ttk.Button(
            bf, text="Install", width=14, command=self._start_install, state="disabled"
        )
        self._install_btn.pack(side="left")
        self._cancel_btn = ttk.Button(bf, text="Cancel", width=12, command=root.destroy)
        self._cancel_btn.pack(side="right")

        self._refresh_state()

    def _refresh_header(self) -> None:
        """Re-render the fixed header after the skill combobox changes."""
        if not self.tk:
            return
        meta = self._skill()
        self._title_label.config(text=f"{meta.name}  v{meta.version}")

    def _refresh_state(self) -> None:
        """Single source of truth for every derived UI state."""
        if not self.tk:
            return
        scope = self._scope_var.get()
        plats = self._selected_platforms()

        # Per-framework target path (second line of each checklist row).
        for key, (_cb, path_lbl) in self._platform_checks.items():
            if scope == "user":
                path_lbl.config(text=str(resolve_target_root(key, "user")))
            elif scope == "project":
                path_lbl.config(
                    text=str(self.project_dir / PLATFORMS[key]["project"])
                )
            else:
                path_lbl.config(text="- pick a scope below -")

        # Project picker: visible only in project scope.
        if scope == "project":
            self._project_row.pack(fill="x", padx=10, pady=(2, 8))
            self._update_target_summary(plats)
        else:
            self._project_row.pack_forget()

        # Install enablement + guidance line.
        if plats and scope:
            self._install_btn.config(state="normal")
            self._set_status(
                f"Ready to install into {len(plats)} framework(s). Click Install."
            )
        else:
            self._install_btn.config(state="disabled")
            missing = []
            if not plats:
                missing.append("at least one framework")
            if not scope:
                missing.append("a scope")
            self._set_status("Select " + " and ".join(missing) + " to continue.")

    def _update_target_summary(self, plats: List[str]) -> None:
        if not plats:
            self._target_summary.config(
                text="(tick a framework above to see the install path)"
            )
            return
        parts = [str(self.project_dir / PLATFORMS[k]["project"]) for k in plats]
        self._target_summary.config(
            text="Will install to:   " + "   +   ".join(parts)
        )

    def _commit_project_entry(self) -> None:
        """Adopt the text currently in the project-folder combobox."""
        if not self.tk:
            return
        text = self._project_entry.get().strip().strip('"')
        if text:
            self.project_dir = Path(text)
            self._refresh_state()

    def _browse(self) -> None:
        from tkinter import filedialog

        chosen = filedialog.askdirectory(
            title="Choose the task folder to install into",
            initialdir=str(self.project_dir),
        )
        if chosen:
            self.project_dir = Path(chosen)
            self._project_entry.set(str(self.project_dir))
            self._refresh_state()

    # ------------------------------------------------------------------
    # install flow (worker thread + progress display)
    # ------------------------------------------------------------------
    def _set_status(self, text: str) -> None:
        self._status_var.set(text)

    def _start_install(self) -> None:
        if self._busy:
            return
        if not self._selected_platforms() or not self._current_scope():
            # Defensive: the button is disabled until both are chosen.
            self._refresh_state()
            return
        self._busy = True
        self._install_btn.config(state="disabled")
        self._cancel_btn.config(state="disabled")
        self._progress.pack(fill="x", pady=(4, 0), before=self._status_label)
        self._progress.config(mode="determinate", maximum=100)
        self._progress["value"] = 0
        self._set_status("Preparing...")
        # Snapshot every Tk-backed selection HERE, on the main thread.  The
        # worker thread below must never call .get() on a Tk variable.
        self._install_plan = {
            "skill": self._skill(),
            "platforms": list(self._selected_platforms()),
            "scope": self._current_scope(),
        }
        self._q = queue.Queue()
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()
        self.root.after(60, self._poll)

    def _worker(self) -> None:
        q = self._q
        # Everything Tk-backed was snapshotted on the main thread in
        # _start_install; this thread only touches the filesystem + queue.
        plan = self._install_plan or {}
        meta = plan.get("skill") or self.meta
        platforms = list(plan.get("platforms") or [])
        scope = plan.get("scope") or ""
        n_plats = len(platforms)

        def say(msg: str) -> None:
            q.put(("status", msg))

        try:
            if _is_frozen():
                say("Extracting bundled skill...")
            ok, dep_msgs = check_dependencies(meta)
            say("Checking dependencies... " + ("OK" if ok else "missing"))
            if not ok:
                q.put(("error", "\n".join(dep_msgs)))
                return
            results = []
            for idx, plat in enumerate(platforms):
                label = _PLATFORM_LABELS[plat]
                # Explicit scope: never read Tk state from this thread.
                target = self._target_for_platform(plat, scope)
                self._last_target = target
                say(f"Installing to {label} ({idx + 1}/{n_plats}) ...")

                def _on_file(done, total, name, _label=label, _idx=idx, _n=n_plats):
                    # Runs inside copytree (worker thread): forward per-file
                    # progress to the UI queue.  Never raises into the copy.
                    q.put(("progress", (_idx, _n, done, total, name, _label)))

                _, msg = install_skill(
                    meta, target, force=True,
                    keep=keep_paths_for(meta.name), progress=_on_file,
                )
                say(f"Verifying {label} ...")
                vok, vmsg = verify_install(meta, target)
                results.append((label, target, vok, vmsg, msg))
            failed = [r for r in results if not r[2]]
            if failed:
                q.put((
                    "error",
                    "Failed targets:\n"
                    + "\n".join(f"  {r[0]} -> {r[1]}" for r in failed),
                ))
                return
            q.put(("done", results))
        except Exception as e:  # pragma: no cover - defensive
            q.put(("error", f"{type(e).__name__}: {e}"))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "status":
                    self._set_status(payload)
                elif kind == "progress":
                    idx, n, done, total, name, label = payload
                    if total:
                        self._progress["value"] = round(done * 100 / total)
                    head = f"Installing to {label} ({idx + 1}/{n}) ..."
                    if total:
                        head += f"   [{done}/{total}] {name}"
                    self._set_status(head)
                elif kind == "error":
                    self._finish_error(payload)
                    return
                else:
                    self._finish_ok(payload)
                    return
        except queue.Empty:
            pass
        self.root.after(60, self._poll)

    def _finish_error(self, message: str) -> None:
        self._busy = False
        try:
            self._progress.stop()
        except Exception:
            pass
        self._set_status("Installation failed:\n" + message)
        self._install_btn.config(state="normal")
        self._cancel_btn.config(state="normal")
        from tkinter import messagebox

        messagebox.showerror("Installation failed", message)

    def _finish_ok(self, results) -> None:
        self._busy = False
        self._progress["value"] = 100
        # Hide the bar: a full green bar reads as "still installing".  An
        # explicit completion line is unambiguous.
        self._progress.pack_forget()
        meta = (self._install_plan or {}).get("skill") or self.meta
        # The main window keeps a ONE-LINE status only.  The full per-target
        # summary (one long path per framework) used to grow this label until
        # it overflowed the fixed-size setup window; it now lives in a
        # separate modal dialog (see _show_finish_dialog).
        self._set_status(
            f"Installation complete - {meta.name} v{meta.version} "
            f"installed to {len(results)} framework(s)."
        )
        # The main window is finished: both buttons are disabled, and the
        # summary dialog drives the ending (its Finish closes both windows).
        self._install_btn.config(state="disabled")
        self._cancel_btn.config(state="disabled")
        self._show_finish_dialog(meta, results)

    def _show_finish_dialog(self, meta, results) -> None:
        """Modal summary dialog opened when the install completes.

        Rationale: the completion state lists one absolute path per target
        framework.  Rendered inside the main window that list grows without
        bound and overflows the fixed 640x660 geometry; a dedicated dialog
        sizes itself to the content and ends the session explicitly.
        """
        tk = self.tk
        from tkinter import ttk

        dlg = tk.Toplevel(self.root)
        dlg.title("Installation complete")
        # Stay on top of the setup window and take focus.
        dlg.transient(self.root)
        dlg.resizable(False, False)
        # Closing via the window manager's X behaves exactly like Finish.
        dlg.protocol("WM_DELETE_WINDOW", self._finish_close)
        self._finish_dialog = dlg

        frame = ttk.Frame(dlg, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=f"{meta.name} v{meta.version} installed to "
                 f"{len(results)} framework(s):",
            font=("Segoe UI", 10, "bold"),
            wraplength=480,
            justify="left",
        ).pack(anchor="w")

        # Scrollable path list: bounded height, never overflows the dialog.
        lb_frame = ttk.Frame(frame)
        lb_frame.pack(fill="both", expand=True, pady=(10, 0))
        # Size the list to the longest entry (capped) so typical absolute
        # paths are fully visible; the horizontal scrollbar covers the rest.
        entries_text = [f"{label}:  {Path(target) / meta.name}"
                        for label, target, _v, _m, _msg in results]
        width = min(110, max(60, max((len(e) for e in entries_text), default=60) + 2))
        lb = tk.Listbox(
            lb_frame, height=min(8, max(3, len(results))), width=width,
            font=("Segoe UI", 9), activestyle="none",
        )
        sb = ttk.Scrollbar(lb_frame, orient="vertical", command=lb.yview)
        # Absolute paths routinely exceed the dialog width -- without a
        # horizontal scrollbar the tail (e.g. the skill's own directory) is
        # clipped and unreadable.
        hb = ttk.Scrollbar(lb_frame, orient="horizontal", command=lb.xview)
        lb.configure(yscrollcommand=sb.set, xscrollcommand=hb.set)
        lb.pack(side="top", fill="both", expand=True)
        hb.pack(side="bottom", fill="x")
        sb.pack(side="right", fill="y")
        for text in entries_text:
            lb.insert("end", text)
        skill_dirs = [Path(target) / meta.name
                      for _label, target, _v, _m, _msg in results]
        self._finish_open_dir = skill_dirs[-1] if skill_dirs else None

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(14, 0))
        ttk.Button(
            btns, text="Open folder", width=12, command=self._open_target
        ).pack(side="left")
        finish_btn = ttk.Button(
            btns, text="Finish", width=14, command=self._finish_close
        )
        finish_btn.pack(side="right")
        self._finish_finish_btn = finish_btn

        # Centre the dialog over the setup window (best effort; a withdrawn
        # or off-screen parent simply yields a default position).
        dlg.update_idletasks()
        try:
            rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
            dw, dh = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
            dlg.geometry(f"+{rx + max(0, (rw - dw) // 2)}+{ry + max(0, (rh - dh) // 2)}")
        except Exception:
            pass
        dlg.lift()
        try:
            dlg.focus_force()
        except Exception:
            pass
        # Modality is best effort: grab_set can fail on a not-yet-viewable
        # window (e.g. headless tests); the dialog works either way.
        try:
            dlg.grab_set()
        except Exception:
            pass

    def _finish_close(self) -> None:
        """Finish: close the summary dialog AND the main window."""
        dlg = self._finish_dialog
        if dlg is not None:
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()
        self.root.destroy()

    def _open_target(self) -> None:
        # Prefer the exact skill directory offered by the completion dialog.
        target = getattr(self, "_finish_open_dir", None) or self._last_target
        if target is None:
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(target))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", str(target)], check=False)
            else:
                subprocess.run(["xdg-open", str(target)], check=False)
        except Exception as e:
            from tkinter import messagebox

            messagebox.showerror("Open folder", str(e))

    # ------------------------------------------------------------------
    def run(self) -> int:
        tk = _tk()
        self.tk = tk
        root = self._root_arg if self._root_arg is not None else tk.Tk()
        self.root = root
        self._build_ui()
        root.mainloop()
        return 0


# ---------------------------------------------------------------------------
# CLI + self-check
# ---------------------------------------------------------------------------


def _cli_install(app: "InstallerGUI", argv: List[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="installer", description="Headless skill install")
    # No argparse ``choices`` here: values may be comma-separated, which is
    # validated *after* splitting below (argparse would reject the raw
    # "workbuddy,claude" string before we ever get to split it).
    p.add_argument(
        "--platform", action="append", default=None,
        help="target framework (repeatable or comma-separated; default: workbuddy)",
    )
    p.add_argument("--scope", default="user", choices=["user", "project"])
    p.add_argument("--dir", default=None, help="task folder (project scope only)")
    a = p.parse_args(argv)

    meta = app.meta
    ok, dep_msgs = check_dependencies(meta)
    for line in dep_msgs:
        print(line)
    if not ok:
        print("Refusing to install: unmet dependencies.")
        return 2

    # Repeatable and/or comma-separated, order-preserving dedupe.
    plats: List[str] = []
    for item in a.platform or ["workbuddy"]:
        for piece in item.split(","):
            piece = piece.strip()
            if piece and piece not in plats:
                plats.append(piece)
    unknown = [p for p in plats if p not in PLATFORMS]
    if unknown:
        print(
            f"Unknown platform(s): {', '.join(unknown)}. "
            f"Choose from: {', '.join(sorted(PLATFORMS))}"
        )
        return 2

    if a.scope == "project":
        app.project_dir = Path(a.dir) if a.dir else Path.cwd()

    all_ok = True
    for plat in plats:
        target = app._target_for_platform(plat, a.scope)
        print(
            f"Installing {meta.name} v{meta.version} to "
            f"{_PLATFORM_LABELS[plat]} -> {target} ..."
        )
        _, msg = install_skill(meta, target, force=True, keep=keep_paths_for(meta.name))
        vok, vmsg = verify_install(meta, target)
        print(msg)
        print(vmsg)
        all_ok = all_ok and vok
    return 0 if all_ok else 1


def _self_check() -> int:
    """Verify the bundled tkinter can initialise; used as a build smoke test."""
    try:
        tk = _tk()
        r = tk.Tk()
        r.withdraw()
        r.destroy()
    except Exception as e:
        print(f"tkinter self-check FAILED: {type(e).__name__}: {e}")
        return 1
    print("tkinter self-check OK")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if "--check" in argv:
        return _self_check()

    frozen = _is_frozen()
    if frozen:
        root_dir = _bundled_skill_root()
        if root_dir is None:
            raise SystemExit(
                "This installer was built without a bundled skill. "
                "Run it from the repository root instead."
            )
        skill_name = _bundled_skill_name()
    else:
        skill_name = None
        root_dir = Path(__file__).resolve().parent.parent

    app = InstallerGUI(None, repo_root=root_dir, skill_name=skill_name)

    if "--cli" in argv:
        rest = [a for a in argv if a != "--cli"]
        return _cli_install(app, rest)

    try:
        return app.run()
    except ImportError as e:
        # No usable GUI (e.g. a stripped Python): fall back to the CLI.
        print(f"GUI unavailable ({e}); falling back to CLI install.")
        print("Re-run with --cli --platform <name> --scope <user|project>")
        return _cli_install(app, [])


if __name__ == "__main__":
    raise SystemExit(main())
