-- Analytical queries for Day 2

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
