-- 04. Forensic integrity checks

-- A. Duplicate payment inflation (extra rows by payment_id, not extra unique IDs)
SELECT
    'extra_payment_id_rows' AS audit_check,
    COUNT(*) - COUNT(DISTINCT payment_id) AS extra_rows,
    COUNT(DISTINCT payment_id) AS unique_ids
FROM raw.payments;

-- B. Disposition taxonomy by version (no cliff)
SELECT
    disposition_version,
    COUNT(*) FILTER (WHERE disposition_code = 'PTP') AS count_ptp_short,
    COUNT(*) FILTER (WHERE disposition_code = 'PROMISE_TO_PAY') AS count_ptp_full,
    ROUND(COUNT(*) FILTER (WHERE disposition_code IN ('PTP', 'PROMISE_TO_PAY')) * 100.0 / COUNT(*), 2) AS ptp_share_pct
FROM raw.call_dispositions
GROUP BY disposition_version;

-- C. Agent identity is many-to-many
SELECT
    COUNT(*) AS agent_rows,
    COUNT(DISTINCT employee_code) AS employees,
    COUNT(DISTINCT agent_id) AS agent_ids
FROM raw.agents;

-- D. 7-day last-touch vs organic self-cure
WITH touchpoints AS (
    SELECT account_id, event_at::timestamp AS event_at, 'VOICE' AS channel FROM raw.calls
    UNION ALL
    SELECT account_id, event_at::timestamp, 'WHATSAPP' FROM raw.whatsapp_events
    UNION ALL
    SELECT account_id, event_at::timestamp, 'SMS' FROM raw.sms_events
    UNION ALL
    SELECT account_id, event_at::timestamp, 'FIELD' FROM raw.field_visits
),
touch_ranked AS (
    SELECT
        p.payment_id,
        p.amount,
        t.channel,
        ROW_NUMBER() OVER (PARTITION BY p.payment_id ORDER BY t.event_at DESC) AS rn
    FROM clean.successful_payments p
    JOIN touchpoints t
      ON p.account_id = t.account_id
     AND t.event_at <= p.event_at::timestamp
     AND t.event_at >= p.event_at::timestamp - INTERVAL '7 days'
)
SELECT
    COALESCE(tr.channel, 'ORGANIC_SELF_CURE') AS attributed_channel,
    COUNT(p.payment_id) AS payment_count,
    ROUND(SUM(p.amount) / 10000000.0, 2) AS attributed_recovery_cr,
    ROUND(COUNT(p.payment_id) * 100.0 / (SELECT COUNT(*) FROM clean.successful_payments), 2) AS pct_of_payments
FROM clean.successful_payments p
LEFT JOIN touch_ranked tr ON p.payment_id = tr.payment_id AND tr.rn = 1
GROUP BY 1
ORDER BY attributed_recovery_cr DESC;

-- E. Denominator: untargeted accounts still recover
SELECT
    targeted_flag,
    COUNT(*) AS accounts,
    ROUND(AVG(paid_flag::float) * 100, 2) AS recovery_rate_pct
FROM gold.account_recovery
GROUP BY 1;

-- F. Exclusive-strategy outcomes (accounts that saw only one strategy_version)
SELECT
    first_strategy_version,
    COUNT(*) AS accounts,
    ROUND(AVG(paid_flag::float) * 100, 2) AS recovery_rate_pct,
    ROUND(AVG(net_successful_recovery), 0) AS avg_recovery
FROM gold.account_recovery
WHERE exclusive_strategy_flag = 1
GROUP BY 1
ORDER BY 1;

-- G. payment_reference reused across accounts
SELECT COUNT(*) AS reused_references
FROM (
    SELECT payment_reference
    FROM raw.payments
    WHERE payment_reference IS NOT NULL
    GROUP BY payment_reference
    HAVING COUNT(DISTINCT account_id) > 1
) s;
