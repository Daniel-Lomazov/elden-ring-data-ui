# Elden Ring Data UI: Detailed View and Sidebar Refactor

## Summary of Changes (since last commit)

### 1. Sidebar Controls & Label Consistency
- All sidebar dropdowns, radio buttons, and captions now use Title Case for labels and option display values (e.g., "Choose Scope", "Choose Piece", "Detected Set").
- Added a shared `sidebar_title_case()` helper for consistent formatting.
- Updated dataset/view selectors to use Title Case.

### 2. Full-Scope Set Synchronization
- When a piece is changed in full-scope mode, the inferred family key is stored and applied before rendering the set dropdown, ensuring the set selector stays in sync with piece changes.
- Randomizer logic for full/custom scope now reliably updates all relevant session state keys.

### 3. Detailed View Card Rendering
- Full scope and custom scope now render as a single, centered set card (with 4-in-1 image grid, summed stats, and inferred set description).
- Custom scope card uses a distinct icon and label ("Custom Armor Set").
- Totals row is included for custom/full scope, matching optimization mode behavior.
- All item names, descriptions, and stats are normalized for display.

### 4. Integrity & Startup Improvements
- Integrity check is now explicit: startup and manual test update sidebar status icon and timestamp.
- Startup script (`scripts/start-app.ps1`) defaults to browser open/refresh behavior and reports status.

### 5. Miscellaneous
- Refactored helper functions for set-name inference, tokenization, and description aggregation.
- Ensured all session state keys are safely updated before widget instantiation.
- Ran workspace quick verification: **WORKSPACE_VERIFY: SUCCESS**.
- No errors found in [app.py](app.py).

## Commit Message
```
Refactor sidebar controls and detailed view:
- Title Case for all sidebar labels and dropdowns
- Full-scope set sync on piece change (pending family key)
- Unified full/custom scope card rendering (centered, 4-in-1 image, summed stats, set description)
- Custom scope card with distinct icon/label
- Integrity check/status and startup browser handling improvements
- All changes validated, workspace quick verify: SUCCESS
```

## Next Steps
- Confirm UI visually in app for full-scope and custom-scope detailed views.
- Continue with further UX polish or new features as needed.
