"""Small smoke script for optimizer dialect + encounter survival.

Run:
    python -m tools.optimizer_smoke
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from optimizer import load_request, optimize, optimize_single_piece
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


def _run_stat_rank_sanity_checks() -> None:
    df = pd.DataFrame(
        [
            {"name": "A", "poise": 20, "Res: Fir": 10, "weight": 6},
            {"name": "B", "poise": 15, "Res: Fir": 15, "weight": 8},
            {"name": "C", "poise": 10, "Res: Fir": 20, "weight": 4},
        ]
    )

    legacy_request = {
        "version": 1,
        "engine": "legacy",
        "scope": "single_piece",
        "objective": {
            "type": "stat_rank",
            "method": "weighted_sum_normalized",
            "weights": {"poise": 2.0, "Res: Fir": 1.0, "weight": 0.0},
        },
        "selected_stats": ["poise", "Res: Fir", "weight"],
        "config": {"minimize_stats": ["weight"]},
    }
    advanced_request = dict(legacy_request, engine="advanced")

    legacy_ranked = optimize(df, legacy_request)
    advanced_ranked = optimize(df, advanced_request)

    assert legacy_ranked["name"].tolist() == advanced_ranked["name"].tolist()
    assert legacy_ranked["__opt_tiebreak"].tolist() == advanced_ranked["__opt_tiebreak"].tolist()

    collapsed = optimize_single_piece(
        df,
        ["poise", "Res: Fir"],
        method="weighted_sum_normalized",
        config={"weights": {"poise": 1.0, "Res: Fir": 0.0}},
    )
    assert str(collapsed.iloc[0]["name"]) == "A"


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    profiles_dir = repo_root / "data" / "profiles"
    df = _load_armors()

    _run_stat_rank_sanity_checks()

    for profile_name in [
        "Katana_Slash_Bleed.yaml",
        "RayaLucaria_Mages.yaml",
        "Bayle_Phys_Fire_Lightning.yaml",
    ]:
        _run_profile(df, profiles_dir / profile_name)

    print("\noptimizer_smoke: SUCCESS")


if __name__ == "__main__":
    main()
