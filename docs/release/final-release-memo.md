# Final Release Memo

Status: Release-ready recommendation

Decision:
- Recommended version: `0.1.0`
- Release status: Ready for a first tracked baseline release

Verification evidence:
- App launch verified successfully through the documented local Streamlit command, including a final launch check on `127.0.0.1:8766`.
- `C:\Users\lomaz\anaconda3\envs\elden_ring_ui\python.exe -m unittest discover tests` passed with 11 tests.
- `C:\Users\lomaz\anaconda3\envs\elden_ring_ui\python.exe -m tools.workspace_verify` passed with final check, optimizer check, and tests.
- Critical UI flows are smoke-tested by `tests/test_ui_smoke.py`.

Accepted risks:
- `app.py` remains a large monolithic UI surface and should be treated as a refactor candidate rather than a release blocker for `0.1.0`.
- Documentation drift remains a live maintenance risk and should continue to be managed with paired updates.
- Local transient artifacts may still appear during verification, but ignored cache/tmp paths no longer interfere with normal git status or release verification.

Change summary:
- Explicit runtime dependency declaration for `plotly`.
- Stronger CI and workspace verification coverage.
- DataLoader cache invalidation tied to file signatures with regression tests.
- Automated UI smoke coverage for the default detailed view and main optimization flow.
- Release-management docs established under `docs/release/`.

User-facing impact summary:
- Documented launch and verification paths are now verified.
- Default ranking and optimization entry paths are covered by automated smoke checks.
- Data reload behavior is more reliable after file changes.
