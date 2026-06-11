"""Simple risk-based fund recommender.

This module reads scheme performance data and selects the top funds by Sharpe ratio
for a given risk appetite. It is intentionally simple, transparent, and aligned with
Day 6 deliverables.
"""

from pathlib import Path
import argparse
import logging
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"

RISK_MAPPING = {
    "low": ["Low"],
    "moderate": ["Moderate", "Moderately High"],
    "high": ["High", "Very High"],
}


def load_scheme_performance():
    """Load the processed scheme performance dataset."""
    return pd.read_csv(PROCESSED_DIR / "07_scheme_performance_processed.csv")


def recommend_funds(risk_appetite: str, top_n: int = 3) -> pd.DataFrame:
    """Return top Sharpe-ranked funds matching a risk appetite."""
    appetite_key = risk_appetite.strip().lower()
    if appetite_key not in RISK_MAPPING:
        raise ValueError(f"Risk appetite must be one of {list(RISK_MAPPING)}")

    perf = load_scheme_performance()
    allowed_risks = RISK_MAPPING[appetite_key]
    candidates = perf[perf["risk_grade"].isin(allowed_risks)].copy()
    candidates = candidates.sort_values("sharpe_ratio", ascending=False)
    return candidates.head(top_n)[
        ["amfi_code", "scheme_name", "fund_house", "category", "plan", "risk_grade", "aum_crore", "sharpe_ratio"]
    ]


def main():
    """Run the CLI recommender and log a plain-text recommendation table."""
    parser = argparse.ArgumentParser(description="Recommend top funds by risk appetite.")
    parser.add_argument(
        "--risk",
        choices=["Low", "Moderate", "High"],
        default="Moderate",
        help="Investor risk appetite: Low, Moderate, or High.",
    )
    parser.add_argument("--top", type=int, default=3, help="Number of funds to recommend.")
    args = parser.parse_args()

    recommendations = recommend_funds(args.risk, top_n=args.top)
    if recommendations.empty:
        logging.info("No funds found for risk appetite '%s'.", args.risk)
        return

    logging.info(
        "Top %d recommendations for risk appetite '%s':\n%s",
        len(recommendations),
        args.risk,
        recommendations.to_string(index=False),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    main()
