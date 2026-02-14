# UI Smoke Checklist

Use this quick checklist after running `streamlit run app.py`.

1. Select `armors` dataset and `Single piece` mode (default piece type should be `Armor`).
2. Pick 2+ highlighted stats including `weight`.
3. Confirm info note appears: weight minimized, others maximized.
4. Toggle sort between Highest/Lowest and verify order reverses.
5. Switch method to `weighted_sum_normalized`, set one stat weight higher, and verify rankings shift.
6. Set `Rows to show` to 5 then 25 and verify card list count updates.
7. Enable `Show raw data table (dev view)` and verify columns include:
   - `name`, `type`, `__opt_score`, `__opt_method`
   - selected stats
   - `Norm: <stat>` contribution columns when present.
8. Enable `Use max weight constraint`, set a low value, verify candidate count/ranking changes.
9. Confirm histogram view defaults to `Interactive (click-to-set)`; switch to `Classic` and back; check axis labels are fully visible.
10. Switch to `Full armor set` mode and verify five columns: Helm/Armor/Gauntlets/Greaves/Overall.
11. Verify `Overall` sums highlighted stats and shows aligned rows (phantom spacer in place of image).
12. Click `📥 Export <column> rows (CSV)` and verify the downloaded file reflects current rows.
13. Open `Why this is #1` and verify top-vs-#2 deltas are shown.
14. Click `Reset filters/stats` while in full armor set mode; ensure the mode stays unchanged.
