param(
    [int]$Port = 8501,
    [switch]$RemovePycache,
    [switch]$ClearRuffCache
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[reset] $Message" -ForegroundColor Cyan
}

function Stop-ProcessSafe([int]$ProcessId) {
    try {
        Stop-Process -Id $ProcessId -Force -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Step "Workspace: $repoRoot"

$stopped = @()

$listenerPid = $null
if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) {
        $listenerPid = [int]$listener.OwningProcess
    }
} else {
    $netstatRows = netstat -ano -p tcp | Select-String -Pattern ":$Port\s" | ForEach-Object { $_.ToString() }
    foreach ($row in $netstatRows) {
        if ($row -match "LISTENING\s+(\d+)$") {
            $listenerPid = [int]$matches[1]
            break
        }
    }
}

if ($listenerPid) {
    if (Stop-ProcessSafe -ProcessId $listenerPid) {
        $stopped += $listenerPid
        Write-Step "Stopped listener on port $Port (PID $listenerPid)."
    }
}

$workspacePattern = [Regex]::Escape($repoRoot)
if (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) {
    $streamlitProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match "python|streamlit|conda" -and
            $_.CommandLine -and
            $_.CommandLine -match "streamlit\s+run\s+app.py" -and
            $_.CommandLine -match $workspacePattern
        }

    foreach ($proc in $streamlitProcesses) {
        if ($stopped -contains $proc.ProcessId) { continue }
        if (Stop-ProcessSafe -ProcessId $proc.ProcessId) {
            $stopped += $proc.ProcessId
            Write-Step "Stopped workspace Streamlit process (PID $($proc.ProcessId))."
        }
    }
} else {
    Write-Step "Get-CimInstance not available; skipped command-line process scan."
}

if (-not $stopped -or $stopped.Count -eq 0) {
    Write-Step "No running workspace Streamlit processes found."
}

if ($RemovePycache) {
    Write-Step "Removing __pycache__ folders..."
    Get-ChildItem -Path $repoRoot -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq "__pycache__" } |
        ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
}

if ($ClearRuffCache -and (Test-Path ".ruff_cache")) {
    Write-Step "Removing .ruff_cache..."
    Remove-Item ".ruff_cache" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Step "Reset complete."
