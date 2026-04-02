param(
    [string]$EnvName = "elden_ring_ui",
    [int]$Port = 8501,
    [switch]$ResetFirst,
    [int]$WaitForReadySeconds = 45,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot\conda-utils.ps1"

function Write-Step([string]$Message) {
    Write-Host "[start-app] $Message" -ForegroundColor Green
}

function Resolve-EnvPython([string]$TargetEnvName) {
    $condaExe = Resolve-CondaExecutable
    if (-not $condaExe) {
        throw "Conda is required but was not found. Install conda or initialize your shell."
    }

    $envJson = & $condaExe env list --json | Out-String | ConvertFrom-Json
    $envPath = $null
    foreach ($path in $envJson.envs) {
        if ((Split-Path $path -Leaf) -ieq $TargetEnvName) {
            $envPath = $path
            break
        }
    }

    if (-not $envPath) {
        throw "Conda environment '$TargetEnvName' was not found. Run scripts/ensure-conda-env.ps1 first."
    }

    $pythonExe = Join-Path $envPath "python.exe"
    if (-not (Test-Path $pythonExe)) {
        throw "Python executable not found in environment '$TargetEnvName': $pythonExe"
    }

    return $pythonExe
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not $PSBoundParameters.ContainsKey("OpenBrowser")) {
    $OpenBrowser = $false
    Write-Step "External browser launch disabled by default. Open the app URL inside VS Code when needed."
}

$controllerCommand = if ($ResetFirst) { "recover" } else { "start" }
$pythonExe = Resolve-EnvPython -TargetEnvName $EnvName
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
