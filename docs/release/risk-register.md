# Risk Register

Baseline date: `2026-03-18`

## Current Risks

| ID | Risk | Impact | Likelihood | Status | Mitigation |
| --- | --- | --- | --- | --- | --- |
| R1 | `app.py` is a large monolithic UI file | High | High | Open | Track safe modular extraction and avoid broad UI churn |
| R2 | `plotly` runtime dependency was missing from `requirements.txt` | Medium | Medium | Closed | Added explicit `plotly==5.24.1` runtime dependency |
| R3 | CI and workspace verification did not execute the full unit test suite | High | Medium | Closed | CI now runs `python -m tools.workspace_verify`, and workspace verification runs unit tests by default |
| R4 | Runtime and generated artifacts may surface during local verification | Medium | Medium | Accepted | `.cache/` and `tmp*/` are ignored so transient artifacts do not block normal git status or release verification |
| R5 | Streamlit caching may mask stale-state issues | Medium | Medium | Closed | Mitigated with file-signature cache keys and regression tests |
| R6 | Documentation may drift from behavior during concurrent changes | High | Medium | Open | Require paired doc updates for every merged behavior change |

## Risk Handling Rules

- Blocker risks must be recorded before release approval.
- A risk is only removed when evidence exists in code, docs, and verification.
- New risks discovered during integration must be appended here immediately.
