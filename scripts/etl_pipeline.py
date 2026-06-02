from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DB_DIR = ROOT / "data" / "db"
DB_PATH = DB_DIR / "bluestock_mf.db"
REPORTS_DIR = ROOT / "reports"


DATE_COLUMNS = {
    "01_fund_master.csv": ["launch_date"],
    "02_nav_history.csv": ["date"],
    "03_aum_by_fund_house.csv": ["date"],
    "04_monthly_sip_inflows.csv": ["month"],
    "05_category_inflows.csv": ["month"],
    "06_industry_folio_count.csv": ["month"],
    "08_investor_transactions.csv": ["transaction_date"],
    "09_portfolio_holdings.csv": ["portfolio_date"],
    "10_benchmark_indices.csv": ["date"],
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def print_profile(name: str, df: pd.DataFrame) -> None:
    print(f"\n{'=' * 80}")
    print(name)
    print(f"shape: {df.shape}")
    print("\ndtypes:")
    print(df.dtypes)
    print("\nhead:")
    print(df.head())


def missing_summary(name: str, df: pd.DataFrame) -> list[str]:
    lines: list[str] = []
    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    if missing.empty:
        lines.append(f"- `{name}`: no missing values.")
        return lines

    cols = ", ".join(f"{col}={count}" for col, count in missing.items())
    lines.append(f"- `{name}`: missing values found: {cols}.")
    return lines


def duplicate_summary(name: str, df: pd.DataFrame) -> str:
    duplicates = int(df.duplicated().sum())
    return f"- `{name}`: {duplicates} fully duplicated rows."


def date_anomalies(name: str, df: pd.DataFrame) -> list[str]:
    lines: list[str] = []
    for column in DATE_COLUMNS.get(name, []):
        if column not in df.columns:
            lines.append(f"- `{name}`: expected date column `{column}` is missing.")
            continue
        parsed = pd.to_datetime(df[column], errors="coerce")
        invalid_count = int(parsed.isna().sum())
        min_date = parsed.min()
        max_date = parsed.max()
        lines.append(
            f"- `{name}` `{column}`: invalid={invalid_count}, "
            f"min={min_date.date() if pd.notna(min_date) else 'n/a'}, "
            f"max={max_date.date() if pd.notna(max_date) else 'n/a'}."
        )
    return lines


def numeric_anomalies(name: str, df: pd.DataFrame) -> list[str]:
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return [f"- `{name}`: no numeric columns to check."]

    negative_counts = {
        col: int((numeric[col] < 0).sum())
        for col in numeric.columns
        if int((numeric[col] < 0).sum()) > 0
    }
    if not negative_counts:
        return [f"- `{name}`: no negative values in numeric columns."]

    details = ", ".join(f"{col}={count}" for col, count in negative_counts.items())
    return [f"- `{name}`: negative numeric values found: {details}."]


def key_checks(datasets: dict[str, pd.DataFrame]) -> list[str]:
    lines: list[str] = ["## Key Validation"]
    master = datasets.get("01_fund_master.csv")
    nav = datasets.get("02_nav_history.csv")
    if master is None or nav is None:
        return lines + ["- Could not validate AMFI codes because master or NAV history is missing."]

    master_codes = set(master["amfi_code"].astype(str))
    nav_codes = set(nav["amfi_code"].astype(str))
    missing_in_nav = sorted(master_codes - nav_codes)
    extra_in_nav = sorted(nav_codes - master_codes)

    lines.append(f"- Fund master AMFI codes: {len(master_codes)} unique codes.")
    lines.append(f"- NAV history AMFI codes: {len(nav_codes)} unique codes.")
    lines.append(f"- Every fund master code exists in NAV history: {not missing_in_nav}.")
    if missing_in_nav:
        lines.append(f"- Missing in NAV history: {', '.join(missing_in_nav)}.")
    if extra_in_nav:
        lines.append(f"- NAV codes not in fund master: {', '.join(extra_in_nav)}.")

    duplicate_master_codes = int(master["amfi_code"].duplicated().sum())
    duplicate_nav_keys = int(nav.duplicated(subset=["amfi_code", "date"]).sum())
    lines.append(f"- Duplicate AMFI codes in fund master: {duplicate_master_codes}.")
    lines.append(f"- Duplicate `(amfi_code, date)` rows in NAV history: {duplicate_nav_keys}.")
    return lines


def fund_master_exploration(master: pd.DataFrame) -> list[str]:
    lines = ["## Fund Master Exploration"]
    for column in ["fund_house", "category", "sub_category", "risk_category"]:
        if column not in master.columns:
            lines.append(f"- `{column}` column missing.")
            continue
        values = sorted(master[column].dropna().astype(str).unique())
        lines.append(f"- Unique `{column}` values ({len(values)}): {', '.join(values)}.")

    if "amfi_code" in master.columns:
        code_lengths = master["amfi_code"].astype(str).str.len().value_counts().sort_index()
        code_parts = ", ".join(f"{length} digits={count}" for length, count in code_lengths.items())
        lines.append(f"- AMFI scheme codes in this extract are numeric identifiers: {code_parts}.")
        lines.append("- They function as scheme-level keys joining fund master, NAV history, performance, transactions, and holdings.")
    return lines


def write_report(datasets: dict[str, pd.DataFrame]) -> None:
    lines: list[str] = [
        "# Day 1 Data Quality Summary",
        "",
        "## Dataset Inventory",
    ]
    for name, df in datasets.items():
        lines.append(f"- `{name}`: {df.shape[0]:,} rows x {df.shape[1]:,} columns.")

    lines.extend(["", "## Missing Values"])
    for name, df in datasets.items():
        lines.extend(missing_summary(name, df))

    lines.extend(["", "## Duplicate Rows"])
    for name, df in datasets.items():
        lines.append(duplicate_summary(name, df))

    lines.extend(["", "## Date Checks"])
    for name, df in datasets.items():
        lines.extend(date_anomalies(name, df))

    lines.extend(["", "## Numeric Checks"])
    for name, df in datasets.items():
        lines.extend(numeric_anomalies(name, df))

    master = datasets.get("01_fund_master.csv")
    if master is not None:
        lines.extend([""])
        lines.extend(fund_master_exploration(master))

    lines.extend([""])
    lines.extend(key_checks(datasets))

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "day1_data_quality_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_processed_outputs(datasets: dict[str, pd.DataFrame]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in datasets.items():
        cleaned = df.copy()
        for column in DATE_COLUMNS.get(name, []):
            if column in cleaned.columns:
                cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")
        cleaned.to_csv(PROCESSED_DIR / name.replace(".csv", "_processed.csv"), index=False)


def table_name(csv_name: str) -> str:
    return csv_name.removesuffix(".csv")[3:]


def write_sqlite_database(datasets: dict[str, pd.DataFrame]) -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        for name, df in datasets.items():
            df.to_sql(table_name(name), connection, if_exists="replace", index=False)


def main() -> None:
    csv_paths = sorted(path for path in RAW_DIR.glob("*.csv") if path.name[:2].isdigit())
    if not csv_paths:
        raise FileNotFoundError(f"No provided CSV files found in {RAW_DIR}")

    datasets: dict[str, pd.DataFrame] = {}
    for path in csv_paths:
        df = read_csv(path)
        datasets[path.name] = df
        print_profile(path.name, df)

    write_report(datasets)
    write_processed_outputs(datasets)
    write_sqlite_database(datasets)
    print(f"\nWrote report: {REPORTS_DIR / 'day1_data_quality_summary.md'}")
    print(f"Wrote processed CSVs to: {PROCESSED_DIR}")
    print(f"Wrote SQLite database: {DB_PATH}")


if __name__ == "__main__":
    main()
