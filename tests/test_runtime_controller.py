from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.runtime_controller import RuntimeController


class FakeProcess:
    def __init__(self, pid: int, exit_code: int | None = None):
        self.pid = pid
        self._exit_code = exit_code

    def poll(self) -> int | None:
        return self._exit_code


class RuntimeControllerTests(unittest.TestCase):
    def make_controller(self) -> RuntimeController:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        return RuntimeController(root=root)

    def capture_output(self, callback):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = callback()
        return exit_code, buffer.getvalue()

    def test_inspect_reports_stopped_when_no_state_or_listener_exists(self):
        controller = self.make_controller()
        controller.listener_pid = lambda port: None  # type: ignore[method-assign]
        controller.port_is_open = lambda port: False  # type: ignore[method-assign]
        controller.http_ready = lambda url: False  # type: ignore[method-assign]
        controller.scan_same_app_processes = lambda: []  # type: ignore[method-assign]

        status, state, detail = controller.inspect(8501)

        self.assertEqual(status, "stopped")
        self.assertEqual(state["last_status"], "stopped")
        self.assertFalse(state["ready"])
        self.assertEqual(detail, "no running session detected")
        self.assertFalse(controller.state_path.exists())

    def test_inspect_reports_port_conflict_for_foreign_listener(self):
        controller = self.make_controller()
        controller.listener_pid = lambda port: 9001  # type: ignore[method-assign]
        controller.port_is_open = lambda port: True  # type: ignore[method-assign]
        controller.http_ready = lambda url: False  # type: ignore[method-assign]
        controller.scan_same_app_processes = lambda: []  # type: ignore[method-assign]

        status, state, detail = controller.inspect(8501)

        self.assertEqual(status, "port_conflict")
        self.assertEqual(state["listener_pid"], 9001)
        self.assertEqual(detail, "target port is occupied by an unrelated process")
        persisted = json.loads(controller.state_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["last_status"], "port_conflict")

    def test_start_reuses_existing_running_session_without_spawning(self):
        controller = self.make_controller()
        existing_state = {
            "app_pid": 1234,
            "app_created_at": "created",
            "command": ["python", "-m", "streamlit", "run", "app.py", "--server.port", "8501"],
            "listener_pid": 1234,
            "ready": True,
            "browser_pid": None,
        }

        controller.inspect = lambda port: (  # type: ignore[method-assign]
            "running",
            existing_state,
            "controller-managed session detected",
        )
        controller.open_browser = lambda port, state: ("skipped", None)  # type: ignore[method-assign]
        controller.spawn_process = lambda port: (_ for _ in ()).throw(AssertionError("spawn should not run"))  # type: ignore[method-assign]

        exit_code, output = self.capture_output(
            lambda: controller.start(8501, wait_seconds=45, open_browser_on_ready=False)
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("STATUS=running", output)
        self.assertIn("START_PID=1234", output)
        self.assertIn("DETAIL=session already running", output)
        persisted = json.loads(controller.state_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["app_pid"], 1234)
        self.assertEqual(persisted["last_status"], "running")

    def test_start_writes_state_when_launch_becomes_ready(self):
        controller = self.make_controller()
        controller.inspect = lambda port: (  # type: ignore[method-assign]
            "stopped",
            controller.build_state(
                port=port,
                process=None,
                status="stopped",
                ready=False,
                listener_pid=None,
                previous_state={},
            ),
            "no running session detected",
        )
        controller.spawn_process = lambda port: FakeProcess(pid=4321)  # type: ignore[method-assign]
        controller.find_same_app_process = lambda port, preferred_pid=None: {  # type: ignore[method-assign]
            "pid": 4321,
            "created_at": "created-4321",
            "command": "python -m streamlit run app.py --server.port 8501 --server.headless true",
        }
        controller.wait_for_ready = lambda process, port, wait_seconds: (True, 4321)  # type: ignore[method-assign]
        controller.open_browser = lambda port, state: ("skipped", None)  # type: ignore[method-assign]

        exit_code, output = self.capture_output(
            lambda: controller.start(8501, wait_seconds=45, open_browser_on_ready=False)
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("STATUS=running", output)
        self.assertIn("START_PID=4321", output)
        persisted = json.loads(controller.state_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["app_pid"], 4321)
        self.assertEqual(persisted["listener_pid"], 4321)
        self.assertTrue(persisted["ready"])
        self.assertEqual(persisted["last_status"], "running")

    def test_stop_is_safe_noop_when_nothing_is_running(self):
        controller = self.make_controller()
        controller.inspect = lambda port: (  # type: ignore[method-assign]
            "stopped",
            controller.build_state(
                port=port,
                process=None,
                status="stopped",
                ready=False,
                listener_pid=None,
                previous_state={},
            ),
            "no running session detected",
        )
        controller.find_same_app_processes = lambda port, preferred_pid=None: []  # type: ignore[method-assign]
        controller.wait_for_port_release = lambda port, timeout_seconds=10: True  # type: ignore[method-assign]

        exit_code, output = self.capture_output(lambda: controller.stop(8501))

        self.assertEqual(exit_code, 0)
        self.assertIn("STATUS=stopped", output)
        self.assertIn("DETAIL=no running session found", output)
        self.assertFalse(controller.state_path.exists())

    def test_recover_calls_stop_then_start(self):
        controller = self.make_controller()
        calls: list[tuple] = []

        def fake_stop(port: int) -> int:
            calls.append(("stop", port))
            return 0

        def fake_start(port: int, wait_seconds: int, open_browser_on_ready: bool) -> int:
            calls.append(("start", port, wait_seconds, open_browser_on_ready))
            return 0

        controller.stop = fake_stop  # type: ignore[method-assign]
        controller.start = fake_start  # type: ignore[method-assign]

        exit_code = controller.recover(8501, wait_seconds=30, open_browser_on_ready=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            calls,
            [
                ("stop", 8501),
                ("start", 8501, 30, True),
            ],
        )


if __name__ == "__main__":
    unittest.main()