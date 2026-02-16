# Docs Onboarding + Documentation Refactor Suggestions

## Source context
The uploaded `README.md` is a **documentation index**. It instructs onboarding readers to start with `../README.md` and then proceed through session deep dives under `docs/session/`.


This file suggests changes that improve:
- “Start here” accuracy
- discoverability
- repeatability of verification steps
- traceability between code and decisions

---

## 1) Clarify file identity: `docs/README.md` vs root `README.md`
### Recommendation
- Rename the uploaded index file to **`docs/README.md`** (if it is not already).
- Ensure the root `README.md` contains a prominent “Documentation” section that links to:
  - `docs/README.md`
  - the newest deep dive file
  - the newest commit summary

This prevents confusion when a reader opens “README.md” and expects setup instructions.

---

## 2) Make the onboarding order self-checking
### Add a “Quick verification” block to `docs/README.md`
- Commands:
  - create venv / install deps
  - run the app
  - run a minimal “optimizer smoke test”
- Expected outputs (short)

This matches your repo’s “startup and verify” session note style.

---

## 3) Add an explicit “Optimization overview” pointer
The index currently says root README covers “optimization overview”.
Add *one more explicit pointer*:
- `docs/optimizer/README.md` (new): canonical stat keys, methods, dialect schema, and examples.

This prevents optimization design from being scattered across session notes.

---

## 4) Document conventions (tighten)
Keep the existing conventions, but add:
- Each session doc must include:
  - “What changed”
  - “How to verify”
  - “Known limitations”
- Add a short “Glossary” section:
  - ALMOP, families, normalization, etc. (whatever terms your repo uses)

---

## 5) Add “living specs” as first-class docs
Create:
- `docs/specs/optimizer_dialect.md`
- `docs/specs/encounter_profiles.md`
- `docs/specs/icon_registry.md`

These are stable references that session docs can link to.

---

## 6) Lightweight docs automation (optional but high leverage)
- Add a CI check (or local script) that:
  - verifies links to internal docs exist
  - validates that referenced files in `docs/README.md` are present
  - checks JSON/YAML specs against schemas

---

## 7) Suggested doc tree
```
docs/
  README.md
  specs/
    optimizer_dialect.md
    encounter_profiles.md
    icon_registry.md
  optimizer/
    README.md
  session/
    ...
```

