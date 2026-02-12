"""Compute SHA256 checksums for files under data/ and create a timestamped ZIP backup.

Outputs:
- data_checksums.txt  (tab-separated: SHA256\tsize\tmtime\tpath)
- data_checksums.json (structured manifest)
- data_backup_YYYYmmdd_HHMMSS.zip (contains data/)

Run: python secure_data.py
"""

import hashlib
import json
import os
import shutil
import stat
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DATA_DIR = ROOT / "data"
OUT_CHECK_TXT = ROOT / "data_checksums.txt"
OUT_CHECK_JSON = ROOT / "data_checksums.json"
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_ZIP = ROOT / f"data_backup_{TS}.zip"


def sha256_of_file(p: Path, buf_size: int = 65536) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(buf_size), b""):
            h.update(chunk)
    return h.hexdigest()


if not DATA_DIR.exists():
    print("No data/ folder found at", DATA_DIR)
    raise SystemExit(1)

manifest = []
print("Scanning files under", DATA_DIR)
for root, dirs, files in os.walk(DATA_DIR):
    for fn in files:
        fp = Path(root) / fn
        rel = fp.relative_to(ROOT)
        try:
            sha = sha256_of_file(fp)
            st = fp.stat()
            item = {
                "path": str(rel).replace("\\", "/"),
                "sha256": sha,
                "size": st.st_size,
                "mtime": int(st.st_mtime),
            }
            manifest.append(item)
            print("OK", item["path"], item["sha256"][:8], "size=", item["size"])
        except Exception as e:
            print("ERR", fp, e)

# write textual manifest
with OUT_CHECK_TXT.open("w", encoding="utf-8") as f:
    for it in manifest:
        f.write(f"{it['sha256']}\t{it['size']}\t{it['mtime']}\t{it['path']}\n")

# write structured manifest
with OUT_CHECK_JSON.open("w", encoding="utf-8") as f:
    json.dump({"generated": TS, "files": manifest}, f, indent=2)

# create zip archive
print("Creating zip backup at", OUT_ZIP.name)
shutil.make_archive(str(OUT_ZIP.with_suffix("")), "zip", root_dir=ROOT, base_dir="data")

# make the zip read-only
try:
    OUT_ZIP.chmod(stat.S_IREAD)
    print("Set read-only attribute on", OUT_ZIP.name)
except Exception:
    print("Could not change file permissions on", OUT_ZIP.name)

print("\nWrote:", OUT_CHECK_TXT.name, OUT_CHECK_JSON.name, OUT_ZIP.name)
