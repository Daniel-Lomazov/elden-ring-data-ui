# Security Policy

## Supported Versions

This is a personal/demonstration project. Only the latest commit on the default
branch (`main`) is supported with security fixes.

| Branch | Supported |
|--------|-----------|
| `main` (latest) | Yes |
| older commits | No |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

If you discover a vulnerability, please report it privately:

1. Navigate to the [Security tab](https://github.com/Daniel-Lomazov/elden-ring-data-ui/security) of this repository.
2. Click **"Report a vulnerability"** to open a private advisory draft.
3. Describe the vulnerability, steps to reproduce, and potential impact.

You should receive an acknowledgement within 7 days. If this route is unavailable,
contact the repository owner directly via GitHub profile.

## Scope

This project is a local Streamlit data-exploration tool. It does not expose a
public API, accept user-submitted data, or persist any authentication credentials.
The primary risk surface is:

- **Data loading**: CSV files read from `data/`; no external network calls during
  runtime.
- **Dependency chain**: packages pinned in `requirements.txt`; update notices
  through GitHub Dependabot if enabled.

## Out of scope

- Issues in upstream packages (Streamlit, pandas, plotly) that are not exploitable
  in this project's specific usage context.
- General Elden Ring game data accuracy.
