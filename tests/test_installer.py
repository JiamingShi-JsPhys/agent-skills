"""Unit tests for installer.platform_paths and installer.installer_core.

These exercise the pure-logic modules only; the GUI / CLI entry points
require a real home directory and are tested through :mod:`installer_core`
with a tmp target root.
"""

from __future__ import annotations

import json
import shutil
import sys
from typing import Optional
from pathlib import Path

import pytest

from installer.installer_core import (  # noqa: E402
    INSTALL_MANIFEST,
    check_dependencies,
    install_skill,
    uninstall_skill,
    verify_install,
)
from installer.platform_paths import (  # noqa: E402
    PLATFORMS,
    known_platforms,
    resolve_target_root,
)
from installer.skill_loader import SkillMeta, discover_skills, load_skill_meta  # noqa: E402


# ---------------------------------------------------------------------------
# platform_paths
# ---------------------------------------------------------------------------

def test_known_platforms_cover_spec() -> None:
    # The shared (.agents/skills) option was removed at the user's request.
    assert set(known_platforms()) == {"workbuddy", "claude", "codex", "dsh"}


def test_platform_labels_are_full_names() -> None:
    from installer.installer_gui import _PLATFORM_LABELS, _PLATFORM_ORDER

    # Full product names, as requested.
    assert _PLATFORM_LABELS == {
        "claude": "Claude Code",
        "codex": "OpenAI Codex",
        "dsh": "DeepSeek Harness",
        "workbuddy": "WorkBuddy",
    }
    # No "shared" option anywhere.
    assert "shared" not in _PLATFORM_LABELS
    # Checklist order follows the displayed label alphabetically.
    labels = [_PLATFORM_LABELS[k] for k in _PLATFORM_ORDER]
    assert labels == sorted(labels)
    assert len(labels) == 4


def test_discover_project_folders_finds_marked_dirs(tmp_path: Path) -> None:
    from installer.installer_gui import discover_project_folders

    (tmp_path / "repo_a" / ".git").mkdir(parents=True)
    (tmp_path / "wb_proj" / ".workbuddy").mkdir(parents=True)
    (tmp_path / "plain_dir").mkdir()
    (tmp_path / ".hidden_proj" / ".git").mkdir(parents=True)
    (tmp_path / "loose.txt").write_text("x", encoding="utf-8")

    found = discover_project_folders(roots=[tmp_path])
    names = {Path(p).name for p in found}
    assert "repo_a" in names
    assert "wb_proj" in names
    assert "plain_dir" not in names
    assert ".hidden_proj" not in names  # dot-dirs are never task folders


def test_discover_project_folders_tolerates_missing_roots(tmp_path: Path) -> None:
    from installer.installer_gui import discover_project_folders

    # A non-existent root must be skipped, not raised.
    assert discover_project_folders(roots=[tmp_path / "nope"]) == []


def test_resolve_target_root_user_scope_expands_home() -> None:
    p = resolve_target_root("workbuddy", "user")
    # User scope must be under the OS home dir.
    assert p.parent.parent.name != ""  # sanity
    assert str(p).endswith(".workbuddy/skills") or str(p).endswith(".workbuddy\\skills")


def test_resolve_target_root_project_scope_is_cwd_relative(tmp_path, monkeypatch) -> None:
    """Project scope must resolve relative to the CWD, not the home dir."""
    import os

    # Force CWD to a tmp dir so the project path is CWD-relative.
    monkeypatch.chdir(tmp_path)
    p = resolve_target_root("claude", "project")
    assert p.name == "skills"
    # The path must start with the CWD (not the home dir)
    assert str(p).startswith(str(tmp_path))


def test_resolve_target_root_unknown_platform_raises() -> None:
    with pytest.raises(KeyError):
        resolve_target_root("nope", "user")


def test_resolve_target_root_unknown_scope_raises() -> None:
    with pytest.raises(KeyError):
        resolve_target_root("workbuddy", "bogus")


def test_platforms_mapping_shape() -> None:
    for plat, mapping in PLATFORMS.items():
        assert "user" in mapping
        assert "project" in mapping
        assert mapping["user"]
        assert mapping["project"]


# ---------------------------------------------------------------------------
# installer_core (with a synthetic skill)
# ---------------------------------------------------------------------------

def _make_skill(tmp_path: Path, name: str = "test_skill") -> SkillMeta:
    """Create a minimal skill on disk and return its meta."""
    d = tmp_path / "fake_repo" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\n"
        "name: test_skill\n"
        "version: 1.0.0\n"
        "author: Jiaming Shi\n"
        "license: MIT\n"
        "entry: src/cli.py\n"
        "metadata:\n"
        "  python_requires: '>=3.9'\n"
        "  python_dependencies: []\n"
        "---\n\n# test\n",
        encoding="utf-8",
    )
    (d / "src").mkdir()
    (d / "src" / "cli.py").write_text("def main(): pass\n", encoding="utf-8")
    return load_skill_meta(d)


def test_load_skill_meta_synthesizes_from_frontmatter(tmp_path: Path) -> None:
    meta = _make_skill(tmp_path)
    assert meta.name == "test_skill"
    assert meta.version == "1.0.0"
    assert meta.author == "Jiaming Shi"
    assert meta.has_skill_md


def test_load_skill_meta_bare_skill(tmp_path: Path) -> None:
    d = tmp_path / "fake_repo2" / "bare_skill"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text("---\nname: bare_skill\nversion: 2.0.0\n---\n", encoding="utf-8")
    meta = load_skill_meta(d)
    assert meta.name == "bare_skill"
    assert meta.version == "2.0.0"
    assert meta.has_skill_md


def test_load_skill_meta_rejects_non_skill_dir(tmp_path: Path) -> None:
    d = tmp_path / "fake_repo3" / "not_a_skill"
    d.mkdir(parents=True, exist_ok=True)
    with pytest.raises(FileNotFoundError):
        load_skill_meta(d)


def test_discover_skills_finds_root_and_skills_dir(tmp_path: Path) -> None:
    repo = tmp_path / "fake_repo"
    repo.mkdir()
    # Root-level skill.
    (repo / "root_skill").mkdir()
    (repo / "root_skill" / "SKILL.md").write_text("---\nname: root_skill\nversion: 1.0.0\n---\n", encoding="utf-8")
    # skills/ subdirectory.
    (repo / "skills" / "nested_skill").mkdir(parents=True, exist_ok=True)
    (repo / "skills" / "nested_skill" / "SKILL.md").write_text("---\nname: nested_skill\nversion: 1.0.0\n---\n", encoding="utf-8")

    found = discover_skills(repo)
    names = {m.name for m in found}
    assert names == {"root_skill", "nested_skill"}


def test_discover_skills_dedupe_root_wins(tmp_path: Path) -> None:
    repo = tmp_path / "fake_repo"
    repo.mkdir()
    (repo / "dup").mkdir()
    (repo / "dup" / "SKILL.md").write_text("---\nname: dup\nversion: 1.0.0\n---\n", encoding="utf-8")
    (repo / "skills" / "dup").mkdir(parents=True)
    (repo / "skills" / "dup" / "SKILL.md").write_text("---\nname: dup\nversion: 9.9.9\n---\n", encoding="utf-8")

    found = discover_skills(repo)
    dup = [m for m in found if m.name == "dup"][0]
    # Root version (1.0.0) wins over skills/ version (9.9.9).
    assert dup.version == "1.0.0"


def test_install_skill_creates_copy(tmp_path: Path) -> None:
    meta = _make_skill(tmp_path)
    target = tmp_path / "target"
    ok, msg = install_skill(meta, target, force=False, dry_run=False)
    assert ok
    assert (target / "test_skill" / "SKILL.md").exists()


def test_install_skill_dry_run_no_write(tmp_path: Path) -> None:
    meta = _make_skill(tmp_path)
    target = tmp_path / "target"
    ok, msg = install_skill(meta, target, dry_run=True)
    assert ok
    assert not (target / "test_skill").exists()


def test_install_skill_skips_existing(tmp_path: Path) -> None:
    meta = _make_skill(tmp_path)
    target = tmp_path / "target"
    ok1, _ = install_skill(meta, target)
    assert ok1
    ok2, msg2 = install_skill(meta, target, force=False)
    assert not ok2
    assert "SKIP" in msg2 or "already exists" in msg2


def test_install_skill_force_overwrites(tmp_path: Path) -> None:
    meta = _make_skill(tmp_path)
    target = tmp_path / "target"
    install_skill(meta, target)
    ok, msg = install_skill(meta, target, force=True)
    assert ok
    assert "OK" in msg


def test_install_skill_progress_reports_every_file(tmp_path: Path) -> None:
    # The progress hook powers the downloader-style bar; both the core module
    # and the GUI's self-contained copy must emit it.
    from installer import installer_gui

    d = tmp_path / "fake_repo" / "progress_skill"
    (d / "sub").mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: progress_skill\nversion: 1.0.0\n---\n", encoding="utf-8")
    (d / "run.py").write_text("x = 1\n", encoding="utf-8")
    (d / "sub" / "a.txt").write_text("a\n", encoding="utf-8")
    (d / "sub" / "b.txt").write_text("b\n", encoding="utf-8")
    meta = load_skill_meta(d)

    for fn in (install_skill, installer_gui.install_skill):
        events: list = []
        target = tmp_path / f"target_{fn.__module__}"
        ok, _ = fn(meta, target, progress=lambda done, total, name: events.append((done, total, name)))
        assert ok
        # 4 files + one final tick; monotonic, exact total, ends complete.
        assert [e[0] for e in events] == [1, 2, 3, 4, 4], events
        assert {e[1] for e in events} == {4}
        assert events[-1][2] == ""  # final tick carries no file name
        assert (target / "progress_skill" / "sub" / "b.txt").exists()


def test_install_skill_progress_hook_exception_is_swallowed(tmp_path: Path) -> None:
    # A broken progress display must never break the install itself.
    def _boom(done, total, name):
        raise RuntimeError("display exploded")

    meta = _make_skill(tmp_path)
    target = tmp_path / "target"
    ok, msg = install_skill(meta, target, progress=_boom)
    assert ok
    assert (target / "test_skill" / "SKILL.md").exists()


def test_gui_install_button_click_completes(tmp_path: Path) -> None:
    """Regression guard: clicking Install must actually install.

    Two bugs used to live on this path, both invisible to CLI-only tests:
    ``pack(before=<StringVar>)`` raised a TclError that killed the click,
    and the worker thread read Tk variables off the main thread
    (RuntimeError: main thread is not in main loop).  This test drives the
    real window: tick frameworks, pick scope, click, pump the loop.
    """
    import time

    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except Exception as e:  # no display (headless CI)
        pytest.skip(f"tkinter unavailable: {e}")

    from installer import installer_gui

    repo_root = Path(__file__).resolve().parent.parent
    root.withdraw()
    app = installer_gui.InstallerGUI(root, repo_root=repo_root, skill_name="task-organizer")
    app.tk = tk
    app.root = root
    app._build_ui()
    root.update()

    cb_errors: list = []
    root.report_callback_exception = lambda exc, val, tb: cb_errors.append(val)

    proj = tmp_path / "proj"
    proj.mkdir()
    for k in ("workbuddy", "claude"):
        app._platform_vars[k].set(True)
    app._scope_var.set("project")
    app._project_entry.delete(0, "end")
    app._project_entry.insert(0, str(proj))
    app._commit_project_entry()
    app._refresh_state()
    root.update()

    # Swap in a destroy spy BEFORE the install: the completion dialog's
    # Finish command calls ``self.root.destroy`` (via _finish_close), so the
    # spy lets the test click Finish for real without killing the window
    # (the finally block below destroys it for real afterwards).
    real_destroy = root.destroy
    destroyed: list = []
    root.destroy = lambda: destroyed.append(True)  # type: ignore[method-assign]

    try:
        app._start_install()
        for _ in range(600):  # up to ~30s
            root.update()
            if not app._busy:
                break
            time.sleep(0.05)
        root.update()

        assert not cb_errors, f"Tk callback exceptions: {cb_errors}"
        assert not app._busy, "install never finished"
        # Completion state: the main window shows a one-line status and both
        # buttons are disabled -- the summary dialog drives the ending (the
        # full per-target path list used to overflow the main window).
        assert app._progress["value"] == 100
        assert app._progress.winfo_manager() != "pack"
        assert app._status_var.get().startswith("Installation complete")
        assert str(app._install_btn["state"]) == "disabled"
        assert str(app._cancel_btn["state"]) == "disabled"
        assert (proj / ".workbuddy" / "skills" / "task-organizer" / "SKILL.md").exists()
        assert (proj / ".claude" / "skills" / "task-organizer" / "SKILL.md").exists()
        # A modal summary dialog opened, listing every target.
        dlg = app._finish_dialog
        assert dlg is not None, "no completion dialog"
        assert dlg.title() == "Installation complete"
        def _descendants(w):
            # The listbox lives one level deeper (dlg > frame > lb_frame > lb);
            # walk the whole widget tree instead of assuming a fixed depth.
            for c in w.winfo_children():
                yield c
                yield from _descendants(c)

        listboxes = [
            w for w in _descendants(dlg) if w.winfo_class() == "Listbox"
        ]
        assert listboxes, "dialog has no path list"
        # Absolute paths exceed the dialog width: a horizontal scrollbar is
        # mandatory, otherwise the tail (the skill's own directory) is
        # clipped and unreadable.
        hbars = [
            w for w in _descendants(dlg)
            if w.winfo_class() in ("Scrollbar", "TScrollbar")
            and str(w.cget("orient")) == "horizontal"
        ]
        assert hbars, "dialog list has no horizontal scrollbar"
        entries = listboxes[0].get(0, "end")
        assert len(entries) == 2, f"expected 2 targets, got {entries}"
        # Each entry names the framework AND the exact skill directory it
        # installed into (the framework root alone does not say where the
        # skill itself landed).
        for e in entries:
            assert "task-organizer" in e, e
            assert e.replace("\\", "/").endswith("skills/task-organizer"), e
        assert any(e.startswith("WorkBuddy") for e in entries), entries
        assert any(e.startswith("Claude Code") for e in entries), entries
        # The listbox must be wide enough to show the longest entry (capped
        # at 110 chars); a too-narrow list clips the path tail.
        longest = max(len(e) for e in entries)
        expected_w = min(110, max(60, longest + 2))
        assert int(listboxes[0]["width"]) >= expected_w, (
            f"list width {listboxes[0]['width']} < {expected_w}"
        )
        assert app._finish_finish_btn is not None
        # Finish in the dialog must close BOTH windows: the dialog for real,
        # the main window through the destroy spy.
        app._finish_finish_btn.invoke()
        root.update()
        assert not dlg.winfo_exists(), "Finish did not close the dialog"
        assert destroyed, "Finish did not close the main window"
    finally:
        real_destroy()


def test_uninstall_skill(tmp_path: Path) -> None:
    meta = _make_skill(tmp_path)
    target = tmp_path / "target"
    install_skill(meta, target)
    ok, msg = uninstall_skill("test_skill", target)
    assert ok
    assert not (target / "test_skill").exists()


def test_uninstall_skill_missing_reports_not_found(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    ok, msg = uninstall_skill("ghost", target)
    assert not ok
    assert "NOT FOUND" in msg


def test_verify_install_ok(tmp_path: Path) -> None:
    meta = _make_skill(tmp_path)
    target = tmp_path / "target"
    install_skill(meta, target)
    ok, msg = verify_install(meta, target)
    assert ok
    assert "OK" in msg


def test_verify_install_missing_skill_md(tmp_path: Path) -> None:
    meta = _make_skill(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    ok, msg = verify_install(meta, target)
    assert not ok
    assert "missing SKILL.md" in msg or "ERROR" in msg


def test_check_dependencies_ok(tmp_path: Path) -> None:
    meta = _make_skill(tmp_path)
    ok, msgs = check_dependencies(meta, verbose=False)
    assert ok
    # Python dep satisfied (we are running on >= 3.8).
    assert any(m.startswith("OK") for m in msgs)


# ---------------------------------------------------------------------------
# Install manifest (lean runtime copy)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


def _expected_installed_files(skill_dir: Path, keep) -> set:
    """Relative posix paths a manifest install must produce."""
    from installer.installer_core import _keep_ignore

    out = set()
    for p in _iter_files(skill_dir, _keep_ignore(skill_dir, keep)):
        out.add(p.relative_to(skill_dir).as_posix())
    return out


def _iter_files(root: Path, ignore_fn):
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        skipped = set(ignore_fn(dirpath, list(dirnames) + list(filenames)))
        dirnames[:] = [d for d in dirnames if d not in skipped]
        for name in filenames:
            if name not in skipped:
                yield Path(dirpath) / name


def test_install_manifest_matches_gui_inline_copy() -> None:
    # Frozen builds cannot import installer_core, so installer_gui.py keeps
    # an inline copy of the manifest; the two must never drift apart.
    from installer import installer_core, installer_gui

    assert installer_core.INSTALL_MANIFEST == installer_gui.INSTALL_MANIFEST


def test_install_manifest_matches_web_script() -> None:
    # install-web.ps1 is the no-Python route and carries its own table.
    from installer.installer_core import INSTALL_MANIFEST

    text = (REPO_ROOT / "install-web.ps1").read_text(encoding="utf-8")
    start = text.index("$InstallManifest = @{")
    end = text.index("}", start)
    block = text[start:end]
    parsed = {}
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith('"'):
            continue
        name, _, rest = line.partition("=")
        name = name.strip().strip('"')
        rest = rest.strip()
        if rest.startswith("@("):
            rest = rest[2:]
        if rest.endswith(")"):
            rest = rest[:-1]
        entries = [e.strip().strip('"') for e in rest.split(",")]
        parsed[name] = [e for e in entries if e]
    assert parsed == INSTALL_MANIFEST


@pytest.mark.parametrize("skill", sorted(INSTALL_MANIFEST))
def test_install_skill_installs_only_manifest_files(skill: str, tmp_path: Path) -> None:
    """The installed copy is lean: exactly the manifest, nothing else."""
    from installer.installer_core import INSTALL_MANIFEST

    skill_dir = SKILLS_DIR / skill
    meta = load_skill_meta(skill_dir)
    keep = INSTALL_MANIFEST[skill]
    target = tmp_path / "skills_root"
    ok, _ = install_skill(meta, target, force=True, keep=keep)
    assert ok
    installed = target / skill

    got = {
        p.relative_to(installed).as_posix()
        for p in installed.rglob("*") if p.is_file()
    }
    expected = _expected_installed_files(skill_dir, keep)
    assert got == expected, (
        f"installed set differs from manifest: "
        f"extra={sorted(got - expected)} missing={sorted(expected - got)}"
    )
    # SKILL.md must be byte-identical (the agent-facing contract).
    assert (installed / "SKILL.md").read_bytes() == (skill_dir / "SKILL.md").read_bytes()
    # Repo-only material must never reach the user's skills folder.
    for junk in (
        "README.md", "README_zh.md", "CHANGELOG.md", "AUTHORS.md",
        "CITATION.cff", "CONTRIBUTING.md", "LICENSE", "pyproject.toml",
        "requirements.txt", ".gitignore",
    ):
        assert not (installed / junk).exists(), f"{junk} must not be installed"
    assert not (installed / "tests").exists(), "tests/ must not be installed"


def test_manifest_keeps_runtime_referenced_files(tmp_path: Path) -> None:
    """Spot-check the boundary decisions behind the manifest."""
    from installer.installer_core import INSTALL_MANIFEST

    cases = {
        # SKILL.md's usage examples run against this file verbatim.
        "multi-dim-manager": (["config.example.yaml"], []),
        # R scripts are invoked at runtime; the example config is too.
        "longitudinal-analysis": (
            ["R/lmm.R", "R/mediation.R", "config/examples/behavior_2x2x2.yaml"],
            # Nothing loads the schema; it is documentation and stays in
            # the repo / source archive.
            ["config/schema.yaml"],
        ),
        # init writes its own .task-organizer.yml template and builds the
        # broadcast index inline, so assets/ is repo-only.
        "task-organizer": (["scripts/run.py"], ["assets/index-template.md"]),
    }
    for skill, (mustHave, mustNotHave) in cases.items():
        skill_dir = SKILLS_DIR / skill
        meta = load_skill_meta(skill_dir)
        target = tmp_path / "skills_root"
        ok, _ = install_skill(
            meta, target, force=True, keep=INSTALL_MANIFEST[skill]
        )
        assert ok
        installed = target / skill
        for rel in mustHave:
            assert (installed / rel).exists(), f"{skill}: {rel} must install"
        for rel in mustNotHave:
            assert not (installed / rel).exists(), (
                f"{skill}: {rel} must NOT install"
            )


def test_install_skill_without_keep_copies_everything(tmp_path: Path) -> None:
    """keep=None keeps the legacy behaviour (full copy minus caches)."""
    meta = _make_skill(tmp_path)
    target = tmp_path / "full_copy"
    ok, _ = install_skill(meta, target)
    assert ok
    assert (target / "test_skill" / "SKILL.md").exists()
    assert (target / "test_skill" / "src" / "cli.py").exists()


# ---------------------------------------------------------------------------
# CLI install (installer_gui._cli_install)
# ---------------------------------------------------------------------------

class _FakeCLIApp:
    """Minimal stand-in for InstallerGUI: only what _cli_install touches.

    ``_target_for_platform`` mirrors the real one (user scope resolves via
    :func:`resolve_target_root`; project scope uses the platform's project
    relative path) so the assertions below check real install layouts.
    """

    def __init__(self, meta: SkillMeta, project_dir: Path) -> None:
        self.meta = meta
        self.project_dir = project_dir

    def _target_for_platform(self, platform: str, scope: Optional[str] = None) -> Path:
        scope = scope or "user"
        if scope == "project":
            return self.project_dir / PLATFORMS[platform]["project"]
        return resolve_target_root(platform, "user")


def test_cli_install_multi_platform_comma_and_repeat(tmp_path: Path) -> None:
    from installer.installer_gui import _cli_install

    meta = _make_skill(tmp_path)
    proj = tmp_path / "proj"
    app = _FakeCLIApp(meta, proj)

    # Comma-separated: one flag, several frameworks (this used to be rejected
    # by argparse `choices` before the string was ever split).
    rc = _cli_install(
        app, ["--platform", "workbuddy,claude", "--scope", "project", "--dir", str(proj)]
    )
    assert rc == 0
    assert (proj / ".workbuddy" / "skills" / "test_skill" / "SKILL.md").exists()
    assert (proj / ".claude" / "skills" / "test_skill" / "SKILL.md").exists()

    # Repeatable flag, mixed with a comma group; order-preserving dedupe.
    rc2 = _cli_install(
        app,
        ["--platform", "dsh", "--platform", "codex,dsh", "--scope", "project", "--dir", str(proj)],
    )
    assert rc2 == 0
    assert (proj / ".dsh" / "skills" / "test_skill" / "SKILL.md").exists()
    # Codex's project layout is the shared agents root, not .codex.
    assert (proj / ".agents" / "skills" / "test_skill" / "SKILL.md").exists()


def test_cli_install_rejects_unknown_platform(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from installer.installer_gui import _cli_install

    meta = _make_skill(tmp_path)
    app = _FakeCLIApp(meta, tmp_path / "proj")
    rc = _cli_install(app, ["--platform", "bogus"])
    assert rc == 2
    assert "Unknown platform(s): bogus" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Frozen bundle extraction (installer_gui._bundled_skill_root)
# ---------------------------------------------------------------------------
#
# These guard the exact regression that broke the shipped .exe installers:
# a frozen bundle must surface as ONE discovered skill whose name / version
# / description come from the baked-in SKILL.md -- never "_BUNDLED_SKILL".

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _stage_frozen_bundle(tmp_path: Path, skill: str, nested: bool) -> str:
    """Build a fake ``sys._MEIPASS/_BUNDLED_SKILL`` tree for one real skill.

    Mirrors the two layouts PyInstaller can produce from the staged skill
    archive: either ``_BUNDLED_SKILL/SKILL.md`` (direct) or
    ``_BUNDLED_SKILL/<skill>/SKILL.md`` (container wraps one subdir).
    """
    meipass = tmp_path / "_meipass"
    bundle = meipass / "_BUNDLED_SKILL"
    if nested:
        bundle = bundle / skill
    bundle.mkdir(parents=True)
    shutil.copy2(_REPO_ROOT / "skills" / skill / "SKILL.md", bundle / "SKILL.md")
    return str(meipass)


def _assert_discovered(root: Path, expected_name: str, expected_version: str) -> None:
    from installer.installer_gui import discover_skills

    skills = discover_skills(root)
    assert len(skills) == 1, skills
    assert skills[0].name == expected_name
    assert skills[0].version == expected_version
    assert skills[0].description  # non-empty, pulled from frontmatter
    # The frozen-quirk container name must never leak into the skill.
    assert "_BUNDLED_SKILL" not in skills[0].name


def test_bundled_skill_root_direct_layout(tmp_path: Path, monkeypatch) -> None:
    from installer.installer_gui import _bundled_skill_root, _bundled_skill_name

    meipass = _stage_frozen_bundle(tmp_path, "task-organizer", nested=False)
    monkeypatch.setattr(sys, "_MEIPASS", meipass, raising=False)
    root = _bundled_skill_root()
    assert root is not None
    try:
        # Repository-shaped: exactly one child named after the real skill.
        assert [p.name for p in root.iterdir()] == ["task-organizer"]
        assert (root / "task-organizer" / "SKILL.md").exists()
        assert _bundled_skill_name() == "task-organizer"
        _assert_discovered(root, "task-organizer", "1.0.1")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_bundled_skill_root_nested_layout(tmp_path: Path, monkeypatch) -> None:
    from installer.installer_gui import _bundled_skill_root, _bundled_skill_name

    meipass = _stage_frozen_bundle(tmp_path, "video-tracker", nested=True)
    monkeypatch.setattr(sys, "_MEIPASS", meipass, raising=False)
    root = _bundled_skill_root()
    assert root is not None
    try:
        assert [p.name for p in root.iterdir()] == ["video-tracker"]
        assert (root / "video-tracker" / "SKILL.md").exists()
        assert _bundled_skill_name() == "video-tracker"
        _assert_discovered(root, "video-tracker", "0.0.0")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_bundled_skill_root_returns_none_without_meipass(tmp_path, monkeypatch) -> None:
    from installer.installer_gui import _bundled_skill_root

    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert _bundled_skill_root() is None

