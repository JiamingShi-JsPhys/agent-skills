`English`· [中文说明](README_zh.md)
# agent-skills

> `agent-skills` is a collection of self-contained Agent Skills developed and
> maintained by **Jiaming Shi**. It gives AI-agent harnesses standardized,
> auditable, and reliable local execution capabilities. Each skill is an
> independent, self-contained package: no complex install or build step is
> required — it drops straight into any agent environment that supports the
> Skill specification.

<!-- TOC depthFrom:2 -->

- [agent-skills](#agent-skills)
  - [Design principles & core features](#design-principles-&-core-features)
  - [The seven skills](#the-seven-skills)
  - [Download and install](#download-and-install)
  - [Quick start](#quick-start)
  - [Repository layout](#repository-layout)
  - [Development and contribution](#development-and-contribution)
  - [License](#license)
  - [Report issues](#report-issues)

<!-- END_TOC -->

## Design principles & core features

1. **Agent-Native**: Each skill ships a `SKILL.md` with standard metadata. The agent reads that file on its own, understands the skill's scope and execution steps, and autonomously invokes the underlying scripts.
2. **Zero-Dependency Deployment**: Skills use only the Python standard library wherever possible, avoiding complex dependency chains and ensuring plug-and-play across platforms (Windows / macOS / Linux).
3. **Deterministic Safety**: To guard against execution hallucinations, each skill enforces verifiable, rollback-capable operations with complete audit logs.
4. **Trigger-to-Act**: Each skill's `SKILL.md` opens with a mandatory workflow, so a matching request makes the agent *run* the tool and report the result — never answer with a description of what the tool does.

## The seven skills

The seven installable skills are grouped by function. Each row links to that skill's `README.md` (this table is the single place you read all of them; the linked README is the per-skill deep-dive).

| | Category | Skill | One-line summary | Dependencies |
| :--- | :--- | :---: | :--- | :--- |
| | **File & Project Management** | [`task-organizer`](skills/task-organizer/README.md) v1.0.1 | Reorganize a messy task folder into a verified three-tier structure, with a broadcast center as a context-compression index | Standard library |
| | | [`document-evolution-tracker`](skills/document-evolution-tracker/README.md) v1.0.0 | Track version alignment and concept lineage across a document family; auto-discovers versions, block-level diffs, timeline report | Standard library |
| | **Experiment State & Scheduling** | [`multi-dim-manager`](skills/multi-dim-manager/README.md) v1.0.1 | Cartesian-expand a parameter space into independent rounds for auto-running many same-type tasks | Standard library + PyYAML (optional, for YAML configs) |
| | **Data Analysis & Extraction** | [`longitudinal-analysis`](skills/longitudinal-analysis/README.md) v1.0.0 | Longitudinal statistics pipeline: descriptive, manipulation check, LMM, lagged mediation, sensitivity | `pandas`, `numpy`, `scipy`, `statsmodels`, `openpyxl`; optional `Rscript` + `lme4`/`lavaan` |
| | | [`video-tracker`](skills/video-tracker/README.md) v0.0.0 (beta) | Extracts standardized motion data from experiment videos: OpenCV tracking, FFT spectrum, physics-consistency probes | `numpy`, `opencv-contrib-python-headless`; optional `matplotlib`, `pyyaml` |
| | **Verification & Detection** | [`formula-validator`](skills/formula-validator/README.md) v1.0.1 | Deterministic physics / math formula checker; multi-layer independent checks with a report | Standard library |
| | | [`conflict-detector`](skills/conflict-detector/README.md) v1.0.0 | Cross-document conflict detector; extracts numeric / boolean claims and classifies clauses | Standard library |

## Download and install

There are **four** standard ways to get a skill.

**Option 1 — The per-skill installer (recommended)**

The **Releases** page publishes **one installer per skill** (seven in this release). Download the installer for the skill you want and run it — a native installer window opens (like a standard setup program): the skill's title and description are fixed at the top, you tick one or more target harness frameworks (a checklist of full names: Claude Code, DeepSeek Harness, OpenAI Codex, WorkBuddy) and pick the scope (user or project), then click **Install**; a determinate progress bar tracks the copy file by file. Nothing is preselected when the window opens. With the project scope, the installer first scans your machine for task folders (detected via `.git`, `.workbuddy`, `.claude`, `.codex`, `.dsh`, `.agents`, `.task-organizer.yml` markers) and lets you pick one from a drop-down:

- **Windows**: `<skill>-installer.exe` (one per skill, e.g. `task-organizer-installer.exe`). Each binary bundles its own skill; double-clicking installs just that one.
- **macOS / Linux**: a double-click `.app` is **not yet available** (planned). Until then, use the source-archive route below (Option 2) or run the CLI from a repo checkout.

Drive the same logic from the CLI instead:

```bash
# List what would be installed.
python install.py --list

# Install all discovered skills into the user scope of all four frameworks.
python install.py --platform all --scope user

# Install a single skill in project scope (relative to the current directory).
python install.py --skill task-organizer --scope project

# Force-overwrite an existing install.
python install.py --platform workbuddy --scope user --force
```

Equivalent entry points: `uninstall.py` (remove an installed skill) and `verify.py` (check an install is intact). Shell forwarders `install.sh` / `install.ps1` exist for shell users. The Windows installers are built from `installer/installer_gui.py` (a self-contained, pure-stdlib tkinter front-end) one per skill; the build toolchain lives outside this repository and is not part of the install path — the prebuilt installers ship on the Releases page.

#### One-line install — no download (Windows PowerShell)

Prefer not to download anything? Run this single command — it fetches the installer script straight from GitHub, installs, and cleans up after itself:

```powershell
irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1 | iex
```

That installs **all** skills into the user scope of **Codex** (the default framework). To choose skills, frameworks, or scope, pass parameters via a scriptblock:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill task-organizer -Frameworks workbuddy,claude -Scope user
```

Parameters: `-Skill` (a skill name, comma-separated names, or `*` for all), `-Frameworks` (`workbuddy`, `claude`, `codex`, `dsh`), `-Scope` (`user` or `project`), `-Dir` (task folder for project scope), `-Repo` / `-Branch` (defaults: this repository, `main`), `-Force` (overwrite existing installs). Windows PowerShell 5.1+; no Python required.

**Option 2 — The source archive**

From the **Releases** page (or "Generate ZIP / Generate Tarball"), download the source archive and unpack it — no installer required:

```bash
unzip js_agent_skills-<version>.zip        # or: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills   # each skill is its own top-level folder
```

**Option 3 — Let an Agent fetch it**

Copy the instruction below to your agent; it will locate the matching skill and install it for you:

> Visit the repository https://github.com/JiamingShi-JsPhys/agent-skills, find the skill folder you need (name the skill or describe its function), read the `README.md` inside that folder, and follow its instructions to download or install the skill.

You only need to tell the agent the skill name — it handles the rest.

**Option 4 — Clone the repository**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills   # each skill is its own top-level folder
```

## Quick start

Each skill provides a Python CLI. For `task-organizer`:

```bash
cd agent-skills/skills/task-organizer
python -m scripts.run /path/to/task_folder
```

For `conflict-detector`:

```bash
cd agent-skills/skills/conflict-detector
python -m src.cli --help
```

Or call a module directly from Python:

```python
from pathlib import Path
from scripts import run   # refer to the actual implementation inside the skill

result = run.organize(Path("/path/to/task_folder"))
print(result.summary_lines())
```

> The examples above are illustrative; the actual interface is defined by the documentation inside each skill folder.

## Repository layout

Released skills live under a top-level **`skills/`** directory, each in its own folder. The tree below is a 1:1 mapping of the on-disk layout: top-level directories first, then files, each group in **alphabetical order**. The internal layout of every skill is documented in that skill's own README.

```
agent-skills/
├── skills/
│   ├── conflict-detector/                 # cross-document conflict detector
│   ├── document-evolution-tracker/        # version alignment + concept lineage
│   ├── formula-validator/                 # deterministic physics / math formula checker
│   ├── longitudinal-analysis/             # longitudinal statistics pipeline
│   ├── multi-dim-manager/                 # multi-dimensional experiment state manager
│   ├── task-organizer/                    # task-folder organizer + broadcast center
│   └── video-tracker/                     # experiment-video motion data extractor
├── installer/                                # cross-platform installer (native tkinter window + core)
│   ├── __init__.py
│   ├── assets/
│   │   └── README.md                         #   icon assets (place platform icons here)
│   ├── installer_core.py                     #   GUI-agnostic install / uninstall / verify
│   ├── installer_gui.py                      #   double-click target (packaged with PyInstaller)
│   ├── platform_paths.py                     #   (platform, scope) -> target directory
│   ├── requirements.txt
│   └── skill_loader.py                       #   auto-adaptive skill discovery
├── tests/                                    # installer unit tests
├── .gitignore
├── AUTHORS.md
├── CITATION.cff
├── install-web.ps1                           # one-line web installer (PowerShell)
├── LICENSE
├── README.md
├── README_zh.md
├── VERSION
├── conftest.py
├── install.ps1
├── install.py
├── install.sh
├── uninstall.py
└── verify.py
```

A skill is a directory containing a `SKILL.md` with frontmatter metadata (version, name, description). Every released skill ships at least `SKILL.md`, bilingual READMEs, `LICENSE`, `CHANGELOG.md`, `requirements.txt`, and a `tests/` suite; most also ship `pyproject.toml`, `CITATION.cff`, and `AUTHORS.md` (the formula validator is the exception), plus per-skill extras such as `CONTRIBUTING.md`, config examples, or `src/` / `scripts/` code trees.

## Development and contribution

This repository follows strict open-source engineering standards. If you wish to submit a new skill or fix an existing issue:

1. **Independence**: Each skill must live in its own folder and include a complete `LICENSE`, `README.md`, and a standard `SKILL.md` file.
2. **Quality Baseline**: Submitted Python code must include type hints and docstrings, and come with unit tests covering the core logic (target coverage >= 80%).
3. **Versioning**: Follow [Semantic Versioning](https://semver.org/) and [Keep a Changelog](https://keepachangelog.com/).
4. **Code Style**: Follow PEP 8 (suggested line width <= 88). Core flows must handle exceptions and degrade gracefully; avoid crashing on expected I/O errors.

## License

This repository is released under the [MIT License](LICENSE). See the `LICENSE` file in the root directory for details.

Each skill package carries its own `LICENSE` file; please refer to the declaration in that skill's folder.

## Report issues

Preferred: Open an issue on the repository's **Issues** page. For security-vulnerability reports, use the alternative channel below.

Alternative (security-vulnerability reports only): Send an email to `jiamingshi_git@outlook.com`.

- **Subject**: Must include the prefix `agent-skill_report`, the specific skill name, and a brief description.
  - Example: `agent-skill_report task-organizer: path traversal allows reading outside the task folder`
- **Body**: Must include reproduction steps, expected behavior, actual behavior, and the runtime environment (OS, Python version, relevant dependencies installed).
- For severe reports like "file lost or corrupted", attach the before/after directory tree (`tree` output) and the generated `verification_report.md`.
- Contributors who submit clear, reproducible issues or pull requests will be listed in the acknowledgements of the next release notes.
