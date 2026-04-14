# PR / Commit Plan: Optimizer Dialect + Encounter Survival (Incremental)

> **Internal historical note** — This is a development planning document from
> February 2026. The work it describes has been completed. It is kept for historical
> reference only and does not reflect any pending work.

## Goal
Introduce an encounter-aware optimizer (damage mix + status threats) without breaking existing workflows.

---

## PR 1 — Canonical schema + icon registry scaffolding
**Changes**
- Add `optimizer/schema.py`:
  - canonical key enums
  - categories and directions
- Add `data/armor_stat_schema.json`:
  - canonical_key → df_column_name mapping
- Add `data/icons/icons.json` + placeholder local icons folder

**Verify**
- app still launches
- existing ranking still works (no behavior changes)

---

## PR 2 — Dialect request object + validation
**Changes**
- Add `optimizer/dialect.py`:
  - load/validate YAML/JSON requests
  - defaults
  - canonicalization (keys validated against schema)
- Add `optimizer/api.py`:
  - `optimize(df, request)`

**Verify**
- create a dialect request that reproduces current “stat rank” behavior

---

## PR 3 — Encounter survival strategy (HP channel only)
**Changes**
- Add `optimizer/strategies/encounter_survival.py`
  - compute `M = sum w_t*(1-N_t)`
  - rank by `M` ascending
- Add explain payload: `taken_by_type`, `expected_taken_M`

**Verify**
- create a simple profile:
  - 100% magic
  - check that magic negation drives the ranking

---

## PR 4 — Status channel (bleed/frost/etc.) v1 estimator
**Changes**
- Add status threat parsing in dialect
- Add threshold proxy function:
  - configurable `a,b` per status family
- Add composite objective `J = M + lambda*StatusPenalty`

**Verify**
- katana profile (slash + bleed):
  - items with higher `neg.sla` should improve `M`
  - items with higher `res.rob` should increase hits-to-proc and reduce penalty

---

## PR 5 — Full-set (armor-only) optimization with pruning
**Changes**
- Implement `scope: full_set`
- Slot split + top-K prune + combo enumeration under constraints
- Return top-N + (optional) Pareto set for exploration

**Verify**
- Medium roll constraint respected
- sanity: full set score <= any of its component single-piece scores (under the same objective definition)

---

## PR 6 — Docs + examples + smoke tests
**Changes**
- Add `docs/specs/optimizer_dialect.md`
- Add 3 built-in encounter profiles:
  - `Katana_Slash_Bleed`
  - `RayaLucaria_Mages`
  - `Bayle_Phys_Fire_Lightning`
- Add a tiny CLI or script:
  - loads df
  - runs 2–3 requests
  - prints top 5 with explain payload

**Verify**
- “Start here” docs include the smoke test
- New optimizer path is demonstrably working

---

## PR 7 (optional) — Defense curve / hit-size modeling
**Changes**
- Add optional `incoming.hit_size` and defense multiplier function
- Keep v1 available as fallback

**Verify**
- results are stable and explainable
- add tests for monotonicity vs negation and vs defense

