-- ====================================================================
-- 02. Golden Layer: Unified Account-Grain Analytical Dataset
-- ====================================================================
CREATE SCHEMA IF NOT EXISTS gold;

DROP TABLE IF EXISTS gold.account_recovery;
CREATE TABLE gold.account_recovery AS
WITH successful_payments AS (
    SELECT 
        account_id,
        SUM(amount) AS net_successful_recovery,
        COUNT(DISTINCT payment_id) AS successful_payment_count,
        MIN(event_at) AS first_successful_payment,
        MAX(event_at) AS last_successful_payment
    FROM clean.payments
    WHERE payment_status = 'SUCCESS'
    GROUP BY account_id
),
call_summary AS (
    SELECT 
        account_id,
        COUNT(DISTINCT call_id) AS total_calls,
        SUM(CASE WHEN call_status = 'ANSWERED' THEN 1 ELSE 0 END) AS answered_calls,
        SUM(duration_sec) AS total_call_duration_sec
    FROM raw.calls
    GROUP BY account_id
),
wa_summary AS (
    SELECT 
        account_id,
        COUNT(DISTINCT whatsapp_event_id) AS total_wa_events,
        SUM(CASE WHEN event_type = 'PAYMENT_CLICK' THEN 1 ELSE 0 END) AS wa_clicks
    FROM raw.whatsapp_events
    GROUP BY account_id
),
sms_summary AS (
    SELECT 
        account_id,
        COUNT(DISTINCT sms_event_id) AS total_sms_events
    FROM raw.sms_events
    GROUP BY account_id
),
field_summary AS (
    SELECT 
        account_id,
        COUNT(DISTINCT visit_id) AS total_field_visits,
        SUM(CASE WHEN outcome IN ('PAID', 'PTP', 'CONTACTED') THEN 1 ELSE 0 END) AS successful_field_contacts
    FROM raw.field_visits
    GROUP BY account_id
),
ptp_summary AS (
    SELECT 
        account_id,
        COUNT(DISTINCT ptp_id) AS total_ptp_count,
        SUM(CASE WHEN status = 'KEPT' THEN 1 ELSE 0 END) AS kept_ptp_count
    FROM raw.promises_to_pay
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
    a.status AS account_status,
    a.opened_at,
    COALESCE(s.net_successful_recovery, 0.0) AS net_successful_recovery,
    COALESCE(s.successful_payment_count, 0) AS successful_payment_count,
    CASE WHEN COALESCE(s.successful_payment_count, 0) > 0 THEN 1 ELSE 0 END AS paid_flag,
    COALESCE(c.total_calls, 0) AS total_calls,
    COALESCE(c.answered_calls, 0) AS answered_calls,
    COALESCE(w.total_wa_events, 0) AS total_wa_events,
    COALESCE(m.total_sms_events, 0) AS total_sms_events,
    COALESCE(f.total_field_visits, 0) AS total_field_visits,
    COALESCE(p.total_ptp_count, 0) AS total_ptp_count,
    COALESCE(p.kept_ptp_count, 0) AS kept_ptp_count,
    s.first_successful_payment,
    s.last_successful_payment
FROM raw.accounts a
LEFT JOIN successful_payments s USING (account_id)
LEFT JOIN call_summary c USING (account_id)
LEFT JOIN wa_summary w USING (account_id)
LEFT JOIN sms_summary m USING (account_id)
LEFT JOIN field_summary f USING (account_id)
LEFT JOIN ptp_summary p USING (account_id);
