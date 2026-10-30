-- 02. Golden layer: account grain (one row per account_id)
-- Population: ALL snapshot accounts, including untargeted, WRITEOFF, CLOSED.
-- Recovery: SUM(clean.successful_payments.amount) only.

CREATE SCHEMA IF NOT EXISTS gold;

DROP TABLE IF EXISTS gold.account_recovery;
CREATE TABLE gold.account_recovery AS
WITH successful_payments AS (
    SELECT
        account_id,
        SUM(amount) AS net_successful_recovery,
        COUNT(DISTINCT payment_id) AS successful_payment_count,
        MIN(event_at) AS first_paid,
        MAX(event_at) AS last_paid
    FROM clean.successful_payments
    GROUP BY account_id
),
call_summary AS (
    SELECT
        account_id,
        COUNT(DISTINCT call_id) AS call_count,
        SUM(CASE WHEN call_status = 'ANSWERED' THEN 1 ELSE 0 END) AS answered_calls
    FROM (SELECT DISTINCT * FROM raw.calls) c
    GROUP BY account_id
),
wa_summary AS (
    SELECT
        account_id,
        COUNT(DISTINCT whatsapp_event_id) AS wa_count
    FROM (SELECT DISTINCT * FROM raw.whatsapp_events) w
    GROUP BY account_id
),
sms_summary AS (
    SELECT
        account_id,
        COUNT(DISTINCT sms_event_id) AS sms_count
    FROM raw.sms_events
    GROUP BY account_id
),
field_summary AS (
    SELECT
        account_id,
        COUNT(DISTINCT visit_id) AS fv_count,
        SUM(CASE WHEN outcome IN ('PAID', 'PTP', 'CONTACTED') THEN 1 ELSE 0 END) AS successful_field_contacts
    FROM raw.field_visits
    GROUP BY account_id
),
ptp_summary AS (
    SELECT
        account_id,
        COUNT(DISTINCT ptp_id) AS ptp_count,
        SUM(CASE WHEN status = 'KEPT' THEN 1 ELSE 0 END) AS kept_ptp_count
    FROM raw.promises_to_pay
    GROUP BY account_id
),
first_strategy AS (
    SELECT
        t.account_id,
        (ARRAY_AGG(c.strategy_version ORDER BY t.target_date))[1] AS first_strategy_version,
        COUNT(DISTINCT c.strategy_version) AS n_strategies,
        COUNT(DISTINCT t.target_id) AS targeting_days
    FROM raw.daily_targeting t
    JOIN raw.campaigns c USING (campaign_id)
    GROUP BY t.account_id
),
complaints AS (
    SELECT account_id, COUNT(*) AS complaint_count
    FROM raw.complaints
    GROUP BY account_id
)
SELECT
    a.account_id,
    a.borrower_id,
    a.loan_type,
    a.principal_amount,
    a.outstanding_amount,
    a.dpd,
    CASE
        WHEN a.dpd <= 30 THEN '0-30 DPD'
        WHEN a.dpd <= 60 THEN '31-60 DPD'
        WHEN a.dpd <= 90 THEN '61-90 DPD'
        ELSE '90+ DPD'
    END AS dpd_bucket,
    a.risk_segment,
    a.status,
    a.opened_at,
    a.timezone,
    a.schema_version,
    b.city,
    b.state,
    CASE WHEN a.borrower_id IS NULL THEN 1 ELSE 0 END AS borrower_missing_flag,
    CASE WHEN a.borrower_id IS NOT NULL AND b.borrower_id IS NULL THEN 1 ELSE 0 END AS borrower_unmatched_flag,
    COALESCE(b.borrower_conflict_flag, 0) AS borrower_conflict_flag,
    COALESCE(s.net_successful_recovery, 0.0) AS net_successful_recovery,
    COALESCE(s.successful_payment_count, 0) AS successful_payment_count,
    CASE WHEN COALESCE(s.successful_payment_count, 0) > 0 THEN 1 ELSE 0 END AS paid_flag,
    s.first_paid,
    s.last_paid,
    COALESCE(c.call_count, 0) AS call_count,
    COALESCE(c.answered_calls, 0) AS answered_calls,
    COALESCE(w.wa_count, 0) AS wa_count,
    COALESCE(m.sms_count, 0) AS sms_count,
    COALESCE(f.fv_count, 0) AS fv_count,
    COALESCE(f.successful_field_contacts, 0) AS successful_field_contacts,
    COALESCE(p.ptp_count, 0) AS ptp_count,
    COALESCE(p.kept_ptp_count, 0) AS kept_ptp_count,
    CASE WHEN COALESCE(fs.targeting_days, 0) > 0 THEN 1 ELSE 0 END AS targeted_flag,
    fs.first_strategy_version,
    COALESCE(fs.n_strategies, 0) AS n_strategies,
    CASE WHEN COALESCE(fs.n_strategies, 0) = 1 THEN 1 ELSE 0 END AS exclusive_strategy_flag,
    CASE WHEN COALESCE(cp.complaint_count, 0) > 0 THEN 1 ELSE 0 END AS complaint_flag,
    COALESCE(cp.complaint_count, 0) AS complaint_count,
    COALESCE(s.net_successful_recovery, 0.0) AS total_recovered,
    COALESCE(s.successful_payment_count, 0) AS payment_count
FROM raw.accounts a
LEFT JOIN clean.borrowers b USING (borrower_id)
LEFT JOIN successful_payments s USING (account_id)
LEFT JOIN call_summary c USING (account_id)
LEFT JOIN wa_summary w USING (account_id)
LEFT JOIN sms_summary m USING (account_id)
LEFT JOIN field_summary f USING (account_id)
LEFT JOIN ptp_summary p USING (account_id)
LEFT JOIN first_strategy fs USING (account_id)
LEFT JOIN complaints cp USING (account_id);
