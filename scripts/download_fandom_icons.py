"""Download icon assets from Fandom file-page links listed in data/icons/icons.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import requests


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "icons" / "icons.json"
FANDOM_API = "https://eldenring.fandom.com/api.php"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def extract_file_title(source_url: str) -> str | None:
    token = str(source_url or "").strip()
    if not token:
        return None
    match = re.search(r"/wiki/File:([^?#]+)", token)
    if not match:
        return None
    return unquote(match.group(1)).strip()


def resolve_image_url(file_title: str) -> str | None:
    params = {
        "action": "query",
        "titles": f"File:{file_title}",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
    }
    response = requests.get(FANDOM_API, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    pages = ((payload.get("query") or {}).get("pages") or {})
    for page in pages.values():
        imageinfo = page.get("imageinfo") if isinstance(page, dict) else None
        if isinstance(imageinfo, list) and imageinfo:
            url = str(imageinfo[0].get("url", "")).strip()
            if url:
                return url
    return None


def main() -> int:
    if not REGISTRY_PATH.exists():
        print(f"[download-fandom-icons] Missing registry: {REGISTRY_PATH}")
        return 1

    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    icons = payload.get("icons", []) if isinstance(payload, dict) else []

    downloaded = 0
    skipped = 0
    errors = 0

    for row in icons:
        if not isinstance(row, dict):
            continue
        icon_id = str(row.get("icon_id", "")).strip() or "<unknown>"
        source_url = str(row.get("source_url", "")).strip()
        local_path = str(row.get("local_path", "")).strip()

        if "eldenring.fandom.com/wiki/File:" not in source_url or not local_path:
            skipped += 1
            continue

        file_title = extract_file_title(source_url)
        if not file_title:
            print(f"[download-fandom-icons] skip {icon_id}: cannot parse file title")
            skipped += 1
            continue

        try:
            image_url = resolve_image_url(file_title)
            if not image_url:
                print(f"[download-fandom-icons] fail {icon_id}: no image url for {file_title}")
                errors += 1
                continue

            image_resp = requests.get(image_url, headers=HEADERS, timeout=30)
            image_resp.raise_for_status()

            target = ROOT / local_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(image_resp.content)
            content_type = str(image_resp.headers.get("Content-Type", "")).strip() or "unknown"
            print(f"[download-fandom-icons] ok {icon_id}: {target} ({content_type}, {len(image_resp.content)} bytes)")
            downloaded += 1
        except Exception as exc:
            print(f"[download-fandom-icons] fail {icon_id}: {exc}")
            errors += 1

    print(f"[download-fandom-icons] downloaded={downloaded} skipped={skipped} errors={errors}")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
