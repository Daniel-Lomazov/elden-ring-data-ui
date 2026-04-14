# Optimizer Dialect Refactor Suggestions (v2)

> **Internal historical note** — This document captures optimizer dialect iteration
> notes from early development (February 2026). For the current optimizer contract
> see [`specs/optimizer_dialect.md`](specs/optimizer_dialect.md).

## Source context
The uploaded `README.md` is a *documentation index* that points onboarding readers to `../README.md` and a set of session deep-dives under `docs/session/`.

- It strongly implies: (1) the root README contains **setup/usage/debugging/optimization overview**, and (2) the repo already maintains **commit-oriented session notes**.

This refactor plan is designed to fit that style: small, verifiable commits with strong docs and an optimizer architecture that can evolve from “stat ranking” to “encounter-aware survival”.


---

## 1) Target capability
Accept a single **Optimization Request Dialect** object that can express:

- **Scope**: `single_piece | per_slot | full_set | complete_loadout`
- **Constraints**: equip-load class (or max weight), minimum poise, slot locks, include/exclude lists
- **Threat model** (encounter profile): damage-type mixture + status threats (bleed/frost/rot/sleep/madness/deathblight)
- **Objective**: expected damage taken, effective HP (reported), Pareto tradeoffs, or a utility function
- **Explainability**: per-type taken multipliers + status proc metrics + ranking rationale

The goal is *dialect-first*: new strategies and new encounter profiles should be addable without changing UI glue.

---

## 2) Canonical stat vocabulary (internal keys)
### 2.1 Armor stats
- `weight`
- `poise`

### 2.2 Damage negation keys (armor-facing)
Use a canonical namespace, independent of the dataset’s column names:

- `neg.phys` (aggregate physical, if present)
- `neg.std` (standard)
- `neg.str` (strike)
- `neg.sla` (slash)
- `neg.pie` (pierce)
- `neg.mag` (magic)
- `neg.fir` (fire)
- `neg.lit` (lightning)
- `neg.hol` (holy)

### 2.3 Resistance stats (armor-facing)
- `res.imm` (immunity)
- `res.rob` (robustness)
- `res.foc` (focus)
- `res.vit` (vitality)

### 2.4 Status-effect threat keys (encounter-facing)
These are not necessarily armor columns; they are *threat channels* that map to one of the resistance stats:

- `status.poison`   → `res.imm`
- `status.rot`      → `res.imm`
- `status.bleed`    → `res.rob`
- `status.frost`    → `res.rob`
- `status.sleep`    → `res.foc`
- `status.madness`  → `res.foc`
- `status.death`    → `res.vit` (death blight)

---

## 3) Icon / symbol registry (complete, reusable)
### 3.1 What to store
Add `data/icons/icons.json` with:

- `icon_id`
- `canonical_key` (optional)
- `label`
- `local_path` (preferred for offline)
- `source_url` (optional provenance)
- `category`: `armor_stat | negation | resistance | status`

### 3.2 Minimum icon set
Include icons for:
- weight, poise
- each negation type listed above
- immunity/robustness/focus/vitality
- each status threat listed above (bleed/frost/poison/rot/sleep/madness/deathblight)

(Your earlier link list can be copied into this registry as `source_url` values; the app should load local copies.)

---

## 4) Mechanics engine: two parallel channels
### 4.1 HP-damage channel (v1: negation-only, no defense curve)
For a profile with damage mix weights `w_t` and build negations `N_t`:

- Taken multiplier per type: `m_t = 1 - N_t`
- Expected taken multiplier: `M = sum_t w_t * m_t`
- Reported eHP: `eHP = HP / max(M, eps)` (eps prevents divide-by-zero)
- Optimization objective should be stable:
  - minimize `M`, or minimize `-log(max(M, eps))`

> Keep eHP as a *reporting* metric; use `M` as the primary optimization value for ranking stability.

### 4.2 HP-damage channel (v2: defense curve)
Later, extend profiles with representative hit sizes (or distributions):
- `attack_t` for each type or `attack_total` + split.

Then:
- compute defense multiplier `f(attack/defense)` (piecewise)
- apply negation multiplier (product over sources)
- sum over types

This should live behind an interface so v1/v2 swap without touching the dialect.

### 4.3 Status channel (v1: hits-to-proc estimator)
For each status threat `s`:
- map to resistance key `res_key`
- define `buildup_per_hit`
- define `proc_penalty` (damage-equivalent or “death”)
- compute threshold proxy `T = a * resistance + b` (configurable)
- hits-to-proc `k = ceil(T / buildup_per_hit)`
- penalty per hit `p = proc_penalty / k`

Composite:
- `StatusPenalty = sum_s (weight_s * p_s)`

### 4.4 Composite encounter survival score
Define a profile score to minimize:
- `J = M + lambda * StatusPenalty`

Where `lambda` is either:
- a user-facing slider (“How much do you fear procs?”), or
- derived from the profile (“bleed-heavy enemy”)

---

## 5) Dialect schema (Optimization Request)
Store user requests (and built-in presets) as JSON/YAML.

### 5.1 Example: katana (slash + bleed), single piece
```yaml
version: 1
scope: single_piece
slot: head
constraints:
  roll_class: medium
  min_poise: null
objective:
  type: encounter_survival
  hp: 1600
  eps: 0.01
  lambda_status: 1.0
encounter:
  name: Katana_Slash_Bleed
  incoming:
    damage_mix:
      neg.sla: 1.0
  status_threats:
    status.bleed:
      buildup_per_hit: 45
      proc_penalty: 150
      weight: 1.0
```

### 5.2 Example: Raya Lucaria (magic + physical)
```yaml
encounter:
  name: RayaLucaria_Mages
  incoming:
    damage_mix:
      neg.mag: 0.75
      neg.phys: 0.25
```

### 5.3 Example: Bayle (physical + fire + lightning)
```yaml
encounter:
  name: Bayle_Phys_Fire_Lightning
  incoming:
    damage_mix:
      neg.phys: 0.45
      neg.fir: 0.40
      neg.lit: 0.15
```

---

## 6) Optimizer architecture refactor (modules + interfaces)
### 6.1 Package layout
```
optimizer/
  __init__.py
  api.py                 # optimize(df, request) -> RankedResult
  dialect.py             # load/validate/canonicalize request
  schema.py              # canonical keys, mappings, dataclasses
  registry.py            # register strategies
  constraints.py         # weight/roll/slot locks/min poise
  explain.py             # explainability payload builders
  strategies/
    stat_rank.py         # existing normalized ranking methods
    encounter_survival.py
    pareto.py
  features/
    armor.py             # compute build totals from pieces
    stacking.py          # multiplicative stacks for negations
```

### 6.2 Strategy interface (stable)
Each strategy:
- takes `df` + `request` + optional `context`
- returns:
  - ranked dataframe view
  - `explain[row_id]` dict
  - `metadata`

---

## 7) Full-set optimization (pruning-first)
### 7.1 Armor-only full set (v1)
- Split df by slot
- Precompute per-piece features needed for the score
- Prune to top-K per slot using a cheap surrogate (e.g., minimize `M` ignoring status)
- Enumerate combinations under constraints
- Return top N + Pareto set

### 7.2 Extend to talismans/buffs later
Treat each source as a “modifier object” with:
- affected keys
- multiplicative/additive semantics
- conditions

---

## 8) Explainability contract (what the UI can render)
For each candidate:
- `total_weight`, `roll_class`
- `taken_by_type`: `{neg.sla: 0.78, neg.mag: 0.92, ...}`
- `expected_taken_M`
- `status`: for each status, `{threshold, buildup, k_hits, pen_per_hit}`
- `final_score_J`
- `notes`: textual bullet points (short)

---

## 9) Data and migration notes
- Keep legacy dataframe column names, but add a canonical mapping layer:
  - `data/armor_stat_schema.json`: canonical_key → df_column_name + direction + category
- Rename ambiguous columns:
  - ensure `poise` is not stored as `Res: Poi.`; keep it separate.

---

## 10) Acceptance criteria (definition of “done”)
- Existing “stat normalized ranking” still works unchanged via dialect `objective.type = stat_rank`.
- New `objective.type = encounter_survival` works for:
  - `single_piece`
  - `per_slot`
  - `full_set` (armor-only)
- Icons are loaded via the registry; UI can render the full icon vocabulary.
- Each recommendation includes a machine-readable explainability payload.

