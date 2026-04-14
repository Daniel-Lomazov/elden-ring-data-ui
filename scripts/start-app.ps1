param(
    [int]$Port = 8501,
    [switch]$ResetFirst,
    [int]$WaitForReadySeconds = 45,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[start-app] $Message" -ForegroundColor Green
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found in .venv: $pythonExe. Run .\setup.ps1 first."
}

if (-not $PSBoundParameters.ContainsKey("OpenBrowser")) {
    $OpenBrowser = $false
    Write-Step "External browser launch disabled by default. Open the app URL inside VS Code when needed."
}

$controllerCommand = if ($ResetFirst) { "recover" } else { "start" }
$controllerArgs = @(
    "-m",
    "tools.runtime_controller",
    $controllerCommand,
    "--port",
    "$Port",
    "--wait-seconds",
    "$WaitForReadySeconds"
)

if ($OpenBrowser) {
    $controllerArgs += "--open-browser"
} else {
    $controllerArgs += "--no-open-browser"
}

Write-Step "Delegating $controllerCommand to runtime controller on http://localhost:$Port ..."
& $pythonExe @controllerArgs
$controllerExitCode = $LASTEXITCODE
if ($controllerExitCode -ne 0) {
    throw "Runtime controller $controllerCommand failed with exit code $controllerExitCode."
}
