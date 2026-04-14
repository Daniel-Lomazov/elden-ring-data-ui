from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class RuntimeControllerState:
    version: int = 1
    workspace_root: str = ""
    entrypoint: str = "app.py"
    python_exe: str = ""
    command: list[str] = field(default_factory=list)
    url: str = ""
    port: int = 0
    app_pid: int | None = None
    app_created_at: str | None = None
    listener_pid: int | None = None
    listener_observed_at: str | None = None
    ready: bool = False
    ready_at: str | None = None
    last_status: str = "stopped"
    last_error: str | None = None
    log_path: str | None = None
    app_started_at: str | None = None
    browser_pid: int | None = None
    browser_last_action: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> RuntimeControllerState | None:
        if not isinstance(payload, Mapping):
            return None

        command = payload.get("command") or []
        if not isinstance(command, list):
            command = [str(command)]

        def _as_int(value: Any) -> int | None:
            if value in (None, ""):
                return None
            try:
                return int(value)
            except Exception:
                return None

        return cls(
            version=int(payload.get("version") or 1),
            workspace_root=str(payload.get("workspace_root") or ""),
            entrypoint=str(payload.get("entrypoint") or "app.py"),
            python_exe=str(payload.get("python_exe") or ""),
            command=[str(item) for item in command],
            url=str(payload.get("url") or ""),
            port=int(payload.get("port") or 0),
            app_pid=_as_int(payload.get("app_pid")),
            app_created_at=str(payload.get("app_created_at") or "") or None,
            listener_pid=_as_int(payload.get("listener_pid")),
            listener_observed_at=str(payload.get("listener_observed_at") or "") or None,
            ready=bool(payload.get("ready")),
            ready_at=str(payload.get("ready_at") or "") or None,
            last_status=str(payload.get("last_status") or "stopped"),
            last_error=str(payload.get("last_error") or "") or None,
            log_path=str(payload.get("log_path") or "") or None,
            app_started_at=str(payload.get("app_started_at") or "") or None,
            browser_pid=_as_int(payload.get("browser_pid")),
            browser_last_action=str(payload.get("browser_last_action") or "") or None,
        )
