param(
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[run_streamlit_local] $Message" -ForegroundColor Green
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found in .venv: $pythonExe. Run .\setup.ps1 first."
}

$url = "http://localhost:$Port"
Write-Step "Starting Streamlit (local-only defaults from .streamlit/config.toml)..."
Write-Host "LOCAL_URL=$url"
Write-Host "Press Ctrl+C in this terminal to stop Streamlit."
Write-Host "If process persists, run: ./scripts/stop_streamlit_port.ps1 -Port $Port"

& $pythonExe -m streamlit run app.py --server.port $Port
