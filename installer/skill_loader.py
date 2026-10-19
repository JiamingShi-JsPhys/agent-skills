"""Skill discovery and metadata loading for the agent-skills installer.

The installer is *auto-adaptive*: it looks for skill directories both at the
repository root (the original layout) and under a top-level ``skills/``
directory (the 方案 C target layout). A directory is treated as a skill when
it contains a ``SKILL.md``. Metadata is read from ``skill.json`` when
present; when absent, a minimal record is synthesised from the directory
name so the installer still works for skills that only carry ``SKILL.md``.

Pure standard library.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

__all__ = [
    "SkillMeta",
    "discover_skills",
    "load_skill_meta",
]

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
    platforms: List[str] = field(default_factory=lambda: ["workbuddy", "claude", "codex", "dsh"])

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


def _read_dependencies(skill_md: Path) -> Dict:
    """Read the dependency spec from the frontmatter ``metadata:`` block.

    The block is a YAML mapping with optional ``python_requires`` and
    ``python_dependencies`` keys. Returns the skill.json-style shape
    ``{"python": ">=3.9", "pip": [...]}`` (both keys may be absent).
    """
    out: Dict = {}
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return out
    m = re.search(r"^metadata:\s*$\n((?:[ \t]+[^\n]*\n)+)", text, re.MULTILINE)
    if not m:
        return out
    block = m.group(1)
    pm = re.search(r"python_requires:\s*(\S+)", block)
    if pm:
        out["python"] = pm.group(1).strip().strip("'").strip('"')
    pip: List[str] = []
    dm = re.search(r"python_dependencies:\s*\n((?:[ \t]+-[^\n]*\n?)+)", block)
    if dm:
        for line in dm.group(1).splitlines():
            line = line.strip()
            if line.startswith("-"):
                pip.append(line[1:].strip().strip("'").strip('"'))
    if re.search(r"python_dependencies:\s*\[\s*\]", block):
        pip = []
    if "python" in out or pip:
        out.setdefault("pip", pip)
    return out


def _synthesize_meta(skill_dir: Path) -> SkillMeta:
    """Build a minimal meta from a directory that lacks skill.json."""
    sm = skill_dir / "SKILL.md"
    fm = _read_frontmatter(sm)
    return SkillMeta(
        name=skill_dir.name,
        directory=skill_dir,
        version=fm.get("version") or "0.0.0",
        description=fm.get("description", ""),
        author=fm.get("author") or "Jiaming Shi",
        license=fm.get("license") or "MIT",
        entry=fm.get("entry", ""),
        dependencies=_read_dependencies(sm),
    )


def load_skill_meta(skill_dir: Path) -> SkillMeta:
    """Load a skill's metadata from ``skill.json`` (or SKILL.md frontmatter).

    ``skill.json`` is optional; when absent the record is synthesised from
    the SKILL.md frontmatter (the authoritative source). Raises
    ``FileNotFoundError`` if the directory does not contain a ``SKILL.md``
    (i.e. it is not a skill at all).
    """
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
    """A directory is a skill iff it directly contains a SKILL.md."""
    return entry.is_dir() and (entry / "SKILL.md").exists()


def discover_skills(repo_root: Path) -> List[SkillMeta]:
    """Discover installable skills across both repo layouts.

    Scans the two candidate locations:

    - ``repo_root/*``  -- skills that live at the repository root.
    - ``repo_root/skills/*``  -- skills under the 方案 C ``skills/`` dir.

    Results are de-duplicated by skill name (root wins if a name appears in
    both) and returned sorted by name for deterministic installer UI.
    """
    repo_root = Path(repo_root)
    found: Dict[str, SkillMeta] = {}

    # 1) Root-level skills.
    for entry in sorted(repo_root.iterdir()):
        if _is_skill_dir(entry):
            meta = load_skill_meta(entry)
            found.setdefault(meta.name, meta)

    # 2) skills/ subdirectory.
    skills_dir = repo_root / "skills"
    if skills_dir.is_dir():
        for entry in sorted(skills_dir.iterdir()):
            if _is_skill_dir(entry):
                meta = load_skill_meta(entry)
                # Root layout takes precedence when both define the same name.
                if meta.name not in found:
                    found[meta.name] = meta

    return sorted(found.values(), key=lambda m: m.name)
