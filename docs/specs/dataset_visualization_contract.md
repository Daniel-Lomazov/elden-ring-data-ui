# Dataset Visualization Contract

## Goal

Define one stable presentation contract for top-level datasets in `data/*.csv` so the Streamlit UI can display them consistently without hard-coding a new rendering branch for every dataset.

## Scope

- Applies to top-level datasets under `data/*.csv`.
- Does not require enabling `data/items/*` in the same rollout.
- Does not rewrite source CSV files.
- Keeps armor and talisman optimization behavior intact.

## Presentation model

Dataset presentation is driven by `app_support/dataset_presentations.py`.

Each dataset resolves to a `DatasetPresentationSpec` with these responsibilities:

- `name_field`: canonical item title column for the dataset.
- `numeric_like_columns`: text columns that are safe to coerce into numeric values for ranking and display.
- `card_meta_fields`: ordered metadata rows or captions shown on cards.
- `card_metric_fields`: ordered metric rows shown alongside highlighted stats.
- `detail_summary_fields`: summary fields shown above detailed sections.
- `detail_sections`: grouped detail sections with field order and formatter rules.

Each field resolves through `FieldPresentation`:

- `label`: user-facing field label.
- `source_key`: source CSV column used for the field.
- `formatter`: semantic formatter name.
- `style`: `label` or `caption`.

Unknown placeholder tokens such as `???` are treated as missing values during numeric coercion so mixed-quality datasets can still expose rankable numeric fields when the remaining values are cleanly numeric.

## Formatter rules

These formatter names are the stable contract for this slice:

- `text`: raw trimmed text.
- `integer`: integer-like numeric value with no percent suffix.
- `raw_number`: numeric value with no unit suffix.
- `weight`: numeric weight value with no percent suffix.
- `fp_cost`: FP cost; preserve composite strings if parsing would lose meaning.
- `stamina_cost`: stamina cost with no percent suffix.
- `dlc`: user-facing edition label (`Base game` or `DLC`).
- `requirements_map`: parsed requirements map such as `STR 15, DEX 14`.
- `structured`: parsed serialized list or dict values rendered into readable text.
- `effect_type`: talisman-effect category text derived from the raw effect string.
- `effect_magnitude`: best-effort talisman effect magnitude such as `6%` or `7`.

## Unit rules

- Weight must remain a raw numeric quantity and must never be formatted as a percentage.
- Costs remain costs. `FP`, `FP cost`, and `stamina cost` are displayed as costs, not percentages.
- Percentages are shown only when the underlying field or text explicitly represents a percentage.
- Free-text fields that embed a percentage may expose a derived percentage field, but the original source text remains visible.

## Dataset families for this slice

### Armor and talisman optimizer datasets

- `armors`: keep the existing armor stat panel and grouped stat behavior.
- `talismans`: show effect type, effect magnitude, value, weight, and edition with deterministic ordering.

### Spell and summon datasets

- `incantations`
- `sorceries`
- `spiritAshes`
- `skills`
- `ashesOfWar`

These datasets must surface cost, requirements, effect text, and acquisition metadata clearly.

### Equipment datasets

- `weapons`
- `shields`

These datasets must surface category, damage type, skill, passive effect, parsed requirements, weight, and FP cost where present.

### World and entity datasets

- `bosses`
- `creatures`
- `locations`
- `npcs`

These datasets must render serialized list or dict fields as readable structured content instead of raw Python-like literals whenever parsing is reliable.

### Progression-table datasets

- `weapons_upgrades`
- `shields_upgrades`

These datasets use a browse-only progression summary plus grouped item-detail rendering rather than ranked item cards.

## Deferred selector contract

If a dataset remains registered but unsupported, it stays visible in the selector with a `Not implemented yet` suffix instead of disappearing from the UI entirely.

## Extension rule for `data/items/*`

The next rollout for `data/items/*` should require only:

1. adding a `DatasetUiSpec` entry,
2. adding a `DatasetPresentationSpec` entry or using the generic fallback,
3. adding any dataset-specific column profile only if full-file loading is too broad,
4. adding tests for formatter and detail-section expectations.