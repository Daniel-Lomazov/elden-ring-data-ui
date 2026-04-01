# UI Smoke Checklist

Use this quick checklist after running `streamlit run app.py`.

1. Select `armors` dataset and `Single piece` mode (default piece type should be `Armor`).
2. Pick highlighted stats from the dropdown (weight should not appear there).
3. Confirm `Reset` appears at the top of ranking controls and resets filters/stats while preserving armor mode.
4. Use the highlighted-stat add/remove flow and verify each action applies cleanly.
5. Toggle `Optimize with weight` off; verify ranking excludes weight objective.
6. Toggle `Optimize with weight` on; confirm info note appears: weight minimized, others maximized.
7. Enable `Use max weight constraint`, set a low value, verify candidate count/ranking changes.
8. Confirm histogram view defaults to `Interactive (click-to-set)`; switch to `Classic` and back; check axis labels are fully visible.
9. In main view (right side aligned with ranking/export block), switch method to `weighted_sum_normalized`, set one stat weight higher, and verify rankings shift.
11. Set `Rows to show` to 5 then 25 and verify card list count updates.
12. Switch to `Full armor set` mode and verify five columns: Helm/Armor/Gauntlets/Greaves/Overall.
13. Verify `Overall` sums highlighted stats and shows aligned rows (phantom spacer in place of image).
14. Click `📥 Export <column> rows (CSV)` and verify the downloaded file reflects current rows.
15. Open `Why this is #1` and verify top-vs-#2 deltas are shown.
16. Switch to `Talismans`, open `Optimization view`, and verify `Highlighted stats:` includes `value` but does not include `weight`.
17. Switch to `Incantations` and verify the shared catalog controls expose numeric spell stats such as `slot`, `FAI`, and `stamina cost`.
18. Open a spell, weapon, and location card and verify detail panels render semantic fields cleanly: costs as costs, requirements maps parsed, and serialized lists shown as readable text instead of raw literals.
