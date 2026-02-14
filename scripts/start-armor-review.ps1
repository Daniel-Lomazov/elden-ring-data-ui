param(
    [string]$EnvName = "elden_ring_ui",
    [int]$Limit = 25,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$dryArg = if ($DryRun) { "--dry-run" } else { "" }
$cmd = "Set-Location '$repoRoot'; conda run -n $EnvName python scripts/armor_family_review.py --limit $Limit $dryArg"

Start-Process -FilePath "pwsh" -ArgumentList @("-NoExit", "-Command", $cmd) | Out-Null
Write-Host "[start-armor-review] Opened review window." -ForegroundColor Green
