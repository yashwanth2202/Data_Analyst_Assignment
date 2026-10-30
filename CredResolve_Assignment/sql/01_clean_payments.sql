-- ====================================================================
-- Production Collections Analytics Pipeline - SQL Repository
-- ====================================================================

-- --------------------------------------------------------------------
-- 01. Staging & Cleaning: Payments & Deduplication
-- --------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS clean;

-- Step 1.1: Exact Row Deduplication & Payload Conflict Quarantine
CREATE TABLE IF NOT EXISTS clean.payment_quarantine AS
SELECT p.*, 'EXACT_DUPLICATE_OR_CONFLICT'::text AS quarantine_reason
FROM raw.payments p WHERE FALSE;

CREATE TEMP TABLE payment_dedup AS
SELECT DISTINCT * FROM raw.payments;

CREATE TEMP TABLE conflicting_payment_ids AS
SELECT payment_id
FROM payment_dedup
GROUP BY payment_id
HAVING COUNT(*) > 1;

INSERT INTO clean.payment_quarantine
SELECT d.*, 'CONFLICTING_PAYMENT_ID'::text
FROM payment_dedup d
JOIN conflicting_payment_ids c USING (payment_id);

CREATE TABLE IF NOT EXISTS clean.payments AS
SELECT d.*
FROM payment_dedup d
LEFT JOIN conflicting_payment_ids c USING (payment_id)
WHERE c.payment_id IS NULL;

-- --------------------------------------------------------------------
-- 02. Agent Identity Entity Resolution
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clean.agent_canonical AS
WITH ranked_agents AS (
    SELECT 
        employee_code,
        agent_id,
        agent_name,
        vendor_id,
        team,
        status,
        joined_at,
        updated_at,
        ROW_NUMBER() OVER (
            PARTITION BY employee_code 
            ORDER BY updated_at DESC, joined_at DESC
        ) AS rn
    FROM raw.agents
)
SELECT 
    employee_code,
    agent_id AS canonical_agent_id,
    agent_name,
    vendor_id,
    team,
    status,
    joined_at
FROM ranked_agents
WHERE rn = 1;

-- --------------------------------------------------------------------
-- 03. Call Disposition Harmonization & Standard Taxonomy
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clean.call_dispositions_harmonized AS
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
        WHEN disposition_code = 'PTP_BROKEN' THEN 'PTP_BROKEN'
        WHEN disposition_code IN ('PAID', 'SETTLED') THEN 'PAID'
        WHEN disposition_code IN ('CALLBACK', 'DISPUTE', 'REFUSED') THEN 'CONTACT_OTHER'
        WHEN disposition_code IN ('NO_CONTACT', 'WRONG_NUMBER', 'UNREACHABLE') THEN 'NO_CONTACT'
        ELSE 'OTHER'
    END AS canonical_disposition,
    CASE 
        WHEN disposition_code IN ('PROMISE_TO_PAY', 'PTP', 'PAID', 'CALLBACK', 'DISPUTE', 'REFUSED') THEN 1
        ELSE 0
    END AS is_rpc_flag
FROM raw.call_dispositions;
