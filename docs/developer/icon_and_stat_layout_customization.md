# Icon and Stat Layout Customization Guide

This guide explains where to change icon sizes, icon naming, and armor card stat layout.

## 1) Change icon sizes

Main controls are in [app.py](app.py):

- `STAT_ICON_SIZE_PX`
- `STAT_TOP_ICON_SIZE_PX`
- `STAT_PANEL_VALUE_DECIMALS`

These constants are defined near the top of the file and are used by:

- `stat_icon_html(...)`
- `armor_panel_item_html(...)`
- `render_armor_square_stat_panel(...)`

## 2) Change icon/name mapping per stat

Use [data/stat_ui_map.json](data/stat_ui_map.json).

Each stat entry supports:

- `column` (internal stat key)
- `display_name` (UI label)
- `icon_id` (icon registry key)
- `emoji` (fallback icon)

Examples of stat keys used by armor cards:

- Damage negation: `Dmg: Phy`, `Dmg: VS Str.`, `Dmg: VS Sla.`, `Dmg: VS Pie.`, `Dmg: Mag`, `Dmg: Fir`, `Dmg: Lit`, `Dmg: Hol`
- Status resistances: `status.poison`, `status.rot`, `status.bleed`, `status.frost`, `status.sleep`, `status.madness`, `status.death`
- Poise: `Res: Poi.`
- Weight: `weight`

## 3) Change icon files/source links

Use [data/icons/icons.json](data/icons/icons.json).

Each icon entry supports:

- `icon_id`
- `local_path`
- `source_url`

To refresh local icons from Fandom links in the registry:

```powershell
conda run -n elden_ring_ui python scripts/download_fandom_icons.py
```

To verify local icon files exist:

```powershell
python scripts/verify_icon_assets.py
```

## 4) Change armor stat block layout structure

Layout renderer lives in [app.py](app.py):

- `render_armor_square_stat_panel(...)`

Current structure:

- Top row: poison (left), weight + poise (right)
- Grid row:
  - `Damage Negation` (physical/strike/slash/pierce)
  - `Elemental` (magic/fire/lightning/holy)
  - `Resistances` (rot/bleed/frost/sleep/madness/death)

To re-order stats or move items between columns, edit the stat lists inside `render_armor_square_stat_panel(...)`:

- `physical_damage_stats`
- `elemental_damage_stats`
- `resistance_stats`
- `top_left_stat`
- `top_right_stats`

## 5) CSS styling for visual tuning

All stat panel styles are in the global CSS block in [app.py](app.py):

- `.er-armor-panel`
- `.er-armor-top`
- `.er-armor-grid`
- `.er-armor-section`
- `.er-armor-item`

Adjust spacing, grid columns, border radius, or typography there.

## 6) Detailed single-scope viewport focus and text cleanup

Detailed single-scope armor cards now auto-focus the viewport to the image/name start anchor after render.

Implementation in [app.py](app.py):

- `focus_detail_anchor(...)` for viewport scrolling
- single-scope anchor id: `detail-scope-anchor`

Single-scope `name` and `description` display use minimal normalization (whitespace/punctuation spacing only) without changing dataset storage:

- `normalize_dataset_text(...)`
