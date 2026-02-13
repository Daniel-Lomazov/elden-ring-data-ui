param(
    [string]$EnvName = "elden_ring_ui",
    [string]$EnvFile = "environment.yml",
    [string]$RequirementsFile = "requirements.txt",
    [switch]$AlwaysUpdate
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[env] $Message" -ForegroundColor Cyan
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Step "Workspace: $repoRoot"

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw "Conda is not installed or not on PATH."
}

if (-not (Test-Path $EnvFile)) {
    throw "Environment file not found: $EnvFile"
}

$envJson = conda env list --json | Out-String | ConvertFrom-Json
$envExists = $false
foreach ($path in $envJson.envs) {
    if ((Split-Path $path -Leaf) -ieq $EnvName) {
        $envExists = $true
        break
    }
}

if (-not $envExists) {
    Write-Step "Creating conda environment '$EnvName' from $EnvFile..."
    conda env create -n $EnvName -f $EnvFile
} elseif ($AlwaysUpdate) {
    Write-Step "Updating conda environment '$EnvName' from $EnvFile..."
    conda env update -n $EnvName -f $EnvFile
} else {
    Write-Step "Conda environment '$EnvName' already exists."
}

if (Test-Path $RequirementsFile) {
    Write-Step "Installing/updating pip requirements from $RequirementsFile..."
    conda run -n $EnvName python -m pip install --upgrade pip
    conda run -n $EnvName python -m pip install -r $RequirementsFile
}

Write-Step "Environment ready: $EnvName"
