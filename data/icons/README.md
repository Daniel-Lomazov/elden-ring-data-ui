# Icon Registry (Optimizer Dialect v1)

This folder hosts local icon assets referenced by `data/icons/icons.json`.

## Contract

- Registry file: `data/icons/icons.json`
- Each entry includes:
  - `icon_id`
  - `canonical_key` (optional for generic icons)
  - `label`
  - `local_path` (preferred offline source)
  - `source_url` (optional provenance)
  - `category`: `armor_stat | negation | resistance | status`

## Notes

- PR1 adds schema + registry scaffolding only; image files are placeholders and can be filled in later without code changes.
- Use paths relative to repo root, for example: `data/icons/neg_mag.png`.
- Validate that all declared local icon files exist:

  ```powershell
  python scripts/verify_icon_assets.py
  ```

- Download/update local icons from Fandom file-page links in the registry:

  ```powershell
  .\.venv\Scripts\python.exe scripts/download_fandom_icons.py
  ```
