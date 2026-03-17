function Resolve-CondaExecutable {
    $commandCandidates = @("conda", "conda.exe")
    foreach ($command in $commandCandidates) {
        $resolved = Get-Command $command -ErrorAction SilentlyContinue
        if ($resolved -and $resolved.Source -and (Test-Path $resolved.Source)) {
            return (Resolve-Path $resolved.Source).Path
        }
    }

    $pathCandidates = @()
    if ($env:CONDA_EXE) {
        $pathCandidates += $env:CONDA_EXE
    }

    $userHome = [Environment]::GetFolderPath("UserProfile")
    if ($userHome) {
        $pathCandidates += (Join-Path $userHome "anaconda3\Scripts\conda.exe")
        $pathCandidates += (Join-Path $userHome "miniconda3\Scripts\conda.exe")
        $pathCandidates += (Join-Path $userHome "AppData\Local\anaconda3\Scripts\conda.exe")
        $pathCandidates += (Join-Path $userHome "AppData\Local\miniconda3\Scripts\conda.exe")
    }

    if ($env:ProgramData) {
        $pathCandidates += (Join-Path $env:ProgramData "Anaconda3\Scripts\conda.exe")
        $pathCandidates += (Join-Path $env:ProgramData "Miniconda3\Scripts\conda.exe")
    }

    $uniqueCandidates = $pathCandidates | Where-Object { $_ } | Select-Object -Unique
    foreach ($candidate in $uniqueCandidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    return $null
}