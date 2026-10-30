-- 01. Staging and cleaning: payments, borrowers, agents, dispositions
-- Grain: one verified payment_id after exact-dup drop and conflict quarantine.
-- Timestamps: stored naive. Do not DATE_TRUNC until the account/call timezone
-- interpretation is declared. Observed window: 2026-01-01 to 2026-08-08.

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS clean;

DROP TABLE IF EXISTS staging.payments;
CREATE TABLE staging.payments AS
SELECT * FROM raw.payments;

DROP TABLE IF EXISTS clean.payment_quarantine;
CREATE TABLE clean.payment_quarantine AS
SELECT p.*, 'CONFLICTING_PAYMENT_ID'::text AS quarantine_reason
FROM (
    SELECT DISTINCT * FROM staging.payments
) p
JOIN (
    SELECT payment_id
    FROM (SELECT DISTINCT * FROM staging.payments) d
    GROUP BY payment_id
    HAVING COUNT(*) > 1
) c USING (payment_id);

DROP TABLE IF EXISTS clean.payments;
CREATE TABLE clean.payments AS
SELECT d.*
FROM (SELECT DISTINCT * FROM staging.payments) d
LEFT JOIN (
    SELECT DISTINCT payment_id FROM clean.payment_quarantine
) q USING (payment_id)
WHERE q.payment_id IS NULL;

DROP TABLE IF EXISTS clean.successful_payments;
CREATE TABLE clean.successful_payments AS
SELECT *
FROM clean.payments
WHERE payment_status = 'SUCCESS';

-- Borrowers: exact dups dropped; conflicting borrower_id kept as latest updated_at
DROP TABLE IF EXISTS clean.borrowers;
CREATE TABLE clean.borrowers AS
WITH dedup AS (
    SELECT DISTINCT * FROM raw.borrowers
),
ranked AS (
    SELECT
        d.*,
        COUNT(*) OVER (PARTITION BY borrower_id) AS payload_versions,
        ROW_NUMBER() OVER (PARTITION BY borrower_id ORDER BY updated_at DESC NULLS LAST) AS rn
    FROM dedup d
)
SELECT
    borrower_id,
    name,
    phone,
    email,
    city,
    state,
    created_at,
    updated_at,
    CASE WHEN payload_versions > 1 THEN 1 ELSE 0 END AS borrower_conflict_flag
FROM ranked
WHERE rn = 1;

-- Agents: employee_code is the person grain; agent_id is not unique identity
DROP TABLE IF EXISTS clean.agent_canonical;
CREATE TABLE clean.agent_canonical AS
SELECT
    employee_code,
    MIN(joined_at) AS first_joined_at,
    MAX(updated_at) AS last_updated_at,
    COUNT(DISTINCT agent_id) AS linked_agent_ids,
    COUNT(*) AS assignment_rows
FROM raw.agents
GROUP BY employee_code;

DROP TABLE IF EXISTS clean.call_dispositions_harmonized;
CREATE TABLE clean.call_dispositions_harmonized AS
SELECT
    disposition_id,
    account_id,
    borrower_id,
    call_id,
    agent_id,
    event_at,
    disposition_version,
    disposition_code AS raw_disposition_code,
    CASE
        WHEN disposition_code IN ('PROMISE_TO_PAY', 'PTP') THEN 'PTP'
        WHEN disposition_code IN ('PAID', 'SETTLED') THEN 'PAID'
        WHEN disposition_code IN ('CALLBACK', 'DISPUTE', 'REFUSED', 'PTP_BROKEN') THEN 'RPC_OTHER'
        WHEN disposition_code IN ('NO_CONTACT', 'WRONG_NUMBER', 'UNREACHABLE') THEN 'NO_CONTACT'
        ELSE 'OTHER'
    END AS canonical_disposition,
    CASE
        WHEN disposition_code IN ('PROMISE_TO_PAY', 'PTP', 'PAID', 'CALLBACK', 'DISPUTE', 'REFUSED', 'PTP_BROKEN') THEN 1
        ELSE 0
    END AS is_rpc_flag
FROM raw.call_dispositions;
