"""Verify local stat icon assets referenced in data/icons/icons.json."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "icons" / "icons.json"


def main() -> int:
    if not REGISTRY.exists():
        print(f"[verify-icon-assets] Missing registry: {REGISTRY}")
        return 1

    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    icons = payload.get("icons", []) if isinstance(payload, dict) else []

    missing = []
    present = 0
    for row in icons:
        if not isinstance(row, dict):
            continue
        icon_id = str(row.get("icon_id", "")).strip() or "<unknown>"
        local_path = str(row.get("local_path", "")).strip()
        if not local_path:
            missing.append((icon_id, "<missing-local-path>"))
            continue
        abs_path = ROOT / local_path
        if abs_path.exists() and abs_path.is_file():
            present += 1
        else:
            missing.append((icon_id, local_path))

    total = present + len(missing)
    print(f"[verify-icon-assets] Present: {present}/{total}")
    if missing:
        print("[verify-icon-assets] Missing files:")
        for icon_id, path in missing:
            print(f"  - {icon_id}: {path}")
        return 2

    print("[verify-icon-assets] All icon assets are available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
