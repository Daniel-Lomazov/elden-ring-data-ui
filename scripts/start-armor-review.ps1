param(
    [int]$Limit = 25,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found in .venv: $pythonExe. Run .\setup.ps1 first."
}

$dryArg = if ($DryRun) { "--dry-run" } else { "" }
$cmd = "Set-Location '$repoRoot'; & '$pythonExe' scripts/armor_family_review.py --limit $Limit $dryArg"

Start-Process -FilePath "pwsh" -ArgumentList @("-NoExit", "-Command", $cmd) | Out-Null
Write-Host "[start-armor-review] Opened review window." -ForegroundColor Green
