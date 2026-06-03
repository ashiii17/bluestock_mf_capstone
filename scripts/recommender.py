"""Recommender placeholder for fund suggestions.

This module will implement a simple rule-based recommender and later a content-based
or collaborative filtering approach using investor transactions and scheme performance.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"


def load_transactions():
    return pd.read_csv(PROCESSED_DIR / "08_investor_transactions_processed.csv")


if __name__ == "__main__":
    tx = load_transactions()
    print("Loaded transactions:", len(tx))
