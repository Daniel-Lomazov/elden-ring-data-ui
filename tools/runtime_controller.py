from __future__ import annotations

import argparse
import base64
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.runtime_controller_state import RuntimeControllerState


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORT = 8501
DEFAULT_WAIT_SECONDS = 45
APP_TITLE = "Elden Ring - Ranking UI"
SAME_APP_PATTERN = re.compile(r"streamlit\s+run\s+app\.py", re.IGNORECASE)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def to_bool_text(value: bool) -> str:
    return "true" if value else "false"


class RuntimeController:
    def __init__(
        self,
        root: Path = ROOT,
        state_path: Path | None = None,
        log_path: Path | None = None,
        app_title: str = APP_TITLE,
    ) -> None:
        self.root = Path(root)
        cache_dir = self.root / ".cache"
        self.state_path = state_path or cache_dir / "runtime-controller.json"
        self.log_path = log_path or cache_dir / "runtime-controller.log"
        self.app_title = app_title

    def build_command(self, port: int) -> list[str]:
        return [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
        ]

    def ensure_cache_dir(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def append_log(self, message: str) -> None:
        self.ensure_cache_dir()
        with self.log_path.open("a", encoding="utf-8") as file_handle:
            file_handle.write(f"[{utc_now_iso()}] {message}\n")

    def load_state(self) -> dict[str, Any] | None:
        if not self.state_path.exists():
            return None
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.append_log(f"state read failed: {exc}")
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def load_state_model(self) -> RuntimeControllerState | None:
        return RuntimeControllerState.from_payload(self.load_state())

    def save_state(self, state: dict[str, Any] | RuntimeControllerState) -> None:
        self.ensure_cache_dir()
        normalized = (
            state.to_payload()
            if isinstance(state, RuntimeControllerState)
            else dict(state)
        )
        normalized["log_path"] = self.relative_log_path()
        self.state_path.write_text(json.dumps(normalized, indent=2, sort_keys=True), encoding="utf-8")

    def clear_state(self) -> None:
        if self.state_path.exists():
            self.state_path.unlink(missing_ok=True)

    def relative_log_path(self) -> str:
        try:
            return str(self.log_path.relative_to(self.root)).replace("\\", "/")
        except ValueError:
            return str(self.log_path).replace("\\", "/")

    def url_for_port(self, port: int) -> str:
        return f"http://localhost:{port}"

    def http_ready(self, url: str) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return 200 <= int(response.status) < 500
        except urllib.error.HTTPError as exc:
            return 200 <= int(exc.code) < 500
        except Exception:
            return False

    def port_is_open(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex(("127.0.0.1", port)) == 0

    def listener_pid(self, port: int) -> int | None:
        if sys.platform == "win32":
            try:
                completed = subprocess.run(
                    ["netstat", "-ano", "-p", "tcp"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except FileNotFoundError:
                return None
            pattern = re.compile(rf"^\s*TCP\s+\S+:{port}\s+\S+\s+LISTENING\s+(\d+)\s*$", re.IGNORECASE)
            for line in completed.stdout.splitlines():
                match = pattern.match(line)
                if match:
                    return int(match.group(1))
            return None

        commands = [
            ["ss", "-ltnp", f"sport = :{port}"],
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
        ]
        for command in commands:
            try:
                completed = subprocess.run(command, check=False, capture_output=True, text=True)
            except FileNotFoundError:
                continue
            for line in completed.stdout.splitlines():
                pid_match = re.search(r"pid=(\d+)", line)
                if pid_match:
                    return int(pid_match.group(1))
                stripped = line.strip()
                if stripped.isdigit():
                    return int(stripped)
        return None

    def scan_same_app_processes(self) -> list[dict[str, Any]]:
        if sys.platform == "win32":
            return self._scan_same_app_processes_windows()
        return self._scan_same_app_processes_posix()

    def _scan_same_app_processes_windows(self) -> list[dict[str, Any]]:
        script = r"""
$items = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -match 'streamlit\s+run\s+app\.py' } |
    Select-Object ProcessId, CommandLine, CreationDate
if (-not $items) {
    '[]'
} else {
    $items | ConvertTo-Json -Compress
}
"""
        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-EncodedCommand",
                    base64.b64encode(script.encode("utf-16le")).decode("ascii"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return []
        return self._normalize_process_payload(completed.stdout)

    def _scan_same_app_processes_posix(self) -> list[dict[str, Any]]:
        try:
            completed = subprocess.run(
                ["ps", "-eo", "pid=,lstart=,args="],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return []
        processes: list[dict[str, Any]] = []
        for line in completed.stdout.splitlines():
            parts = line.strip().split(None, 6)
            if len(parts) < 7:
                continue
            pid_token, day_name, month_name, day_number, time_token, year_token, command = parts
            if not pid_token.isdigit():
                continue
            if not SAME_APP_PATTERN.search(command):
                continue
            processes.append(
                {
                    "pid": int(pid_token),
                    "command": command,
                    "created_at": " ".join(
                        [day_name, month_name, day_number, time_token, year_token]
                    ),
                }
            )
        return processes

    def _normalize_process_payload(self, payload: str) -> list[dict[str, Any]]:
        text = payload.strip()
        if not text:
            return []
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            return []
        if isinstance(decoded, dict):
            decoded = [decoded]
        if not isinstance(decoded, list):
            return []
        processes: list[dict[str, Any]] = []
        for item in decoded:
            if not isinstance(item, dict):
                continue
            pid = item.get("ProcessId") or item.get("pid")
            command = item.get("CommandLine") or item.get("command") or ""
            created_at = item.get("CreationDate") or item.get("created_at")
            if not isinstance(pid, int):
                try:
                    pid = int(pid)
                except Exception:
                    continue
            if not isinstance(command, str) or not SAME_APP_PATTERN.search(command):
                continue
            processes.append({"pid": pid, "command": command, "created_at": created_at})
        return processes

    def command_matches_port(self, command: str, port: int) -> bool:
        compact = " ".join((command or "").split())
        patterns = [
            rf"--server\.port\s+{port}(\D|$)",
            rf"server\.port\s+{port}(\D|$)",
            rf"--server\.port={port}(\D|$)",
            rf"server\.port={port}(\D|$)",
        ]
        if any(re.search(pattern, compact, re.IGNORECASE) for pattern in patterns):
            return True
        return port == DEFAULT_PORT

    def find_same_app_process(self, port: int, preferred_pid: int | None = None) -> dict[str, Any] | None:
        candidates = [
            process
            for process in self.scan_same_app_processes()
            if self.command_matches_port(str(process.get("command", "")), port)
        ]
        if preferred_pid is not None:
            for process in candidates:
                if int(process.get("pid", -1)) == preferred_pid:
                    return process
        return candidates[0] if candidates else None

    def find_same_app_processes(self, port: int, preferred_pid: int | None = None) -> list[dict[str, Any]]:
        candidates = [
            process
            for process in self.scan_same_app_processes()
            if self.command_matches_port(str(process.get("command", "")), port)
        ]
        if preferred_pid is None:
            return candidates
        prioritized = [process for process in candidates if int(process.get("pid", -1)) == preferred_pid]
        remaining = [process for process in candidates if int(process.get("pid", -1)) != preferred_pid]
        return prioritized + remaining

    def state_matches_process(self, state: dict[str, Any], process: dict[str, Any]) -> bool:
        state_pid = int(state.get("app_pid") or 0)
        process_pid = int(process.get("pid") or 0)
        if state_pid != process_pid or state_pid <= 0:
            return False
        expected_created_at = state.get("app_created_at")
        observed_created_at = process.get("created_at")
        if expected_created_at and observed_created_at:
            return str(expected_created_at) == str(observed_created_at)
        return True

    def build_state_model(
        self,
        *,
        port: int,
        process: dict[str, Any] | None,
        status: str,
        ready: bool,
        listener_pid: int | None,
        browser_pid: int | None = None,
        browser_action: str | None = None,
        last_error: str | None = None,
        previous_state: dict[str, Any] | None = None,
    ) -> RuntimeControllerState:
        url = self.url_for_port(port)
        state = dict(previous_state or {})
        command = self.build_command(port)
        state.update(
            {
                "version": 1,
                "workspace_root": str(self.root).replace("\\", "/"),
                "entrypoint": "app.py",
                "python_exe": sys.executable,
                "command": command,
                "url": url,
                "port": port,
                "app_pid": int(process.get("pid", 0)) if process else None,
                "app_created_at": process.get("created_at") if process else None,
                "listener_pid": listener_pid,
                "listener_observed_at": utc_now_iso() if listener_pid is not None else None,
                "ready": bool(ready),
                "ready_at": state.get("ready_at") if state.get("ready") and ready else None,
                "last_status": status,
                "last_error": last_error,
                "log_path": self.relative_log_path(),
            }
        )
        if state.get("app_started_at") is None and process:
            state["app_started_at"] = utc_now_iso()
        if ready and not state.get("ready_at"):
            state["ready_at"] = utc_now_iso()
        if browser_pid is not None:
            state["browser_pid"] = browser_pid
        if browser_action is not None:
            state["browser_last_action"] = browser_action
        model = RuntimeControllerState.from_payload(state)
        if model is None:
            raise ValueError("Could not build runtime controller state payload")
        return model

    def build_state(
        self,
        *,
        port: int,
        process: dict[str, Any] | None,
        status: str,
        ready: bool,
        listener_pid: int | None,
        browser_pid: int | None = None,
        browser_action: str | None = None,
        last_error: str | None = None,
        previous_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.build_state_model(
            port=port,
            process=process,
            status=status,
            ready=ready,
            listener_pid=listener_pid,
            browser_pid=browser_pid,
            browser_action=browser_action,
            last_error=last_error,
            previous_state=previous_state,
        ).to_payload()

    def inspect(self, port: int) -> tuple[str, dict[str, Any], str]:
        url = self.url_for_port(port)
        state = self.load_state() or {}
        listener_pid = self.listener_pid(port)
        ready = self.http_ready(url)
        live_state_process: dict[str, Any] | None = None
        state_process_id = state.get("app_pid")
        if isinstance(state_process_id, int) and state_process_id > 0:
            for process in self.find_same_app_processes(port, preferred_pid=state_process_id):
                if self.state_matches_process(state, process):
                    live_state_process = process
                    break
        if live_state_process is not None:
            status = "running" if ready else "starting"
            refreshed = self.build_state(
                port=port,
                process=live_state_process,
                status=status,
                ready=ready,
                listener_pid=listener_pid or int(live_state_process["pid"]),
                previous_state=state,
            )
            self.save_state(refreshed)
            return status, refreshed, "controller-managed session detected"

        same_app = self.find_same_app_process(port, preferred_pid=listener_pid)
        if same_app is not None:
            refreshed = self.build_state(
                port=port,
                process=same_app,
                status="unmanaged_same_app",
                ready=ready,
                listener_pid=listener_pid or int(same_app["pid"]),
                previous_state=state,
            )
            self.save_state(refreshed)
            return "unmanaged_same_app", refreshed, "same-app session found without matching controller state"

        if listener_pid is not None or self.port_is_open(port):
            conflict_state = self.build_state(
                port=port,
                process=None,
                status="port_conflict",
                ready=ready,
                listener_pid=listener_pid,
                last_error="target port is occupied by an unrelated process",
                previous_state=state,
            )
            self.save_state(conflict_state)
            return "port_conflict", conflict_state, "target port is occupied by an unrelated process"

        if state:
            stale_state = self.build_state(
                port=port,
                process=None,
                status="stale",
                ready=False,
                listener_pid=None,
                last_error="controller state is stale",
                previous_state=state,
            )
            self.save_state(stale_state)
            return "stale", stale_state, "controller state is stale"

        stopped_state = self.build_state(
            port=port,
            process=None,
            status="stopped",
            ready=False,
            listener_pid=None,
            previous_state={},
        )
        return "stopped", stopped_state, "no running session detected"

    def emit(self, **fields: Any) -> None:
        ordered = [
            "STATUS",
            "APP_URL",
            "APP_PID",
            "START_PID",
            "LISTENER_PID",
            "READY",
            "STARTUP_SECONDS",
            "BROWSER_ACTION",
            "STOPPED_PIDS",
            "DETAIL",
            "LOG_PATH",
        ]
        for key in ordered:
            if key in fields and fields[key] is not None:
                print(f"{key}={fields[key]}")
        remaining = [key for key in fields if key not in ordered and fields[key] is not None]
        for key in sorted(remaining):
            print(f"{key}={fields[key]}")

    def wait_for_ready(self, process: subprocess.Popen[Any], port: int, wait_seconds: int) -> tuple[bool, int | None]:
        deadline = time.time() + max(1, wait_seconds)
        url = self.url_for_port(port)
        listener_pid = None
        while time.time() < deadline:
            listener_pid = self.listener_pid(port)
            if (listener_pid is not None or self.port_is_open(port)) and self.http_ready(url):
                return True, listener_pid
            if process.poll() is not None:
                return False, listener_pid
            time.sleep(0.6)
        return False, listener_pid

    def spawn_process(self, port: int) -> subprocess.Popen[Any]:
        self.ensure_cache_dir()
        log_handle = self.log_path.open("a", encoding="utf-8")
        command = self.build_command(port)
        creationflags = 0
        start_new_session = False
        if sys.platform == "win32":
            creationflags = (
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        else:
            start_new_session = True
        process = subprocess.Popen(
            command,
            cwd=str(self.root),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=log_handle,
            creationflags=creationflags,
            start_new_session=start_new_session,
        )
        log_handle.close()
        return process

    def terminate_pid(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            if sys.platform == "win32":
                completed = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                return completed.returncode == 0
            os.kill(pid, signal.SIGTERM)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return False
        except Exception:
            return False

    def wait_for_port_release(self, port: int, timeout_seconds: int = 10) -> bool:
        deadline = time.time() + max(1, timeout_seconds)
        while time.time() < deadline:
            if not self.port_is_open(port) and self.listener_pid(port) is None:
                return True
            time.sleep(0.4)
        return not self.port_is_open(port)

    def open_browser(
        self,
        port: int,
        state: dict[str, Any],
        *,
        force_new_window: bool = False,
    ) -> tuple[str, int | None]:
        url = self.url_for_port(port)
        if sys.platform != "win32":
            opened = webbrowser.open(url)
            return ("opened" if opened else "failed"), None
        try:
            return self._open_browser_windows(url, port, state, force_new_window=force_new_window)
        except Exception as exc:
            self.append_log(f"browser helper failed: {exc}")
            opened = webbrowser.open(url)
            return ("opened" if opened else "failed"), None

    def _open_browser_windows(
        self,
        url: str,
        port: int,
        state: dict[str, Any],
        *,
        force_new_window: bool = False,
    ) -> tuple[str, int | None]:
        script = r"""
$TargetUrl = $env:RUNTIME_CONTROLLER_URL
$TargetPort = [int]$env:RUNTIME_CONTROLLER_PORT
$SavedBrowserPid = $env:RUNTIME_CONTROLLER_BROWSER_PID
$AppTitle = $env:RUNTIME_CONTROLLER_APP_TITLE
$ForceNewWindow = $env:RUNTIME_CONTROLLER_FORCE_NEW_WINDOW -eq 'true'

function Find-TargetEdgeWindows([int]$PortToMatch) {
    try {
        return Get-Process -Name 'msedge' -ErrorAction SilentlyContinue |
            Where-Object {
                $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*localhost:$PortToMatch*"
            }
    } catch {
        return @()
    }
}

function Try-FocusAndRefresh([object]$ProcToRefresh, [object]$Shell) {
    if (-not $ProcToRefresh) {
        return $false
    }
    $activated = $false
    try {
        $activated = $Shell.AppActivate([int]$ProcToRefresh.Id)
    } catch {
        $activated = $false
    }
    if (-not $activated -and $ProcToRefresh.MainWindowTitle) {
        try {
            $activated = $Shell.AppActivate($ProcToRefresh.MainWindowTitle)
        } catch {
            $activated = $false
        }
    }
    if (-not $activated) {
        return $false
    }
    Start-Sleep -Milliseconds 250
    $Shell.SendKeys('{F5}')
    return $true
}

function Open-NewWindow([string]$UrlToOpen) {
    $edgeCmd = Get-Command msedge -ErrorAction SilentlyContinue
    if ($edgeCmd) {
        $proc = Start-Process -FilePath $edgeCmd.Source -ArgumentList @('--new-window', $UrlToOpen) -PassThru
        return @{ action = 'opened'; browser_pid = $proc.Id } | ConvertTo-Json -Compress
    }
    Start-Process $UrlToOpen | Out-Null
    return @{ action = 'opened'; browser_pid = $null } | ConvertTo-Json -Compress
}

try {
    $shell = New-Object -ComObject WScript.Shell
} catch {
    Start-Process $TargetUrl | Out-Null
    @{ action = 'opened'; browser_pid = $null } | ConvertTo-Json -Compress
    exit 0
}

$windows = @(Find-TargetEdgeWindows -PortToMatch $TargetPort)
if ($ForceNewWindow) {
    foreach ($proc in $windows) {
        try {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        } catch {
        }
    }
    if ($SavedBrowserPid) {
        try {
            Stop-Process -Id ([int]$SavedBrowserPid) -Force -ErrorAction SilentlyContinue
        } catch {
        }
    }
    Start-Sleep -Milliseconds 300
    Open-NewWindow -UrlToOpen $TargetUrl
    exit 0
}

if ($windows.Count -gt 1) {
    foreach ($proc in $windows) {
        try {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        } catch {
        }
    }
    Start-Sleep -Milliseconds 300
    Open-NewWindow -UrlToOpen $TargetUrl
    exit 0
}

if ($windows.Count -eq 1) {
    $proc = $windows[0]
    if (Try-FocusAndRefresh -ProcToRefresh $proc -Shell $shell) {
        @{ action = 'refreshed'; browser_pid = $proc.Id } | ConvertTo-Json -Compress
        exit 0
    }
}

if ($SavedBrowserPid) {
    try {
        $savedProc = Get-Process -Id ([int]$SavedBrowserPid) -ErrorAction SilentlyContinue
        if ($savedProc -and $savedProc.MainWindowHandle -ne 0) {
            if (Try-FocusAndRefresh -ProcToRefresh $savedProc -Shell $shell) {
                @{ action = 'refreshed'; browser_pid = $savedProc.Id } | ConvertTo-Json -Compress
                exit 0
            }
        }
    } catch {
    }
}

try {
    $titleWindow = Get-Process -Name 'msedge' -ErrorAction SilentlyContinue |
        Where-Object {
            $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$AppTitle*"
        } |
        Select-Object -First 1
    if ($titleWindow) {
        if (Try-FocusAndRefresh -ProcToRefresh $titleWindow -Shell $shell) {
            @{ action = 'refreshed'; browser_pid = $titleWindow.Id } | ConvertTo-Json -Compress
            exit 0
        }
    }
} catch {
}

Open-NewWindow -UrlToOpen $TargetUrl
"""
        env = os.environ.copy()
        env["RUNTIME_CONTROLLER_URL"] = url
        env["RUNTIME_CONTROLLER_PORT"] = str(port)
        env["RUNTIME_CONTROLLER_BROWSER_PID"] = str(state.get("browser_pid") or "")
        env["RUNTIME_CONTROLLER_APP_TITLE"] = self.app_title
        env["RUNTIME_CONTROLLER_FORCE_NEW_WINDOW"] = "true" if force_new_window else "false"
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-EncodedCommand",
                base64.b64encode(script.encode("utf-16le")).decode("ascii"),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        output = completed.stdout.strip() or completed.stderr.strip()
        if not output:
            return "failed", None
        payload = json.loads(output.splitlines()[-1])
        action = str(payload.get("action") or "failed")
        browser_pid = payload.get("browser_pid")
        if browser_pid is not None:
            try:
                browser_pid = int(browser_pid)
            except Exception:
                browser_pid = None
        return action, browser_pid

    def start(
        self,
        port: int,
        wait_seconds: int,
        open_browser_on_ready: bool,
        *,
        restart_if_busy: bool = True,
        replace_existing_window_on_ready: bool = False,
    ) -> int:
        started_at = time.perf_counter()
        status, state, detail = self.inspect(port)
        if status == "port_conflict":
            self.append_log(f"start blocked by foreign port owner on {port}")
            self.emit(
                STATUS=status,
                APP_URL=self.url_for_port(port),
                LISTENER_PID=state.get("listener_pid") or "unknown",
                READY=to_bool_text(bool(state.get("ready"))),
                DETAIL=detail,
                LOG_PATH=self.relative_log_path(),
            )
            return 2

        if status in {"running", "starting", "unmanaged_same_app"}:
            if restart_if_busy:
                self.append_log(f"start detected busy same-app session on {port}; restarting")
                stop_code = self.stop(port)
                if stop_code != 0:
                    return stop_code
                return self.start(
                    port,
                    wait_seconds,
                    open_browser_on_ready,
                    restart_if_busy=False,
                    replace_existing_window_on_ready=True,
                )

            self.append_log(f"start refused to reuse busy same-app session on {port}")
            self.emit(
                STATUS="failed",
                APP_URL=self.url_for_port(port),
                LISTENER_PID=state.get("listener_pid") or "unknown",
                READY=to_bool_text(bool(state.get("ready"))),
                STARTUP_SECONDS=f"{time.perf_counter() - started_at:.2f}",
                DETAIL="same-app session remained busy after restart attempt",
                LOG_PATH=self.relative_log_path(),
            )
            return 1

        if status == "stale":
            self.append_log(f"clearing stale state before start on {port}")
            self.clear_state()

        self.append_log(f"starting detached Streamlit on port {port}")
        process = self.spawn_process(port)
        process_info = {"pid": process.pid, "created_at": None, "command": " ".join(self.build_command(port))}
        same_app = self.find_same_app_process(port, preferred_pid=process.pid)
        if same_app is not None:
            process_info["created_at"] = same_app.get("created_at")
            process_info["command"] = same_app.get("command") or process_info["command"]
        initial_state = self.build_state(
            port=port,
            process=process_info,
            status="starting",
            ready=False,
            listener_pid=None,
            previous_state=state,
        )
        self.save_state(initial_state)

        ready, listener_pid = self.wait_for_ready(process, port, wait_seconds)
        if not ready:
            exit_code = process.poll()
            failure_state = self.build_state(
                port=port,
                process=process_info,
                status="failed",
                ready=False,
                listener_pid=listener_pid,
                last_error=f"streamlit did not become ready within {wait_seconds}s; exit={exit_code}",
                previous_state=initial_state,
            )
            self.save_state(failure_state)
            self.append_log(f"start failed on port {port}; exit={exit_code}")
            self.emit(
                STATUS="failed",
                APP_URL=self.url_for_port(port),
                START_PID=process.pid,
                LISTENER_PID=listener_pid or "unknown",
                READY=to_bool_text(False),
                STARTUP_SECONDS=f"{time.perf_counter() - started_at:.2f}",
                DETAIL=f"readiness not confirmed within {wait_seconds} seconds",
                LOG_PATH=self.relative_log_path(),
            )
            return 1

        final_process = self.find_same_app_process(port, preferred_pid=listener_pid or process.pid) or process_info
        browser_action = "skipped"
        browser_pid = None
        ready_state = self.build_state(
            port=port,
            process=final_process,
            status="running",
            ready=True,
            listener_pid=listener_pid or process.pid,
            previous_state=initial_state,
        )
        if open_browser_on_ready:
            browser_action, browser_pid = self.open_browser(
                port,
                ready_state,
                force_new_window=replace_existing_window_on_ready,
            )
            ready_state = self.build_state(
                port=port,
                process=final_process,
                status="running",
                ready=True,
                listener_pid=listener_pid or process.pid,
                previous_state=ready_state,
                browser_pid=browser_pid,
                browser_action=browser_action,
            )
        self.save_state(ready_state)
        self.append_log(f"start succeeded on port {port}; pid={ready_state.get('app_pid')}")
        self.emit(
            STATUS="running",
            APP_URL=self.url_for_port(port),
            START_PID=ready_state.get("app_pid") or process.pid,
            LISTENER_PID=ready_state.get("listener_pid") or "unknown",
            READY=to_bool_text(True),
            STARTUP_SECONDS=f"{time.perf_counter() - started_at:.2f}",
            BROWSER_ACTION=browser_action,
            DETAIL="session ready",
            LOG_PATH=self.relative_log_path(),
        )
        return 0

    def status(self, port: int) -> int:
        status, state, detail = self.inspect(port)
        self.append_log(f"status -> {status} on port {port}")
        self.emit(
            STATUS=status,
            APP_URL=self.url_for_port(port),
            APP_PID=state.get("app_pid") or "none",
            LISTENER_PID=state.get("listener_pid") or "none",
            READY=to_bool_text(bool(state.get("ready"))),
            DETAIL=detail,
            LOG_PATH=self.relative_log_path(),
        )
        return 2 if status == "port_conflict" else 0

    def open(self, port: int) -> int:
        status, state, detail = self.inspect(port)
        if status not in {"running", "starting", "unmanaged_same_app"}:
            self.append_log(f"open failed on port {port}: {status}")
            self.emit(
                STATUS=status,
                APP_URL=self.url_for_port(port),
                READY=to_bool_text(bool(state.get("ready"))),
                DETAIL="app is not running",
                LOG_PATH=self.relative_log_path(),
            )
            return 1
        browser_action, browser_pid = self.open_browser(port, state)
        next_status = "running" if bool(state.get("ready")) else "starting"
        refreshed = self.build_state(
            port=port,
            process={
                "pid": state.get("app_pid"),
                "created_at": state.get("app_created_at"),
                "command": " ".join(state.get("command") or []),
            }
            if state.get("app_pid")
            else None,
            status=next_status,
            ready=bool(state.get("ready")),
            listener_pid=state.get("listener_pid"),
            previous_state=state,
            browser_pid=browser_pid,
            browser_action=browser_action,
        )
        self.save_state(refreshed)
        self.append_log(f"open -> {browser_action} on port {port}")
        self.emit(
            STATUS=next_status,
            APP_URL=self.url_for_port(port),
            READY=to_bool_text(bool(refreshed.get("ready"))),
            BROWSER_ACTION=browser_action,
            DETAIL=detail,
            LOG_PATH=self.relative_log_path(),
        )
        return 0 if browser_action != "failed" else 1

    def stop(self, port: int) -> int:
        status, state, detail = self.inspect(port)
        if status == "port_conflict":
            self.append_log(f"stop refused foreign port owner on {port}")
            self.emit(
                STATUS=status,
                APP_URL=self.url_for_port(port),
                STOPPED_PIDS="",
                DETAIL=detail,
                LOG_PATH=self.relative_log_path(),
            )
            return 2

        candidates: list[int] = []
        preferred_pid = state.get("listener_pid") if isinstance(state.get("listener_pid"), int) else None
        for process in self.find_same_app_processes(port, preferred_pid=preferred_pid):
            pid = int(process.get("pid") or 0)
            if pid > 0 and pid not in candidates:
                candidates.append(pid)
        state_pid = state.get("app_pid")
        if isinstance(state_pid, int) and state_pid > 0 and state_pid not in candidates:
            candidates.append(state_pid)
        listener_pid = state.get("listener_pid")
        if isinstance(listener_pid, int) and listener_pid > 0 and listener_pid not in candidates:
            candidates.append(listener_pid)

        stopped: list[int] = []
        for pid in candidates:
            if self.terminate_pid(pid):
                stopped.append(pid)

        self.wait_for_port_release(port)
        self.clear_state()
        self.append_log(f"stop completed on port {port}; stopped={stopped}")
        self.emit(
            STATUS="stopped",
            APP_URL=self.url_for_port(port),
            STOPPED_PIDS=",".join(str(pid) for pid in stopped),
            DETAIL=("session stopped" if stopped else "no running session found"),
            LOG_PATH=self.relative_log_path(),
        )
        return 0

    def restart(self, port: int, wait_seconds: int, open_browser_on_ready: bool) -> int:
        self.append_log(f"restart requested on port {port}")
        stop_code = self.stop(port)
        if stop_code != 0:
            return stop_code
        return self.start(
            port,
            wait_seconds,
            open_browser_on_ready,
            replace_existing_window_on_ready=True,
        )

    def recover(self, port: int, wait_seconds: int, open_browser_on_ready: bool) -> int:
        self.append_log(f"recover requested on port {port}")
        stop_code = self.stop(port)
        if stop_code != 0:
            return stop_code
        return self.start(
            port,
            wait_seconds,
            open_browser_on_ready,
            replace_existing_window_on_ready=True,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage detached Streamlit runtime lifecycle")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_arguments(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--port", type=int, default=DEFAULT_PORT)

    start_parser = subparsers.add_parser("start", help="Start detached Streamlit runtime")
    add_common_arguments(start_parser)
    start_parser.add_argument("--wait-seconds", type=int, default=DEFAULT_WAIT_SECONDS)
    start_parser.add_argument(
        "--open-browser",
        action=argparse.BooleanOptionalAction,
        default=False,
    )

    status_parser = subparsers.add_parser("status", help="Report runtime status")
    add_common_arguments(status_parser)

    open_parser = subparsers.add_parser("open", help="Open or focus the running UI")
    add_common_arguments(open_parser)

    stop_parser = subparsers.add_parser("stop", help="Stop detached Streamlit runtime")
    add_common_arguments(stop_parser)

    restart_parser = subparsers.add_parser("restart", help="Restart detached Streamlit runtime")
    add_common_arguments(restart_parser)
    restart_parser.add_argument("--wait-seconds", type=int, default=DEFAULT_WAIT_SECONDS)
    restart_parser.add_argument(
        "--open-browser",
        action=argparse.BooleanOptionalAction,
        default=False,
    )

    recover_parser = subparsers.add_parser("recover", help="Recover detached Streamlit runtime")
    add_common_arguments(recover_parser)
    recover_parser.add_argument("--wait-seconds", type=int, default=DEFAULT_WAIT_SECONDS)
    recover_parser.add_argument(
        "--open-browser",
        action=argparse.BooleanOptionalAction,
        default=False,
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    controller = RuntimeController()

    if args.command == "start":
        return controller.start(args.port, args.wait_seconds, args.open_browser)
    if args.command == "status":
        return controller.status(args.port)
    if args.command == "open":
        return controller.open(args.port)
    if args.command == "stop":
        return controller.stop(args.port)
    if args.command == "restart":
        return controller.restart(args.port, args.wait_seconds, args.open_browser)
    if args.command == "recover":
        return controller.recover(args.port, args.wait_seconds, args.open_browser)
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
