<#
Simple Windows setup script for the trimmed Elden Ring Data UI.
Usage:
  - To create the uv-managed local environment (recommended):
      .\setup.ps1
  - The -UseVenv switch is retained as a compatibility alias:
      .\setup.ps1 -UseVenv
#>
param(
    [switch]$UseVenv
)

function Write-Info($msg){ Write-Host $msg -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host $msg -ForegroundColor Red }

$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Err "uv not found. Install uv and re-run this script."
    throw "uv not found. Install uv and re-run this script."
}

if ($UseVenv) {
    Write-Warn "-UseVenv is now a compatibility alias; uv handles the environment setup."
}

$repoRoot = $PSScriptRoot
Set-Location $repoRoot

$venvPath = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$desiredPythonVersion = "3.11"

if (Test-Path $venvPython) {
    try {
        $existingPythonVersion = & $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($existingPythonVersion.Trim() -ne $desiredPythonVersion) {
            Write-Warn "Existing .venv uses Python $existingPythonVersion; recreating with Python $desiredPythonVersion..."
            Remove-Item -Recurse -Force $venvPath
        } else {
            Write-Info "Refreshing existing .venv with uv..."
        }
    } catch {
        Write-Warn "Existing .venv could not be inspected; recreating it with uv..."
        Remove-Item -Recurse -Force $venvPath
    }
}

if (-not (Test-Path $venvPython)) {
    Write-Info "Creating .venv with uv..."
    uv venv --python $desiredPythonVersion .venv
    if ($LASTEXITCODE -ne 0) { throw "uv venv failed with exit code $LASTEXITCODE." }
}

if (-not (Test-Path "requirements.txt")) {
    Write-Err "requirements.txt not found. Cannot sync dependencies."
    throw "requirements.txt not found. Cannot sync dependencies."
}

Write-Info "Installing requirements into .venv..."
uv pip install --reinstall --python $venvPython -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "uv pip install failed with exit code $LASTEXITCODE." }

Write-Info 'Done. Activate with: .\.venv\Scripts\Activate.ps1'
Write-Info 'Or run directly with: .\.venv\Scripts\python.exe -m streamlit run app.py'
Write-Info "Setup complete."
