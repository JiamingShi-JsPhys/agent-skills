`English` · [中文说明](README_zh.md)

# video-tracker

> **Status: experimental / unstable.** A self-contained video-motion-data
> extractor for physics experiments. It tracks 1–2 objects in an `.mp4` /
> `.avi` / `.mov` video with OpenCV CSRT, re-acquires the target via template
> matching when occluded, runs an FFT amplitude spectrum on the tracked
> coordinates, and emits standardized CSV / JSON / PNG outputs that can be
> fed directly into a downstream formula validator. Accuracy is
> target-specific — clean single-object footage tracks well, but occluded,
> deformable, or fast targets degrade the result. Verify outputs against a
> known reference before trusting any number.

## Design principles & core features

- **Standardized, machine-readable outputs.** Every run writes a fixed set
  of artifacts — `<video>_tracking.csv`, `<video>_summary.json`,
  `<video>_fft.json`, `<video>_spectra.png`, `<video>_report.md` — under
  `output/`, so downstream tooling (e.g. a formula validator) has a stable
  contract to consume.
- **Pluggable tracking backend.** One tracker instance per declared object;
  `tracker_type` selects the backend: `auto` uses OpenCV's CSRT on 4.x
  builds and automatically falls back to a pure `cv2.matchTemplate` backend
  (zero external weights) on 5.x where CSRT was removed; `csrt` forces CSRT;
  `template` forces the template backend (works on every OpenCV build).
- **Template-matching re-acquire.** When the tracker reports a loss, an
  optional template-matching re-acquire runs: the target's ROI template is
  matched against a CLAHE-enhanced gray frame via normalized correlation,
  and if the score clears `template_match_threshold` the ROI is repositioned
  and the tracker is re-initialized.
- **FFT amplitude spectrum.** The tracked 1-D coordinate series is fed
  through a normalized one-sided DFT (`numpy.fft`); the dominant
  positive-frequency peak, its period, and the top-N resonances are
  extracted, with a matplotlib figure showing the amplitude spectrum and the
  xy trajectory.
- **Physics-consistency probes (numpy-only).** An optional companion step
  checks whether the tracked trajectory *obeys Newtonian laws* rather than
  only matching a reference path — teleport/smoothness, conservation, and
  equation-of-motion fit — and writes a per-object
  `<video>_physics.json`. No reference video is required.
- **Non-destructive.** The raw video is never modified; all outputs land
  under `output/`.
- **Parameterized, headless.** ROIs, FPS, and tuning knobs are declared in a
  config (`config.yaml` or JSON); there is no `selectROI` / `input` / GUI.

## Download and install

There are **four** standard ways to get this skill:

**Option 1 — The per-skill installer (recommended)**

The **Releases** page publishes **one installer per skill**. Download this
skill's installer and run it — a native installer window opens (like a
standard setup program): the skill's title and description are fixed at the
top, you tick one or more target harness frameworks (a checklist of full
names: Claude Code, DeepSeek Harness, OpenAI Codex, WorkBuddy) and the scope,
then click Install; a determinate progress bar tracks the copy file by file
(like a standard downloader, showing the current file and how many remain).
Nothing is preselected when the window opens; with the project scope the
installer first scans your machine for task folders (detected via `.git`,
`.workbuddy`, `.claude`, `.codex`, `.dsh`, `.agents`, and other project
markers) and lets you pick one from a drop-down:

- **Windows**: `video-tracker-installer.exe` (this skill only)
- **macOS / Linux**: a double-click `.app` / `.sh` is **not yet available**
  (planned). Until then, use the source-archive route below (Option 2) or the
  CLI from a repo checkout.

No command line needed: the binary installs just this skill. To drive the
same logic from the CLI instead:

```bash
python install.py --skill video-tracker --scope user
```

Or install with a single command, no download required (Windows PowerShell)
— it fetches the installer script straight from GitHub, installs, and cleans
up after itself:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill video-tracker
```

That installs **this skill** into the user scope of **Codex** (the
default framework). To pick target harness frameworks (a checklist of full
names: Claude Code, DeepSeek Harness, OpenAI Codex, WorkBuddy) or the scope,
add `-Frameworks` (`workbuddy`, `claude`, `codex`, `dsh`) or `-Scope`
(`user` or `project`). Windows PowerShell 5.1+; no Python required — the full
parameter set is documented in the root `README.md`.

**Option 2 — The source archive**

From the **Releases** page (or "Generate ZIP / Generate Tarball"), download
the source archive and unpack it — no installer required:

```bash
unzip agent-skills-<version>.zip        # or: tar xzf agent-skills-<version>.tar.gz
cd agent-skills/skills/video-tracker    # this skill is its own folder
pip install -r requirements.txt
```

**Option 3 — Let an Agent fetch it**

Copy the following instruction to your Agent; it will locate this skill,
download the installer from the **Releases** page, and install it for you:

> Please visit https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/video-tracker, read the `README.md` in that folder, and follow its instructions to download or install the skill.

You only need to tell the Agent the skill name; it handles the rest.

**Option 4 — Clone the repository**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/video-tracker
pip install -r requirements.txt
```

Requirements: Python 3.10+. Core dependencies: `numpy`,
`opencv-contrib-python-headless`. Optional: `matplotlib` (for PNG spectra
figures), `pyyaml` (for YAML configs).

## Quick start

```bash
cd video-tracker

# 0. inspect the video container (no tracking)
python scripts/run.py probe --config config.yaml

# 1. track + write CSV / JSON under ./output
python scripts/run.py track --config config.yaml

# 2. FFT spectrum + PNG figures
python scripts/run.py fft --config config.yaml

# 3. Markdown report
python scripts/run.py report --config config.yaml

# 4. physics-consistency probes on an existing track (numpy-only)
python scripts/run.py physics --config config.yaml --family harmonic --fx 0.5

# 5. built-in synthetic demo (no video needed)
python scripts/run.py demo
```

### Output shape

```
output/
  <video>_tracking.csv      # per-object column group
  <video>_summary.json      # fps, n_frames, success rates, lost/reinit
  <video>_fft.json          # per-signal spectrum + top-N peaks
  <video>_spectra.png       # amplitude spectra + xy trajectory
  <video>_report.md         # Markdown combining all of the above
  <video>_physics.json      # per-object physics-consistency probes
  batch_summary.json        # roll-up when processing multiple videos
```

### How the tracker keeps state

- **Re-acquire on loss.** When a tracker reports a lost target, an optional
  template-matching re-acquire (Thomas-Kr scheme) repositions the ROI; a
  dense Farneback optical-flow estimate (`use_optical_flow_fallback`)
  advances the last known centre instead of freezing it. Optional sub-pixel
  refinement (`subpixel`) nudges each reported centre below integer
  precision via a local template match and parabolic peak interpolation.
- **Event-window tracking.** Long or multi-event videos rarely have the
  interesting motion spread across the whole file. Declaring
  `frame_range: [start, end]` (inclusive) in the config limits the tracking
  sweep to that window: the reader seeks directly to `start`, tracks through
  `end`, and stops. Frame numbers in the CSV stay source-absolute (so any
  row maps back to the original file), while the time axis is shifted so
  `time_s = 0` at the window start. This is the documented way to keep a
  1080p multi-minute video fast — track the few-seconds sub-window, not the
  whole file.

## Limitations

- **Unstable / experimental.** The skill is shipped as a preliminary tool.
  Tracking error is target-specific and can be several pixels even on clean
  benchmarks (and worse on cluttered footage); verify results against a known
  reference before relying on them.
- **CPU-only.** OpenCV's trackers have no GPU path; keep resolution modest,
  or set `max_dim` to auto-downscale large frames for speed.
- **Single-camera, 1–2 objects.** Heavily occluded or deformable targets may
  still drop out even with the template fallback.
- **FFT resolution** is bounded by video length (longer clips resolve finer
  frequencies).
- **A lost target with no flow signal** freezes at the last known bbox and
  records `confidence = 0` — but only when both template re-acquire and the
  optical-flow fallback fail.
- **YAML configs need PyYAML.** JSON configs work with the standard library
  alone; OpenCV is required only for the video steps.

## Tests & coverage

The suite currently covers 124 cases. Run it with:

```bash
python -m pytest -q
```

Target line coverage is >= 80%, matching the repository's quality baseline.
OpenCV-dependent tests skip cleanly when the full stack is not installed; the
FFT / CSV / JSON / report paths are pure numpy and always run.

## Project layout

```
video-tracker/
  SKILL.md                  # agent execution guide (MANDATORY WORKFLOW)
  README.md / README_zh.md  # docs (this file + Chinese)
  config.yaml               # configuration template
  scripts/
    __init__.py
    errors.py               # exception types
    config.py               # config loading + validation + TrackerParams
    tracker.py              # CSRT loop + template re-acquire
    fft_analyzer.py         # numpy FFT + peak extraction + figures
    physics.py              # numpy-only physics-consistency probes
    data_export.py          # CSV / JSON writers
    report.py               # Markdown report
    run.py                  # CLI entry point
  tests/                    # unit + documentation-contract tests
  assets/example_output/    # outputs from the built-in demo
```

## Using as an agent skill

Drop the folder into any Agent harness that supports the Skill
specification. When a request matches the scope (experiment video, physics
motion data extraction), the Agent reads `SKILL.md` and follows its
MANDATORY WORKFLOW:

1. Confirm the video path, FPS, and the ROI(s) of the target object(s).
2. Load the config (`config.yaml` or JSON) — declares `videos`, `objects`,
   `fps`, optional `scale_cm_per_px`, CSRT `params`, and the tracking knobs
   `tracker_type` / `subpixel` / `use_optical_flow_fallback` / `max_dim` /
   `frame_step`.
3. Probe the container: `python scripts/run.py probe --config cfg` prints FPS,
   frame count, resolution.
4. Track: `python scripts/run.py track --config cfg` writes
   `<video>_tracking.csv` and `<video>_summary.json`. The raw video is never
   modified.
5. Spectrum: `python scripts/run.py fft --config cfg` writes
   `<video>_fft.json` + `<video>_spectra.png`.
6. Report: `python scripts/run.py report --config cfg` writes
   `<video>_report.md`.
7. Tune tracking quality if needed: switch `tracker_type` (`auto` / `csrt` /
   `template`), adjust `params` (e.g. lower `psr_threshold` for
   occlusion-prone setups), or enable `subpixel` /
   `use_optical_flow_fallback`.

Common request shapes:

- "Track the pendulum bob in this video and give me x(t) in cm."
- "What's the dominant frequency of the oscillation?"
- "The ball hides behind the shelf for two seconds — can you re-acquire?"
- "Process these three projectile videos and roll up the results."

The skill is self-contained: it imports nothing from sibling skills.

## License

Released under the MIT License. See `LICENSE`. Upstream reference material
(Theddeus / Thomas-Kr CSRT scripts) that this skill was derived from is kept
out of the shipped tree; the skill is self-contained and imports nothing from
sibling skills or external reference directories.

## Report issues

Preferred: Open an issue on the repository's **Issues** page. For
security-vulnerability reports, use the alternative channel below.

Alternative (security-vulnerability reports only): Send an email to
`jiamingshi_git@outlook.com`.

- **Subject**: Must include the prefix `agent-skill_report`, the specific
  skill name, and a brief description.
  - Example: `agent-skill_report video-tracker: the template re-acquire
    drifts off a fast-moving target and the report silently mislabels the
    lost frames`
- **Body**: Must include reproduction steps, expected behavior, actual
  behavior, and the runtime environment (OS, Python version, relevant
  dependencies installed).
- For severe reports like "file lost or corrupted", attach the before/after
  directory tree (`tree` output) and the generated `verification_report.md`.
- Contributors who submit clear, reproducible issues or pull requests will be
  listed in the acknowledgements of the next release notes.
