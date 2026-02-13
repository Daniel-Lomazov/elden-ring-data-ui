param(
    [string]$EnvName = "elden_ring_ui"
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[verify] $Message" -ForegroundColor Cyan
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$requiredPaths = @(
    "app.py",
    "environment.yml",
    "requirements.txt",
    "data/armors.csv",
    "final_check.py",
    "optimizer_check.py"
)

foreach ($path in $requiredPaths) {
    if (-not (Test-Path $path)) {
        throw "Missing required file: $path"
    }
}

Write-Step "Running final_check.py..."
conda run -n $EnvName python final_check.py

Write-Step "Running optimizer_check.py..."
conda run -n $EnvName python optimizer_check.py

Write-Step "Verification complete."
