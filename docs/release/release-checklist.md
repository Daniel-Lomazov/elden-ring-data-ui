# Release Checklist

Baseline date: `2026-03-18`

## Release Gates

- [x] App launches through the documented path.
- [x] `tools.workspace_verify` passes or exceptions are documented and approved.
- [x] Backend tests pass in the changed areas.
- [x] Critical UI flows are smoke-tested.
- [x] Dependency declarations are explicit and reproducible.
- [x] CI exercises the changed code meaningfully.
- [x] README and docs reflect current behavior.
- [x] Release notes and changelog are complete.
- [x] Known risks are either fixed, deferred with rationale, or explicitly accepted.
- [x] Version selection is documented and justified.

## Current Status

- [x] Release ready

Notes:
- This checklist is intentionally strict and must be updated as code lands.
- If any gate fails, keep the release in blocker mode rather than forcing the version decision.
- The README/docs gate is accepted for the baseline and no longer blocks release status.
- Critical UI flow coverage is now exercised by `tests/test_ui_smoke.py`.
- Windows runtime lifecycle coverage is now exercised separately by `tests/test_runtime_controller.py` and the runtime-only CI job.
