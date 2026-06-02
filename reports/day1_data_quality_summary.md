# Day 1 Data Quality Summary

## Dataset Inventory
- `01_fund_master.csv`: 40 rows x 15 columns.
- `02_nav_history.csv`: 46,000 rows x 3 columns.
- `03_aum_by_fund_house.csv`: 90 rows x 5 columns.
- `04_monthly_sip_inflows.csv`: 48 rows x 6 columns.
- `05_category_inflows.csv`: 144 rows x 3 columns.
- `06_industry_folio_count.csv`: 21 rows x 6 columns.
- `07_scheme_performance.csv`: 40 rows x 19 columns.
- `08_investor_transactions.csv`: 32,778 rows x 13 columns.
- `09_portfolio_holdings.csv`: 322 rows x 8 columns.
- `10_benchmark_indices.csv`: 8,050 rows x 3 columns.

## Missing Values
- `01_fund_master.csv`: no missing values.
- `02_nav_history.csv`: no missing values.
- `03_aum_by_fund_house.csv`: no missing values.
- `04_monthly_sip_inflows.csv`: missing values found: yoy_growth_pct=12.
- `05_category_inflows.csv`: no missing values.
- `06_industry_folio_count.csv`: no missing values.
- `07_scheme_performance.csv`: no missing values.
- `08_investor_transactions.csv`: no missing values.
- `09_portfolio_holdings.csv`: no missing values.
- `10_benchmark_indices.csv`: no missing values.

## Duplicate Rows
- `01_fund_master.csv`: 0 fully duplicated rows.
- `02_nav_history.csv`: 0 fully duplicated rows.
- `03_aum_by_fund_house.csv`: 0 fully duplicated rows.
- `04_monthly_sip_inflows.csv`: 0 fully duplicated rows.
- `05_category_inflows.csv`: 0 fully duplicated rows.
- `06_industry_folio_count.csv`: 0 fully duplicated rows.
- `07_scheme_performance.csv`: 0 fully duplicated rows.
- `08_investor_transactions.csv`: 0 fully duplicated rows.
- `09_portfolio_holdings.csv`: 0 fully duplicated rows.
- `10_benchmark_indices.csv`: 0 fully duplicated rows.

## Date Checks
- `01_fund_master.csv` `launch_date`: invalid=0, min=1996-09-11, max=2015-12-28.
- `02_nav_history.csv` `date`: invalid=0, min=2022-01-03, max=2026-05-29.
- `03_aum_by_fund_house.csv` `date`: invalid=0, min=2022-03-31, max=2025-12-31.
- `04_monthly_sip_inflows.csv` `month`: invalid=0, min=2022-01-01, max=2025-12-01.
- `05_category_inflows.csv` `month`: invalid=0, min=2024-04-01, max=2025-03-01.
- `06_industry_folio_count.csv` `month`: invalid=0, min=2022-01-01, max=2025-12-01.
- `08_investor_transactions.csv` `transaction_date`: invalid=0, min=2024-01-01, max=2025-05-30.
- `09_portfolio_holdings.csv` `portfolio_date`: invalid=0, min=2025-12-31, max=2025-12-31.
- `10_benchmark_indices.csv` `date`: invalid=0, min=2022-01-03, max=2026-05-29.

## Numeric Checks
- `01_fund_master.csv`: no negative values in numeric columns.
- `02_nav_history.csv`: no negative values in numeric columns.
- `03_aum_by_fund_house.csv`: no negative values in numeric columns.
- `04_monthly_sip_inflows.csv`: no negative values in numeric columns.
- `05_category_inflows.csv`: no negative values in numeric columns.
- `06_industry_folio_count.csv`: no negative values in numeric columns.
- `07_scheme_performance.csv`: negative numeric values found: max_drawdown_pct=40.
- `08_investor_transactions.csv`: no negative values in numeric columns.
- `09_portfolio_holdings.csv`: no negative values in numeric columns.
- `10_benchmark_indices.csv`: no negative values in numeric columns.

## Fund Master Exploration
- Unique `fund_house` values (10): Aditya Birla Sun Life MF, Axis Mutual Fund, DSP Mutual Fund, HDFC Mutual Fund, ICICI Prudential MF, Kotak Mahindra MF, Mirae Asset MF, Nippon India MF, SBI Mutual Fund, UTI Mutual Fund.
- Unique `category` values (2): Debt, Equity.
- Unique `sub_category` values (12): ELSS, Flexi Cap, Gilt, Index, Index/ETF, Large & Mid Cap, Large Cap, Liquid, Mid Cap, Short Duration, Small Cap, Value.
- Unique `risk_category` values (5): High, Low, Moderate, Moderately High, Very High.
- AMFI scheme codes in this extract are numeric identifiers: 6 digits=40.
- They function as scheme-level keys joining fund master, NAV history, performance, transactions, and holdings.

## Key Validation
- Fund master AMFI codes: 40 unique codes.
- NAV history AMFI codes: 40 unique codes.
- Every fund master code exists in NAV history: True.
- Duplicate AMFI codes in fund master: 0.
- Duplicate `(amfi_code, date)` rows in NAV history: 0.
