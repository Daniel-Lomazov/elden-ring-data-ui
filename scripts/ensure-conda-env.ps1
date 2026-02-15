param(
    [string]$EnvName = "elden_ring_ui",
    [string]$EnvFile = "environment.yml",
    [string]$RequirementsFile = "requirements.txt",
    [switch]$AlwaysUpdate,
    [switch]$AlwaysSyncPip
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[env] $Message" -ForegroundColor Cyan
}

function Get-FileSha256([string]$Path) {
    if (-not (Test-Path $Path)) {
        return ""
    }
    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
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
    $cacheDir = Join-Path $repoRoot ".cache"
    $reqStampPath = Join-Path $cacheDir "requirements.sha256"
    $currentHash = Get-FileSha256 -Path $RequirementsFile
    $previousHash = ""
    if (Test-Path $reqStampPath) {
        $previousHash = (Get-Content $reqStampPath -ErrorAction SilentlyContinue | Select-Object -First 1)
    }

    $needsPipSync = $AlwaysSyncPip -or $AlwaysUpdate -or (-not $envExists) -or ($currentHash -ne $previousHash)
    if ($needsPipSync) {
        Write-Step "Installing/updating pip requirements from $RequirementsFile..."
        conda run -n $EnvName python -m pip install --upgrade pip
        conda run -n $EnvName python -m pip install -r $RequirementsFile
        if (-not (Test-Path $cacheDir)) {
            New-Item -ItemType Directory -Path $cacheDir | Out-Null
        }
        Set-Content -Path $reqStampPath -Value $currentHash -Encoding utf8
    } else {
        Write-Step "Pip requirements unchanged; skipping pip sync (use -AlwaysSyncPip to force)."
    }
}

Write-Step "Environment ready: $EnvName"
