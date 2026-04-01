param(
    [int]$Port = 8501,
    [string]$EnvName = "elden_ring_ui",
    [switch]$ForceAnyListener
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot\conda-utils.ps1"

function Write-Step([string]$Message) {
    Write-Host "[stop_streamlit_port] $Message" -ForegroundColor Cyan
}

function Resolve-EnvPython([string]$TargetEnvName) {
    $condaExe = Resolve-CondaExecutable
    if (-not $condaExe) {
        return $null
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
        return $null
    }

    $pythonExe = Join-Path $envPath "python.exe"
    if (-not (Test-Path $pythonExe)) {
        return $null
    }

    return $pythonExe
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not $ForceAnyListener) {
    $pythonExe = Resolve-EnvPython -TargetEnvName $EnvName
    if ($pythonExe) {
        Write-Step "Delegating stop to runtime controller..."
        & $pythonExe -m tools.runtime_controller stop --port $Port
        $controllerExitCode = $LASTEXITCODE
        if ($controllerExitCode -eq 0) {
            return
        }
        throw "Runtime controller stop failed with exit code $controllerExitCode. Re-run with -ForceAnyListener to hard-kill any listener on the port."
    }

    Write-Step "Runtime controller Python could not be resolved. Falling back to emergency port kill."
}

$pids = @()
$rows = netstat -ano | findstr ":$Port"
if ($rows) {
    foreach ($row in $rows) {
        $line = ($row -replace "\s+", " ").Trim()
        if ($line -match "^(TCP|UDP)\s+\S+:$Port\s+\S+\s+(LISTENING\s+)?(\d+)$") {
            $procId = [int]$matches[3]
            if (-not ($pids -contains $procId)) { $pids += $procId }
        }
    }
}

if (-not $pids -or $pids.Count -eq 0) {
    Write-Step "No process is listening on port $Port."
    return
}

foreach ($procId in $pids) {
    Write-Step "Stopping PID $procId on port $Port ..."
    taskkill /PID $procId /F | Out-Null
}

Start-Sleep -Milliseconds 250
$remaining = netstat -ano | findstr ":$Port" | findstr "LISTENING"
if ($remaining) {
    throw "Port $Port still has active listener entries after emergency cleanup."
}

Write-Step "Port $Port is no longer listening."
