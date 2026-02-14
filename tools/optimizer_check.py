"""Lightweight verification for two-stat optimizer behavior.

Run:
  python optimizer_check.py
"""

import pandas as pd

from optimizer import optimize_single_piece


def run_checks() -> None:
    df = pd.DataFrame(
        [
            {"name": "A", "poise": 20, "Res: Fir": 10},
            {"name": "B", "poise": 15, "Res: Fir": 15},
            {"name": "C", "poise": 10, "Res: Fir": 20},
            {"name": "D", "poise": 5, "Res: Fir": 5},
        ]
    )

    ranked = optimize_single_piece(df, ["poise", "Res: Fir"])
    assert not ranked.empty, "Expected non-empty ranking output"
    assert "__opt_score" in ranked.columns, "Missing optimization score column"
    assert "__opt_rank" in ranked.columns, "Missing rank column"

    top_name = str(ranked.iloc[0]["name"])
    assert top_name == "B", (
        "Expected balanced item 'B' to rank first under maximin_normalized "
        f"but got '{top_name}'"
    )

    df_weight = pd.DataFrame(
        [
            {"name": "LightGood", "weight": 4, "Res: Fir": 13},
            {"name": "HeavyGood", "weight": 12, "Res: Fir": 15},
            {"name": "Medium", "weight": 8, "Res: Fir": 14},
        ]
    )
    ranked_weight = optimize_single_piece(df_weight, ["weight", "Res: Fir"])
    top_weight_name = str(ranked_weight.iloc[0]["name"])
    assert top_weight_name == "Medium", (
        "Expected 'Medium' to rank first when weight is minimized and resistance "
        f"maximized, but got '{top_weight_name}'"
    )

    ranked_weighted = optimize_single_piece(
        df_weight,
        ["weight", "Res: Fir"],
        method="weighted_sum_normalized",
        config={"weights": {"weight": 1.0, "Res: Fir": 2.0}},
    )
    assert "__opt_method" in ranked_weighted.columns, "Missing method metadata"
    assert str(ranked_weighted.iloc[0]["__opt_method"]) == "weighted_sum_normalized"

    print("optimizer_check: SUCCESS")


if __name__ == "__main__":
    run_checks()
