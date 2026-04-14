# Contributing

> **Note:** This project is published for reference and learning. All rights are
> reserved. Contributions are welcome via pull request, but the project owner
> retains full discretion over acceptance and integration.

## Prerequisites

- Windows (primary supported platform) with **PowerShell 7+**
- [uv](https://docs.astral.sh/uv/) installed and on `PATH`
  (`winget install astral-sh.uv` or `pip install uv`)
- Python **3.11** (uv will download it automatically if missing via `uv venv --python 3.11`)

## First-time setup

```powershell
# Clone the repo
git clone https://github.com/Daniel-Lomazov/elden-ring-data-ui.git
cd elden-ring-data-ui

# Bootstrap the virtual environment and install dependencies
.\setup.ps1

# Activate the environment (optional for script use; required for direct python calls)
.\.venv\Scripts\Activate.ps1
```

`setup.ps1` creates a uv-managed `.venv` at Python 3.11 and installs everything
from `requirements.txt`. The `.venv` is the only supported runtime path — do not
install packages globally or via Conda.

## Running the app

```powershell
# Foreground development loop
.\scripts\run_streamlit_local.ps1

# Managed detached mode (runtime_controller backed)
.\scripts\start-app.ps1
.\scripts\recover-app.ps1   # restart
.\scripts\stop_streamlit_port.ps1 -Port 8501
```

See `README.md` for the full runtime command matrix.

## Verification

Run verification before pushing any change:

```powershell
# Quick lint + smoke check (fast, ~10s)
.\.venv\Scripts\python.exe -m tools.workspace_verify --quick

# Full verification suite (~60s)
.\.venv\Scripts\python.exe -m tools.workspace_verify

# Targeted test subsets
.\.venv\Scripts\python.exe -m unittest tests.test_ui_smoke -q
.\.venv\Scripts\python.exe -m unittest tests.test_runtime_controller -q
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

CI runs the same `tools.workspace_verify` orchestrator on both Linux and Windows.
A pull request must pass the `lint-and-verify` check before it can be merged
into `main`.

## Branching and pull requests

- Branch from `dev/lomazov` (or `main` if `dev/lomazov` is not present in your fork).
- Use descriptive branch names: `fix/<short-description>`, `feature/<name>`.
- Keep commits focused; one logical change per commit.
- Include verification output in the PR description if the change touches
  `app.py`, `optimizer/`, or `tools/`.
- `main` has branch protection: 1 approving review required, all conversations
  must be resolved, and the `lint-and-verify` status check must pass.

## Code style

Linting is enforced with [ruff](https://docs.astral.sh/ruff/):

```powershell
.\.venv\Scripts\python.exe -m ruff check .
```

There is no auto-formatter currently enforced. Follow the existing style
(single quotes, 4-space indent, no trailing whitespace).

## Architecture overview

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for a full architecture guide,
module roles, and testing conventions.

## License

By submitting a contribution, you agree that your changes will be subject to
the same [all-rights-reserved license](LICENSE) as the rest of this project.
