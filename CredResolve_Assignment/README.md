# Collections Recovery Forensics & Analytics System — Submission

**Candidate Assignment:** Lead Data Analyst — Collections Recovery Forensics  
**Date:** 30 October 2026  
**Status:** Completed & Validated  

---

## 📌 Executive Summary

The business claim that **"Recovery has improved by 11% month-on-month" is FALSE.**

Forensic analysis revealed:

1. **The 11% Improvement is a Calendar Artifact:** Comparing March 2026 (₹118.86 Cr clean) against February 2026 (₹117.00 Cr clean) yields **+10.96%** (+10.99% raw). However, February has 28 days and March has 31 days. On a **Daily Run Rate** basis, daily collections were virtually flat (**₹160.72 L/day vs ₹160.85 L/day, +0.25%**).
2. **Attribution Fallacy:** **79.8%** of recovered cash occurred with **zero operational touches within 7 days prior**. Last-touch attribution models were claiming credit for organic borrower self-cures.
3. **Data Quality & Schema Audit:**
   - **Payment Ingestion Inflation:** 500 duplicate payment IDs artificially inflated successful collections by **₹12.59 Cr** (₹13.84 Cr across all statuses including failed/reversed).
   - **Agent Multiplicity:** 30,000 assignment rows reflect **1,099 unique collectors (`employee_code`)** cycling across **1,000 system-generated `agent_id` identifiers** (each collector appears in 7 to 46 rows).
   - **Disposition Taxonomy:** Disposition codes split evenly between `PTP` (3,904) and `PROMISE_TO_PAY` (3,926) at ~1,300 per version across legacy, v1, and v2; there is no historical drop cliff, but harmonizing the two spellings is necessary for clean pipelines.
   - **Synthetic Channel Noise:** The 60,600 WhatsApp events are uniformly generated (~10,000 per event type). Account cure rates for borrowers who clicked payment links (44.2%) are identical to those who did not (44.5%), indicating zero empirical recovery lift.
4. **Capital Investment Strategy:** Reject unsubstantiated claims of ₹132 Cr recovery / 220% ROI. Instead, adopt an **evidence-gated deployment of the ₹110 Cr**: fund an initial ₹150L–₹11 Cr randomized controlled trial (A/B holdout test) to measure true incremental lift, allocate ₹11.5 Cr–₹12 Cr to data hygiene (idempotent ingestion, agent entity resolution, incremental attribution modeling), and conditionally release remaining funds only if digital lift proves statistically significant.

---

## Repository Structure & Deliverables

| Deliverable | File / Path | Description |
| :--- | :--- | :--- |
| **1. SQL Repository** | [`sql/`](sql/) | Production SQL covering payment cleaning, agent identity resolution, disposition harmonization, golden account grain, and monthly run rate normalization. |
| **2. Analysis Notebook** | [`analysis_notebook.ipynb`](analysis_notebook.ipynb) | End-to-end Python forensic workflow covering Parts 1 through 5, visualizations, and statistical modeling. |
| **3. Golden Dataset** | [`golden_account_dataset.csv`](golden_account_dataset.csv) | Unified account-grain analytical dataset (30,000 rows, 37 attributes) integrating loan profiles, recoveries, and multi-channel touch volumes. |
| **4. Data Quality Report** | [`data_quality_report.csv`](data_quality_report.csv) | Forensic audit of 19 specific data issues across all 16 tables, including row counts, treatments, and business impact. |
| **5. Executive Dashboard** | [`executive_dashboard.html`](executive_dashboard.html) | Single-screen executive dashboard designed for a 60-second CEO decision review. |
| **6. Executive Memo** | [`executive_memo.md`](executive_memo.md) | 2-page decision memo covering what happened, why it happened, evidence classification, and financial investment modeling. |
| **7. Architecture Diagram** | [`architecture.svg`](architecture.svg) | Production data pipeline diagram (Raw → Staging → Clean → Golden → Feature → Metrics). |

---

## 🔬 Analysis Coverage

| Assignment Part | Status | Key Output |
| :--- | :---: | :--- |
| **Part 1 — Golden Dataset** | ✅ Complete | `golden_account_dataset.csv`, `sql/01_clean_payments.sql`, `sql/02_golden_account.sql` |
| **Part 2 — Data Forensics** | ✅ Complete | `data_quality_report.csv`, `sql/04_forensic_checks.sql`, `derived/` CSVs |
| **Part 3 — Statistical Investigation** | ✅ Complete | Mix effects, cohort effects, survivorship bias, Simpson's paradox tested in notebook |
| **Part 4 — Counterfactual** | ✅ Complete | Strategy matching, DiD, propensity scoring in notebook + `derived/strategy_matched_lift.csv` |
| **Part 5 — Production Analytics Design** | ✅ Complete | `sql/05_metric_definitions.sql`, `metric_definitions.csv`, `architecture.svg` |

---

## 📁 Derived Analytical Files

| File | Contents |
| :--- | :--- |
| `derived/agent_tenure_answer.csv` | Agent tenure vs. recovery rate analysis |
| `derived/attempt_frequency.csv` | Call attempt frequency vs. outcome rates |
| `derived/disposition_crosstab.csv` | PTP / PROMISE_TO_PAY harmonization audit |
| `derived/dpd_recovery_share_by_month.csv` | DPD bucket mix shifts over time |
| `derived/exclusive_strategy_outcomes.csv` | Single-strategy-only accounts — causal lift isolation |
| `derived/first_strategy_outcomes.csv` | First-touch strategy attribution by version |
| `derived/geo_state.csv` | State-level recovery and complaint rates |
| `derived/hour_answer_naive.csv` + `hour_answer_if_utc.csv` | Timezone sensitivity for calling-hour metrics |
| `derived/mix_dpd.csv`, `mix_loan.csv`, `mix_risk.csv` | Portfolio mix decomposition |
| `derived/open_cohort.csv` | Open (not yet resolved) account cohort analysis |
| `derived/strategy_matched_lift.csv` | Propensity-matched incremental lift by strategy |
| `derived/survivorship_latest_status.csv` | Survivorship bias check (CLOSED/WRITTEN-OFF exclusions) |
| `derived/targeted_vs_untargeted.csv` | Recovery rates: targeted vs. untargeted accounts |
| `derived/vendor_performance.csv` | Telephony vendor answer rate and PTP conversion |
| `attribution_7d.csv` | 7-day last-touch attribution waterfall |
| `monthly_recovery.csv` | Clean monthly recovery with observed-day normalization |

---

## ⚙️ Reproducibility

- **Python:** Run `python build_notebook.py` or launch Jupyter: `jupyter notebook analysis_notebook.ipynb`
- **SQL:** Compatible with standard PostgreSQL / Databricks / Snowflake. Scripts are in `sql/`
- **Dashboard:** Open `executive_dashboard.html` in any modern web browser
- **Dependencies:** `pandas`, `numpy`, `matplotlib`, `scipy`
