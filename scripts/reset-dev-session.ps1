param(
    [int]$Port = 8501,
    [switch]$RemovePycache,
    [switch]$ClearRuffCache
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[reset] $Message" -ForegroundColor Cyan
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Step "Workspace: $repoRoot"

$stopFailed = $false
try {
    & "$PSScriptRoot\stop_streamlit_port.ps1" -Port $Port
} catch {
    $stopFailed = $true
    Write-Step $_.Exception.Message
}

if ($RemovePycache) {
    Write-Step "Removing __pycache__ folders..."
    Get-ChildItem -Path $repoRoot -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq "__pycache__" } |
        ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
}

if ($ClearRuffCache -and (Test-Path ".ruff_cache")) {
    Write-Step "Removing .ruff_cache..."
    Remove-Item ".ruff_cache" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Step "Reset complete."
if ($stopFailed) {
    throw "Reset completed local cache cleanup, but runtime stop did not succeed."
}
