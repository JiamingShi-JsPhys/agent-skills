`English` · [中文说明](README_zh.md)
# multi-dim-manager

> A self-contained state manager for multi-dimensional computational experiments,
> part of the agent-skills collection. It iterates a parameter grid over many
> rounds, snapshots declared critical files each round, audits every round, and
> rolls back to any round non-destructively.

<!-- TOC depthFrom:2 -->

- [multi-dim-manager](#multi-dim-manager)
  - [Design principles & core features](#design-principles-&-core-features)
  - [Download and install](#download-and-install)
  - [Quick start](#quick-start)
  - [Common request shapes](#common-request-shapes)
  - [How the manager keeps state](#how-the-manager-keeps-state)
  - [Limitations](#limitations)
  - [Tests & coverage](#tests-&-coverage)
  - [Project layout](#project-layout)
  - [Using as an agent skill](#using-as-an-agent-skill)
  - [License](#license)
  - [Report issues](#report-issues)

<!-- END_TOC -->

---

## Design principles & core features

- **Separation of concerns**: your compute plugin does the math; this skill manages the state (snapshots, audit, rollback) around it.
- **Trigger-to-act**: when a user asks to run, inspect, or recover a multi-dimensional experiment, load the config and confirm the parameter space, critical paths, and plugin command are present; report the total round count first; prefer a dry run so the user sees the full plan before any side effect; then execute the sweep — snapshot critical paths before, invoke the plugin, snapshot after, and append one audit record per round. On a failed round, record its status and (if `auto_rollback`) recover the last good baseline — audited. Do not abort the whole sweep. Summarize at the end, and recover on request with `rollback`.
- **Non-destructive rollback**: by default the restored state lands in a NEW directory (`<workdir>.rollback_NNNN`); only `--force` overwrites the live working directory. Either way the action is written to the audit log.
- **Auditable**: every round appends one JSON line to `audit_log.jsonl` carrying the parameter combination, input hash, output hash, timestamp, plugin exit code, and both snapshots (pre/post). Rollback actions are recorded too, so the entire history is reproducible after the fact.
- **Snapshots are content-addressed**: only the files you declare in `critical_paths` are snapshotted — never the whole working directory. Each file's content is stored once, addressed by its SHA-256 hash, so a file that does not change between rounds costs no extra space. A snapshot is just a manifest: `relative_path -> content_hash`.
- **Summaries**: write `results_summary.csv/.md`, `report_draft.md`, `run_metadata.json`.
- **Plugin contract**: one shell command, JSON in/out, exit 0/1/2.
- **Pure standard library by default**: JSON configs work with the standard library alone; YAML configs need `pyyaml`.

---

## Download and install

There are **four** standard ways to get this skill:

**Option 1 — The per-skill installer (recommended)**

The **Releases** page publishes **one installer per skill**. Download this skill's installer and run it — a native installer window opens (like a standard setup program): the skill's title and description are fixed at the top, you tick one or more target harness frameworks (a checklist of full names: Claude Code, DeepSeek Harness, OpenAI Codex, WorkBuddy) and the scope, then click Install; a determinate progress bar tracks the copy file by file (like a standard downloader, showing the current file and how many remain). Nothing is preselected when the window opens; with the project scope the installer first scans your machine for task folders (detected via `.git`, `.workbuddy`, `.claude`, `.codex`, `.dsh`, `.agents`, and other project markers) and lets you pick one from a drop-down:
- **Windows**: `multi-dim-manager-installer.exe` (this skill only)
- **macOS / Linux**: a double-click `.app` is **not yet available** (planned). Until then, use the source-archive route below (Option 2) or the CLI from a repo checkout.

No command line needed: the binary installs just this skill. To drive the same logic from the CLI instead:

```bash
python install.py --skill multi-dim-manager --scope user
```

Or install with a single command, no download required (Windows PowerShell) — it fetches the installer script straight from GitHub, installs, and cleans up after itself:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill multi-dim-manager
```

That installs **this skill** into the user scope of **Codex** (the default framework). To pick frameworks or the scope, add `-Frameworks` (`workbuddy`, `claude`, `codex`, `dsh`) or `-Scope` (`user` or `project`). Windows PowerShell 5.1+; no Python required — the full parameter set is documented in the root `README.md`.

**Option 2 — The source archive**

From the **Releases** page (or "Generate ZIP / Generate Tarball"), download the source archive and unpack it — no installer required:

```bash
unzip js_agent_skills-<version>.zip        # or: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills/multi-dim-manager    # this skill is its own top-level folder
pip install -r requirements.txt
```

**Option 3 — Let an Agent fetch it**

Copy the following instruction to your Agent; it will locate this skill, download the installer from the **Releases** page, and install it for you:

> Please visit https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/multi-dim-manager, read the `README.md` in that folder, and follow its instructions to download or install the skill.

You only need to tell the Agent the skill name; it handles the rest.

**Option 4 — Clone the repository**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/multi-dim-manager
pip install -r requirements.txt
```

Requirements: Python 3.10+. No third-party package is required for JSON configs. YAML configs need `pyyaml` (`pip install pyyaml`). The skill uses only the Python standard library otherwise.

---

## Quick start

```bash
cd agent-skills/skills/multi-dim-manager

# 0. (optional) see the full plan without running anything
python scripts/run.py dryrun --config config.example.yaml

# 1. run the sweep (writes audit log, snapshots, summaries under ./output)
python scripts/run.py run --config config.example.yaml

# 2. restore a past round into a new directory
python scripts/run.py rollback --config config.example.yaml --round 12

# 3. regenerate the summaries from the audit log
python scripts/run.py summary --config config.example.yaml

# 4. check one round's plugin-contract outcome
python scripts/run.py verify --config config.example.yaml --round 12
```

### Output shape

```
output/
  audit_log.jsonl      # one JSON line per round (+ rollbacks)
  snapshots/store/     # content-addressed critical-file store
  results_summary.csv  # flat, filterable table
  results_summary.md   # same table in Markdown
  report_draft.md      # narrative draft
  run_metadata.json    # space, plugin, timing
```

---

## Common request shapes

- "Run this 2x2x2 grid, 200 rounds, and tell me which combinations passed."
- "Round 47 crashed — restore its state so I can inspect the inputs."
- "Roll everything back to round 150 and re-run from there with new params."
- "Show me the audit trail for the last 10 rounds."

---

## How the manager keeps state

The skill treats an experiment as a state machine over rounds. Three mechanisms keep it honest.

### Snapshots (content-addressed, critical-path only)

Only the files you declare in `critical_paths` are snapshotted — never the whole working directory. Each file's content is stored once, addressed by its SHA-256 hash, so a file that does not change between rounds costs no extra space. A snapshot is just a manifest: `relative_path -> content_hash`.

### Audit

Every round appends one JSON line to `audit_log.jsonl` carrying the parameter combination, input hash, output hash, timestamp, plugin exit code, and both snapshots (pre/post). Rollback actions are recorded too, so the entire history is reproducible after the fact.

### Rollback (non-destructive)

`rollback --round N` restores round N's post-state. By default it lands in a NEW directory (`<workdir>.rollback_NNNN`); only `--force` overwrites the live working directory. Either way the action is written to the audit log.

### Guarantees

- **Traceable**: every output is tied to a parameter combination and a snapshot.
- **Recoverable**: any recorded round can be restored, with the action logged.
- **Deterministic orchestration**: the same params always yield the same plan and the same recorded hashes. (The plugin's own determinism is the user's job — see Limitations.)

---

## Limitations

- **Determinism is orchestration-layer only.** The manager records hashes and replays the same plan for the same inputs, but it cannot make a non-deterministic plugin deterministic. If the plugin touches the network, uses random seeds, or reads the wall clock, identical inputs may diverge. Declare such behaviour in the plugin yourself.
- **Critical paths must be declared up front.** Files not listed in `critical_paths` are never snapshotted and therefore cannot be rolled back.
- **Golden-output verification is v0.2.** The current verifier only checks the plugin contract (exit 0 + a result file). Comparison against a known expected output is planned but not yet implemented.
- **YAML configs need PyYAML.** JSON configs work with the standard library alone.

---

## Tests & coverage

The suite currently covers 87 cases. Run it with:

```bash
python -m pytest -q
```

Target line coverage is >= 80%, matching the repository's quality baseline. Two YAML-config tests skip automatically when PyYAML is not installed; JSON configs always run.

---

## Project layout

```
multi-dim-manager/
  SKILL.md                 # agent execution guide (MANDATORY WORKFLOW)
  README.md                # docs (this file)
  README_zh.md             # Chinese mirror
  LICENSE                  # MIT
  CHANGELOG.md
  AUTHORS.md
  CITATION.cff
  .gitignore
  config.example.yaml      # configuration template
  pyproject.toml           # packaging + tool configuration
  requirements.txt         # pyyaml (optional; JSON configs need nothing)
  sample_plugin.py         # example compute plugin (contract demo)
  scripts/
    __init__.py
    param_space.py         # space parsing + expansion
    config.py              # experiment config loading
    executor.py            # plugin invocation (shell + JSON + exit 0/1/2)
    snapshot.py            # content-addressed critical-path snapshots
    audit.py               # append-only JSONL audit log
    rollback.py            # non-destructive rollback
    aggregator.py          # result table aggregation
    report.py              # Markdown summaries / draft
    verify.py              # plugin-contract verification (golden: v0.2)
    run.py                 # CLI entry point
    common.py              # common helpers used across the core modules
    errors.py              # domain-specific error types
  tests/                   # unit + documentation-contract tests
    conftest.py
    test_aggregator.py
    test_audit.py
    test_config.py
    test_executor.py
    test_param_space.py
    test_report.py
    test_rollback.py
    test_run_cli.py
    test_skill_docs.py     # documentation contract
    test_snapshot.py
    test_verify.py
```

---

## Using as an agent skill

Drop the folder into any Agent harness that supports the Skill specification. When a request matches the scope (multi-round, multi-dimensional experiment with state to track), the Agent reads `SKILL.md` and follows its MANDATORY WORKFLOW. The skill is self-contained: it imports nothing from sibling skills.

---

## License

Released under the MIT License. See `LICENSE`.

---

## Report issues

Preferred: Open an issue on the repository's **Issues** page. For security-vulnerability reports, use the alternative channel below.

Alternative (security-vulnerability reports only): Send an email to `jiamingshi_git@outlook.com`.

- **Subject**: Must include the prefix `agent-skill_report`, the specific skill name, and a brief description.
  - Example: `agent-skill_report multi-dim-manager: a rollback command can restore a snapshotted file to an arbitrary absolute path`
- **Body**: Must include reproduction steps, expected behavior, actual behavior, and the runtime environment (OS, Python version, relevant dependencies installed).
- For severe reports like "file lost or corrupted", attach the before/after directory tree (`tree` output) and the generated `verification_report.md`.
- Contributors who submit clear, reproducible issues or pull requests will be listed in the acknowledgements of the next release notes.
