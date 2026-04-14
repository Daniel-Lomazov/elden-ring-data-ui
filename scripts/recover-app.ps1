param(
    [int]$Port = 8501,
    [int]$WaitForReadySeconds = 60,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[recover] $Message" -ForegroundColor Green
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Step "Delegating recovery to runtime controller..."
& "$PSScriptRoot\start-app.ps1" -Port $Port -ResetFirst -WaitForReadySeconds $WaitForReadySeconds -OpenBrowser:$OpenBrowser
