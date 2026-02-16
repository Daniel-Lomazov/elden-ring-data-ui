"""Compute SHA256 checksums for files under data/ and create a timestamped ZIP backup.

Outputs:
- data_checksums.txt  (tab-separated: SHA256\tsize\tmtime\tpath)
- data_checksums.json (structured manifest)
- data_backup_YYYYmmdd_HHMMSS.zip (contains data/)

Run: python -m tools.secure_data
"""

import hashlib
import json
import os
import shutil
import stat
from datetime import datetime
from pathlib import Path


def sha256_of_file(path: Path, buf_size: int = 65536) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(buf_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run() -> int:
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data"
    out_check_txt = root / "data_checksums.txt"
    out_check_json = root / "data_checksums.json"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_zip = root / f"data_backup_{ts}.zip"

    if not data_dir.exists():
        print("No data/ folder found at", data_dir)
        return 1

    manifest = []
    print("Scanning files under", data_dir)
    for current_root, _dirs, files in os.walk(data_dir):
        for filename in files:
            file_path = Path(current_root) / filename
            rel = file_path.relative_to(root)
            try:
                sha = sha256_of_file(file_path)
                file_stat = file_path.stat()
                item = {
                    "path": str(rel).replace("\\", "/"),
                    "sha256": sha,
                    "size": file_stat.st_size,
                    "mtime": int(file_stat.st_mtime),
                }
                manifest.append(item)
                print("OK", item["path"], item["sha256"][:8], "size=", item["size"])
            except Exception as exc:
                print("ERR", file_path, exc)

    with out_check_txt.open("w", encoding="utf-8") as file_handle:
        for item in manifest:
            file_handle.write(
                f"{item['sha256']}\t{item['size']}\t{item['mtime']}\t{item['path']}\n"
            )

    with out_check_json.open("w", encoding="utf-8") as file_handle:
        json.dump({"generated": ts, "files": manifest}, file_handle, indent=2)

    print("Creating zip backup at", out_zip.name)
    shutil.make_archive(str(out_zip.with_suffix("")), "zip", root_dir=root, base_dir="data")

    try:
        out_zip.chmod(stat.S_IREAD)
        print("Set read-only attribute on", out_zip.name)
    except Exception:
        print("Could not change file permissions on", out_zip.name)

    print("\nWrote:", out_check_txt.name, out_check_json.name, out_zip.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
