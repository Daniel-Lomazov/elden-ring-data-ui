import importlib
import sys

from data_loader import DataLoader
from ui_components import parse_armor_stats


def run_checks() -> int:
    print("FINAL_CHECK: Starting import verification...")
    errors = []

    modules = ["pandas", "streamlit", "data_loader", "ui_components", "app"]

    for module_name in modules:
        try:
            importlib.import_module(module_name)
            print(f"OK: imported {module_name}")
        except Exception as exc:
            print(f"ERR: failed to import {module_name}: {exc}")
            errors.append((module_name, str(exc)))

    loader = DataLoader(data_dir="data")
    available = loader.get_available_datasets()
    print("Available datasets:", available)
    if available:
        path = f"data/{available[0]}.csv"
        print("Trying to load", path)
        df = DataLoader.load_file(path)
        if df is None:
            print("WARN: file could not be loaded")
        else:
            try:
                parsed = parse_armor_stats(df)
                print("Parsed columns sample:", parsed.columns.tolist()[:20])
            except Exception as exc:
                print("ERR parsing stats:", exc)
                errors.append(("parse", str(exc)))

    if errors:
        print("\nFINAL_CHECK: FAILED")
        for module_name, error_text in errors:
            print("-", module_name, ":", error_text)
        return 2

    print("\nFINAL_CHECK: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
