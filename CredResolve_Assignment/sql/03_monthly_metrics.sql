-- ====================================================================
-- 03. Metrics Layer: Monthly Run Rates & Normalized Metrics
-- ====================================================================
CREATE SCHEMA IF NOT EXISTS metrics;

CREATE OR REPLACE VIEW metrics.monthly_recovery_trends AS
WITH monthly_raw AS (
    SELECT 
        DATE_TRUNC('month', event_at::timestamp) AS month_date,
        COUNT(*) AS total_payment_attempts,
        SUM(amount) AS raw_attempted_amount,
        SUM(CASE WHEN payment_status = 'SUCCESS' THEN amount ELSE 0 END) AS raw_success_amount,
        COUNT(CASE WHEN payment_status = 'SUCCESS' THEN 1 END) AS raw_success_count
    FROM raw.payments
    GROUP BY 1
),
monthly_clean AS (
    SELECT 
        DATE_TRUNC('month', event_at::timestamp) AS month_date,
        SUM(CASE WHEN payment_status = 'SUCCESS' THEN amount ELSE 0 END) AS clean_success_amount,
        COUNT(CASE WHEN payment_status = 'SUCCESS' THEN 1 END) AS clean_success_count
    FROM clean.payments
    GROUP BY 1
)
SELECT 
    r.month_date,
    TO_CHAR(r.month_date, 'YYYY-MM') AS month_label,
    r.raw_attempted_amount,
    r.raw_success_amount,
    c.clean_success_amount,
    r.raw_success_amount - c.clean_success_amount AS duplicate_inflation_amount,
    -- Day normalization to solve February 28d vs March 31d calendar artifact
    EXTRACT(DAY FROM (r.month_date + INTERVAL '1 month' - INTERVAL '1 day')) AS days_in_month,
    c.clean_success_amount / NULLIF(EXTRACT(DAY FROM (r.month_date + INTERVAL '1 month' - INTERVAL '1 day')), 0) AS daily_run_rate_clean,
    LAG(c.clean_success_amount) OVER (ORDER BY r.month_date) AS prev_month_clean_amount,
    (c.clean_success_amount - LAG(c.clean_success_amount) OVER (ORDER BY r.month_date)) 
        / NULLIF(LAG(c.clean_success_amount) OVER (ORDER BY r.month_date), 0) * 100.0 AS reported_mom_pct,
    -- Normalized MoM removing calendar day distortion
    ((c.clean_success_amount / NULLIF(EXTRACT(DAY FROM (r.month_date + INTERVAL '1 month' - INTERVAL '1 day')), 0))
     - LAG(c.clean_success_amount / NULLIF(EXTRACT(DAY FROM (r.month_date + INTERVAL '1 month' - INTERVAL '1 day')), 0)) OVER (ORDER BY r.month_date))
     / NULLIF(LAG(c.clean_success_amount / NULLIF(EXTRACT(DAY FROM (r.month_date + INTERVAL '1 month' - INTERVAL '1 day')), 0)) OVER (ORDER BY r.month_date), 0) * 100.0 AS calendar_normalized_mom_pct
FROM monthly_raw r
LEFT JOIN monthly_clean c USING (month_date)
ORDER BY r.month_date;
