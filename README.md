# Elden Ring Data UI

A modular Streamlit application for loading, comparing, filtering, and optimizing Elden Ring datasets using least squares regression.

## Quick Start

This repository contains a compact Streamlit app focused on ranking and sorting Elden Ring datasets (armors, weapons, items). The trimmed project keeps only the app, data loader, parsing helpers, and dataset CSVs.

Windows (Conda, recommended):

```powershell
conda env create -f environment.yml
conda activate elden_ring_ui
streamlit run app.py
```

Cross-platform (venv):

```bash
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
pip install -r requirements.txt
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

- This trimmed project focuses on the ranking/sorting UI. Some earlier modules (filtering, optimization helpers, and tests) were removed during cleanup to keep the codebase minimal and focused.
- If you need the removed features restored, I can add them back or provide separate branches for experimental tooling.

## Troubleshooting

- If packages fail to install, recreate the environment or use the venv approach above.
- Ensure CSV files are present in `data/`.

---

<!-- Removed assistant-suggested helper offer to keep README focused and minimal -->
<!-- CI trigger: heartbeat -->
