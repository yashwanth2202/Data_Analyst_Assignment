-- ====================================================================
-- 04. Forensic Integrity & Data Audit Queries
-- ====================================================================

-- Check A: Duplicate Payment Inflation Analysis
SELECT 
    'Exact Duplicate Payments' AS audit_check,
    COUNT(*) AS duplicate_row_count,
    SUM(amount) AS inflated_amount_inr
FROM (
    SELECT payment_id, amount, COUNT(*) 
    FROM raw.payments 
    GROUP BY 1, 2 
    HAVING COUNT(*) > 1
) sub;

-- Check B: Telephony Disposition Shift Impact
SELECT 
    disposition_version,
    COUNT(CASE WHEN disposition_code = 'PTP' THEN 1 END) AS count_ptp_short,
    COUNT(CASE WHEN disposition_code = 'PROMISE_TO_PAY' THEN 1 END) AS count_ptp_full,
    COUNT(CASE WHEN disposition_code IN ('PTP', 'PROMISE_TO_PAY') THEN 1 END) AS count_ptp_total,
    ROUND(COUNT(CASE WHEN disposition_code IN ('PTP', 'PROMISE_TO_PAY') THEN 1 END) * 100.0 / COUNT(*), 2) AS ptp_rate_pct
FROM raw.call_dispositions
GROUP BY disposition_version;

-- Check C: Agent Identifier Multiplicity / Aliasing
SELECT 
    employee_code,
    COUNT(DISTINCT agent_id) AS linked_agent_ids,
    COUNT(*) AS total_agent_records
FROM raw.agents
GROUP BY employee_code
HAVING COUNT(DISTINCT agent_id) > 1
ORDER BY linked_agent_ids DESC
LIMIT 10;

-- Check D: 7-Day Last-Touch Attribution Breakdown vs Organic Self-Cure
WITH touchpoints AS (
    SELECT account_id, event_at, 'VOICE' AS channel FROM raw.calls
    UNION ALL
    SELECT account_id, event_at, 'WHATSAPP' FROM raw.whatsapp_events
    UNION ALL
    SELECT account_id, event_at, 'SMS' FROM raw.sms_events
    UNION ALL
    SELECT account_id, event_at, 'FIELD' FROM raw.field_visits
),
clean_succ_pay AS (
    SELECT payment_id, account_id, event_at, amount
    FROM clean.payments
    WHERE payment_status = 'SUCCESS'
),
touch_ranked AS (
    SELECT 
        p.payment_id,
        p.amount,
        t.channel,
        ROW_NUMBER() OVER (PARTITION BY p.payment_id ORDER BY t.event_at DESC) AS rn
    FROM clean_succ_pay p
    JOIN touchpoints t 
      ON p.account_id = t.account_id 
     AND t.event_at <= p.event_at 
     AND t.event_at >= (p.event_at - INTERVAL '7 days')
)
SELECT 
    COALESCE(tr.channel, 'ORGANIC_SELF_CURE') AS attributed_channel,
    COUNT(p.payment_id) AS payment_count,
    ROUND(SUM(p.amount) / 10000000.0, 2) AS attributed_recovery_cr,
    ROUND(COUNT(p.payment_id) * 100.0 / (SELECT COUNT(*) FROM clean_succ_pay), 2) AS pct_of_payments
FROM clean_succ_pay p
LEFT JOIN touch_ranked tr ON p.payment_id = tr.payment_id AND tr.rn = 1
GROUP BY 1
ORDER BY attributed_recovery_cr DESC;
