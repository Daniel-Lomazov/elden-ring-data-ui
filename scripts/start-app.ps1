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

function Write-Timing([string]$Label, [double]$Seconds) {
    Write-Host ("[start-app] {0}: {1:N2}s" -f $Label, $Seconds) -ForegroundColor DarkGreen
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not $PSBoundParameters.ContainsKey("OpenBrowser")) {
    $OpenBrowser = $true
    Write-Step "Browser handling enabled by default."
}

$totalTimer = [System.Diagnostics.Stopwatch]::StartNew()

if ($ResetFirst) {
    & "$PSScriptRoot\reset-dev-session.ps1" -Port $Port
}

$condaExe = Resolve-CondaExecutable
if (-not $condaExe) {
    throw "Conda is required but was not found. Install conda or initialize your shell."
}

$envJson = & $condaExe env list --json | Out-String | ConvertFrom-Json
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

$url = "http://localhost:$Port"
$browserPidStatePath = Join-Path $repoRoot ".streamlit_browser_pid"

Write-Step "Starting Streamlit in background on $url ..."
$spawnTimer = [System.Diagnostics.Stopwatch]::StartNew()
$process = Start-Process -FilePath $pythonExe -ArgumentList @(
    "-m",
    "streamlit",
    "run",
    "app.py",
    "--server.port",
    "$Port",
    "--server.headless",
    "true"
) -WorkingDirectory $repoRoot -WindowStyle Minimized -PassThru
$spawnTimer.Stop()
Write-Timing "Spawn Streamlit process" $spawnTimer.Elapsed.TotalSeconds

Start-Sleep -Milliseconds 500

function Get-ListenerPid([int]$TargetPort) {
    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $listener = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($listener) {
            return [int]$listener.OwningProcess
        }
        return $null
    }

    $netstatRows = netstat -ano -p tcp | Select-String -Pattern ":$TargetPort\s" | ForEach-Object { $_.ToString() }
    foreach ($row in $netstatRows) {
        if ($row -match "LISTENING\s+(\d+)$") {
            return [int]$matches[1]
        }
    }
    return $null
}

function Test-UrlReady([string]$TargetUrl) {
    try {
        $response = Invoke-WebRequest -Uri $TargetUrl -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Open-OrRefreshBrowser([string]$TargetUrl, [int]$TargetPort) {
    try {
        $wshell = New-Object -ComObject WScript.Shell
    } catch {
        Start-Process $TargetUrl | Out-Null
        return "opened"
    }

    function Find-TargetEdgeWindows([int]$PortToMatch) {
        try {
            return Get-Process -Name "msedge" -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*localhost:$PortToMatch*"
                }
        } catch {
            return @()
        }
    }

    function Try-FocusAndRefresh([object]$ProcToRefresh) {
        if (-not $ProcToRefresh) {
            return $false
        }
        $activated = $false
        try {
            $activated = $wshell.AppActivate([int]$ProcToRefresh.Id)
        } catch {
            $activated = $false
        }
        if (-not $activated -and $ProcToRefresh.MainWindowTitle) {
            try {
                $activated = $wshell.AppActivate($ProcToRefresh.MainWindowTitle)
            } catch {
                $activated = $false
            }
        }
        if (-not $activated) {
            return $false
        }
        Start-Sleep -Milliseconds 250
        $wshell.SendKeys("{F5}")
        return $true
    }

    function Open-NewEdgeWindow([string]$UrlToOpen) {
        $edgeCmd = Get-Command msedge -ErrorAction SilentlyContinue
        if ($edgeCmd) {
            $openedProc = Start-Process -FilePath $edgeCmd.Source -ArgumentList @("--new-window", $UrlToOpen) -PassThru
            if ($openedProc) {
                Set-Content -Path $browserPidStatePath -Value "$($openedProc.Id)" -Encoding utf8
            }
            Start-Sleep -Milliseconds 500
            $candidateWindows = @(Find-TargetEdgeWindows -PortToMatch $TargetPort)
            if ($candidateWindows.Count -gt 0) {
                $focusProc = $candidateWindows | Select-Object -Last 1
                if (Try-FocusAndRefresh -ProcToRefresh $focusProc) {
                    return "opened_refreshed"
                }
            }
            return "opened"
        }
        Start-Process $UrlToOpen | Out-Null
        return "opened"
    }

    $targetWindows = @(Find-TargetEdgeWindows -PortToMatch $TargetPort)
    if ($targetWindows.Count -gt 1) {
        foreach ($proc in $targetWindows) {
            try {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            } catch {
            }
        }
        Start-Sleep -Milliseconds 400
        return Open-NewEdgeWindow -UrlToOpen $TargetUrl
    }

    if ($targetWindows.Count -eq 1) {
        $single = $targetWindows[0]
        if (Try-FocusAndRefresh -ProcToRefresh $single) {
            Set-Content -Path $browserPidStatePath -Value "$($single.Id)" -Encoding utf8
            return "refreshed"
        }
        return Open-NewEdgeWindow -UrlToOpen $TargetUrl
    }

    if (Test-Path $browserPidStatePath) {
        try {
            $savedPidRaw = Get-Content $browserPidStatePath -ErrorAction Stop | Select-Object -First 1
            $savedPid = [int]$savedPidRaw
            $savedProc = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
            if ($savedProc -and $savedProc.MainWindowHandle -ne 0) {
                if (Try-FocusAndRefresh -ProcToRefresh $savedProc) {
                    return "refreshed"
                }
            }
        } catch {
        }
    }

    try {
        $appTitleWindow = Get-Process -Name "msedge" -ErrorAction SilentlyContinue |
            Where-Object {
                $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*Elden Ring - Ranking UI*"
            } |
            Select-Object -First 1
        if ($appTitleWindow) {
            if (Try-FocusAndRefresh -ProcToRefresh $appTitleWindow) {
                Set-Content -Path $browserPidStatePath -Value "$($appTitleWindow.Id)" -Encoding utf8
                return "refreshed"
            }
        }
    } catch {
    }

    return Open-NewEdgeWindow -UrlToOpen $TargetUrl
}

$listenerPid = $null
$ready = $false
$deadline = (Get-Date).AddSeconds([Math]::Max(1, $WaitForReadySeconds))

while ((Get-Date) -lt $deadline) {
    $listenerPid = Get-ListenerPid -TargetPort $Port
    if ($listenerPid -and (Test-UrlReady -TargetUrl $url)) {
        $ready = $true
        break
    }
    Start-Sleep -Milliseconds 600
}

$totalTimer.Stop()

Write-Host "APP_URL=$url"
Write-Host "START_PID=$($process.Id)"
if ($listenerPid) {
    Write-Host "LISTENER_PID=$listenerPid"
} else {
    Write-Host "LISTENER_PID=unknown"
}
Write-Host "READY=$ready"
Write-Host ("STARTUP_SECONDS={0:N2}" -f $totalTimer.Elapsed.TotalSeconds)

if (-not $ready) {
    Write-Step "App readiness not confirmed within $WaitForReadySeconds seconds."
}

if ($ready -and $OpenBrowser) {
    try {
        $browserAction = Open-OrRefreshBrowser -TargetUrl $url -TargetPort $Port
            if ($browserAction -eq "opened_refreshed" -or $browserAction -eq "refreshed") {
            Write-Host "BROWSER_REFRESHED=True"
        } else {
            Write-Host "BROWSER_OPENED=True"
        }
    } catch {
        Write-Host "BROWSER_OPENED=False"
        Write-Step "Could not open browser automatically: $($_.Exception.Message)"
    }
}

Write-Step "Use scripts/reset-dev-session.ps1 to stop the app cleanly."
