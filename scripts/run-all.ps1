param(
    [string]$EnvName = "elden_ring_ui",
    [int]$Port = 8501,
    [switch]$SkipReset,
    [switch]$SkipVerify,
    [switch]$RunApp,
    [switch]$OpenBrowser,
    [switch]$AlwaysUpdateEnv,
    [switch]$RemovePycache,
    [switch]$ClearRuffCache,
    [int]$WaitForReadySeconds = 45
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[run-all] $Message" -ForegroundColor Green
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not $SkipReset) {
    Write-Step "Resetting local dev session..."
    & "$PSScriptRoot\reset-dev-session.ps1" -RemovePycache:$RemovePycache -ClearRuffCache:$ClearRuffCache
}

Write-Step "Ensuring conda environment..."
& "$PSScriptRoot\ensure-conda-env.ps1" -EnvName $EnvName -AlwaysUpdate:$AlwaysUpdateEnv

if (-not $SkipVerify) {
    Write-Step "Running workspace verification..."
    & "$PSScriptRoot\verify-workspace.ps1" -EnvName $EnvName
}

if ($RunApp) {
    Write-Step "Starting Streamlit app..."
    & "$PSScriptRoot\start-app.ps1" -EnvName $EnvName -Port $Port -WaitForReadySeconds $WaitForReadySeconds -OpenBrowser
} else {
    Write-Step "Done. App not started (use -RunApp to launch)."
}
