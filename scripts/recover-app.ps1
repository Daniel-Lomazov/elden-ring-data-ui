param(
    [int]$Port = 8501,
    [int]$WaitForReadySeconds = 60,
    [string]$EnvName = "elden_ring_ui",
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[recover] $Message" -ForegroundColor Green
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Step "Resetting local app session..."
& "$PSScriptRoot\reset-dev-session.ps1" -Port $Port

Write-Step "Starting app in background and waiting for readiness..."
& "$PSScriptRoot\start-app.ps1" -EnvName $EnvName -Port $Port -WaitForReadySeconds $WaitForReadySeconds -OpenBrowser:$OpenBrowser
