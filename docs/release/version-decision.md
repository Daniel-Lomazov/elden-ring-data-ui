# Version Decision Record

Date: `2026-03-18`

Decision:
- Recommended version: `0.1.0`
- Policy: SemVer in `0.x` until release evidence supports `1.0.0`

Rationale:
- No existing repo version marker or published release policy was found.
- The codebase has a substantial UI and optimizer surface, but the accepted baseline now covers explicit runtime dependencies, unit-test execution through workspace verification, and a mitigated DataLoader stale-cache risk.
- A `0.1.0` baseline is still the correct first tracked release line while the project remains pre-`1.0`.
- The remaining open risks are primarily UI monolith/hygiene/doc-drift issues rather than release-blocking dependency or verification gaps.

Decision rules:
- Use `0.MINOR.PATCH` while the project remains pre-`1.0`.
- Reserve `1.0.0` for a release that has verified stability, documentation alignment, sustained test coverage, and a lower operational-risk profile.
- Revisit the recommendation only if a broader release candidate needs to move beyond the first tracked baseline.

Open questions:
- Whether the next release should remain an internal baseline or become the first public baseline.
- Whether UI modularization should be treated as a release-blocking concern for a later major version.
