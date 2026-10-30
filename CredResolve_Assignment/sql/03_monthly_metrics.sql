-- 03. Metrics: monthly recovery with OBSERVED days, not calendar month length.
-- August 2026 is truncated at 2026-08-08 (8 days). Using 31 would understate
-- the daily run rate and invent a collapse.

CREATE SCHEMA IF NOT EXISTS metrics;

CREATE OR REPLACE VIEW metrics.monthly_recovery_trends AS
WITH monthly_raw AS (
    SELECT
        DATE_TRUNC('month', event_at::timestamp)::date AS month_date,
        SUM(CASE WHEN payment_status = 'SUCCESS' THEN amount ELSE 0 END) AS raw_success_amount
    FROM raw.payments
    GROUP BY 1
),
monthly_clean AS (
    SELECT
        DATE_TRUNC('month', event_at::timestamp)::date AS month_date,
        SUM(amount) AS clean_success_amount,
        COUNT(DISTINCT payment_id) AS clean_success_count
    FROM clean.successful_payments
    GROUP BY 1
)
SELECT
    c.month_date,
    TO_CHAR(c.month_date, 'YYYY-MM') AS month_label,
    r.raw_success_amount,
    c.clean_success_amount,
    r.raw_success_amount - c.clean_success_amount AS duplicate_inflation_amount,
    -- Observed days: Jan-Jul full calendar months; Aug = 8
    CASE
        WHEN TO_CHAR(c.month_date, 'YYYY-MM') = '2026-08' THEN 8
        ELSE EXTRACT(DAY FROM (c.month_date + INTERVAL '1 month' - INTERVAL '1 day'))::int
    END AS days_observed,
    c.clean_success_amount / NULLIF(
        CASE
            WHEN TO_CHAR(c.month_date, 'YYYY-MM') = '2026-08' THEN 8
            ELSE EXTRACT(DAY FROM (c.month_date + INTERVAL '1 month' - INTERVAL '1 day'))
        END, 0) AS daily_run_rate_clean,
    LAG(c.clean_success_amount) OVER (ORDER BY c.month_date) AS prev_month_clean_amount,
    (c.clean_success_amount - LAG(c.clean_success_amount) OVER (ORDER BY c.month_date))
        / NULLIF(LAG(c.clean_success_amount) OVER (ORDER BY c.month_date), 0) * 100.0 AS reported_mom_pct,
    (
        (c.clean_success_amount / NULLIF(
            CASE WHEN TO_CHAR(c.month_date, 'YYYY-MM') = '2026-08' THEN 8
                 ELSE EXTRACT(DAY FROM (c.month_date + INTERVAL '1 month' - INTERVAL '1 day')) END, 0))
        - LAG(c.clean_success_amount / NULLIF(
            CASE WHEN TO_CHAR(c.month_date, 'YYYY-MM') = '2026-08' THEN 8
                 ELSE EXTRACT(DAY FROM (c.month_date + INTERVAL '1 month' - INTERVAL '1 day')) END, 0))
          OVER (ORDER BY c.month_date)
    ) / NULLIF(
        LAG(c.clean_success_amount / NULLIF(
            CASE WHEN TO_CHAR(c.month_date, 'YYYY-MM') = '2026-08' THEN 8
                 ELSE EXTRACT(DAY FROM (c.month_date + INTERVAL '1 month' - INTERVAL '1 day')) END, 0))
        OVER (ORDER BY c.month_date), 0) * 100.0 AS calendar_normalized_mom_pct
FROM monthly_clean c
LEFT JOIN monthly_raw r USING (month_date)
ORDER BY c.month_date;

CREATE OR REPLACE VIEW metrics.independent_kpis AS
SELECT
    COUNT(*) FILTER (WHERE call_status = 'ANSWERED')::float / NULLIF(COUNT(*), 0) AS contact_rate
FROM (SELECT DISTINCT * FROM raw.calls) c;

CREATE OR REPLACE VIEW metrics.recovery_rate AS
SELECT AVG(paid_flag::float) AS recovery_rate,
       AVG(net_successful_recovery) AS recovery_per_account
FROM gold.account_recovery;
