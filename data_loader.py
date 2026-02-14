"""
Data loading module for Elden Ring datasets.
Handles loading CSV files from the data directory.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Sequence
import streamlit as st


class DataLoader:
    """Loads and caches Elden Ring data from CSV files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.root_files = [
            "armors.csv",
            "ashesOfWar.csv",
            "bosses.csv",
            "creatures.csv",
            "incantations.csv",
            "locations.csv",
            "npcs.csv",
            "shields.csv",
            "shields_upgrades.csv",
            "skills.csv",
            "sorceries.csv",
            "spiritAshes.csv",
            "talismans.csv",
            "weapons.csv",
            "weapons_upgrades.csv",
        ]
        self.item_files = [
            "ammos.csv",
            "bells.csv",
            "consumables.csv",
            "cookbooks.csv",
            "crystalTears.csv",
            "greatRunes.csv",
            "keyItems.csv",
            "materials.csv",
            "multi.csv",
            "remembrances.csv",
            "tools.csv",
            "upgradeMaterials.csv",
            "whetblades.csv",
        ]

    @staticmethod
    @st.cache_data
    def get_file_columns(filepath: str) -> list[str]:
        """Read only the CSV header and return available columns."""
        try:
            header_df = pd.read_csv(filepath, nrows=0)
            return [str(c) for c in header_df.columns]
        except Exception:
            return []

    @staticmethod
    def _sanitize_column_sequence(columns: Optional[Sequence[str]]) -> Optional[list[str]]:
        if columns is None:
            return None
        sanitized = [str(col) for col in columns if str(col).strip()]
        if not sanitized:
            return None
        deduped = list(dict.fromkeys(sanitized))
        return deduped

    @staticmethod
    def _resolve_usecols(
        filepath: str,
        include_columns: Optional[Sequence[str]],
        exclude_columns: Optional[Sequence[str]],
    ) -> Optional[list[str]]:
        include_clean = DataLoader._sanitize_column_sequence(include_columns)
        exclude_clean = set(
            DataLoader._sanitize_column_sequence(exclude_columns) or []
        )

        if include_clean is not None:
            if not exclude_clean:
                return include_clean
            return [col for col in include_clean if col not in exclude_clean]

        if exclude_clean:
            all_columns = DataLoader.get_file_columns(filepath)
            return [col for col in all_columns if col not in exclude_clean]

        return None

    @staticmethod
    @st.cache_data
    def load_file(
        filepath: str,
        include_columns: Optional[tuple[str, ...]] = None,
        exclude_columns: Optional[tuple[str, ...]] = None,
        dtype_overrides: Optional[dict] = None,
    ) -> Optional[pd.DataFrame]:
        """Load a single CSV file with caching and optional column pruning.

        Args:
            filepath: CSV path.
            include_columns: Optional whitelist of columns to load.
            exclude_columns: Optional blacklist of columns to skip.
            dtype_overrides: Optional pandas dtype mapping.

        Notes:
            - If both include/exclude are provided, include is applied first,
              then excluded columns are removed from that set.
            - By default (all optional args omitted), behavior is identical to
              previous implementation: load all columns.
        """
        try:
            usecols = DataLoader._resolve_usecols(
                filepath,
                include_columns=include_columns,
                exclude_columns=exclude_columns,
            )
            if usecols is not None and len(usecols) == 0:
                return pd.DataFrame()

            read_kwargs = {}
            if usecols is not None:
                read_kwargs["usecols"] = usecols
            if dtype_overrides:
                read_kwargs["dtype"] = dict(dtype_overrides)

            df = pd.read_csv(filepath, **read_kwargs)
            return df
        except FileNotFoundError:
            return None
        except ValueError:
            # Common failure mode: requested columns missing from file.
            return None
        except Exception as e:
            st.error(f"Error loading {filepath}: {e}")
            return None

    @staticmethod
    def drop_columns(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
        """Return a DataFrame without the specified columns (no-op if absent)."""
        if df is None or df.empty:
            return pd.DataFrame() if df is None else df
        drop_list = DataLoader._sanitize_column_sequence(columns) or []
        if not drop_list:
            return df
        return df.drop(columns=drop_list, errors="ignore")

    def load_all_datasets(self) -> Dict[str, pd.DataFrame]:
        """Load all available datasets."""
        datasets = {}

        # Load root files
        for filename in self.root_files:
            filepath = self.data_dir / filename
            if filepath.exists():
                df = DataLoader.load_file(str(filepath))
                if df is not None:
                    datasets[filename.replace(".csv", "")] = df

        # Load items files
        for filename in self.item_files:
            filepath = self.data_dir / "items" / filename
            if filepath.exists():
                df = DataLoader.load_file(str(filepath))
                if df is not None:
                    datasets[f"items/{filename.replace('.csv', '')}"] = df

        return datasets

    def get_available_datasets(self) -> list:
        """Get list of available dataset files."""
        available = []

        for filename in self.root_files:
            if (self.data_dir / filename).exists():
                available.append(filename.replace(".csv", ""))

        for filename in self.item_files:
            if (self.data_dir / "items" / filename).exists():
                available.append(f"items/{filename.replace('.csv', '')}")

        return sorted(available)
