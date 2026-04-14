# UI Customization Guide (Icons, Layout, Detailed Scope)

This guide documents where to safely tune icon rendering, armor stat layout, and detailed-scope behavior.

## 1) Stat icon size and numeric formatting

Main constants are in `app.py`:

- `STAT_ICON_SIZE_PX`
- `STAT_TOP_ICON_SIZE_PX`
- `STAT_PANEL_VALUE_DECIMALS`

Formatting logic:

- `format_metric_value(...)` in `app.py`
  - `status.*` and `Res:*` display as integers
  - non-resistance metrics follow configured decimal precision

## 2) Stat UI map and stat icon registry

- Stat label/icon mapping: `data/stat_ui_map.json`
- Icon file registry: `data/icons/icons.json`

Helpers in `app.py`:

- `load_stat_ui_map(...)`
- `load_icon_registry(...)`
- `icon_data_uri_for_icon_id(...)`
- `stat_icon_html(...)`

## 3) Parser dialect normalization (no CSV rewrite)

Armor dictionaries are normalized in code while preserving source CSV values.

File: `ui_components.py`

- `parse_armor_stats(...)`
- `damage_key_aliases`
- `resistance_key_aliases`

This handles variants like:

- `VS Str` vs `VS Str.`
- `Rob.` vs `Robu.`
- `Vit.` vs `Vita.`

## 4) Armor stat panel structure

Renderer: `render_armor_square_stat_panel(...)` in `app.py`

Current structure:

- Top row
  - Left: `Res: Poi.`
  - Right: `weight`
- Left column
  - `Physical Damage Negation`
  - `Elemental Damage Negation`
- Right column
  - `Status Effects Resistances`
- Middle column
  - spacer controlled by `ARMOR_PANEL_MIDDLE_SPACER_RATIO`

Spacing controls:

- `ARMOR_PANEL_DENSITY_SCALE`
- `ARMOR_PANEL_TITLE_GAP_SCALE`

## 5) Detailed-scope helpers (moved to package)

Session-specific detailed-scope helpers are isolated in package `app_support`:

- `app_support/detail_scope.py`
  - `DETAIL_SCOPE_ANCHOR_ID`
  - `normalize_dataset_text(...)`
  - `focus_detail_anchor(...)`
  - `ARMOR_FULL_SCOPE_DESCRIPTION_PLACEHOLDER`
  - `ARMOR_CUSTOM_SCOPE_NAME_PLACEHOLDER`
  - `ARMOR_CUSTOM_SCOPE_DESCRIPTION_PLACEHOLDER`

`app.py` imports these helpers from `app_support`.

## 6) Full/custom scope placeholders

Current behavior:

- Single scope: name/description from dataset (minimal display normalization only)
- Full scope:
  - set name from selected family label
  - description from `ARMOR_FULL_SCOPE_DESCRIPTION_PLACEHOLDER`
- Custom scope:
  - name from `ARMOR_CUSTOM_SCOPE_NAME_PLACEHOLDER`
  - description from `ARMOR_CUSTOM_SCOPE_DESCRIPTION_PLACEHOLDER`

## 7) Separate slot icon pipeline (fallback-safe)

Slot icons are intentionally separate from stat icons.

Optional registry file:

- `data/icons/scope_slot_icons.json`

Accepted formats:

- Object map:
  - `{ "helm": "data/icons/slots/helm.png", "armor": "..." }`
- List format:
  - `{ "icons": [ { "slot_key": "helm", "local_path": "data/icons/slots/helm.png" } ] }`

If slot icons are missing, UI falls back to emoji slot icons.

## 8) Quick validation commands

```powershell
.\.venv\Scripts\python.exe -m py_compile app.py ui_components.py
.\.venv\Scripts\python.exe -c "import pandas as pd; from ui_components import parse_armor_stats; df=parse_armor_stats(pd.read_csv('data/armors.csv')); r=df.loc[df['id']==597].iloc[0]; print(r['status.bleed'], r['status.frost'], r['status.death'])"
```
