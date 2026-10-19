<#
.SYNOPSIS
  One-line web installer for agent-skills -- no local installer file needed.

.DESCRIPTION
  Self-contained bootstrap designed to be piped straight into PowerShell:

      irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1 | iex

  It downloads the repository archive to a temp folder, copies the requested
  skill(s) into each target harness framework's skills directory, verifies
  the install, and cleans up after itself.  Nothing is left on disk except
  the installed skills.  Pure Windows PowerShell 5.1+; no Python required.

  To pass parameters through the pipe, use the scriptblock form:

      & ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) `
          -Skill task-organizer -Frameworks codex,workbuddy -Scope project -Dir C:\path\to\proj

.PARAMETER Repo
  GitHub "owner/name" of the repository.  Defaults to the public repo.

.PARAMETER Branch
  Branch or tag to fetch.  Defaults to "main".

.PARAMETER Skill
  Skill name(s) to install; comma-separated values are accepted.  "*" (the
  default) installs every skill that ships in the repository.

.PARAMETER Frameworks
  Target harness framework(s): workbuddy, claude, codex, dsh.  Comma-
  separated values are accepted.  Defaults to codex.

.PARAMETER Scope
  "user" installs into your home folder (every project of the framework can
  use the skill); "project" installs into one task folder only.

.PARAMETER Dir
  Task folder for project scope (defaults to the current directory).

.PARAMETER Force
  Overwrite an existing install instead of skipping it.

.EXAMPLE
  irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1 | iex
  Install every skill into the user-scoped Codex directory.

.EXAMPLE
  & ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill conflict-detector -Frameworks codex,workbuddy -Scope project -Dir D:\work\myproj
#>
[CmdletBinding()]
param(
    [string]$Repo = "JiamingShi-JsPhys/agent-skills",
    [string]$Branch = "main",
    [string[]]$Skill = @("*"),
    [string[]]$Frameworks = @("codex"),
    [ValidateSet("user", "project")]
    [string]$Scope = "user",
    [string]$Dir = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
# Windows PowerShell 5.1 renders a slow per-byte progress bar for
# Invoke-WebRequest / Expand-Archive; for a piped one-liner that spam is
# worse than useless.
$ProgressPreference = "SilentlyContinue"
# Windows PowerShell 5.1 defaults to TLS 1.0 on older systems; GitHub needs 1.2.
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
}
catch {
    # Best effort only; newer runtimes ignore this.
}

# --------------------------------------------------------------------------
# Framework table (must match installer/platform_paths.py)
# --------------------------------------------------------------------------
$FrameworkLabels = @{
    workbuddy = "WorkBuddy"
    claude    = "Claude Code"
    codex     = "OpenAI Codex"
    dsh       = "DeepSeek Harness"
}
$UserRoots = @{
    workbuddy = ".workbuddy\skills"
    claude    = ".claude\skills"
    codex     = ".codex\skills"
    dsh       = ".dsh\skills"
}
$ProjectRoots = @{
    workbuddy = ".workbuddy\skills"
    claude    = ".claude\skills"
    codex     = ".agents\skills"   # Codex's project layout is the shared agents root
    dsh       = ".dsh\skills"
}

# --------------------------------------------------------------------------
# Install manifest (must match INSTALL_MANIFEST in installer/installer_core.py)
# --------------------------------------------------------------------------
# Only these files/directories are installed: a lean runtime copy (SKILL.md +
# code + runtime-referenced files).  Repo-only material -- README, CHANGELOG,
# tests, packaging metadata, unused examples -- stays in the archive; a
# user's skills folder should hold what runs, not what develops.  A root
# test fails when this table and the Python manifest drift apart.  A skill
# missing from the table is copied whole (forward-compatible default).
$InstallManifest = @{
    "task-organizer"             = @("SKILL.md", "scripts")
    "formula-validator"          = @("SKILL.md", "scripts")
    "multi-dim-manager"          = @("SKILL.md", "scripts", "config.example.yaml")
    "longitudinal-analysis"      = @("SKILL.md", "src", "R", "config/examples")
    "conflict-detector"          = @("SKILL.md", "src", "config/examples")
    "document-evolution-tracker" = @("SKILL.md", "src", "config/examples")
    "video-tracker"              = @("SKILL.md", "scripts")
}

function Resolve-TargetRoot {
    param([string]$Framework, [string]$Scope, [string]$ProjectDir)
    if ($Scope -eq "user") {
        return (Join-Path $HOME $UserRoots[$Framework])
    }
    return (Join-Path $ProjectDir $ProjectRoots[$Framework])
}

# --------------------------------------------------------------------------
# Validate inputs
# --------------------------------------------------------------------------
$badFw = $Frameworks | Where-Object { -not $FrameworkLabels.ContainsKey($_) }
if ($badFw) {
    throw "Unknown framework(s): $($badFw -join ', '). Choose from: $($FrameworkLabels.Keys -join ', ')"
}
if ($Scope -eq "project") {
    if ([string]::IsNullOrWhiteSpace($Dir)) {
        $Dir = (Get-Location).Path
    }
    if (-not (Test-Path -LiteralPath $Dir)) {
        throw "Task folder not found: $Dir"
    }
}

# --------------------------------------------------------------------------
# Download + expand the repository archive into a temp folder
# --------------------------------------------------------------------------
$token = [guid]::NewGuid().ToString("N")
$archive = Join-Path $env:TEMP "agent-skills-$token.zip"
$expand = Join-Path $env:TEMP "agent-skills-$token"
try {
    $url = "https://codeload.github.com/$Repo/zip/refs/heads/$Branch"
    Write-Host "agent-skills web installer"
    Write-Host "  source  : $Repo @ $Branch"
    Write-Host "  scope   : $Scope$(if ($Scope -eq 'project') { " -> $Dir" })"
    Write-Host "  targets : $(($Frameworks | ForEach-Object { $FrameworkLabels[$_] }) -join ', ')"
    Write-Host ""
    Write-Host "Downloading repository archive ..."
    Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing
    # .NET extraction instead of Expand-Archive: the cmdlet's progress bar
    # ignores $ProgressPreference on PowerShell 5.1 and floods the console.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($archive, $expand)
    $root = Get-ChildItem -Path $expand -Directory | Select-Object -First 1
    if (-not $root) {
        throw "Archive did not contain a repository folder: $archive"
    }

    # --------------------------------------------------------------------------
    # Resolve the skill list (方案 C layout: skills live under skills/<name>)
    # --------------------------------------------------------------------------
    $skillsDir = Join-Path $root.FullName "skills"
    $allSkills = Get-ChildItem -Path $skillsDir -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
        Select-Object -ExpandProperty Name
    if (-not $allSkills) {
        throw "No skill (folder with SKILL.md) found in $Repo @ $Branch"
    }
    if ($Skill -contains "*" -or $Skill -contains "all") {
        $skills = $allSkills
    }
    else {
        $skills = @()
        foreach ($name in $Skill) {
            if ($allSkills -contains $name) {
                $skills += $name
            }
            else {
                throw "Skill '$name' not found. Available: $($allSkills -join ', ')"
            }
        }
    }
    Write-Host "  skills  : $($skills -join ', ')"
    Write-Host ""

    # --------------------------------------------------------------------------
    # Install: skill x framework
    # --------------------------------------------------------------------------
    $installed = 0
    $skipped = 0
    $failed = @()
    foreach ($name in $skills) {
        $src = Join-Path $skillsDir $name
        foreach ($fw in $Frameworks) {
            $label = $FrameworkLabels[$fw]
            $targetRoot = Resolve-TargetRoot -Framework $fw -Scope $Scope -ProjectDir $Dir
            $dst = Join-Path $targetRoot $name
            if (Test-Path -LiteralPath $dst) {
                if ($Force) {
                    Remove-Item -LiteralPath $dst -Recurse -Force
                }
                else {
                    Write-Host ("  SKIP  {0,-24} {1,-14} already exists (use -Force)" -f $name, $label)
                    $skipped++
                    continue
                }
            }
            New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
            New-Item -ItemType Directory -Path $dst -Force | Out-Null
            $keep = $InstallManifest[$name]
            $installOk = $true
            if ($keep) {
                foreach ($rel in $keep) {
                    $item = Join-Path $src $rel
                    if (-not (Test-Path -LiteralPath $item)) {
                        Write-Host ("  FAIL  {0,-24} {1,-14} manifest entry missing: {2}" -f $name, $label, $rel)
                        $installOk = $false
                        continue
                    }
                    Copy-Item -LiteralPath $item -Destination (Join-Path $dst $rel) -Recurse -Force
                }
            }
            else {
                # Unknown skill (not in the manifest): copy everything.
                Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force
            }
            if ($installOk -and (Test-Path -LiteralPath (Join-Path $dst "SKILL.md"))) {
                Write-Host ("  OK    {0,-24} {1,-14} {2}" -f $name, $label, $dst)
                $installed++
            }
            else {
                Write-Host ("  FAIL  {0,-24} {1,-14} verification failed" -f $name, $label)
                $failed += "$name -> $label"
            }
        }
    }

    Write-Host ""
    if ($failed.Count -gt 0) {
        Write-Host "Installation finished with errors:" -ForegroundColor Red
        $failed | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        exit 1
    }
    Write-Host "Installation complete: $installed skill install(s), $skipped skipped."
    if ($Scope -eq "project") {
        Write-Host "Only this task folder can see the skill(s): $Dir"
    }
    else {
        Write-Host "Every project of the selected framework(s) can use the skill(s)."
    }
    exit 0
}
finally {
    # Never leave the archive or its extraction behind.
    Remove-Item -LiteralPath $expand -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
}
