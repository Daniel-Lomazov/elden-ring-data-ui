"""
Data loading module for Elden Ring datasets.
Handles loading CSV files from the data directory.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional
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
    def load_file(filepath: str) -> Optional[pd.DataFrame]:
        """Load a single CSV file with caching."""
        try:
            df = pd.read_csv(filepath)
            return df
        except FileNotFoundError:
            return None
        except Exception as e:
            st.error(f"Error loading {filepath}: {e}")
            return None

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
