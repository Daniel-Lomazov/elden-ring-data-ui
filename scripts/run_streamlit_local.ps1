param(
    [string]$EnvName = "elden_ring_ui",
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[run_streamlit_local] $Message" -ForegroundColor Green
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw "Conda is required but was not found on PATH."
}

$envJson = conda env list --json | Out-String | ConvertFrom-Json
$envPath = $null
foreach ($path in $envJson.envs) {
    if ((Split-Path $path -Leaf) -ieq $EnvName) {
        $envPath = $path
        break
    }
}
if (-not $envPath) {
    throw "Conda environment '$EnvName' was not found."
}

$pythonExe = Join-Path $envPath "python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found in environment '$EnvName': $pythonExe"
}

$url = "http://localhost:$Port"
Write-Step "Starting Streamlit (local-only defaults from .streamlit/config.toml)..."
Write-Host "LOCAL_URL=$url"
Write-Host "Press Ctrl+C in this terminal to stop Streamlit."
Write-Host "If process persists, run: ./scripts/stop_streamlit_port.ps1 -Port $Port"

& $pythonExe -m streamlit run app.py --server.port $Port
