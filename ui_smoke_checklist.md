# UI Smoke Checklist

Use this quick checklist after running `streamlit run app.py`.

1. Select `armors` dataset and `Single piece` mode.
2. Pick 2+ highlighted stats including `weight`.
3. Confirm info note appears: weight minimized, others maximized.
4. Toggle sort between Highest/Lowest and verify order reverses.
5. Set `Rows to show` to 5 then 25 and verify card list count updates.
6. Enable `Show raw data table (dev view)` and verify columns include:
   - `name`, `type`, `__opt_score`, `__opt_method`
   - selected stats
   - `Norm: <stat>` contribution columns when present.
7. Enable `Use max weight constraint`, set a low value, verify candidate count/ranking changes.
8. Click `📥 Export current ranked rows (CSV)` and verify downloaded file reflects current rows.
9. Open `Why this is #1` and verify top-vs-#2 deltas are shown.
10. Click `Reset filters/stats` and verify controls return to defaults.
