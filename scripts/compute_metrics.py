"""Compute metrics for reporting (placeholder).

Fill this file with functions to compute AUM growth, CAGR, volatility, Sharpe, Sortino,
and other performance metrics using the cleaned datasets in data/processed/.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"


def load_nav():
    return pd.read_csv(PROCESSED_DIR / "02_nav_history_processed.csv")


if __name__ == "__main__":
    df = load_nav()
    print("Loaded nav rows:", len(df))
