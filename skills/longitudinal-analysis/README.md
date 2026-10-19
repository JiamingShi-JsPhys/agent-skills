`English` · [中文说明](README_zh.md)
# longitudinal-analysis

> A longitudinal statistics pipeline skill from the agent-skills collection. It drives
> multi-step analysis — LMM, growth curves, mediation / SEM — from one
> reproducible YAML config, with an optional R backend.

<!-- TOC depthFrom:2 -->

- [longitudinal-analysis](#longitudinal-analysis)
  - [Design principles & core features](#design-principles-&-core-features)
  - [Download and install](#download-and-install)
  - [Quick start](#quick-start)
  - [Pipeline steps](#pipeline-steps)
  - [Project layout](#project-layout)
  - [Run tests](#run-tests)
  - [Dependencies](#dependencies)
  - [License](#license)
  - [Report issues](#report-issues)

<!-- END_TOC -->

longitudinal-analysis runs a longitudinal (repeated-measures) analysis as an ordered pipeline: one YAML file declares the design, the timepoints, and the steps to run, and the same config reproduces the same run. Steps execute in order; pass `--step <name>` to run a single step. Steps that need `Rscript` skip automatically when R is absent.

## Design principles & core features

- **Config-driven**: one YAML defines the design, timepoints, and analysis steps; the same config reproduces the run.
- **Mixed-method friendly**: LMM, growth curves, and mediation / SEM coexist, enabled as needed.
- **R as an optional backend**: linear mixed models run through an external `Rscript`; without R, those steps skip automatically.
- **Linear mixed models (LMM)**: fixed + random effects for repeated measures.
- **Growth-curve modelling**: trajectory terms (intercept, slope, ...).
- **Mediation / structural equations**: cross-timepoint path models, needs R `lavaan`.

## Download and install

There are **four** standard ways to get this skill:

**Option 1 — The per-skill installer (recommended)**

The **Releases** page publishes **one installer per skill**. Download this skill's installer and run it — a native installer window opens (like a standard setup program): the skill's title and description are fixed at the top, you tick one or more target harness frameworks (a checklist of full names: Claude Code, DeepSeek Harness, OpenAI Codex, WorkBuddy) and the scope, then click Install; a determinate progress bar tracks the copy file by file (like a standard downloader, showing the current file and how many remain). Nothing is preselected when the window opens; with the project scope the installer first scans your machine for task folders (detected via `.git`, `.workbuddy`, `.claude`, `.codex`, `.dsh`, `.agents`, and other project markers) and lets you pick one from a drop-down:
- **Windows**: `longitudinal-analysis-installer.exe` (this skill only)
- **macOS / Linux**: a double-click `.app` is **not yet available** (planned). Until then, use the source-archive route below (Option 2) or the CLI from a repo checkout.

No command line needed: the binary installs just this skill. To drive the same logic from the CLI instead:

```bash
python install.py --skill longitudinal-analysis --scope user
```

Or install with a single command, no download required (Windows PowerShell) — it fetches the installer script straight from GitHub, installs, and cleans up after itself:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill longitudinal-analysis
```

That installs **this skill** into the user scope of **Codex** (the default framework). To pick frameworks or the scope, add `-Frameworks` (`workbuddy`, `claude`, `codex`, `dsh`) or `-Scope` (`user` or `project`). Windows PowerShell 5.1+; no Python required — the full parameter set is documented in the root `README.md`.

**Option 2 — The source archive**

From the **Releases** page (or "Generate ZIP / Generate Tarball"), download the source archive and unpack it — no installer required:

```bash
unzip js_agent_skills-<version>.zip        # or: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills/longitudinal-analysis    # this skill is its own top-level folder
pip install -e .
```

**Option 3 — Let an Agent fetch it**

Copy the following instruction to your Agent; it will locate this skill, download the installer from the **Releases** page, and install it for you:

> Please visit https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/longitudinal-analysis, read the `README.md` in that folder, and follow its instructions to download or install the skill.

You only need to tell the Agent the skill name; it handles the rest.

**Option 4 — Clone the repository**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/longitudinal-analysis
pip install -e .
```

Requirements: Python 3.10+. Core dependencies: `pandas`, `numpy`, `scipy`, `statsmodels`, `openpyxl`. Optional: R with `lme4` (LMM) and `lavaan` (SEM) for the R-backend steps; without R, those steps skip automatically.

## Quick start

```bash
pip install -e .
python -m src.cli run --config config/examples/behavior_2x2x2.yaml
```

Steps execute in order; add `--step lmm` (or any step name) to run a single step. Steps that need `Rscript` skip automatically when R is absent.

## Pipeline steps

| Step | What it does |
|---|---|
| `lmm` | Linear mixed model on the primary outcome |
| `growth` | Growth-curve / trajectory decomposition |
| `mediation` | Mediation and SEM paths (needs R `lavaan`) |

## Project layout

```
longitudinal-analysis/
├── SKILL.md                # agent execution guide (MANDATORY WORKFLOW)
├── README.md
├── README_zh.md            # Chinese mirror
├── LICENSE                 # MIT
├── CHANGELOG.md
├── AUTHORS.md
├── CITATION.cff
├── .gitignore
├── pyproject.toml          # packaging + tool configuration
├── requirements.txt        # pandas, numpy, scipy, statsmodels, PyYAML
├── config/
│   ├── schema.yaml         # configuration schema
│   └── examples/
│       └── behavior_2x2x2.yaml   # 2x2x2 worked example
├── R/
│   ├── lmm.R               # lme4 linear mixed models
│   └── mediation.R         # lavaan mediation / SEM
├── src/
│   ├── __init__.py
│   ├── cli.py              # entry point
│   ├── config.py           # config loading (YAML / JSON)
│   ├── pipeline.py         # step orchestration (R-optional degradation)
│   ├── r_runner.py         # R invocation (JSON over stdin / stdout)
│   ├── audit.py            # append-only run audit (input / output hashes)
│   └── steps/
│       ├── __init__.py
│       ├── descriptive.py  # descriptive statistics (pure pandas)
│       ├── manipulation.py # manipulation checks (Type II ANOVA)
│       ├── lmm.py          # linear mixed models (R backend)
│       ├── mediation.py    # time-lagged mediation / SEM (R backend)
│       └── sensitivity.py  # random-effects / covariance sensitivity
└── tests/
    ├── conftest.py
    ├── fixture_panel.csv   # example panel data
    ├── test_cli.py
    ├── test_manipulation.py
    ├── test_pipeline.py
    ├── test_r_steps.py
    └── test_skill_docs.py  # documentation contract
```

## Run tests

```bash
cd longitudinal-analysis
pytest tests
```

## Dependencies

Core: `pandas`, `numpy`, `scipy`, `statsmodels`, `openpyxl`.
Optional: R with `lme4` (LMM) and `lavaan` (SEM) for the R-backend steps.

## License

MIT License, see [LICENSE](LICENSE) and [CITATION.cff](CITATION.cff).

Please submit issues and pull requests in the main repository.

## Report issues

Preferred: Open an issue on the repository's **Issues** page. For security-vulnerability reports, use the alternative channel below.

Alternative (security-vulnerability reports only): Send an email to `jiamingshi_git@outlook.com`.

- **Subject**: Must include the prefix `agent-skill_report`, the specific skill name, and a brief description.
  - Example: `agent-skill_report longitudinal-analysis: the r-runner step executes unvalidated shell commands from the config file`
- **Body**: Must include reproduction steps, expected behavior, actual behavior, and the runtime environment (OS, Python version, relevant dependencies installed).
- For severe reports like "file lost or corrupted", attach the before/after directory tree (`tree` output) and the generated `verification_report.md`.
- Contributors who submit clear, reproducible issues or pull requests will be listed in the acknowledgements of the next release notes.
