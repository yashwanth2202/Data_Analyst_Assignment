# Executive Memo: Collections Recovery Forensics & Capital Allocation Audit

**To:** Leadership Team & Investment Committee  
**From:** Lead Data Analyst / Forensics  
**Date:** 30 October 2026  
**Subject:** Forensic Audit of the "11% Recovery Improvement" Claim & ₹10 Cr Capital Deployment Strategy  

---

## 1. Executive Summary & Forensic Verdict

The business claim that **"Recovery has improved by 11% month-on-month" is FALSE.**

Our forensic investigation proves that this claim is a pure calendar artifact:
1. **The Calendar Artifact:** The reported +11% (+10.96% in clean data, +10.99% in raw data) was calculated by comparing March 2026 (₹18.86 Cr clean) against February 2026 (₹17.00 Cr clean). February has **28 days**, whereas March has **31 days**—an automatic $+10.71\%$ increase in operational days.
2. **Normalized Performance:** Normalized to a **Daily Run Rate**, collections were essentially flat: **₹60.72 Lakhs/day in February vs ₹60.85 Lakhs/day in March (+0.25% MoM)**. Operational recovery productivity did not improve.
3. **Observation Window:** The dataset spans 1 January to 8 August 2026 (only 7 complete months). August is severely truncated (8 days), creating an artificial $-74.8\%$ drop if unadjusted.
4. **Self-Cure Dominance:** **79.8% of recovered cash occurred with ZERO recorded operational touchpoints in the 7 days prior to payment**. The majority of portfolio recoveries are organic self-cures, meaning operational outreach claims credit for baseline borrower behavior.

---

## 2. Forensic Investigation of Inconsistencies & Data Limitations

An audit of all 16 operational datasets uncovered key structural anomalies and data realities that directly constrain strategic recommendations:

- **A. Duplicate Payments Accounting:** 
  - There are 500 duplicate `payment_id` rows (486 exact duplicates and 28 conflicting records across 14 IDs). 
  - If looking across all statuses (including `FAILED`, `PENDING`, `REVERSED`), the inflated portion totals **₹3.84 Cr**.
  - Restricting strictly to **`SUCCESS` payments**, the actual collected inflation is **₹2.59 Cr** (or ₹2.68 Cr when removing conflicting quarantined IDs). Reporting ₹3.76 Cr without specifying that it includes uncollected failed/pending attempts overstates the impact on collected cash.
- **B. Agent Identifier Multiplicity & Churn:**
  - The `agents` table contains **30,000 operational assignment rows** representing **1,099 unique human collectors (`employee_code`)** cycling across **1,000 system-generated `agent_id` identifiers**.
  - Each collector appears across 7 to 46 rows (averaging ~27 rows). This indicates aggressive identifier reuse/re-rotation across campaigns and shifts, which distorts individual agent scorecards and hourly recovery metrics if un-aliased.
- **C. Telephony Disposition Harmonization (No Drift Cliff):**
  - In `call_dispositions`, codes split between `PROMISE_TO_PAY` (3,926 records) and `PTP` (3,904 records).
  - Both codes appear uniformly at ~1,300 records per version across `legacy`, `v1`, and `v2`. 
  - While there is **no sudden drop or drift over time**, the two concurrent spellings must be harmonized into a canonical standard to prevent fragmented pipeline reporting.
- **D. WhatsApp Engagement Data is Synthetic Noise:**
  - The 60,600 WhatsApp events are uniformly distributed across event types (~10,000 each of `SENT`, `READ`, `DELIVERED`, `REPLIED`, `FAILED`, and `PAYMENT_CLICK`).
  - Account recovery rates for borrowers with `PAYMENT_CLICK` events (44.2%) are virtually identical to borrowers with other WhatsApp events (44.5%) and borrowers with no WhatsApp outreach (43.6%). 
  - The 10,180 payment link clicks represent synthetic uniform noise with **zero statistical correlation or causal lift** on actual recoveries.
- **E. Targeting Strategy Ineffectiveness:**
  - Accounts targeted under Legacy, V1, V2, and V3 strategies show virtually identical recovery rates (43.5%–44.7%), proving past targeting adjustments failed to generate incremental lift.
- **F. Complaint Volume is a Compliance Risk:**
  - The `complaints` table contains 8,000 complaints across **7,034 unique accounts (23.4% of the portfolio)**. High and Critical severity complaints account for ~49% of cases. Sources span all channels (Field, Email, WhatsApp, SMS, Call). Any aggressive digital expansion runs this complaint rate significantly higher without proper opt-out/consent guardrails.
- **G. PTP-to-Payment Conversion is Low (24.9% Kept Rate):**
  - Of 18,000 `promises_to_pay` records, only 4,489 (24.9%) have `KEPT` status. 49% are `BROKEN` or `CANCELLED`. PTP-based forecasting and commission models relying on verbal commitments are materially over-optimistic.
- **H. Field Visit Effective Contact Rate is 49.9%:**
  - Half of field visits result in a productive outcome (CONTACTED, PAID, or PTP). While meaningful, at ₹350/touch this is the most capital-intensive channel and faces natural capacity limits as a scale strategy.

---

## 3. Evidence Classification Summary

| Category | Classification | Finding |
| :--- | :---: | :--- |
| **Calendar Artifact** | **Fact** | Feb has 28 days; March has 31 days. Daily run rate changed by only $+0.25\%$. |
| **Ingestion Duplicate Inflation** | **Fact** | Exactly ₹2.59 Cr of inflated `SUCCESS` payments (₹3.84 Cr across all statuses). |
| **Self-Cure Baseline** | **Strong Evidence** | 79.8% of payments occur without any outreach in the preceding 7 days. |
| **Agent Identity Multiplicity** | **Fact** | 1,099 employee codes cycling through 1,000 agent IDs across 30,000 assignment rows. |
| **Telephony Coding Taxonomy** | **Fact** | `PTP` and `PROMISE_TO_PAY` are evenly distributed (~1,300/version); requires taxonomy cleanup. |
| **WhatsApp Predictive Value** | **Warning / Noise** | Event types are uniformly generated; payment-link clicks show 0% incremental lift. |
| **Targeting Strategy Lift** | **Strong Evidence** | Targeting rule adjustments (V1–V3) produced zero observable lift over Legacy. |
| **Complaint Volume** | **High Risk / Fact** | 23.4% of accounts have filed complaints; 49% HIGH or CRITICAL severity. |
| **PTP Kept Rate** | **Structural Risk** | Only 24.9% of Promises to Pay are honoured. PTP-based forecasts are materially inflated. |
| **Field Visit Contact Rate** | **Operational Fact** | 49.9% effective contact rate at ₹350/touch — highest-cost, capacity-constrained channel. |

---

## 4. Capital Allocation Review: The ₹10 Cr Decision

### The Flaw in Aggressive Projections
Standard proposals often claim that committing ₹10 Cr to WhatsApp/Digital will yield ₹32 Cr of incremental recovery with a 220% ROI and 3.8-month payback based on assumed low unit costs (e.g. ₹0.50/touch). 

**In an executive review or interview, this does not hold up:**
1. **Unsubstantiated Lift:** Unit costs per touch are operational assumptions, not empirical recovery multipliers. Given that existing targeting strategies produced 0% lift and 79.8% of borrowers self-cure, assuming ₹32 Cr in net-new cash from digital touches is unsubstantiated.
2. **Channel Noise:** The raw WhatsApp data shows flat recovery across clicked vs non-clicked accounts. Projecting 220% returns onto noise invites immediate audit failure.
3. **Complaint Risk Multiplier:** Any aggressive digital push without TRAI/RBI-compliant consent, frequency capping, and DND screening will drive the already-high 23.4% complaint rate materially higher, creating regulatory exposure.

### Pragmatic, Defensible Capital Deployment Recommendation
Rather than a blind ₹10 Cr unhedged deployment into WhatsApp or Field expansion, leadership should execute a **Phased, Evidence-Gated Strategy**:

1. **Phase 1: Controlled Randomized Pilot (Budget: ₹50 Lakhs – ₹1.0 Cr)**
   - **Pre-Investment Randomized Controlled Trial (RCT):** Run a 60-day randomized holdout test across 10,000 accounts:
     - Group A (Control): Standard baseline (no outreach / self-cure observation).
     - Group B (Conversational WhatsApp): Interactive payment links, automated reminders, and UPI deep-links.
     - Group C (Human Dialer): Standard outbound calling.
   - **Measure True Incremental Lift:** Quantify incremental recovery above the ~44% organic baseline. If incremental recovery is statistically indistinguishable from zero, halt further digital capital allocation.
2. **Phase 2: Fix Foundational Infrastructure & Self-Cure Attribution (Budget: ₹1.5 Cr – ₹2.0 Cr)**
   - **Deduplication & Ingestion Guards:** Enforce idempotency keys on payment webhooks to prevent the ₹2.59 Cr duplicate recovery distortion.
   - **Agent & Disposition Identity Layer:** Resolve agent IDs to master employee codes and standardize `PTP`/`PROMISE_TO_PAY` taxonomies.
   - **Lift-Based Attribution:** Shift scoring models away from last-touch attribution to incremental lift models, preventing teams from spending outreach budget on borrowers who pay organically.
3. **Phase 3: Conditional Capital Tranche Deployment (Remaining ₹7.0 – ₹8.0 Cr)**
   - If and only if the Phase 1 pilot demonstrates a statistically significant positive incremental cure rate and positive unit economics (accounting for channel friction, vendor costs, and DLT/opt-out compliance), release the remaining capital into the winning channel.
