"""Compute metrics for reporting.

This module contains helper functions used by the pipeline to load
and compute performance metrics. It intentionally keeps a small API
so it can be reused from `run_pipeline.py` without side-effects.
"""

from pathlib import Path
import logging
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"


def load_nav() -> pd.DataFrame:
    """Load cleaned NAV history for downstream metrics.

    Returns:
        pd.DataFrame: NAV history with at least columns ``amfi_code``, ``date``, ``nav``.
    """
    return pd.read_csv(PROCESSED_DIR / "02_nav_history_processed.csv")


def _cli_check() -> None:
    """Small CLI helper to validate imports when executed directly."""
    df = load_nav()
    logging.info("Loaded nav rows: %d", len(df))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _cli_check()
