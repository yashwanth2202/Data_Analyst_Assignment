-- 05. Metric contracts (production)
-- Primary keys
--   gold.account_recovery.account_id
--   clean.payments.payment_id
--   clean.borrowers.borrower_id  (canonical; conflict_flag = 1 if payloads collided)
--   clean.agent_canonical.employee_code
--
-- Incremental processing: watermark on event_at; late events land in staging and
-- rebuild the affected account_id partition of gold.account_recovery.
-- Backfill: re-run 01 then 02 for the impacted payment_id set.
-- DQ monitors: duplicate payment_id rate, conflict quarantine volume,
--               MoM daily-run-rate z-score, complaint rate, untargeted share.
-- Anomaly: |calendar_normalized_mom_pct| > 5 with days_observed < 28 is truncated-window, not collapse.

CREATE TABLE IF NOT EXISTS metrics.metric_dictionary (
    metric_name text PRIMARY KEY,
    grain text NOT NULL,
    formula text NOT NULL,
    exclusion_rules text NOT NULL
);

INSERT INTO metrics.metric_dictionary (metric_name, grain, formula, exclusion_rules) VALUES
('contact_rate', 'call', 'answered unique calls / unique calls after exact-dup drop', 'IVR rows with null agent_id stay in the denominator'),
('rpc_rate', 'disposition', 'harmonized RPC codes / all dispositions', 'PTP and PROMISE_TO_PAY both count as PTP'),
('ptp_rate', 'disposition', 'canonical PTP / RPC dispositions', 'Not PTP / all dials'),
('ptp_kept_rate', 'ptp_id', 'status = KEPT / all PTP rows', 'OPEN and CANCELLED stay in the denominator'),
('recovery_rate', 'account', 'paid_flag / all snapshot accounts', 'Do not drop WRITEOFF, CLOSED, or untargeted'),
('recovery_per_account', 'account', 'SUM(clean SUCCESS amount) / 30000', 'SUCCESS only'),
('recovery_per_agent_hour', 'portfolio', 'clean SUCCESS amount / session hours', 'Payments have no agent_id; not a person scorecard'),
('daily_run_rate', 'month', 'clean SUCCESS amount / observed days in window', 'August 2026 uses 8 days, never 31'),
('channel_last_touch_7d', 'payment', 'latest touch in 7d before SUCCESS', 'Null touch = ORGANIC_SELF_CURE; not incremental lift')
ON CONFLICT (metric_name) DO UPDATE
SET formula = EXCLUDED.formula,
    exclusion_rules = EXCLUDED.exclusion_rules;
