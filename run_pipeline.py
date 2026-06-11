"""Master execution script for the Bluestock Mutual Fund capstone.

Runs the cleaned ETL, performance analytics, and advanced analytics in
the same order used for final submission. Optional steps are exposed as
flags because live NAV fetching needs network access and dashboard image
export may require Plotly/Kaleido browser support.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache" / "matplotlib"))

from scripts import day6_advanced_analytics
from scripts import etl_pipeline
from scripts import performance_analytics


def parse_args() -> argparse.Namespace:
    """Parse command-line options for the master pipeline."""
    parser = argparse.ArgumentParser(description="Run the Bluestock MF capstone pipeline end to end.")
    parser.add_argument("--skip-etl", action="store_true", help="Skip Day 1/2 ETL and reuse existing processed data.")
    parser.add_argument("--skip-performance", action="store_true", help="Skip performance analytics outputs.")
    parser.add_argument("--skip-advanced", action="store_true", help="Skip advanced analytics and bonus outputs.")
    parser.add_argument("--fetch-live-nav", action="store_true", help="Fetch latest live NAV snapshots from mfapi.in.")
    parser.add_argument("--dashboard-images", action="store_true", help="Generate static dashboard image/PDF exports.")
    return parser.parse_args()


def main() -> None:
    """Run selected pipeline stages in dependency order."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    if args.fetch_live_nav:
        from scripts import live_nav_fetch

        logging.info("Fetching live NAV snapshots")
        live_nav_fetch.main()

    if not args.skip_etl:
        logging.info("Running ETL")
        etl_pipeline.run_day1()
        etl_pipeline.run_day2()

    if not args.skip_performance:
        logging.info("Running performance analytics")
        performance_analytics.main()

    if not args.skip_advanced:
        logging.info("Running advanced analytics and bonus outputs")
        day6_advanced_analytics.main()

    if args.dashboard_images:
        from scripts import create_dashboard_images

        logging.info("Generating dashboard image exports")
        create_dashboard_images.main()

    logging.info("Pipeline complete")


if __name__ == "__main__":
    main()
