import argparse
import time

from tools.final_check import run_checks as run_final_checks
from tools.optimizer_check import run_checks as run_optimizer_checks


def run_step(name: str, callback) -> tuple[bool, float, str]:
    started = time.perf_counter()
    try:
        callback()
        elapsed = time.perf_counter() - started
        return True, elapsed, "ok"
    except SystemExit as exc:
        code = int(getattr(exc, "code", 1) or 0)
        elapsed = time.perf_counter() - started
        if code == 0:
            return True, elapsed, "ok"
        return False, elapsed, f"exit={code}"
    except Exception as exc:
        elapsed = time.perf_counter() - started
        return False, elapsed, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run workspace verification checks")
    parser.add_argument("--skip-final", action="store_true", help="Skip final_check")
    parser.add_argument("--skip-optimizer", action="store_true", help="Skip optimizer_check")
    parser.add_argument("--quick", action="store_true", help="Run faster verification path")
    args = parser.parse_args()

    steps: list[tuple[str, object]] = []

    def run_final_entry() -> None:
        exit_code = int(run_final_checks(include_app_import=not args.quick) or 0)
        if exit_code != 0:
            raise SystemExit(exit_code)

    if not args.skip_final:
        steps.append(("final_check", run_final_entry))
    if not args.skip_optimizer:
        steps.append(("optimizer_check", run_optimizer_checks))

    if not steps:
        print("WORKSPACE_VERIFY: no checks selected")
        return 0

    print("WORKSPACE_VERIFY: started")
    all_ok = True
    total_started = time.perf_counter()
    for step_name, callback in steps:
        print(f"[workspace_verify] running {step_name}...")
        ok, elapsed, message = run_step(step_name, callback)
        state = "PASS" if ok else "FAIL"
        print(f"[workspace_verify] {step_name}: {state} ({elapsed:.2f}s)")
        if message != "ok":
            print(f"[workspace_verify] {step_name} details: {message}")
        all_ok = all_ok and ok

    total_elapsed = time.perf_counter() - total_started
    status = "SUCCESS" if all_ok else "FAILED"
    print(f"WORKSPACE_VERIFY: {status} ({total_elapsed:.2f}s)")
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
