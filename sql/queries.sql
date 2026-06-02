-- Day 1 validation queries.

-- Confirm every master AMFI code exists in NAV history.
SELECT fm.amfi_code
FROM fund_master AS fm
LEFT JOIN nav_history AS nh
  ON fm.amfi_code = nh.amfi_code
WHERE nh.amfi_code IS NULL;

-- Count NAV rows by scheme.
SELECT amfi_code, COUNT(*) AS nav_rows
FROM nav_history
GROUP BY amfi_code
ORDER BY amfi_code;

