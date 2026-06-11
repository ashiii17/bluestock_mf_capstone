# Bluestock Mutual Fund Capstone

End-to-end analytics capstone for Indian mutual fund data. The project ingests raw AMFI-style datasets, cleans and validates them, builds a SQLite star schema, computes fund performance and risk metrics, adds advanced investor analytics, and publishes outputs for a Tableau dashboard, final report, and presentation.

## Project Structure

```text
bluestock_mf_capstone/
├── data/
│   ├── raw/          original source CSVs and live NAV snapshots
│   ├── processed/    cleaned, analysis-ready CSVs
│   └── db/           local SQLite build output; ignored by Git
├── notebooks/        analysis notebooks for each project day
├── scripts/          reusable ETL and analytics scripts
├── sql/              schema.sql and analytical queries.sql
├── dashboard/        Tableau workbook
├── reports/          final report, presentation, charts, and analytics outputs
├── run_pipeline.py   master execution script
└── README.md
```

## Setup

Use Python 3.10+ from the project root.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional dashboard image export uses Plotly static rendering. If `python run_pipeline.py --dashboard-images` fails because Kaleido/Chrome is unavailable, open the Tableau workbook directly from `dashboard/bluestock_mf_dashboard.twb`.

## Run The ETL And Analytics

Run the full local pipeline:

```bash
python run_pipeline.py
```

Optional stages:

```bash
python run_pipeline.py --fetch-live-nav
python run_pipeline.py --dashboard-images
python run_pipeline.py --skip-etl
```

The master script runs:

- Day 1 raw data quality profiling and summary report.
- Day 2 cleaning, weekend/holiday NAV forward-fill, processed CSV export, `schema.sql`, `queries.sql`, `data_dictionary.md`, and local SQLite warehouse creation.
- Performance analytics with CAGR annualized using `252 / n_trading_days`, Sharpe, Sortino, alpha, beta, max drawdown, and scorecard outputs.
- Advanced analytics with VaR/CVaR, rolling Sharpe, investor cohorts, SIP continuity, HHI concentration, Monte Carlo NAV projections, and Markowitz efficient frontier optimization.

## Dashboard

Local workbook:

```text
dashboard/bluestock_mf_dashboard.twb
```

Open it with Tableau Desktop or Tableau Public Desktop and point it to the CSVs in `data/processed/`. The dashboard workbook is designed around interactive Tableau filters/slicers for time period, fund house, category, scheme, and investor attributes.

Tableau Public dashboard URLs:

- Dashboard 1: https://public.tableau.com/app/profile/ashi.dwivedi/viz/bluestock_mf_dashboard_17812008151090/Dashboard1?publish=yes
- Dashboard 2: https://public.tableau.com/app/profile/ashi.dwivedi/viz/bluestock_mf_dashboard_17812008151090/Dashboard2?publish=yes
- Dashboard 3: https://public.tableau.com/app/profile/ashi.dwivedi/viz/bluestock_mf_dashboard_17812008151090/Dashboard3?publish=yes
- Dashboard 4: https://public.tableau.com/app/profile/ashi.dwivedi/viz/bluestock_mf_dashboard_17812008151090/Dashboard4?publish=yes

## Datasets

Raw and processed numbered datasets:

- `01_fund_master.csv` - scheme master, fund house, category, plan, benchmark, expense ratio, launch date, risk category, and manager metadata.
- `02_nav_history.csv` - scheme-level NAV history. The cleaned version reindexes each AMFI code to a complete daily range and forward-fills missing NAV values for weekends/holidays.
- `03_aum_by_fund_house.csv` - AMC-level AUM with explicit `aum_lakh_crore` and `aum_crore` units.
- `04_monthly_sip_inflows.csv` - monthly SIP inflows, SIP account counts, SIP AUM, and YoY growth.
- `05_category_inflows.csv` - monthly net inflows by category.
- `06_industry_folio_count.csv` - industry folio counts by broad category.
- `07_scheme_performance.csv` - scheme returns, benchmark return, alpha, beta, Sharpe, Sortino, volatility, drawdown, AUM, expense ratio, and ratings.
- `08_investor_transactions.csv` - anonymized transaction-level investor activity with geography, age, gender, income, payment mode, and KYC status.
- `09_portfolio_holdings.csv` - scheme holdings by stock, sector, weight, market value, and portfolio date.
- `10_benchmark_indices.csv` - benchmark index close values used for comparisons and alpha/beta.

## Key Outputs

- `sql/schema.sql` - SQLite star schema DDL.
- `sql/queries.sql` - 10 analytical SQL queries.
- `data_dictionary.md` - cleaned dataset dictionary.
- `reports/day1_data_quality_summary.md` - data quality summary.
- `reports/performance/fund_scorecard.csv` - ranked fund scorecard.
- `reports/performance/monte_carlo_nav_projection.csv` and `.png` - B3 bonus output.
- `reports/performance/markowitz_efficient_frontier.csv` and `.png` - B4 bonus output.
- `reports/Final_Report.pdf` - final report deliverable.
- `reports/Bluestock_MF_Presentation.pptx` - final presentation deliverable.

## Self-Review Checklist

- 8 project objectives: met through ingestion, cleaning, SQL warehouse, EDA, performance analytics, dashboard, advanced analytics, and final reporting.
- 7 deliverables: submitted as raw/processed data, SQL schema/queries, notebooks/scripts, dashboard workbook, final report, presentation, and clean GitHub repo with README/tag.
- Code runs without errors: `python run_pipeline.py` completed successfully locally.
- Dashboard loads: Tableau workbook exists at `dashboard/bluestock_mf_dashboard.twb` and the four Tableau Public dashboard URLs are listed above.
- Report quality: `reports/Final_Report.pdf` is present for submission.
- Presentation quality: `reports/Bluestock_MF_Presentation.pptx` is present for submission.
- No hard-coded local paths in scripts: paths are derived from `pathlib.Path(__file__).resolve()`.
- No `.db` files committed: `*.db` is ignored and the generated SQLite database is removed from Git tracking.
