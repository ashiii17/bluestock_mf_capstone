# Bluestock MF Capstone

Day 1 covers project setup and data ingestion for the mutual fund analytics capstone.

## Structure

```text
bluestock_mf_capstone/
├── data/
│   ├── raw/          original downloaded files
│   ├── processed/    cleaned, processed CSVs
│   └── db/           bluestock_mf.db SQLite database
├── notebooks/
├── scripts/
├── sql/
├── dashboard/
├── reports/
└── README.md
```

## Day 1 Commands

```bash
/opt/anaconda3/bin/python scripts/etl_pipeline.py
/opt/anaconda3/bin/python scripts/live_nav_fetch.py
```

`scripts/etl_pipeline.py` prints `.shape`, `.dtypes`, and `.head()` for every raw CSV, writes processed CSVs, creates `data/db/bluestock_mf.db`, and writes `reports/day1_data_quality_summary.md`.

`scripts/live_nav_fetch.py` fetches live NAV data from mfapi.in and writes raw CSV snapshots in `data/raw/`.

## Day 2 Deliverables

Run the Day 2 ETL to clean datasets, build the star-schema SQLite DB, and generate SQL + documentation:

```bash
python scripts/day2_etl.py
```

Outputs produced by Day 2:

- `data/processed/` — 10 cleaned CSVs (numbered)
- `data/db/bluestock_mf.db` — star-schema SQLite database
- `sql/schema.sql` — CREATE TABLE DDL for `dim_*` and `fact_*` tables
- `sql/queries.sql` — 10 analytical SQL queries
- `data_dictionary.md` — data dictionary for cleaned files

Placeholders added for later steps:

- `scripts/compute_metrics.py` — metrics computation utilities
- `scripts/recommender.py` — fund recommender prototype
