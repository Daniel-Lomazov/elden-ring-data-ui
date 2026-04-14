param(
    [switch]$Quick,
    [switch]$SkipFinalCheck,
    [switch]$SkipOptimizerCheck
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[verify] $Message" -ForegroundColor Cyan
}

function Write-Timing([string]$Label, [double]$Seconds) {
    Write-Host ("[verify] {0}: {1:N2}s" -f $Label, $Seconds) -ForegroundColor DarkCyan
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found in .venv: $pythonExe. Run .\setup.ps1 first."
}

$scriptTimer = [System.Diagnostics.Stopwatch]::StartNew()

$requiredPaths = @(
    "app.py",
    "setup.ps1",
    "requirements.txt",
    "tests",
    "data/armors.csv",
    "tools/final_check.py",
    "tools/optimizer_check.py",
    "tools/workspace_verify.py"
)

foreach ($path in $requiredPaths) {
    if (-not (Test-Path $path)) {
        throw "Missing required file: $path"
    }
}

$skipFinal = $SkipFinalCheck.IsPresent
$skipOptimizer = $SkipOptimizerCheck.IsPresent
if ($Quick) {
    $skipOptimizer = $true
}

Write-Step "Running consolidated workspace verification..."
if ($Quick) {
    Write-Step "Quick mode enabled (optimizer check and app import check are skipped)."
}

$verifyTimer = [System.Diagnostics.Stopwatch]::StartNew()

$pythonArgs = @("-m", "tools.workspace_verify")
if ($skipFinal) {
    $pythonArgs += "--skip-final"
}
if ($skipOptimizer) {
    $pythonArgs += "--skip-optimizer"
}
if ($Quick) {
    $pythonArgs += "--quick"
    $pythonArgs += "--skip-tests"
}

& $pythonExe @pythonArgs
$verifyTimer.Stop()
Write-Timing "Verification runtime" $verifyTimer.Elapsed.TotalSeconds

$scriptTimer.Stop()
Write-Timing "Total verify script" $scriptTimer.Elapsed.TotalSeconds
Write-Step "Verification complete."
