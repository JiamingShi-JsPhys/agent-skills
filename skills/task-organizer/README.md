`English` · [中文说明](README_zh.md)
# task-organizer

> A task-folder organizer skill from the agent-skills collection. It reorganizes a
> messy task / project folder into a standard three-tier structure and
> coordinates the file lifecycle of the whole task: build every structural
> directory at task start, register file provenance throughout, publish a
> read-only map of the folder through the broadcast center, and tidy once more
> before final delivery while rebuilding the index.

<!-- TOC depthFrom:2 -->

- [task-organizer](#task-organizer)
  - [Design principles & core features](#design-principles-&-core-features)
  - [Download and install](#download-and-install)
  - [Quick start](#quick-start)
  - [Tests & coverage](#tests-&-coverage)
  - [Project layout](#project-layout)
  - [Using as an agent skill](#using-as-an-agent-skill)
  - [License](#license)
  - [Report issues](#report-issues)

<!-- END_TOC -->

task-organizer turns a messy task / project folder into a unified standard three-tier structure and coordinates the file lifecycle of the whole task: the structure is built at task start, file sources are registered throughout, the broadcast center gives a read-only map of the entire folder, and the folder is organized once more with the index rebuilt before final delivery. The folder stays tidy while the task runs, and long tasks keep their context window protected.

Before and after organizing, the tool takes complete directory snapshots and enforces 8 consistency checks (C1-C8); any failure **automatically rolls back** to the pre-organize state — which usually prevents a "half-organized folder that cannot be proven lossless".

```
task_folder/
+---- _broadcast/            # read-only, context-compressed index
|   +---- INDEX.md           #   one line per file: summary + keywords + category
|   `---- index.json         #   the same index, machine-readable
+---- material/
|   +---- initial/           # your own materials - kept verbatim, never renamed
|   +---- downloaded/        # files the AI downloaded during this conversation
|   +---- duplicates/        # exact duplicates isolated in dedupe mode
|   +---- Index.md           # auto-generated Markdown index
|   `---- Index.xlsx         # auto-generated Excel index (with a Statistics sheet)
+---- process/               # AI output + snapshots + logs + history
|   +---- YYYYMMDD_HHMMSS_before.json
|   +---- YYYYMMDD_HHMMSS_after.json
|   +---- YYYYMMDD_HHMMSS_OrganizeLog.md
|   +---- sources.json       # provenance manifest (user / downloaded)
|   +---- verification_report.md        # C1-C8 verification result
|   +---- history/           # operation history + undo / redo
|   `---- logs/              # per-day activity logs
`---- results/               # final deliverables (names contain final / deliverable / report / summary)
```

**The one rule to remember: `material/initial/` belongs to you alone.** The tool never writes any file it produces into this directory, so it can never collide with your files. All you do: create the folder -> drop your materials in -> run `init`. Your materials stay verbatim — never renamed, never modified.

---

## Design principles & core features

- **Trigger-to-act**: a workspace folder (task / project / research) in play triggers the whole pipeline — read-only `doctor` first, then `init` / `organize` as needed; describing without running counts as a failure.
- **Clean standard structure**: a fixed three-tier layout (`material/` + `process/` + `results/`) plus a read-only `_broadcast/` index; every task folder reads the same.
- **Full-lifecycle coordination**: the structure is built at task start, sources are registered throughout; AI-downloaded files are declared with `mark-downloaded` immediately, and `organize` + `broadcast` rebuild the indexes before delivery.
- **Context-window protection**: `_broadcast/` is a read-only compressed index that writes only `INDEX.md` + `index.json`, supports common formats, and defaults to local summaries (AI summaries optional); later sessions read the directory first, then open the originals.
- **Lossless and safe**: before/after SHA-256 snapshots plus C1-C8 verification, with automatic rollback on failure; supports `undo` / `redo`, `--mode` tiers, and `--keep N` rotation.
- **Optional extras**: deduplication, YAML rules, dual-format indexes, AI summaries, Chinese deliverable keywords, per-day logs.

### Trigger-to-act workflow (brief)

This skill is an "act" instruction, not a summary document: once a trigger matches, you must run the tool and report what it did — answering with a description of the skill's features, commands, or architecture is a task failure. The full agent contract lives in `SKILL.md` (MANDATORY WORKFLOW); the essentials:

1. **Session-start structure check**: once the workspace folder is known, run the read-only `doctor <root>` (always safe — it runs before any confirmation because it changes nothing). If it reports a missing structure, apply the folder-signal gate: an explicit organize / setup request (or the compound "produce a deliverable + keep the folder tidy" intent) runs `init <root>` right away and skips the proposal; a merely referenced / attached folder proposes one init first and then stops — propose first, act second, and run no folder-changing command before the user confirms (at most once per folder).
2. **Resolve the path, pick the entry**: no path given -> ask, offering a concrete default so the user only has to say "yes"; from scratch / empty folder -> `init`, existing content -> `organize`.
3. **Final-delivery bookend**: after the deliverable is written, run `organize <root>` and then `broadcast <root>` to rebuild the index. Only files whose names contain `final` / `deliverable` / `report` / `review` / `summary` land in `results/`.
4. **Register downloads immediately**: every file fetched into the task folder during the session gets `mark-downloaded <root> <file> --url <source>` right away — that is the only way `downloaded/` truly means "files the assistant fetched".
5. **The broadcast center is mandatory, not optional**: `_broadcast/` is a read-only, context-compressed index; rebuild it before final delivery so the next session reads the directory first and opens only the originals it needs, instead of re-reading every source document.

---

## Download and install

There are **four** standard ways to get this skill:

**Option 1 — The per-skill installer (recommended)**

The **Releases** page publishes **one installer per skill**. Download this skill's installer and run it — a native installer window opens (like a standard setup program): the skill's title and description are fixed at the top, you tick one or more target harness frameworks (a checklist of full names: Claude Code, DeepSeek Harness, OpenAI Codex, WorkBuddy) and the scope, then click Install; a determinate progress bar tracks the copy file by file (like a standard downloader, showing the current file and how many remain). Nothing is preselected when the window opens; with the project scope the installer first scans your machine for task folders (detected via `.git`, `.workbuddy`, `.claude`, `.codex`, `.dsh`, `.agents`, `.task-organizer.yml` markers) and lets you pick one from a drop-down:
- **Windows**: `task-organizer-installer.exe` (this skill only)
- **macOS / Linux**: a double-click `.app` is **not yet available** (planned). Until then, use the source-archive route below (Option 2) or the CLI from a repo checkout.

No command line needed: the binary installs just this skill. To drive the same logic from the CLI instead:

```bash
python install.py --skill task-organizer --scope user
```

Or install with a single command, no download required (Windows PowerShell) — it fetches the installer script straight from GitHub, installs, and cleans up after itself:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill task-organizer
```

That installs **this skill** into the user scope of **Codex** (the default framework). To pick frameworks or the scope, add `-Frameworks` (`workbuddy`, `claude`, `codex`, `dsh`) or `-Scope` (`user` or `project`). Windows PowerShell 5.1+; no Python required — the full parameter set is documented in the root `README.md`.

**Option 2 — The source archive**

From the **Releases** page (or "Generate ZIP / Generate Tarball"), download the source archive and unpack it — no installer required:

```bash
unzip js_agent_skills-<version>.zip        # or: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills/task-organizer    # this skill is its own top-level folder
```

**Option 3 — Let an Agent fetch it**

Copy the following instruction to your Agent; it will locate this skill, download the installer from the **Releases** page, and install it for you:

> Please visit https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/task-organizer, read the `README.md` in that folder, and follow its instructions to download or install the skill.

You only need to tell the Agent the skill name; it handles the rest.

**Option 4 — Clone the repository**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/task-organizer
```

Requirements: Python 3.10+. `openpyxl` is an optional dependency (only for generating the Excel index; the Markdown index works without it). Every feature other than `openpyxl` uses the standard library alone — no new dependencies are introduced.

---

## Quick start

```bash
cd agent-skills/skills/task-organizer

# 0. (optional) read-only diagnostics: structure / stray files / broadcast freshness
python -m scripts.run doctor /path/to/task_folder

# 1. create the task folder and drop your own materials in (manual).
# 2. lightweight init: scaffold + move your materials into material/initial/ as-is.
python -m scripts.run init /path/to/task_folder

# 3. full organize + verification (auto-rollback on failure).
python -m scripts.run organize /path/to/task_folder

# 4. AI fetched a file -> declare the source first, then organize.
python -m scripts.run mark-downloaded /path/to/task_folder fetched.pdf --url https://...
python -m scripts.run organize /path/to/task_folder --mode quick
```

Other commands:

```bash
python -m scripts.run organize /path/to/task_folder --mode incremental --keep 5
python -m scripts.run organize /path/to/task_folder --profile pharma --config rules.yml
python -m scripts.run index    /path/to/task_folder        # regenerate the indexes only
python -m scripts.run snapshot /path/to/task_folder        # safety net before risky operations
python -m scripts.run undo     /path/to/task_folder/process/history/<file>.json
python -m scripts.run redo     /path/to/task_folder/process/history/<file>.json
python -m scripts.run dedupe   /path/to/task_folder --action report
python -m scripts.run doctor   /path/to/task_folder        # read-only diagnostics: structure/stray files/broadcast freshness
python -m scripts.run broadcast /path/to/task_folder --ai   # AI summaries (local mode by default)
```

Sample output:

```
Root: /path/to/task_folder
mode: full
organize: done
verification: passed
history: wrote 20261012_191444_history.json
```

When you see `verification: passed`, the three-tier structure is ready to use; `verification: failed` means the system has already rolled back automatically — fix the cause and retry.

### File flow in a healthy folder

```
you create the folder and drop your materials in
        |
        v
   +---------+      +-------------------------------------------+
   |  init   |----->| material/initial/<your files, untouched>   |
   +---------+      +-------------------------------------------+
        |
        v  (as the work proceeds)
   organize --mode=quick|incremental|full
        |
        +--> the AI's own output .................... process/
        +--> names containing final / deliverable ... results/
        +--> after mark-downloaded, then organize .... material/downloaded/
        |
        v
   index     (when a handover report is needed)
   snapshot  (before any risky operation)
```

The goal is to keep the folder tidy throughout the task instead of organizing once at the very end: the scaffold is built once, and everything else goes to its place as you work.

### Step-by-step calls (library use)

```python
from pathlib import Path
from scripts import snapshot, organize, verify, index_md, index_xlsx, rollback, utils

root = Path("/path/to/task_folder").resolve()

before = snapshot.make_snapshot(root, phase="before")
session = utils.OrganizeSession(root=root)
organize.organize_folder(root, session=session)

after = snapshot.make_snapshot(root, phase="after")
vres = verify.verify(root, session=session, before=before, after=after)

if not vres.passed:
    rollback.rollback(root, session=session)   # verification failed -> roll back
else:
    index_md.write_index_md(root)
    index_xlsx.write_index_xlsx(root)
```

---

## Tests & coverage

```bash
pytest                                            # full suite
pytest --cov=scripts --cov-report=term-missing    # with coverage
```

- 340 cases
- `pytest` from this directory; the suite also asserts the documentation contracts (workflow presence, trigger semantics).

Line coverage is around 88% (target >= 80%).

---

## Project layout

```
task-organizer/
+---- SKILL.md              # skill entry (YAML metadata + execution guide)
+---- README.md
+---- README_zh.md          # Chinese mirror
+---- LICENSE               # MIT
+---- CHANGELOG.md
+---- CONTRIBUTING.md
+---- AUTHORS.md
+---- CITATION.cff
+---- .gitignore
+---- .task-organizer.yml.example   # YAML config example (with a pharma domain profile)
+---- pyproject.toml        # packaging + tool configuration
+---- requirements.txt      # openpyxl, pytest, pytest-cov
+---- scripts/
|   +---- __init__.py
|   +---- run.py            # pipeline orchestration + CLI (init/material/index/snapshot/undo/redo/dedupe/mark-*)
|   +---- scan.py           # recursive scan + entry classification
|   +---- snapshot.py       # before/after snapshots (optional hash-cache reuse)
|   +---- organize.py       # three-tier structure + provenance-based placement
|   +---- verify.py         # forced 8-item consistency verification (C1-C8)
|   +---- rollback.py       # log-based rollback
|   +---- dedupe.py         # exact + similarity deduplication
|   +---- history.py        # operation history + undo/redo
|   +---- rules.py          # YAML rule configs + domain profiles
|   +---- init.py           # lightweight scaffold + content move
|   +---- sources.py        # provenance manifest
|   +---- hashcache.py      # incremental hash cache
|   +---- rotate.py         # artifact rotation
|   +---- text_extract.py   # multi-format text extraction (docx/pdf/pptx/xlsx)
|   +---- broadcast.py      # broadcast center: context-compressed index (_broadcast/)
|   +---- doctor.py         # read-only diagnostics: structure / stray files / broadcast freshness
|   +---- index_md.py       # Markdown index
|   +---- index_xlsx.py     # Excel index (openpyxl)
|   `---- utils/            # common helpers (paths/logging/snapshots/AI summaries/structure)
|       +---- __init__.py
|       `---- logger.py     # stdlib logging
+---- assets/
|   +---- index-template.md
|   `---- verification-report-template.md
`---- tests/
    +---- __init__.py
    +---- conftest.py
    +---- test_scan.py
    +---- test_snapshot.py
    +---- test_organize.py
    +---- test_verify.py
    +---- test_rollback.py
    +---- test_index.py
    +---- test_run.py
    +---- test_dedupe.py
    +---- test_history.py
    +---- test_rules.py
    +---- test_logger.py
    +---- test_init.py
    +---- test_sources.py
    +---- test_hashcache.py
    +---- test_rotate.py
    +---- test_doctor.py        # read-only diagnostics
    +---- test_skill_docs.py    # documentation contract
    `---- test_broadcast.py     # broadcast center: extraction, read-only, idempotence
```

---

## Using as an agent skill

This project is a self-contained agent Skill package. `SKILL.md` carries YAML frontmatter (`name` / `description` / `version` / `author` / `license` / `allowed-tools`) followed by an "Execution steps" guide. Point any agent at this folder. When a user request matches this skill's scope, the agent reads the execution steps in `SKILL.md` and shells out to the scripts. (Whether the skill is loaded depends on the agent's recognition of its scope; it is not guaranteed to trigger in every conversation.)

One important convention for the agent: whenever a file is downloaded or fetched into the task folder during the conversation, call `mark-downloaded` immediately (with the source URL). That is the only way `downloaded/` truly means "files the AI downloaded" rather than "files whose name happens to contain download".

You can also call the modules directly from Python:

```python
from pathlib import Path
from scripts import run

result = run.run(Path("/path/to/task_folder"))
print(result.summary_lines())
```

---

## License

MIT License, see [LICENSE](LICENSE).

---

## Report issues

Preferred: Open an issue on the repository's **Issues** page. For security-vulnerability reports, use the alternative channel below.

Alternative (security-vulnerability reports only): Send an email to `jiamingshi_git@outlook.com`.

- **Subject**: Must include the prefix `agent-skill_report`, the specific skill name, and a brief description.
  - Example: `agent-skill_report task-organizer: the dedupe move has a path-traversal flaw that can read outside the task folder`
- **Body**: Must include reproduction steps, expected behavior, actual behavior, and the runtime environment (OS, Python version, relevant dependencies installed).
- For severe reports like "file lost or corrupted", attach the before/after directory tree (`tree` output) and the generated `verification_report.md`.
- Contributors who submit clear, reproducible issues or pull requests will be listed in the acknowledgements of the next release notes.
