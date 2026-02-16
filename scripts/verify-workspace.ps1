param(
    [string]$EnvName = "elden_ring_ui",
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

$scriptTimer = [System.Diagnostics.Stopwatch]::StartNew()

$requiredPaths = @(
    "app.py",
    "environment.yml",
    "requirements.txt",
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
$envJson = conda env list --json | Out-String | ConvertFrom-Json
$envPath = $null
foreach ($path in $envJson.envs) {
    if ((Split-Path $path -Leaf) -ieq $EnvName) {
        $envPath = $path
        break
    }
}
if (-not $envPath) {
    throw "Conda environment '$EnvName' was not found. Run scripts/ensure-conda-env.ps1 first."
}

$pythonExe = Join-Path $envPath "python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found in environment '$EnvName': $pythonExe"
}

$pythonArgs = @("-m", "tools.workspace_verify")
if ($skipFinal) {
    $pythonArgs += "--skip-final"
}
if ($skipOptimizer) {
    $pythonArgs += "--skip-optimizer"
}
if ($Quick) {
    $pythonArgs += "--quick"
}

& $pythonExe @pythonArgs
$verifyTimer.Stop()
Write-Timing "Verification runtime" $verifyTimer.Elapsed.TotalSeconds

$scriptTimer.Stop()
Write-Timing "Total verify script" $scriptTimer.Elapsed.TotalSeconds
Write-Step "Verification complete."
