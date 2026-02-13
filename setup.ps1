<#
Simple Windows setup script for the trimmed Elden Ring Data UI.
Usage:
  - To create the conda environment (recommended):
      .\setup.ps1
  - To create a venv instead:
      .\setup.ps1 -UseVenv
#>
param(
    [switch]$UseVenv
)

function Write-Info($msg){ Write-Host $msg -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host $msg -ForegroundColor Red }

if (-not $UseVenv) {
    if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
        Write-Warn "Conda not found. Re-run with -UseVenv to create a Python venv instead."
        exit 1
    }

    if (Test-Path ".\scripts\ensure-conda-env.ps1") {
        Write-Info "Delegating to scripts\ensure-conda-env.ps1 ..."
        & ".\scripts\ensure-conda-env.ps1" -EnvName "elden_ring_ui"
    } else {
        Write-Info "scripts\ensure-conda-env.ps1 not found, using legacy conda create/update flow..."
        try {
            conda env create -f environment.yml -n elden_ring_ui 2>&1 | Write-Host
        } catch {
            Write-Info "Environment may already exist — attempting update..."
            conda env update -f environment.yml -n elden_ring_ui 2>&1 | Write-Host
        }
    }
    Write-Info 'Done. Activate with: conda activate elden_ring_ui'
} else {
    Write-Info 'Creating a Python virtual environment in .\venv and installing requirements...'
    python -m venv .venv
    .\.venv\Scripts\Activate
    python -m pip install --upgrade pip
    if (Test-Path requirements.txt) {
        pip install -r requirements.txt
    } else {
        Write-Warn "requirements.txt not found. Nothing installed."
    }
    Write-Info 'Done. Activate the venv with: .\.venv\Scripts\Activate'
}

Write-Info "Setup complete. Run the app with: streamlit run app.py"
