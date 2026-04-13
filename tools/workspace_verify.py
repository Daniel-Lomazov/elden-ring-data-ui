import argparse
import contextlib
import io
import logging
import sys
import time
import unittest
from dataclasses import dataclass
from pathlib import Path

from tools.final_check import run_checks as run_final_checks
from tools.optimizer_check import run_checks as run_optimizer_checks
from tools.optimizer_smoke import main as run_optimizer_smoke
from tools.temp_support import (
    ensure_temp_root,
    patched_temporary_directory_cleanup,
    temporary_env_root,
)

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_VERIFY_TEMP_ROOT = ensure_temp_root("workspace-verify")
RUNTIME_CONTROLLER_MODULE = "tests.test_runtime_controller"

logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.caching.cache_data_api").disabled = True


@dataclass(frozen=True)
class VerificationStepResult:
    ok: bool
    elapsed: float
    message: str


def run_step(name: str, callback) -> VerificationStepResult:
    started = time.perf_counter()
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            callback()
        elapsed = time.perf_counter() - started
        return VerificationStepResult(True, elapsed, captured.getvalue())
    except SystemExit as exc:
        code = int(getattr(exc, "code", 1) or 0)
        elapsed = time.perf_counter() - started
        if code == 0:
            return VerificationStepResult(True, elapsed, captured.getvalue())
        details = captured.getvalue()
        if details:
            return VerificationStepResult(False, elapsed, f"{details}\nexit={code}")
        return VerificationStepResult(False, elapsed, f"exit={code}")
    except Exception as exc:
        elapsed = time.perf_counter() - started
        details = captured.getvalue()
        if details:
            return VerificationStepResult(False, elapsed, f"{details}\n{exc}")
        return VerificationStepResult(False, elapsed, str(exc))


def _filter_noisy_output(output: str) -> str:
    if not output:
        return ""
    filtered_lines: list[str] = []
    skip_next = False
    for line in output.splitlines():
        if skip_next:
            skip_next = False
            continue
        stripped = line.strip()
        if "No runtime found, using MemoryCacheStorageManager" in line:
            continue
        if "to view this Streamlit app on a browser, run it with the following" in line:
            skip_next = True
            continue
        if stripped.startswith("streamlit run ") and "workspace_verify.py" in stripped:
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines).strip()


def _iter_test_cases(suite: unittest.TestSuite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_test_cases(item)
        else:
            yield item


def _build_test_suite(kind: str) -> unittest.TestSuite:
    discovered = unittest.defaultTestLoader.discover(
        start_dir=str(ROOT / "tests"),
        top_level_dir=str(ROOT),
    )
    selected = unittest.TestSuite()
    for case in _iter_test_cases(discovered):
        case_id = str(case.id())
        is_runtime_controller = case_id.startswith(f"{RUNTIME_CONTROLLER_MODULE}.")
        if kind == "runtime" and is_runtime_controller:
            selected.addTest(case)
        elif kind == "core" and not is_runtime_controller:
            selected.addTest(case)
        elif kind == "all":
            selected.addTest(case)
    return selected


def run_unittest_checks(kind: str = "all") -> None:
    output_buffer = io.StringIO()
    with temporary_env_root(WORKSPACE_VERIFY_TEMP_ROOT), patched_temporary_directory_cleanup():
        suite = _build_test_suite(kind)
        if suite.countTestCases() == 0:
            print(f"workspace_verify: no tests collected for subset '{kind}'")
            return
        with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
            result = unittest.TextTestRunner(stream=output_buffer, verbosity=2).run(suite)
    if not result.wasSuccessful():
        print(output_buffer.getvalue(), end="")
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run workspace verification checks")
    parser.add_argument("--skip-final", action="store_true", help="Skip final_check")
    parser.add_argument("--skip-optimizer", action="store_true", help="Skip optimizer_check")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip optimizer_smoke")
    parser.add_argument("--skip-tests", action="store_true", help="Skip unittest discovery")
    parser.add_argument("--quick", action="store_true", help="Run faster verification path")
    parser.add_argument(
        "--tests-subset",
        choices=("all", "core", "runtime"),
        default="all",
        help="Select which unittest subset to run.",
    )
    args = parser.parse_args()

    steps: list[tuple[str, object]] = []
    skip_tests = args.skip_tests or args.quick
    skip_smoke = args.skip_smoke or args.quick

    def run_final_entry() -> None:
        exit_code = int(
            run_final_checks(
                include_app_import=not args.quick,
                include_data_probe=not args.quick,
            )
            or 0
        )
        if exit_code != 0:
            raise SystemExit(exit_code)

    if not args.skip_final:
        steps.append(("final_check", run_final_entry))
    if not args.skip_optimizer:
        steps.append(("optimizer_check", run_optimizer_checks))
    if not skip_smoke:
        steps.append(("optimizer_smoke", run_optimizer_smoke))
    if not skip_tests:
        if args.tests_subset == "runtime":
            steps.append(("tests_runtime_controller", lambda: run_unittest_checks("runtime")))
        elif args.tests_subset == "core":
            steps.append(("tests_core", lambda: run_unittest_checks("core")))
        else:
            steps.append(("tests_core", lambda: run_unittest_checks("core")))
            if sys.platform == "win32":
                steps.append(("tests_runtime_controller", lambda: run_unittest_checks("runtime")))

    if not steps:
        print("WORKSPACE_VERIFY: no checks selected")
        return 0

    print("WORKSPACE_VERIFY: started")
    all_ok = True
    total_started = time.perf_counter()
    for step_name, callback in steps:
        print(f"[workspace_verify] running {step_name}...")
        result = run_step(step_name, callback)
        state = "PASS" if result.ok else "FAIL"
        print(f"[workspace_verify] {step_name}: {state} ({result.elapsed:.2f}s)")
        filtered_message = _filter_noisy_output(result.message)
        if filtered_message:
            print(filtered_message)
        if not result.ok and not filtered_message and result.message:
            print(f"[workspace_verify] {step_name} details: {result.message}")
        all_ok = all_ok and result.ok

    total_elapsed = time.perf_counter() - total_started
    status = "SUCCESS" if all_ok else "FAILED"
    print(f"WORKSPACE_VERIFY: {status} ({total_elapsed:.2f}s)")
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
