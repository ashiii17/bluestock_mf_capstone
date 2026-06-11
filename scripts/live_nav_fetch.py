"""Fetch live NAVs for a small set of key schemes.

This utility hits the public MF API to fetch latest NAVs for a
handful of selected schemes and writes CSVs under ``data/raw``.
Designed to be run from the pipeline; it uses logging instead of
printing to stdout.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import logging
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
REPORTS_DIR = ROOT / "reports"
API_URL = "https://api.mfapi.in/mf/{scheme_code}"


SCHEMES = {
    "125497": "HDFC Top 100 Direct",
    "119551": "SBI Bluechip",
    "120503": "ICICI Bluechip",
    "118632": "Nippon Large Cap",
    "119092": "Axis Bluechip",
    "120841": "Kotak Bluechip",
}


def fetch_scheme_nav(scheme_code: str, scheme_label: str) -> pd.DataFrame:
    """Fetch NAV history for one MF API scheme and normalize response fields."""
    response = requests.get(API_URL.format(scheme_code=scheme_code), timeout=30)
    response.raise_for_status()
    payload = response.json()

    meta = payload.get("meta", {})
    rows = payload.get("data", [])
    if not rows:
        raise ValueError(f"No NAV rows returned for {scheme_code} ({scheme_label})")

    df = pd.DataFrame(rows)
    df["scheme_code"] = scheme_code
    df["requested_scheme_label"] = scheme_label
    df["scheme_name"] = meta.get("scheme_name")
    df["fund_house"] = meta.get("fund_house")
    df["scheme_category"] = meta.get("scheme_category")
    df["scheme_type"] = meta.get("scheme_type")
    df["fetched_at"] = datetime.now().isoformat(timespec="seconds")
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    return df


def write_summary(frames: list[pd.DataFrame]) -> None:
    """Write a short markdown summary of the latest fetched NAV per scheme."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Live NAV Fetch Summary", ""]
    for df in frames:
        latest = df.sort_values("date", ascending=False).iloc[0]
        lines.append(
            "- "
            f"{latest['scheme_code']} | {latest['requested_scheme_label']} | "
            f"latest_date={latest['date'].date()} | latest_nav={latest['nav']}"
        )
    (REPORTS_DIR / "live_nav_fetch_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Fetch selected live NAV histories and write raw CSV snapshots."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []

    for scheme_code, scheme_label in SCHEMES.items():
        df = fetch_scheme_nav(scheme_code, scheme_label)
        frames.append(df)
        output_path = RAW_DIR / f"live_nav_{scheme_code}.csv"
        df.to_csv(output_path, index=False)
        latest = df.sort_values("date", ascending=False).iloc[0]
        logging.info("%s %s: %d rows, latest NAV %s on %s", scheme_code, scheme_label, len(df), latest['nav'], latest['date'].date())

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(RAW_DIR / "live_nav_key_schemes.csv", index=False)
    write_summary(frames)
    logging.info("Wrote combined live NAV CSV: %s", RAW_DIR / 'live_nav_key_schemes.csv')
    logging.info("Wrote summary: %s", REPORTS_DIR / 'live_nav_fetch_summary.md')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
