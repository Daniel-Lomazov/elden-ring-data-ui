# Icon Registry Spec

Registry file: `data/icons/icons.json`

Each icon item includes:

- `icon_id`
- `canonical_key` (optional)
- `label`
- `local_path`
- `source_url` (optional)
- `category` in: `armor_stat | negation | resistance | status`

## Minimum Set Included

- Armor stats: `weight`, `poise`
- Negation keys: `neg.phys`, `neg.std`, `neg.str`, `neg.sla`, `neg.pie`, `neg.mag`, `neg.fir`, `neg.lit`, `neg.hol`
- Resistance keys: `res.imm`, `res.rob`, `res.foc`, `res.vit`
- Status keys: `status.poison`, `status.rot`, `status.bleed`, `status.frost`, `status.sleep`, `status.madness`, `status.death`
