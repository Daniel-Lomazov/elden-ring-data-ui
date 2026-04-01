---
goal: Standardize main-dataset visualization and runtime usage docs
version: 1.0
date_created: 2026-04-01
last_updated: 2026-04-01
owner: GitHub Copilot
status: 'In Progress'
tags: [feature, data, visualization, documentation, refactor]
---

# Introduction

![Status: In Progress](https://img.shields.io/badge/status-In%20Progress-yellow)

This plan standardizes how the app documents startup and restart flows, how it presents all top-level `data/*.csv` datasets, and how it prepares the same visualization contract for later extension into `data/items/*`. The plan is grounded in the current repository code and the observed schemas of every top-level dataset.

## Context Map

### Files to Modify

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `README.md` | User-facing startup and restart instructions | Split direct foreground flow, managed controller flow, recover flow, and full orchestration flow into one clear command matrix. |
| `docs/README.md` | Internal onboarding and verification index | Align quick verification and runtime restart language with `README.md`. |
| `app_support/dataset_ui.py` | Dataset registry and capability model | Expand the registry to carry presentation metadata and a dedicated progression-table family. |
| `app.py` | Current rendering logic for cards, metrics, detail inspector, and dataset modes | Replace ad hoc dataset-specific formatting with schema-driven sections and value format rules. |
| `data/column_loading_instructions.json` | Column profiles for fast and detailed loading | Add per-dataset visual/detail profiles for spells, equipment, world entities, and progression tables. |
| `data_loader.py` | Dataset loading and profile resolution | Keep generic, but extend profile usage where dataset-specific visual bundles are needed. |
| `ui_smoke_checklist.md` | Manual smoke coverage | Add non-armor dataset coverage and startup/restart verification steps. |
| `data/active_datasets.json` | Default visible dataset set | Expand only after representative non-armor views are verified. |
| `tests/test_dataset_ui_registry.py` | Registry capability coverage | Extend for new families, presentation rules, and supported top-level datasets. |
| `tests/test_ui_smoke.py` | UI smoke verification | Add representative dataset coverage across spells, equipment, world data, and progression tables. |
| `tests/test_dataset_presentation.py` | New presentation schema tests | Validate per-dataset sections, field ordering, and unit formatting rules. |
| `tests/test_dataset_value_standardization.py` | New formatter/parser tests | Validate percentages, weights, costs, requirements, and structured list/dict parsing. |

### Dependencies (may need updates)

| File | Relationship |
|------|--------------|
| `data/stat_ui_map.json` | Existing stat label/icon source for armor-derived stats; may need extension if more numeric fields become rankable. |
| `armor_column_map.json` | Existing armor-specific helper; remains a reference for dataset-specific presentation logic. |
| `tools/workspace_verify.py` | Existing consolidated verification path; should continue to run all new tests. |
| `docs/session/2026-02-15_startup_and_verify_deep_dive.md` | Existing startup/restart documentation baseline that the new runtime docs must not contradict. |

### Test Files

| Test | Coverage |
|------|----------|
| `tests/test_dataset_ui_registry.py` | Dataset family and support matrix validation. |
| `tests/test_ui_smoke.py` | Real Streamlit startup plus representative UI flows. |
| `tests/test_dataset_presentation.py` | New schema-driven presentation rules. |
| `tests/test_dataset_value_standardization.py` | New formatting and parsing coverage for units and structured fields. |

### Reference Patterns

| File | Pattern |
|------|---------|
| `app_support/dataset_ui.py` | Current registry pattern for dataset capabilities and default view selection. |
| `app.py` | Current armor and talisman rendering logic that should be converted into reusable schema-driven sections. |
| `data/column_loading_instructions.json` | Existing profile-based loading pattern that should remain the mechanism for visual/detail bundles. |

### Risk Assessment

- [ ] Breaking changes to public API
- [ ] Database migrations needed
- [ ] Configuration changes required

## Dataset Inventory Baseline

| Dataset | Rows | Current schema shape | Immediate visualization implication |
|---------|------|----------------------|------------------------------------|
| `armors` | 723 | Numeric `weight`; structured text `damage negation` and `resistance`; text `special effect` | Keep current armor panel as the reference for grouped stat sections. |
| `ashesOfWar` | 117 | Text `affinity`, `skill`, `description`; numeric `dlc` | Add action card/detail layout centered on affinity plus linked skill identity. |
| `bosses` | 153 | Text `HP`; structured text `Locations & Drops`; text `blockquote` | Add entity detail sections for HP, locations, and drops rather than raw dict strings. |
| `creatures` | 205 | Structured text `locations` and `drops`; lore text | Add parsed collection sections with readable lists. |
| `incantations` | 129 | Numeric-like text `FP`; numeric `slot`, `INT`, `FAI`, `ARC`, `stamina cost`; text `bonus`, `group`, `location` | Add spell sections for cost, requirements, school/group, effect, and acquisition. |
| `locations` | 286 | Structured text `items`, `npcs`, `creatures`, `bosses`; text `region`, `description` | Add location detail layout with parsed related-entity lists. |
| `npcs` | 109 | Text `location`, `role`, `voiced by`, `description` | Add lightweight profile layout with consistent field ordering. |
| `shields` | 100 | Numeric `weight` and `FP cost`; structured text `requirements`; text `damage type`, `category`, `passive effect`, `skill` | Add equipment layout with parsed requirements and skill metadata. |
| `shields_upgrades` | 28,286 | Structured text `attack power`, `stat scaling`, `passive effects`, `damage reduction (%)` | Add a dedicated progression-table renderer; do not force this into item-card layout. |
| `skills` | 257 | Composite text `FP`; text `equipament`, `charge`, `effect`, `locations` | Keep FP as literal text until a safe parser exists; group the rest into action metadata. |
| `sorceries` | 84 | Numeric-like text `FP`; numeric `slot`, `INT`, `FAI`, `ARC`, `stamina cost`; text `bonus`, `location` | Reuse the spell layout used for incantations, with optional group support. |
| `spiritAshes` | 84 | Numeric-like text `FP cost`; numeric `HP cost`; text `effect`, `description` | Add summon-cost section with FP and HP separated from effect text. |
| `talismans` | 155 | Numeric `weight`; numeric-like text `value`; percent-bearing text `effect`; text `description` | Extract effect magnitude when safe, but keep `weight` as a raw number and never as a percentage. |
| `weapons` | 402 | Numeric `weight`; structured text `requirements`; text `damage type`, `category`, `passive effect`, `skill`, `FP cost` | Add equipment layout shared with shields, while keeping text FP cost literal if not cleanly numeric. |
| `weapons_upgrades` | 60,201 | Structured text `attack power`, `stat scaling`, `passive effects`, `damage reduction (%)` | Add the same progression-table renderer pattern as `shields_upgrades`. |

## 1. Requirements & Constraints

- **REQ-001**: Clarify the user-facing runtime workflow in `README.md` and `docs/README.md` so the difference between direct foreground run, managed start, recover, stop, and `run-all` orchestration is explicit and non-contradictory.
- **REQ-002**: Every top-level dataset in `data/*.csv` must have a supported visualization route after this feature lands. Item-card datasets and progression-table datasets may use different renderers, but neither may remain an implicit placeholder.
- **REQ-003**: The first implementation slice must prioritize top-level datasets and must not require enabling `data/items/*` yet.
- **REQ-004**: The presentation contract for top-level datasets must be data-driven so that `data/items/*` can later be added by registering metadata rather than by adding new hard-coded branches in `app.py`.
- **REQ-005**: Unit display must be semantically correct. Weight must remain a raw number. Costs must remain costs. Percentages must only be shown when the dataset meaning is actually percentage-like.
- **REQ-006**: `talismans` must surface both effect semantics and magnitude semantics when the effect string encodes them safely.
- **REQ-007**: `incantations` and `sorceries` must expose cost and requirement fields clearly, including `FP`, `slot`, `INT`, `FAI`, `ARC`, and `stamina cost`.
- **REQ-008**: Structured text columns such as `requirements`, `damage negation`, `resistance`, `Locations & Drops`, and list-bearing world-data columns must be rendered as readable grouped content rather than raw serialized strings wherever parsing is reliable.
- **REQ-009**: `shields_upgrades` and `weapons_upgrades` must be treated as progression tables, not as regular item cards.
- **REQ-010**: `active_datasets.json` should not be expanded until representative views and smoke checks pass for the newly supported top-level datasets.
- **CON-001**: Keep existing armor and talisman optimizer behavior intact while adding broader dataset viewing support.
- **CON-002**: Prefer additive changes over broad `app.py` surgery. Move repeated rendering rules into support modules rather than duplicating branches.
- **CON-003**: Do not rewrite CSV source files as part of this feature. Standardization must be done at the loading and presentation layers.
- **GUD-001**: Centralize dataset presentation metadata in one registry-driven layer.
- **GUD-002**: Use deterministic formatter names such as `raw_number`, `percentage`, `cost_fp`, `cost_stamina`, `weight`, `requirements_map`, `structured_list`, and `structured_dict`.
- **PAT-001**: Reuse the existing `DatasetUiSpec` registry pattern in `app_support/dataset_ui.py`.
- **PAT-002**: Reuse `data/column_loading_instructions.json` as the loading contract instead of embedding per-dataset `usecols` directly in `app.py`.
- **PAT-003**: Keep `README.md` user-facing and task-oriented; keep session notes implementation-focused; keep stable rendering contracts in `docs/specs/`.

## 2. Implementation Steps

### Implementation Phase 1

- **GOAL-001**: Freeze the runtime-documentation rules and the top-level dataset audit baseline before changing rendering code.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Update `README.md` to add a single runtime command matrix covering `scripts/run_streamlit_local.ps1`, `scripts/start-app.ps1`, `scripts/recover-app.ps1`, `scripts/stop_streamlit_port.ps1`, and `scripts/run-all.ps1`, with explicit guidance on when to use each command. | Yes | 2026-04-01 |
| TASK-002 | Update `docs/README.md` so the quick verification section uses the same runtime vocabulary and restart guidance as `README.md`, without mixing contradictory foreground and managed flows. | Yes | 2026-04-01 |
| TASK-003 | Create `docs/specs/dataset_visualization_contract.md` to define presentation families, formatter kinds, section ordering rules, and the distinction between item cards and progression tables. | Yes | 2026-04-01 |
| TASK-004 | Keep `data/active_datasets.json` unchanged during the implementation phase, and only expand it after dataset-family smoke verification passes. |  |  |

### Implementation Phase 2

- **GOAL-002**: Introduce a schema-driven presentation contract for all top-level datasets.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Create `app_support/dataset_presentations.py` with explicit dataclasses such as `FieldPresentation`, `SectionPresentation`, and `DatasetPresentationSpec`, plus registry entries for each top-level dataset family. | Yes | 2026-04-01 |
| TASK-006 | Extend `app_support/dataset_ui.py` so each dataset maps to both a capability spec and a presentation spec, including a new progression-table family for `shields_upgrades` and `weapons_upgrades`. |  |  |
| TASK-007 | Extend `data/column_loading_instructions.json` with visual/detail profiles for spells, equipment, world entities, and progression tables so the UI loads the columns it needs deterministically. |  |  |
| TASK-008 | Add parser and formatter helpers to `app_support/dataset_presentations.py` for numeric-like text, talisman effect magnitude extraction, spell costs, equipment requirements, and structured list/dict rendering. | Yes | 2026-04-01 |

### Implementation Phase 3

- **GOAL-003**: Convert generic catalog rendering into schema-driven rendering for all top-level item-card datasets.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-009 | Update `app.py` functions that currently format detail fields and metric rows so they consume `DatasetPresentationSpec` instead of inferring display from raw numeric columns alone. Start with `format_metric_value`, `render_card_meta_fields`, `resolve_item_detail_columns`, `render_item_detail_inspector`, and the non-armor branch inside `render_ranked_cards`. | Yes | 2026-04-01 |
| TASK-010 | Implement the talisman presentation contract so `effect`, parsed effect magnitude, `value`, `weight`, and `dlc` appear in a deterministic order and weight is never shown as a percentage. | Yes | 2026-04-01 |
| TASK-011 | Implement a shared spell presentation for `incantations` and `sorceries`, with explicit sections for costs, requirements, effect, school or bonus tags, and acquisition location. | Yes | 2026-04-01 |
| TASK-012 | Implement a shared equipment presentation for `weapons` and `shields`, with parsed requirements plus ordered display of category, damage type, passive effect, skill, FP cost, and weight. | Yes | 2026-04-01 |
| TASK-013 | Implement world-entity presentations for `bosses`, `creatures`, `locations`, and `npcs`, including parsed list and dict sections for drops, related entities, and region or role metadata. | Yes | 2026-04-01 |
| TASK-014 | Implement action or summon presentations for `ashesOfWar`, `skills`, and `spiritAshes`, including safe handling of literal FP text when parsing would be lossy. | Yes | 2026-04-01 |

### Implementation Phase 4

- **GOAL-004**: Support progression-table datasets and preserve easy future onboarding for `data/items/*`.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-015 | Replace the unsupported placeholder state for `shields_upgrades` and `weapons_upgrades` with a dedicated progression-table view that shows parsed attack power, stat scaling, passive effects, and damage reduction subfields. |  |  |
| TASK-016 | Add a renderer helper in `app_support/dataset_presentations.py` or a dedicated support module for progression-table datasets so `app.py` does not grow new table-specific branches inline. |  |  |
| TASK-017 | Add a default onboarding path for `data/items/*` in the presentation registry so future item-subfolder datasets can be enabled by metadata registration and column-profile wiring rather than by new rendering branches. |  |  |
| TASK-018 | After representative manual verification passes, expand `data/active_datasets.json` from `armors` and `talismans` to the full supported top-level dataset list. |  |  |

### Implementation Phase 5

- **GOAL-005**: Lock behavior with automated and manual verification before enabling broader dataset visibility by default.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-019 | Extend `tests/test_dataset_ui_registry.py` for the new dataset family matrix, including progression-table support and the expected default views per family. |  |  |
| TASK-020 | Add `tests/test_dataset_presentation.py` to validate field ordering, presentation sections, and dataset-to-family mapping. | Yes | 2026-04-01 |
| TASK-021 | Add `tests/test_dataset_value_standardization.py` to validate percentage formatting, weight formatting, spell costs, parsed requirements, and list or dict rendering for structured text fields. | Yes | 2026-04-01 |
| TASK-022 | Extend `tests/test_ui_smoke.py` so at least one representative dataset from each family is opened and inspected: `talismans`, `incantations` or `sorceries`, `weapons` or `shields`, `bosses` or `locations`, and one progression-table dataset. |  |  |
| TASK-023 | Update `ui_smoke_checklist.md` to cover direct run, managed restart, and representative non-armor dataset checks before the full supported dataset list is enabled by default. | Yes | 2026-04-01 |

## 3. Alternatives

- **ALT-001**: Keep adding dataset-specific branches directly inside `app.py`. Rejected because the code already centralizes dataset capability metadata in `app_support/dataset_ui.py`, and more inline branches will make expansion to `data/items/*` slower and riskier.
- **ALT-002**: Normalize all CSV files into one rigid schema before rendering. Rejected because it would rewrite source data, blur original semantics, and create a larger migration than needed for this UI feature.
- **ALT-003**: Enable `data/items/*` in the same implementation slice as the top-level datasets. Rejected for initial scope control, but the presentation contract must make that follow-up trivial.
- **ALT-004**: Continue treating upgrade tables as unsupported. Rejected because the stated goal is broader coverage across all top-level datasets, and the upgrade tables are top-level datasets with a different renderer need rather than a reason to stay hidden.

## 4. Dependencies

- **DEP-001**: `app_support/dataset_ui.py` must remain the authority for dataset capability and default-view decisions.
- **DEP-002**: `data/column_loading_instructions.json` must continue to define visual/detail/ranking column bundles.
- **DEP-003**: `data_loader.py` must continue to resolve root datasets and `items/` datasets through one path-mapping API.
- **DEP-004**: `README.md` and `docs/README.md` must be aligned so startup and restart instructions do not fork.
- **DEP-005**: `tools/workspace_verify.py` must continue to be the main verification entrypoint after tests are expanded.

## 5. Files

- **FILE-001**: `README.md` - clarify runtime command usage and restart logic.
- **FILE-002**: `docs/README.md` - align internal onboarding and quick verification wording.
- **FILE-003**: `docs/specs/dataset_visualization_contract.md` - new stable visualization contract.
- **FILE-004**: `app_support/dataset_ui.py` - extend dataset family and registry metadata.
- **FILE-005**: `app_support/dataset_presentations.py` - new schema-driven presentation and formatter layer.
- **FILE-006**: `app.py` - wire rendering to the presentation layer.
- **FILE-007**: `data/column_loading_instructions.json` - add dataset-specific visual/detail profiles.
- **FILE-008**: `data/active_datasets.json` - expand visible datasets only after verification.
- **FILE-009**: `tests/test_dataset_ui_registry.py` - extend registry coverage.
- **FILE-010**: `tests/test_dataset_presentation.py` - new presentation tests.
- **FILE-011**: `tests/test_dataset_value_standardization.py` - new value-formatting tests.
- **FILE-012**: `tests/test_ui_smoke.py` - broaden family-level smoke coverage.
- **FILE-013**: `ui_smoke_checklist.md` - broaden manual coverage.

## 6. Testing

- **TEST-001**: `python -m unittest tests.test_dataset_ui_registry`
- **TEST-002**: `python -m unittest tests.test_dataset_presentation`
- **TEST-003**: `python -m unittest tests.test_dataset_value_standardization`
- **TEST-004**: `python -m unittest tests.test_ui_smoke`
- **TEST-005**: `./scripts/verify-workspace.ps1`
- **TEST-006**: Manual dataset pass across all top-level datasets, checking section order, unit formatting, and whether structured list/dict fields are readable.
- **TEST-007**: Manual runtime-doc pass confirming the README command matrix matches actual behavior of `run_streamlit_local`, `start-app`, `recover-app`, `stop_streamlit_port`, and `run-all`.

## 7. Risks & Assumptions

- **RISK-001**: Some numeric-looking text fields are semantically mixed. Example: `skills.FP` contains composite strings like `26 (-/12)`, so naive numeric coercion would destroy meaning.
- **RISK-002**: `talismans.effect` contains embedded percentages and absolute values in free text, so magnitude extraction must be best-effort and must never replace the original effect text.
- **RISK-003**: `bosses`, `creatures`, `locations`, and upgrade-table datasets use serialized dict or list strings that may not always parse cleanly.
- **RISK-004**: Expanding `active_datasets.json` too early will expose half-finished layouts to the default user path.
- **ASSUMPTION-001**: The immediate product goal is top-level dataset coverage first, with `data/items/*` enabled later through the same registry and profile system.
- **ASSUMPTION-002**: Existing armor and talisman optimization flows should remain behaviorally stable while generic visualization coverage expands.
- **ASSUMPTION-003**: The current dataset names under `data/*.csv` are stable for this feature slice: `armors`, `ashesOfWar`, `bosses`, `creatures`, `incantations`, `locations`, `npcs`, `shields`, `shields_upgrades`, `skills`, `sorceries`, `spiritAshes`, `talismans`, `weapons`, `weapons_upgrades`.

## 8. Related Specifications / Further Reading

- `README.md`
- `docs/README.md`
- `docs/session/2026-02-15_startup_and_verify_deep_dive.md`
- `app_support/dataset_ui.py`
- `data/column_loading_instructions.json`
- `data/active_datasets.json`