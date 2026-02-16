# Optimizer Dialect Spec (v1)

The optimizer accepts one request object (`dict`, JSON file, or YAML file).

## Shape

```yaml
version: 1
scope: single_piece | per_slot | full_set | complete_loadout
objective:
  type: stat_rank | encounter_survival | pareto | utility
  method: maximin_normalized | weighted_sum_normalized   # stat_rank
  hp: 1600                                               # encounter_survival
  eps: 0.01
  lambda_status: 1.0
selected_stats: [weight, "Res: Fir"]                  # stat_rank
constraints: {}
encounter:
  name: string
  incoming:
    damage_mix:
      neg.mag: 0.75
      neg.phys: 0.25
  status_threats:
    status.bleed:
      buildup_per_hit: 45
      proc_penalty: 150
      weight: 1.0
      a: 10.0
      b: 0.0
```

## Validation

- `version` must be `1`.
- `scope` must be one of canonical scopes.
- `objective.type` must be one of canonical objective types.
- `encounter.incoming.damage_mix` keys must use canonical negation keys (`neg.*`).
- `encounter.status_threats` keys must use canonical status keys (`status.*`).

## Behavior guarantees

- Legacy ranking remains available via `objective.type = stat_rank`.
- Encounter scoring uses:
  - HP channel: `M = Σ w_t * (1 - N_t)`
  - Status channel: `StatusPenalty = Σ weight_s * (proc_penalty / ceil((a*res+b)/buildup))`
  - Composite: `J = M + lambda_status * StatusPenalty`

## UI resistance split contract (v1)

- User-facing armor resistance display in cards uses canonical status keys:
  - `status.poison`
  - `status.rot`
  - `status.bleed`
  - `status.frost`
  - `status.sleep`
  - `status.madness`
  - `status.death`
- Mapping source remains aggregated columns for compatibility:
  - `status.poison`, `status.rot` ← `Res: Imm.`
  - `status.bleed`, `status.frost` ← `Res: Rob.`
  - `status.sleep`, `status.madness` ← `Res: Foc.`
  - `status.death` ← `Res: Vit.`
