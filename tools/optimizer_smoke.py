"""Small smoke script for optimizer dialect + encounter survival.

Run:
    python -m tools.optimizer_smoke
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from optimizer import load_request, optimize
from ui_components import parse_armor_stats


def _load_armors() -> pd.DataFrame:
    repo_root = Path(__file__).resolve().parent.parent
    csv_path = repo_root / "data" / "armors.csv"
    df = pd.read_csv(csv_path)
    return parse_armor_stats(df)


def _run_profile(df: pd.DataFrame, profile_path: Path) -> None:
    request = load_request(profile_path)
    ranked = optimize(df, request)

    print(f"\n== {profile_path.stem} ==")
    keep = [col for col in ["name", "expected_taken_M", "status_penalty", "final_score_J", "__opt_rank"] if col in ranked.columns]
    print(ranked[keep].head(5).to_string(index=False))


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    profiles_dir = repo_root / "data" / "profiles"
    df = _load_armors()

    for profile_name in [
        "Katana_Slash_Bleed.yaml",
        "RayaLucaria_Mages.yaml",
        "Bayle_Phys_Fire_Lightning.yaml",
    ]:
        _run_profile(df, profiles_dir / profile_name)

    print("\noptimizer_smoke: SUCCESS")


if __name__ == "__main__":
    main()
