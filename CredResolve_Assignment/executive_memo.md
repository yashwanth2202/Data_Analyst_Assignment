# Executive Memo: Collections Recovery Forensics & Capital Allocation

**To:** Leadership Team & Investment Committee  
**From:** Lead Data Analyst / Forensics  
**Date:** 30 October 2026  
**Subject:** Forensic Audit of the "11% Recovery Improvement" Claim & ₹10 Cr Capital Deployment Recommendation  

---

## 1. Executive Summary & Forensic Verdict
The business claim that **"Recovery has improved by 11% month-on-month" is NOT TRUE.**

Our forensic investigation revealed that this claim is a statistical artifact:
1. **The Calendar Artifact:** The reported +11% (+10.96% in clean data, +10.99% in raw data) was calculated by comparing March 2026 (₹18.86 Cr clean) against February 2026 (₹17.00 Cr clean). February contains only **28 days**, whereas March contains **31 days**—an automatic $+10.71\%$ increase in operational days.
2. **Normalized Performance:** When normalized to a **Daily Run Rate**, collections were virtually flat: **₹60.72 Lakhs/day in February vs ₹60.85 Lakhs/day in March (+0.25% MoM)**. True operational productivity did not improve.
3. **Observation Window:** The dataset spans 1 January to 8 August 2026 (only 7 complete months). August is severely truncated (8 days), creating an artificial $-74.8\%$ drop if unadjusted.

---

## 2. Forensic Investigation of Inconsistencies

We audited all 16 operational datasets and uncovered 5 major structural data issues:

- **A. Duplicate Payments:** Ingestion retries created 486 exact duplicate payment rows and 28 conflicting records across 14 payment IDs, artificially inflating raw collections by **₹3.76 Cr**. We quarantined conflicting IDs and deduplicated clean payments down to 17,523 verified successful payments (₹131.47 Cr).
- **B. Attribution Window Bias:** Under standard 7-day last-touch attribution, **79.8% of all recovered cash had ZERO recorded operational touchpoints prior to payment**. These borrowers are "self-curing." Operational attribution has been claiming credit for organic inflows.
- **C. Telephony Disposition Shift:** In `call_dispositions`, codes split between `PROMISE_TO_PAY` (v1/legacy) and `PTP` (v2). Unharmonized reporting would show an artificial 50% drop in historical PTP conversion rates.
- **D. Agent Identity Fragmentation:** 1,099 unique human collectors (`employee_code`) are fragmented across 30,000 ephemeral `agent_id` records (up to 46 IDs per collector). This corrupted agent league tables and recovery-per-hour metrics.
- **E. Portfolio Mix & Counterfactual Targeting:** Analyzing accounts across targeting strategies (Legacy, V1, V2, V3) revealed near-identical recovery rates (43.5%–44.7%), proving that recent targeting rule tweaks produced negligible causal lift.

---

## 3. Evidence Classification
| Category | Classification | Finding |
| :--- | :---: | :--- |
| **Calendar Artifact** | **Fact** | Feb has 28 days; March has 31 days. Daily run rate changed by only $+0.25\%$. |
| **Ingestion Inflation** | **Fact** | 486 exact duplicates + 14 conflicting IDs inflated raw data by ₹3.76 Cr. |
| **Self-Cure Baseline** | **Strong Evidence** | 79.8% of payments occur without any outreach in the preceding 7 days. |
| **Targeting Lift** | **Strong Evidence** | V1/V2/V3 targeting strategies show no statistically significant lift over Legacy. |
| **Telephony Coding Drift**| **Fact** | Schema transition from `PROMISE_TO_PAY` to `PTP` caused reporting drift. |

---

## 4. Where Should We Invest ₹10 Cr?

Leadership must choose **one** area for the ₹10 Cr capital deployment.

### **Recommendation: WhatsApp & Conversational Digital Engagement (Option 5)**

### Financial Evaluation & Scenarios
- **Capital Required:** ₹10.00 Cr
- **Expected Incremental Recovery (Base Case):** ₹32.00 Cr
- **Net Incremental Gain:** **₹22.00 Cr**
- **Expected Net ROI:** **220%**
- **Break-Even Horizon:** **3.8 Months**
- **Downside Scenario:** ₹20.00 Cr incremental recovery (Net gain: ₹10.00 Cr, 100% ROI, 6.0-month break-even).
- **Upside Scenario:** ₹45.00 Cr incremental recovery (Net gain: ₹35.00 Cr, 350% ROI, 2.7-month break-even).

### Why WhatsApp / Digital Beats the Other Options:
1. **Unbeatable Unit Economics:** Cost per touch is **₹0.50** (WhatsApp) vs **₹15.00** (Voice Telephony) and **₹350.00** (Field Visits). Cost per ₹ recovered on WhatsApp is **₹0.0004** vs **₹0.298** for Field Operations.
2. **Payment Link Directness:** WhatsApp events show 10,180 payment link clicks—enabling instant borrower checkout via UPI/cards, collapsing the PTP-to-payment conversion friction.
3. **Scalability:** Expanding physical field operations or human agent seats faces steep diminishing returns and overheads; conversational WhatsApp automation scales with zero marginal labor cost.

### Implementation Guardrails & Phased Rollout
1. **Pre-Investment Randomized Controlled Trial (RCT):** Run a 30-day A/B holdout test across 5,000 accounts (WhatsApp interactive flow vs standard IVR/Telephony control) to empirically validate the lift.
2. **Compliance & Frequency Capping:** Implement strict TRAI / RBI opt-out guardrails to avoid complaint spikes (current complaint rate is 0.5%).
