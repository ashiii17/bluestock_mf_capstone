# Bluestock Data Dictionary

This data dictionary documents the cleaned Day 2 datasets, their column names, data types, business definitions, and source CSV references.

## 01_fund_master_processed.csv

| Column | Type | Description | Source |
|---|---|---|---|
| amfi_code | int64 | Fund scheme identifier used as primary key and dimension join key. | 01_fund_master.csv |
| fund_house | str | Cleaned from raw source. | 01_fund_master.csv |
| scheme_name | str | Cleaned from raw source. | 01_fund_master.csv |
| category | str | Cleaned from raw source. | 01_fund_master.csv |
| sub_category | str | Cleaned from raw source. | 01_fund_master.csv |
| plan | str | Cleaned from raw source. | 01_fund_master.csv |
| launch_date | object | Date field parsed to ISO date; source column `launch_date` in 01_fund_master.csv. | 01_fund_master.csv |
| benchmark | str | Cleaned from raw source. | 01_fund_master.csv |
| expense_ratio_pct | float64 | Numeric measure used for analytics and reporting. | 01_fund_master.csv |
| exit_load_pct | float64 | Cleaned from raw source. | 01_fund_master.csv |
| min_sip_amount | int64 | Cleaned from raw source. | 01_fund_master.csv |
| min_lumpsum_amount | int64 | Cleaned from raw source. | 01_fund_master.csv |
| fund_manager | str | Cleaned from raw source. | 01_fund_master.csv |
| risk_category | str | Cleaned from raw source. | 01_fund_master.csv |
| sebi_category_code | str | Cleaned from raw source. | 01_fund_master.csv |

## 02_nav_history_processed.csv

| Column | Type | Description | Source |
|---|---|---|---|
| date | datetime64[s] | Date field parsed to ISO date; source column `date` in 02_nav_history.csv. | 02_nav_history.csv |
| amfi_code | int64 | Fund scheme identifier used as primary key and dimension join key. | 02_nav_history.csv |
| nav | float64 | Numeric measure used for analytics and reporting. | 02_nav_history.csv |

## 03_aum_by_fund_house_processed.csv

| Column | Type | Description | Source |
|---|---|---|---|
| date | object | Date field parsed to ISO date; source column `date` in 03_aum_by_fund_house.csv. | 03_aum_by_fund_house.csv |
| fund_house | str | Cleaned from raw source. | 03_aum_by_fund_house.csv |
| aum_lakh_crore | float64 | Cleaned from raw source. | 03_aum_by_fund_house.csv |
| aum_crore | int64 | Numeric measure used for analytics and reporting. | 03_aum_by_fund_house.csv |
| num_schemes | int64 | Cleaned from raw source. | 03_aum_by_fund_house.csv |

## 04_monthly_sip_inflows_processed.csv

| Column | Type | Description | Source |
|---|---|---|---|
| month | object | Date field parsed to ISO date; source column `month` in 04_monthly_sip_inflows.csv. | 04_monthly_sip_inflows.csv |
| sip_inflow_crore | int64 | Cleaned from raw source. | 04_monthly_sip_inflows.csv |
| active_sip_accounts_crore | float64 | Cleaned from raw source. | 04_monthly_sip_inflows.csv |
| new_sip_accounts_lakh | float64 | Cleaned from raw source. | 04_monthly_sip_inflows.csv |
| sip_aum_lakh_crore | float64 | Cleaned from raw source. | 04_monthly_sip_inflows.csv |
| yoy_growth_pct | float64 | Cleaned from raw source. | 04_monthly_sip_inflows.csv |

## 05_category_inflows_processed.csv

| Column | Type | Description | Source |
|---|---|---|---|
| month | object | Date field parsed to ISO date; source column `month` in 05_category_inflows.csv. | 05_category_inflows.csv |
| category | str | Cleaned from raw source. | 05_category_inflows.csv |
| net_inflow_crore | float64 | Cleaned from raw source. | 05_category_inflows.csv |

## 06_industry_folio_count_processed.csv

| Column | Type | Description | Source |
|---|---|---|---|
| month | object | Date field parsed to ISO date; source column `month` in 06_industry_folio_count.csv. | 06_industry_folio_count.csv |
| total_folios_crore | float64 | Cleaned from raw source. | 06_industry_folio_count.csv |
| equity_folios_crore | float64 | Cleaned from raw source. | 06_industry_folio_count.csv |
| debt_folios_crore | float64 | Cleaned from raw source. | 06_industry_folio_count.csv |
| hybrid_folios_crore | float64 | Cleaned from raw source. | 06_industry_folio_count.csv |
| others_folios_crore | float64 | Cleaned from raw source. | 06_industry_folio_count.csv |

## 07_scheme_performance_processed.csv

| Column | Type | Description | Source |
|---|---|---|---|
| amfi_code | int64 | Fund scheme identifier used as primary key and dimension join key. | 07_scheme_performance.csv |
| scheme_name | str | Cleaned from raw source. | 07_scheme_performance.csv |
| fund_house | str | Cleaned from raw source. | 07_scheme_performance.csv |
| category | str | Cleaned from raw source. | 07_scheme_performance.csv |
| plan | str | Cleaned from raw source. | 07_scheme_performance.csv |
| return_1yr_pct | float64 | Numeric measure used for analytics and reporting. | 07_scheme_performance.csv |
| return_3yr_pct | float64 | Numeric measure used for analytics and reporting. | 07_scheme_performance.csv |
| return_5yr_pct | float64 | Numeric measure used for analytics and reporting. | 07_scheme_performance.csv |
| benchmark_3yr_pct | float64 | Cleaned from raw source. | 07_scheme_performance.csv |
| alpha | float64 | Cleaned from raw source. | 07_scheme_performance.csv |
| beta | float64 | Cleaned from raw source. | 07_scheme_performance.csv |
| sharpe_ratio | float64 | Cleaned from raw source. | 07_scheme_performance.csv |
| sortino_ratio | float64 | Cleaned from raw source. | 07_scheme_performance.csv |
| std_dev_ann_pct | float64 | Cleaned from raw source. | 07_scheme_performance.csv |
| max_drawdown_pct | float64 | Cleaned from raw source. | 07_scheme_performance.csv |
| aum_crore | int64 | Numeric measure used for analytics and reporting. | 07_scheme_performance.csv |
| expense_ratio_pct | float64 | Numeric measure used for analytics and reporting. | 07_scheme_performance.csv |
| morningstar_rating | int64 | Cleaned from raw source. | 07_scheme_performance.csv |
| risk_grade | str | Cleaned from raw source. | 07_scheme_performance.csv |

## 08_investor_transactions_processed.csv

| Column | Type | Description | Source |
|---|---|---|---|
| investor_id | str | Cleaned from raw source. | 08_investor_transactions.csv |
| transaction_date | object | Date field parsed to ISO date; source column `transaction_date` in 08_investor_transactions.csv. | 08_investor_transactions.csv |
| amfi_code | int64 | Fund scheme identifier used as primary key and dimension join key. | 08_investor_transactions.csv |
| transaction_type | str | Cleaned from raw source. | 08_investor_transactions.csv |
| amount_inr | int64 | Numeric measure used for analytics and reporting. | 08_investor_transactions.csv |
| state | str | Cleaned from raw source. | 08_investor_transactions.csv |
| city | str | Cleaned from raw source. | 08_investor_transactions.csv |
| city_tier | str | Cleaned from raw source. | 08_investor_transactions.csv |
| age_group | str | Cleaned from raw source. | 08_investor_transactions.csv |
| gender | str | Cleaned from raw source. | 08_investor_transactions.csv |
| annual_income_lakh | float64 | Cleaned from raw source. | 08_investor_transactions.csv |
| payment_mode | str | Cleaned from raw source. | 08_investor_transactions.csv |
| kyc_status | str | Cleaned from raw source. | 08_investor_transactions.csv |

## 09_portfolio_holdings_processed.csv

| Column | Type | Description | Source |
|---|---|---|---|
| amfi_code | int64 | Fund scheme identifier used as primary key and dimension join key. | 09_portfolio_holdings.csv |
| stock_symbol | str | Cleaned from raw source. | 09_portfolio_holdings.csv |
| stock_name | str | Cleaned from raw source. | 09_portfolio_holdings.csv |
| sector | str | Cleaned from raw source. | 09_portfolio_holdings.csv |
| weight_pct | float64 | Cleaned from raw source. | 09_portfolio_holdings.csv |
| market_value_cr | float64 | Cleaned from raw source. | 09_portfolio_holdings.csv |
| current_price_inr | float64 | Cleaned from raw source. | 09_portfolio_holdings.csv |
| portfolio_date | object | Date field parsed to ISO date; source column `portfolio_date` in 09_portfolio_holdings.csv. | 09_portfolio_holdings.csv |

## 10_benchmark_indices_processed.csv

| Column | Type | Description | Source |
|---|---|---|---|
| date | object | Date field parsed to ISO date; source column `date` in 10_benchmark_indices.csv. | 10_benchmark_indices.csv |
| index_name | str | Cleaned from raw source. | 10_benchmark_indices.csv |
| close_value | float64 | Cleaned from raw source. | 10_benchmark_indices.csv |
