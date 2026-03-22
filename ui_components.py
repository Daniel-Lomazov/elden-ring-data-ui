"""Parsing helpers shared by the Streamlit UI."""

from __future__ import annotations

import ast
import re

import pandas as pd


def parse_armor_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Parse armor negation/resistance dictionaries into numeric columns."""
    df = df.copy()

    def normalize_key(value: str) -> str:
        if not isinstance(value, str):
            return str(value)
        return re.sub(r"[^0-9a-zA-Z]+", " ", value).strip().lower()

    def alias_keys(*aliases: str) -> list[str]:
        return [normalize_key(alias) for alias in aliases if str(alias).strip()]

    def dict_to_normalized(source: dict) -> dict:
        out = {}
        if not isinstance(source, dict):
            return out
        for key, value in source.items():
            normalized_key = normalize_key(key)
            try:
                out[normalized_key] = float(value)
            except Exception:
                try:
                    out[normalized_key] = float(str(value).replace(",", "."))
                except Exception:
                    out[normalized_key] = 0.0
        return out

    def extract_dict(value):
        try:
            if isinstance(value, str):
                parsed = ast.literal_eval(value)
                if isinstance(parsed, list) and parsed:
                    parsed = parsed[0]
                if isinstance(parsed, dict):
                    return parsed
            return {}
        except Exception:
            return {}

    def first_value_for_aliases(normalized_dict: dict, aliases: list[str]) -> float:
        if not isinstance(normalized_dict, dict):
            return 0.0
        for alias in aliases:
            if alias in normalized_dict:
                return normalized_dict.get(alias, 0.0)
        return 0.0

    if "damage negation" in df.columns:
        dmg_norm = df["damage negation"].apply(extract_dict).apply(dict_to_normalized)
        damage_key_aliases = {
            "Phy": alias_keys("Phy", "Physical", "Standard"),
            "VS Str.": alias_keys("VS Str.", "VS Str", "VS Strike", "Strike"),
            "VS Sla.": alias_keys("VS Sla.", "VS Sla", "VS Slash", "Slash"),
            "VS Pie.": alias_keys("VS Pie.", "VS Pie", "VS Pierce", "Pierce"),
            "Mag": alias_keys("Mag", "Magic"),
            "Fir": alias_keys("Fir", "Fire"),
            "Lit": alias_keys("Lit", "Lightning"),
            "Hol": alias_keys("Hol", "Holy"),
        }
        for key, aliases in damage_key_aliases.items():
            df[f"Dmg: {key}"] = dmg_norm.apply(
                lambda normalized_dict, alias_list=aliases: first_value_for_aliases(
                    normalized_dict,
                    alias_list,
                )
            )

    if "resistance" in df.columns:
        res_norm = df["resistance"].apply(extract_dict).apply(dict_to_normalized)
        resistance_key_aliases = {
            "Imm.": alias_keys("Imm.", "Imm", "Immu.", "Immu", "Immunity"),
            "Rob.": alias_keys("Rob.", "Rob", "Robu.", "Robu", "Robust", "Robustness"),
            "Foc.": alias_keys("Foc.", "Foc", "Focus"),
            "Vit.": alias_keys("Vit.", "Vit", "Vita.", "Vita", "Vitality"),
            "Poi.": alias_keys("Poi.", "Poi", "Poise"),
        }
        for key, aliases in resistance_key_aliases.items():
            df[f"Res: {key}"] = res_norm.apply(
                lambda normalized_dict, alias_list=aliases: first_value_for_aliases(
                    normalized_dict,
                    alias_list,
                )
            )

        status_parent_map = {
            "status.poison": "Res: Imm.",
            "status.rot": "Res: Imm.",
            "status.bleed": "Res: Rob.",
            "status.frost": "Res: Rob.",
            "status.sleep": "Res: Foc.",
            "status.madness": "Res: Foc.",
            "status.death": "Res: Vit.",
        }
        for status_key, parent_col in status_parent_map.items():
            if parent_col in df.columns:
                df[status_key] = pd.to_numeric(df[parent_col], errors="coerce").fillna(0.0)
            else:
                df[status_key] = 0.0

    return df
