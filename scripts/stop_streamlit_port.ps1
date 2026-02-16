param(
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[stop_streamlit_port] $Message" -ForegroundColor Cyan
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
    exit 0
}

foreach ($procId in $pids) {
    Write-Step "Stopping PID $procId on port $Port ..."
    taskkill /PID $procId /F | Out-Null
}

Start-Sleep -Milliseconds 250
$remaining = netstat -ano | findstr ":$Port" | findstr "LISTENING"
if ($remaining) {
    Write-Step "Port $Port still has active entries; run again if needed."
    exit 1
}

Write-Step "Port $Port is no longer listening."
