# Elden Ring Data UI

A modular Streamlit application for loading, comparing, filtering, and optimizing Elden Ring datasets using least squares regression.

## Quick Start

```powershell
# Elden Ring Data UI (Minimal)

This repository contains a compact Streamlit app focused on ranking and sorting Elden Ring datasets (armors, weapons, items).

The project was intentionally trimmed to a minimal core: a lightweight ranking UI, a data loader, and a few parsing helpers. This keeps the app fast to run and easy to maintain.

## Quick Start

```powershell
# Create environment from environment.yml (recommended)
conda env create -f environment.yml
conda activate elden_ring_ui

# Or create a minimal venv and install requirements
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Project Structure

```
elden_ring_data_ui/
├── app.py                  # Main minimal Streamlit application (ranking/sorting)
├── data_loader.py          # Data loading helper
├── ui_components.py        # Minimal parsing helpers
├── requirements.txt        # Python dependencies
├── environment.yml         # Conda environment (recommended)
├── data/                   # CSV data directory
│   ├── armors.csv
│   ├── weapons.csv
│   └── items/
└── README.md               # This file
```

## Setup

1. Create the conda environment (recommended):

   ```powershell
   conda env create -f environment.yml
   conda activate elden_ring_ui
   ```

2. Or use a Python virtual environment and pip:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Add your CSV files to the `data/` directory and run the app:

   ```powershell
   streamlit run app.py
   ```

## Notes

- This trimmed project focuses on the ranking/sorting UI. Some earlier modules (filtering, scoring, and other utilities) were removed during cleanup to keep the codebase minimal and focused.
- If you need back the removed features (filters, optimization UI, tests), they can be restored or reimplemented on request.

## Troubleshooting

- If packages fail to install, recreate the environment or use the venv approach above.
- Ensure CSV files are present in `data/`.

---

If you'd like, I can also produce a small `final_check.py` import-verifier and a simple `setup.ps1` to automate the conda commands on Windows. Let me know which you prefer.
   Or:
