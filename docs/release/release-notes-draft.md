# Release Notes Draft

Release target: `0.1.0`
Date: `2026-03-18`

## Summary

This release establishes the first formal release-management baseline for `elden_ring_data_ui`.
It now has stronger release evidence: the runtime dependency surface is explicit, CI runs workspace verification, workspace verification runs unit tests by default, the DataLoader cache risk is mitigated with file-signature keys and regression tests, critical UI flows are covered by automated Streamlit smoke tests, and the app launch path has been verified successfully.

## User-Facing Scope

- Streamlit-based data exploration for Elden Ring datasets.
- Ranking and optimization workflows for armor and talismans.
- Documented startup and verification paths.

## Important Notes

- The project remains in `0.x` release policy.
- `0.1.0` remains the recommended baseline version.
- `1.0.0` is still not justified by the current evidence.
- This baseline is release-ready with accepted residual risks around the monolithic UI surface and ongoing documentation drift.

## Verification Expectations

- App launch verification.
- Workspace verification.
- Backend regression tests.
- UI smoke checks for critical flows.
- Documentation sync for any user-visible behavior changes.
