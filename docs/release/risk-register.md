# Risk Register

> **Internal release analysis** — This document records risks assessed during
> release preparation cycles. It is an internal development artifact retained for
> historical reference.

Baseline date: `2026-03-18`

## Current Risks

| ID | Risk | Impact | Likelihood | Status | Mitigation |
| --- | --- | --- | --- | --- | --- |
| R1 | `app.py` is a large monolithic UI file | High | High | Open | Continue safe modular extraction through `app_support/query_state.py`, `app_support/view_state.py`, and future rendering/orchestration seams |
| R2 | `plotly` runtime dependency was missing from `requirements.txt` | Medium | Medium | Closed | Added explicit `plotly==5.24.1` runtime dependency |
| R3 | CI and workspace verification did not execute the full unit test suite | High | Medium | Closed | CI now runs `python -m tools.workspace_verify`, and workspace verification reports split test coverage by subsystem |
| R4 | Runtime and generated artifacts may surface during local verification | Medium | Medium | Accepted | `.cache/` and `tmp*/` are ignored so transient artifacts do not block normal git status or release verification |
| R5 | Streamlit caching may mask stale-state issues | Medium | Medium | Closed | Mitigated with file-signature cache keys and regression tests |
| R6 | Documentation may drift from behavior during concurrent changes | High | Medium | Open | Require paired doc updates for every merged behavior change |
| R7 | Test temp-root handling caused Windows false negatives in verification | High | High | Closed | Centralized temp helpers and moved runtime-controller coverage onto explicit repo-local workspaces |

## Risk Handling Rules

- Blocker risks must be recorded before release approval.
- A risk is only removed when evidence exists in code, docs, and verification.
- New risks discovered during integration must be appended here immediately.
