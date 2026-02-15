param(
    [string]$EnvName = "elden_ring_ui",
    [int]$Port = 8501,
    [switch]$SkipReset,
    [switch]$SkipVerify,
    [switch]$QuickVerify,
    [switch]$UltraQuick,
    [switch]$RunApp,
    [switch]$OpenBrowser,
    [switch]$AlwaysUpdateEnv,
    [switch]$AlwaysSyncPip,
    [switch]$RemovePycache,
    [switch]$ClearRuffCache,
    [int]$WaitForReadySeconds = 45
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[run-all] $Message" -ForegroundColor Green
}

function Write-Timing([string]$Label, [double]$Seconds) {
    Write-Host ("[run-all] {0}: {1:N2}s" -f $Label, $Seconds) -ForegroundColor DarkGreen
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$totalTimer = [System.Diagnostics.Stopwatch]::StartNew()

$autoFastLaunch = $RunApp -and -not $PSBoundParameters.ContainsKey("UltraQuick") -and -not $PSBoundParameters.ContainsKey("QuickVerify") -and -not $PSBoundParameters.ContainsKey("SkipVerify") -and -not $PSBoundParameters.ContainsKey("AlwaysUpdateEnv") -and -not $PSBoundParameters.ContainsKey("AlwaysSyncPip") -and -not $PSBoundParameters.ContainsKey("SkipReset")
if ($autoFastLaunch) {
    $UltraQuick = $true
    $OpenBrowser = $true
    Write-Step "Defaulting to fastest launch profile (UltraQuick + OpenBrowser)."
}

if ($UltraQuick) {
    $SkipReset = $true
    $SkipVerify = $true
    Write-Step "UltraQuick mode enabled: skipping reset, env setup, and verification."
}

if (-not $SkipReset) {
    Write-Step "Resetting local dev session..."
    $resetTimer = [System.Diagnostics.Stopwatch]::StartNew()
    & "$PSScriptRoot\reset-dev-session.ps1" -RemovePycache:$RemovePycache -ClearRuffCache:$ClearRuffCache
    $resetTimer.Stop()
    Write-Timing "Reset phase" $resetTimer.Elapsed.TotalSeconds
}

if (-not $UltraQuick) {
    Write-Step "Ensuring conda environment..."
    $envTimer = [System.Diagnostics.Stopwatch]::StartNew()
    & "$PSScriptRoot\ensure-conda-env.ps1" -EnvName $EnvName -AlwaysUpdate:$AlwaysUpdateEnv -AlwaysSyncPip:$AlwaysSyncPip
    $envTimer.Stop()
    Write-Timing "Environment phase" $envTimer.Elapsed.TotalSeconds
}

if (-not $SkipVerify) {
    Write-Step "Running workspace verification..."
    $verifyTimer = [System.Diagnostics.Stopwatch]::StartNew()
    & "$PSScriptRoot\verify-workspace.ps1" -EnvName $EnvName -Quick:$QuickVerify
    $verifyTimer.Stop()
    Write-Timing "Verification phase" $verifyTimer.Elapsed.TotalSeconds
}

if ($RunApp) {
    Write-Step "Starting Streamlit app..."
    $appTimer = [System.Diagnostics.Stopwatch]::StartNew()
    & "$PSScriptRoot\start-app.ps1" -EnvName $EnvName -Port $Port -WaitForReadySeconds $WaitForReadySeconds -OpenBrowser:$OpenBrowser
    $appTimer.Stop()
    Write-Timing "App launch phase" $appTimer.Elapsed.TotalSeconds
} else {
    Write-Step "Done. App not started (use -RunApp to launch)."
}

$totalTimer.Stop()
Write-Timing "Total run-all" $totalTimer.Elapsed.TotalSeconds
