import importlib
import sys

from data_loader import DataLoader
from ui_components import parse_armor_stats

print("FINAL_CHECK: Starting import verification...")
errors = []

modules = ["pandas", "streamlit", "data_loader", "ui_components", "app"]

for m in modules:
    try:
        importlib.import_module(m)
        print(f"OK: imported {m}")
    except Exception as e:
        print(f"ERR: failed to import {m}: {e}")
        errors.append((m, str(e)))

dl = DataLoader(data_dir="data")
avail = dl.get_available_datasets()
print("Available datasets:", avail)
if avail:
    path = f"data/{avail[0]}.csv"
    print("Trying to load", path)
    df = DataLoader.load_file(path)
    if df is None:
        print("WARN: file could not be loaded")
    else:
        try:
            df2 = parse_armor_stats(df)
            print("Parsed columns sample:", df2.columns.tolist()[:20])
        except Exception as e:
            print("ERR parsing stats:", e)
            errors.append(("parse", str(e)))

if errors:
    print("\nFINAL_CHECK: FAILED")
    for m, e in errors:
        print("-", m, ":", e)
    sys.exit(2)

print("\nFINAL_CHECK: SUCCESS")
