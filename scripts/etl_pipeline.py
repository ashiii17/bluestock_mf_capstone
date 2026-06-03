from __future__ import annotations

from pathlib import Path
import sqlite3
import argparse
from sqlalchemy import create_engine, text

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


TRANSACTION_TYPE_MAP = {
    "sip": "SIP",
    "sips": "SIP",
    "lumpsum": "Lumpsum",
    "lump sum": "Lumpsum",
    "lump-sum": "Lumpsum",
    "redemption": "Redemption",
    "redeem": "Redemption",
}

ALLOWED_KYC_STATUS = {"Verified", "Pending", "Rejected", "Not Submitted"}

SCHEMA_FILE = ROOT / "sql" / "schema.sql"
QUERIES_FILE = ROOT / "sql" / "queries.sql"
DICTIONARY_FILE = ROOT / "data_dictionary.md"

SCHEMA_SQL = """-- Star schema for Day 2 data warehouse

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_date (
    date_id INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day INTEGER NOT NULL,
    weekday TEXT NOT NULL,
    is_weekend INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code INTEGER PRIMARY KEY,
    scheme_name TEXT,
    fund_house TEXT,
    category TEXT,
    sub_category TEXT,
    plan TEXT,
    benchmark TEXT,
    launch_date TEXT,
    expense_ratio_pct REAL,
    exit_load_pct REAL,
    min_sip_amount REAL,
    min_lumpsum_amount REAL,
    fund_manager TEXT,
    risk_category TEXT,
    sebi_category_code TEXT
);

CREATE TABLE IF NOT EXISTS fact_nav (
    nav_id INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code INTEGER NOT NULL,
    date_id INTEGER NOT NULL,
    nav REAL NOT NULL,
    FOREIGN KEY(amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY(date_id) REFERENCES dim_date(date_id)
);

CREATE TABLE IF NOT EXISTS fact_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id TEXT,
    amfi_code INTEGER NOT NULL,
    date_id INTEGER NOT NULL,
    transaction_type TEXT,
    amount_inr REAL,
    state TEXT,
    city TEXT,
    city_tier TEXT,
    age_group TEXT,
    gender TEXT,
    annual_income_lakh REAL,
    payment_mode TEXT,
    kyc_status TEXT,
    FOREIGN KEY(amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY(date_id) REFERENCES dim_date(date_id)
);

CREATE TABLE IF NOT EXISTS fact_performance (
    performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code INTEGER NOT NULL,
    return_1yr_pct REAL,
    return_3yr_pct REAL,
    return_5yr_pct REAL,
    benchmark_3yr_pct REAL,
    alpha REAL,
    beta REAL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    std_dev_ann_pct REAL,
    max_drawdown_pct REAL,
    aum_crore REAL,
    expense_ratio_pct REAL,
    morningstar_rating INTEGER,
    risk_grade TEXT,
    FOREIGN KEY(amfi_code) REFERENCES dim_fund(amfi_code)
);

CREATE TABLE IF NOT EXISTS fact_aum (
    aum_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id INTEGER NOT NULL,
    fund_house TEXT,
    aum_lakh_crore REAL,
    aum_crore REAL,
    num_schemes INTEGER,
    FOREIGN KEY(date_id) REFERENCES dim_date(date_id)
);
"""

QUERIES_SQL = """-- Analytical queries for Day 2

-- 1. Top 5 funds by scheme-level AUM
SELECT f.scheme_name,
       f.fund_house,
       p.aum_crore
FROM fact_performance AS p
JOIN dim_fund AS f USING (amfi_code)
ORDER BY p.aum_crore DESC
LIMIT 5;

-- 2. Average NAV per month across all schemes
SELECT d.year,
       d.month,
       ROUND(AVG(n.nav), 4) AS avg_monthly_nav,
       COUNT(*) AS observations
FROM fact_nav AS n
JOIN dim_date AS d USING (date_id)
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 3. SIP YoY growth in transaction amount
WITH yearly_sip AS (
    SELECT d.year,
           SUM(t.amount_inr) AS sip_amount
    FROM fact_transactions AS t
    JOIN dim_date AS d USING (date_id)
    WHERE t.transaction_type = 'SIP'
    GROUP BY d.year
)
SELECT y.year,
       y.sip_amount,
       y.sip_amount - LAG(y.sip_amount) OVER (ORDER BY y.year) AS amount_change,
       CASE WHEN LAG(y.sip_amount) OVER (ORDER BY y.year) IS NULL THEN NULL
            ELSE ROUND((y.sip_amount - LAG(y.sip_amount) OVER (ORDER BY y.year)) / NULLIF(LAG(y.sip_amount) OVER (ORDER BY y.year), 0) * 100, 2)
       END AS pct_growth
FROM yearly_sip AS y
ORDER BY y.year;

-- 4. Transactions by state, sorted by transaction volume
SELECT t.state,
       COUNT(*) AS transactions,
       SUM(t.amount_inr) AS total_amount
FROM fact_transactions AS t
GROUP BY t.state
ORDER BY total_amount DESC;

-- 5. Funds with expense ratio below 1%
SELECT f.scheme_name,
       f.fund_house,
       f.expense_ratio_pct
FROM dim_fund AS f
WHERE f.expense_ratio_pct < 1.0
ORDER BY f.expense_ratio_pct ASC;

-- 6. Top 10 funds by 5-year return
SELECT f.scheme_name,
       f.fund_house,
       p.return_5yr_pct
FROM fact_performance AS p
JOIN dim_fund AS f USING (amfi_code)
ORDER BY p.return_5yr_pct DESC
LIMIT 10;

-- 7. Average expense ratio by category
SELECT f.category,
       ROUND(AVG(f.expense_ratio_pct), 3) AS avg_expense_ratio
FROM dim_fund AS f
GROUP BY f.category
ORDER BY avg_expense_ratio ASC;

-- 8. Monthly redemption versus SIP amount
SELECT d.year,
       d.month,
       SUM(CASE WHEN t.transaction_type = 'SIP' THEN t.amount_inr ELSE 0 END) AS sip_amount,
       SUM(CASE WHEN t.transaction_type = 'Redemption' THEN t.amount_inr ELSE 0 END) AS redemption_amount
FROM fact_transactions AS t
JOIN dim_date AS d USING (date_id)
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 9. Funds with the largest number of investor transactions
SELECT f.scheme_name,
       f.fund_house,
       COUNT(t.transaction_id) AS transaction_count
FROM fact_transactions AS t
JOIN dim_fund AS f USING (amfi_code)
GROUP BY f.amfi_code
ORDER BY transaction_count DESC
LIMIT 10;

-- 10. Quarterly AUM by fund house
SELECT d.year,
       d.quarter,
       a.fund_house,
       SUM(a.aum_crore) AS total_aum_crore
FROM fact_aum AS a
JOIN dim_date AS d USING (date_id)
GROUP BY d.year, d.quarter, a.fund_house
ORDER BY d.year, d.quarter, total_aum_crore DESC;
"""


def write_processed_csv(name: str, df: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DIR / name.replace('.csv', '_processed.csv'), index=False)


def parse_date_column(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_datetime(df[column], errors='coerce').dt.date


def clean_nav_history(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['date'] = parse_date_column(df, 'date')
    df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
    df = df.sort_values(['amfi_code', 'date'])
    df = df.drop_duplicates(subset=['amfi_code', 'date'], keep='last')

    filled_frames: list[pd.DataFrame] = []
    for amfi_code, group in df.groupby('amfi_code', sort=False):
        group = group.set_index('date').sort_index()
        all_dates = pd.date_range(group.index.min(), group.index.max(), freq='D')
        group = group.reindex(all_dates)
        group['amfi_code'] = amfi_code
        group['nav'] = group['nav'].ffill()
        filled_frames.append(group.reset_index().rename(columns={'index': 'date'}))

    df = pd.concat(filled_frames, ignore_index=True)
    df = df[df['nav'] > 0]
    df = df.dropna(subset=['date'])
    return df


def clean_investor_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['transaction_date'] = parse_date_column(df, 'transaction_date')
    df['transaction_type'] = (
        df['transaction_type'].astype(str)
        .str.strip()
        .str.lower()
        .replace(TRANSACTION_TYPE_MAP)
    )
    df['transaction_type'] = df['transaction_type'].map(lambda x: x if x in TRANSACTION_TYPE_MAP.values() else x.title())
    df['amount_inr'] = pd.to_numeric(df['amount_inr'], errors='coerce')
    df['kyc_status'] = (
        df['kyc_status'].astype(str)
        .str.strip()
        .str.title()
    )
    df.loc[~df['kyc_status'].isin(ALLOWED_KYC_STATUS), 'kyc_status'] = 'Unknown'
    df = df[df['amount_inr'] > 0]
    return df


def clean_scheme_performance(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    numeric_columns = [
        'return_1yr_pct',
        'return_3yr_pct',
        'return_5yr_pct',
        'benchmark_3yr_pct',
        'alpha',
        'beta',
        'sharpe_ratio',
        'sortino_ratio',
        'std_dev_ann_pct',
        'max_drawdown_pct',
        'aum_crore',
        'expense_ratio_pct',
        'morningstar_rating',
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce')

    if 'expense_ratio_pct' in df.columns:
        out_of_range = df[~df['expense_ratio_pct'].between(0.1, 2.5, inclusive='both')]
        if not out_of_range.empty:
            print(f"Warning: {len(out_of_range)} scheme_performance rows have expense_ratio_pct outside 0.1-2.5% range")
    return df


def build_dim_date(min_date: pd.Timestamp, max_date: pd.Timestamp) -> pd.DataFrame:
    dates = pd.date_range(min_date, max_date, freq='D')
    df = pd.DataFrame({'date': dates})
    df['date_id'] = df['date'].dt.strftime('%Y%m%d').astype(int)
    df['year'] = df['date'].dt.year
    df['quarter'] = df['date'].dt.quarter
    df['month'] = df['date'].dt.month
    df['month_name'] = df['date'].dt.month_name()
    df['day'] = df['date'].dt.day
    df['weekday'] = df['date'].dt.day_name()
    df['is_weekend'] = df['date'].dt.weekday.isin([5, 6]).astype(int)
    return df[['date_id', 'date', 'year', 'quarter', 'month', 'month_name', 'day', 'weekday', 'is_weekend']]


def load_sqlite(df: pd.DataFrame, table_name: str, engine) -> None:
    df.to_sql(table_name, engine, if_exists='append', index=False)


def assign_date_id(df: pd.DataFrame, date_column: str, dim_date: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    date_map = dict(zip(dim_date['date'].dt.date, dim_date['date_id']))
    df['date_id'] = df[date_column].map(date_map)
    return df.drop(columns=[date_column])


def write_schema_file() -> None:
    SCHEMA_FILE.write_text(SCHEMA_SQL, encoding='utf-8')


def write_queries_file() -> None:
    QUERIES_FILE.write_text(QUERIES_SQL, encoding='utf-8')


def build_data_dictionary(datasets: dict[str, pd.DataFrame]) -> None:
    lines = [
        '# Bluestock Data Dictionary',
        '',
        'This data dictionary documents the cleaned Day 2 datasets, their column names, data types, business definitions, and source CSV references.',
        '',
    ]
    for name, df in datasets.items():
        lines.append(f'## {name.replace(".csv", "")}_processed.csv')
        lines.append('')
        lines.append('| Column | Type | Description | Source |')
        lines.append('|---|---|---|---|')
        for column, dtype in df.dtypes.items():
            dtype_name = str(dtype)
            description = 'Cleaned from raw source.'
            if column in DATE_COLUMNS.get(name, []):
                description = f'Date field parsed to ISO date; source column `{column}` in {name}.'
            if 'amfi_code' == column:
                description = 'Fund scheme identifier used as primary key and dimension join key.'
            if column in {'nav', 'amount_inr', 'expense_ratio_pct', 'aum_crore', 'return_1yr_pct', 'return_3yr_pct', 'return_5yr_pct'}:
                description = 'Numeric measure used for analytics and reporting.'
            lines.append(f'| {column} | {dtype_name} | {description} | {name} |')
        lines.append('')
    DICTIONARY_FILE.write_text('\n'.join(lines), encoding='utf-8')


def cleanup_processed_files() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for path in PROCESSED_DIR.glob('*_processed.csv'):
        if not (path.name[:2].isdigit() and path.name.endswith('_processed.csv')):
            path.unlink()



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


def run_day1() -> None:
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


def run_day2() -> None:
    csv_paths = sorted([path for path in RAW_DIR.glob('*.csv') if path.name[:2].isdigit()])
    if not csv_paths:
        raise FileNotFoundError(f'No numbered CSV files found in {RAW_DIR}')

    datasets: dict[str, pd.DataFrame] = {}
    for path in csv_paths:
        df = read_csv(path)
        name = path.name
        if name == '02_nav_history.csv':
            df = clean_nav_history(df)
        elif name == '08_investor_transactions.csv':
            df = clean_investor_transactions(df)
        elif name == '07_scheme_performance.csv':
            df = clean_scheme_performance(df)
        else:
            for column in DATE_COLUMNS.get(name, []):
                if column in df.columns:
                    df[column] = parse_date_column(df, column)
        datasets[name] = df
        write_processed_csv(name, df)
        print(f'Processed {name}: {df.shape[0]} rows, {df.shape[1]} columns')

    cleanup_processed_files()

    write_schema_file()
    write_queries_file()
    build_data_dictionary(datasets)

    all_dates = []
    for name, df in datasets.items():
        for column in DATE_COLUMNS.get(name, []):
            if column in df.columns:
                all_dates.extend(pd.to_datetime(df[column], errors='coerce').dropna().tolist())
    min_date = min(all_dates)
    max_date = max(all_dates)
    dim_date = build_dim_date(min_date, max_date)

    fund_master = datasets['01_fund_master.csv'].copy()
    if 'launch_date' in fund_master.columns:
        fund_master['launch_date'] = pd.to_datetime(fund_master['launch_date'], errors='coerce').dt.date

    DB_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    engine = create_engine(f'sqlite:///{DB_PATH}', future=True)

    with engine.begin() as conn:
        conn.execute(text('PRAGMA foreign_keys = ON'))
        conn.execute(text('DROP TABLE IF EXISTS fact_aum'))
        conn.execute(text('DROP TABLE IF EXISTS fact_performance'))
        conn.execute(text('DROP TABLE IF EXISTS fact_transactions'))
        conn.execute(text('DROP TABLE IF EXISTS fact_nav'))
        conn.execute(text('DROP TABLE IF EXISTS dim_fund'))
        conn.execute(text('DROP TABLE IF EXISTS dim_date'))

    raw_conn = engine.raw_connection()
    try:
        raw_conn.executescript(SCHEMA_SQL)
        raw_conn.commit()
    finally:
        raw_conn.close()

    load_sqlite(dim_date, 'dim_date', engine)
    load_sqlite(fund_master, 'dim_fund', engine)

    fact_nav = assign_date_id(datasets['02_nav_history.csv'], 'date', dim_date)
    load_sqlite(fact_nav, 'fact_nav', engine)

    fact_transactions = assign_date_id(datasets['08_investor_transactions.csv'], 'transaction_date', dim_date)
    load_sqlite(fact_transactions, 'fact_transactions', engine)

    fact_aum = assign_date_id(datasets['03_aum_by_fund_house.csv'], 'date', dim_date)
    load_sqlite(fact_aum, 'fact_aum', engine)

    performance_columns = [
        'amfi_code',
        'return_1yr_pct',
        'return_3yr_pct',
        'return_5yr_pct',
        'benchmark_3yr_pct',
        'alpha',
        'beta',
        'sharpe_ratio',
        'sortino_ratio',
        'std_dev_ann_pct',
        'max_drawdown_pct',
        'aum_crore',
        'expense_ratio_pct',
        'morningstar_rating',
        'risk_grade',
    ]
    fact_performance = datasets['07_scheme_performance.csv'][performance_columns]
    load_sqlite(fact_performance, 'fact_performance', engine)

    print(f'Wrote schema to {DB_DIR / "../sql" / "schema.sql"}')
    print(f'Wrote queries to {DB_DIR / "../sql" / "queries.sql"}')
    print(f'Wrote data dictionary to {DB_DIR / "../data_dictionary.md"}')
    print(f'Wrote SQLite database to {DB_PATH}')


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL runner: day1 data checks and day2 warehouse build")
    parser.add_argument("--mode", choices=("day1", "day2", "all"), default="all", help="Which part to run")
    args = parser.parse_args()

    if args.mode in ("day1", "all"):
        print("Running Day 1 data checks and outputs...")
        run_day1()
    if args.mode in ("day2", "all"):
        print("Running Day 2 cleaning, schema and DB load...")
        run_day2()


if __name__ == "__main__":
    main()
