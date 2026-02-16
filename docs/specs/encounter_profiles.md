# Encounter Profiles (Built-in)

Profiles are stored in `data/profiles/`.

## Available v1 Profiles

- `Katana_Slash_Bleed.yaml`
- `RayaLucaria_Mages.yaml`
- `Bayle_Phys_Fire_Lightning.yaml`

## Notes

- These are ready for `optimizer.load_request(...)` and `optimizer.optimize(...)`.
- Damage mix keys use canonical `neg.*` namespace.
- Status threats use canonical `status.*` namespace and map to resistances via schema.
