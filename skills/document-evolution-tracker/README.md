`English`· [中文说明](README_zh.md)
# document-evolution-tracker

> A document evolution tracker from the agent-skills collection. It traces every text change
> back to where it came from, so a report reads as a story of change rather
> than a raw diff.

<!-- TOC depthFrom:2 -->

- [document-evolution-tracker](#document-evolution-tracker)
  - [Design principles & core features](#design-principles-&-core-features)
  - [Download and install](#download-and-install)
  - [Quick start](#quick-start)
  - [Diff granularities](#diff-granularities)
  - [Project layout](#project-layout)
  - [Run tests](#run-tests)
  - [License](#license)
  - [Report issues](#report-issues)

<!-- END_TOC -->

## Design principles & core features

- **Lineage-first**: each edit is traced to where the text came from, so a report reads as a story of change, not just a diff.
- **Multi-granularity diffs**: compare at line, paragraph, or sentence level depending on how you track edits.
- **Reproducible reports**: every run is versioned under a tracking id, so findings stay auditable.
- **Versioned snapshots** — each revision is recorded with a stable tracking id.
- **Lineage tracking** — show where a passage came from and how it moved across versions.
- **Editable reports** — Markdown + JSON output per run; JSON is the machine-readable contract.

## Download and install

There are **four** standard ways to get this skill:

**Option 1 — The per-skill installer (recommended)**

The **Releases** page publishes **one installer per skill**. Download this skill's installer and run it — a native installer window opens (like a standard setup program): the skill's title and description are fixed at the top, you tick one or more target harness frameworks (a checklist of full names: Claude Code, DeepSeek Harness, OpenAI Codex, WorkBuddy) and the scope, then click Install; a determinate progress bar tracks the copy file by file (like a standard downloader, showing the current file and how many remain). Nothing is preselected when the window opens; with the project scope the installer first scans your machine for task folders (detected via `.git`, `.workbuddy`, `.claude`, `.codex`, `.dsh`, `.agents`, and other project markers) and lets you pick one from a drop-down:
- **Windows**: `document-evolution-tracker-installer.exe` (this skill only)
- **macOS / Linux**: a double-click `.app` is **not yet available**
  (planned). Until then, use the source-archive route below (Option 2) or
  the CLI from a repo checkout.

No command line needed: the binary installs just this skill. To drive the
same logic from the CLI instead:

```bash
python install.py --skill document-evolution-tracker --scope user
```

Or install with a single command, no download required (Windows PowerShell) — it fetches the installer script straight from GitHub, installs, and cleans up after itself:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill document-evolution-tracker
```

That installs **this skill** into the user scope of **Codex** (the default framework). To pick frameworks or the scope, add `-Frameworks` (`workbuddy`, `claude`, `codex`, `dsh`) or `-Scope` (`user` or `project`). Windows PowerShell 5.1+; no Python required — the full parameter set is documented in the root `README.md`.

**Option 2 — The source archive**

From the **Releases** page (or "Generate ZIP / Generate Tarball"), download
the source archive and unpack it — no installer required:

```bash
unzip js_agent_skills-<version>.zip        # or: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills/document-evolution-tracker # this skill is its own top-level folder
pip install -e .
```

**Option 3 — Let an Agent fetch it**

Copy the following instruction to your Agent; it will locate this skill,
download the installer from the **Releases** page, and install it for you:

> Please visit https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/document-evolution-tracker, read the `README.md` in that folder, and follow its instructions to download or install the skill.

You only need to tell the Agent the skill name; it handles the rest.

**Option 4 — Clone the repository**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/document-evolution-tracker
pip install -e .
```

Requirements: Python 3.10+.

## Quick start

```bash
pip install -e .
python -m src.cli run --config config/examples/family.json --concepts "Alpha,Beta"
```

Reports are written to `./evolution/evolution_<tracking_id>.{md,json}`.

## Diff granularities

| Level | Best for |
|---|---|
| `line` | Quick, coarse change overview |
| `paragraph` | Tracking how a passage is revised between versions |
| `sentence` | Precise clause-level edits |

## Project layout

```
document-evolution-tracker/
├── SKILL.md                # agent execution guide (MANDATORY WORKFLOW)
├── README.md
├── README_zh.md            # Chinese mirror
├── LICENSE                 # MIT
├── CHANGELOG.md
├── AUTHORS.md
├── CITATION.cff
├── .gitignore
├── pyproject.toml          # packaging + tool configuration
├── requirements.txt        # PyYAML (optional) + pytest
├── config/
│   ├── schema.yaml         # configuration schema
│   └── examples/
│       ├── family.json      # worked example
│       └── family/          # example document versions
│           ├── v1.md
│           └── v2.md
├── src/
│   ├── __init__.py
│   ├── cli.py               # entry point
│   ├── tracker.py / align.py / diff_blocks.py
│   ├── lineage.py / versioning.py / report.py
│   └── config.py
└── tests/                   # pytest suite
    ├── test_core.py
    ├── test_skill_docs.py   # documentation contract
    └── test_tracker_cli.py
```

## Run tests

```bash
cd document-evolution-tracker
pytest tests
```

## License

MIT License, see [LICENSE](LICENSE) and [CITATION.cff](CITATION.cff).

Please submit issues and pull requests in the main repository.

## Report issues

Preferred: Open an issue on the repository's **Issues** page. For security-vulnerability reports, use the alternative channel below.

Alternative (security-vulnerability reports only): Send an email to `jiamingshi_git@outlook.com`.

- **Subject**: Must include the prefix `agent-skill_report`, the specific skill name, and a brief description.
  - Example: `agent-skill_report document-evolution-tracker: the evolution report writer follows a symlink and overwrites a file outside the workspace`
- **Body**: Must include reproduction steps, expected behavior, actual behavior, and the runtime environment (OS, Python version, relevant dependencies installed).
- For severe reports like "file lost or corrupted", attach the before/after directory tree (`tree` output) and the generated `verification_report.md`.
- Contributors who submit clear, reproducible issues or pull requests will be listed in the acknowledgements of the next release notes.
