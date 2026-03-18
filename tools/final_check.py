import contextlib
import importlib
import io
import logging
import sys

from data_loader import DataLoader
from ui_components import parse_armor_stats

logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.caching.cache_data_api").disabled = True


def _run_quietly(callback):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        return callback()


def run_checks(include_app_import: bool = True, include_data_probe: bool = True) -> int:
    print("FINAL_CHECK: Starting import verification...")
    errors = []

    modules = ["pandas", "streamlit", "data_loader", "ui_components"]
    if include_app_import:
        modules.append("app")

    for module_name in modules:
        try:
            _run_quietly(lambda: importlib.import_module(module_name))
            print(f"OK: imported {module_name}")
        except Exception as exc:
            print(f"ERR: failed to import {module_name}: {exc}")
            errors.append((module_name, str(exc)))

    if include_data_probe:
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
                    parsed = _run_quietly(lambda: parse_armor_stats(df))
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
