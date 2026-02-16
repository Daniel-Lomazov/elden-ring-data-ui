# Optimization Reference — Elden Ring Data UI

This reference documents the optimization subsystem used by the Elden Ring Ranking UI: where the data and stat symbols come from, how stats are parsed and normalized, the scoring strategies, where the UI exposes controls, and where developers can extend or modify behavior.

---

## At-a-glance

- Core optimizer package: `optimizer/` with legacy ranking in `optimizer/legacy.py`.
- Where armor stats are parsed into numeric columns: `ui_components.py::parse_armor_stats` ([ui_components.py](ui_components.py#L1-L120)).
- Canonical column → label map for armor stats: `armor_column_map.json` ([armor_column_map.json](armor_column_map.json#L1-L40)).
- Raw source data (examples and header): `data/armors.csv` ([data/armors.csv](data/armors.csv#L1-L1)).
- App integration (where the UI calls the optimizer): `app.py` ([app.py](app.py#L2320-L2359)).
- Small verification script demonstrating usage: `tools/optimizer_check.py` ([tools/optimizer_check.py](tools/optimizer_check.py#L1-L80)).

---

## 1) Data sources and canonical stat symbols

1. Raw dataset: `data/armors.csv` contains fields `damage negation`, `resistance`, and `weight`.
   - `damage negation` and `resistance` are stored as stringified Python dict/list literals in the CSV. Each row may look like the sample in the CSV header/example.

2. Parsing transforms those literals into numeric columns with canonical names:
   - Damage negation → columns named `Dmg: Phy`, `Dmg: VS Str.`, `Dmg: VS Sla.`, `Dmg: VS Pie.`, `Dmg: Mag`, `Dmg: Fir`, `Dmg: Lit`, `Dmg: Hol` (created by `parse_armor_stats`).
   - Resistance → columns named `Res: Imm.`, `Res: Rob.`, `Res: Foc.`, `Res: Vit.`, `Res: Poi.`.
   - `weight` is taken from the CSV `weight` column.

3. The canonical mapping and friendly labels live in `armor_column_map.json` which maps these `Dmg:` and `Res:` column names to human labels displayed in the UI.

Why this matters: optimization code expects numeric columns with these names; `ui_components.parse_armor_stats` guarantees they exist and are numeric before ranking or optimization runs.

---

## 2) Parsing pipeline (where to look)

- `ui_components.parse_armor_stats(df: pd.DataFrame) -> pd.DataFrame`
  - Reads `damage negation` and `resistance` literal strings with `ast.literal_eval`.
  - Normalizes keys using a simple `normalize_key` helper so variants like `VS Str.` and `VS Str` are handled consistently.
  - Emits numeric columns named `Dmg: <Key>` and `Res: <Key>`.
  - Used by the UI ranking view; any DataFrame plugged into the app should call (or rely on) this parsing step first.

See implementation: [ui_components.py](ui_components.py#L1-L120).

---

## 3) Optimization core and methods

Optimizer logic is split across the `optimizer/` package:

- `optimizer/legacy.py` for existing normalized ranking methods.
- `optimizer/api.py` for dialect-first dispatch via `optimize(df, request)`.
- `optimizer/strategies/encounter_survival.py` for encounter survival scoring.
- `optimizer/strategies/full_set_prune.py` for full-set pruning/enumeration.

Key exported functions:
- `optimize_single_piece(df, selected_stats, method, config)` — single-item ranking (used by the app UI).
- `optimize_full_set`, `optimize_complete_set` — placeholders that reuse the same method registry for different scopes.

Core building blocks:
- `_normalized_view(df, stats, config)`
  - Converts `stats` columns to numeric, computes min and max, scales values to [0, 1] per-stat.
  - If a stat is designated as "minimize" (defaults to `weight`), that stat is inverted after normalization: normalized_value = 1.0 - normalized_value. This makes higher-is-better for all objectives after normalization.

- Scoring strategies (registered strategies):
  - `maximin_normalized` (default)
    - For each candidate row, the score is the minimum of the normalized stat values (the maximin principle). A higher min means the candidate is more balanced across selected stats.
    - Tiebreaker: mean(normalized values).
    - Adds `Norm: <stat>` columns and metadata columns: `__opt_score`, `__opt_tiebreak`, `__opt_method`, `__opt_length`, `__opt_rank`.

  - `weighted_sum_normalized`
    - Weighted linear combination of normalized stats, supports `config={"weights": {...}}` with per-stat weights.
    - Tiebreaker: minimum normalized value.
    - Adds same metadata and `Norm:` columns.

- Method registry and extension points:
  - `_BASE_OPTIMIZER_METHODS` holds the base methods. `OPTIMIZER_METHODS_BY_SCOPE` maps scopes → methods.
  - Developers can add new methods by calling `register_optimizer_method(scope, method_name, strategy)`.

See package entrypoints: [optimizer/__init__.py](optimizer/__init__.py), [optimizer/api.py](optimizer/api.py), [optimizer/legacy.py](optimizer/legacy.py).

---

## 4) Default behavior & minimize stats

- By default the optimizer treats `weight` as a minimize objective. This is controlled by `_resolve_minimize_stats(config)` which returns `{"weight"}` if nothing else is configured.
- To change which stats are minimized in a single call, pass `config={"minimize_stats": ["weight", "some_other_stat"]}` to `optimize_single_piece`.
- The UI uses `minimize_stats` to invert those stats in `_normalized_view`, ensuring consistent higher-is-better semantics for scoring.

Example (Python):

```py
from optimizer import optimize_single_piece
# df has numeric columns: 'weight', 'Res: Fir'
ranked = optimize_single_piece(
    df,
    selected_stats=["weight", "Res: Fir"],
    method="maximin_normalized",
    config={"minimize_stats": ["weight"]},
)
```

`ranked` will include `__opt_score`, `__opt_rank`, and `Norm: weight`, `Norm: Res: Fir` columns.

---

## 5) How the app exposes and uses optimization (user & developer view)

User-facing:
- In `Optimization view`, controls now include:
  - `Optimization engine`: `Legacy` or `Optimization 2.0`
  - `Objective`: `stat_rank` or `encounter_survival` (armors)
  - `Encounter profile` + `Status fear (λ)` when `encounter_survival` is selected
- Legacy engine keeps existing `optimize_single_piece` behavior for stat ranking.
- Optimization 2.0 routes through dialect API `optimize(df, request)` and supports full-set encounter ranking in armor full-set preview.
- See UI invocation and caching path in [app.py](app.py#L2290-L2520).

Developer-facing (where to intervene):
- Data parsing: Modify or extend parsing behavior in `ui_components.parse_armor_stats` if the CSV format changes or if you want to extract additional stat columns.
  - File: [ui_components.py](ui_components.py#L1-L120)
- Column labels and UI-friendly mappings: Update `armor_column_map.json` if you want to rename/relocate labels or expose other columns in UI pickers.
  - File: [armor_column_map.json](armor_column_map.json#L1-L40)
- Optimization behavior:
  - Add new strategies by implementing a function with signature `fn(df: pd.DataFrame, stats: List[str], config: Optional[dict]) -> pd.DataFrame` and registering with `register_optimizer_method(scope, method_name, strategy)`.
  - Modify default minimize stats by changing `_resolve_minimize_stats` or passing `config` at call sites.
  - File: [optimizer/legacy.py](optimizer/legacy.py)
- UI integration:
  - `app.py` now constructs either legacy optimizer arguments or a dialect request payload based on `Optimization engine` and `Objective`.
  - File: [app.py](app.py#L2290-L2520)

---

## 6) Examples and expected results

Example dataset (toy):

```py
import pandas as pd
from optimizer import optimize_single_piece

df = pd.DataFrame([
    {"name": "LightGood", "weight": 4, "Res: Fir": 13},
    {"name": "HeavyGood", "weight": 12, "Res: Fir": 15},
    {"name": "Medium", "weight": 8, "Res: Fir": 14},
])

# Default: maximin_normalized (weight minimized by default)
ranked = optimize_single_piece(df, ["weight", "Res: Fir"])  # returns ranked DataFrame
print(ranked[["name", "__opt_score", "__opt_rank"]])
```

Expected behavior: `Medium` will typically rank first as a compromise between low weight and reasonable fire resistance (this exact behavior mirrors the smoke tests in `tools/optimizer_check.py`).

See the smoke test that asserts this: [tools/optimizer_check.py](tools/optimizer_check.py#L1-L80).

---

## 7) Extension recipes (quick)

- Add a new normalized scoring method that favors top-two stats:
  1. Implement `def score_best_two_normalized(df, stats, config):` returning the same enriched DataFrame shape as the other strategies.
  2. Register with `register_optimizer_method(OPT_SCOPE_SINGLE_PIECE, "best_two_normalized", score_best_two_normalized)`.
  3. Add `"best_two_normalized"` to UI method pickers in `app.py` (where `OPTIMIZER_METHODS` / `OPTIMIZER_METHODS_BY_SCOPE` is used).

- Make weight not the only minimized stat in UI by wiring a checkbox/config option that sets `config["minimize_stats"]` before calling `optimize_single_piece`.

---

## 8) Common pitfalls & notes

- Column name mismatches: optimization expects the `selected_stats` names to exist in the DataFrame. Always call `parse_armor_stats` (or load the CSV through the `DataLoader`) before optimization.
- Zero-range normalization: `_normalized_view` guards against zero division by replacing zero ranges with `1.0`, so constant columns will yield normalized `0.0` across rows (then possibly inverted if minimized).
- Caching: the app caches optimizer results in `st.session_state` keyed by a frame signature. If you change how signatures are computed you may need to clear or invalidate the cache.

---

## 9) Where to look in the code (quick links)

- Parser: [ui_components.py](ui_components.py#L1-L120)
- Column map: [armor_column_map.json](armor_column_map.json#L1-L40)
- Raw CSV: [data/armors.csv](data/armors.csv#L1-L1)
- Optimizer package: [optimizer/__init__.py](optimizer/__init__.py)
- Legacy methods: [optimizer/legacy.py](optimizer/legacy.py)
- Dialect API: [optimizer/api.py](optimizer/api.py)
- App usage: [app.py](app.py#L2290-L2520)
- Smoke test: [tools/optimizer_check.py](tools/optimizer_check.py#L1-L80)

---

Next steps might include:

- Add a short UI developer debug panel that lists detected `Norm:` columns and which stats are currently minimized, or
- Add the above document into the app's `docs/` index and link it from the README.

