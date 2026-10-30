# Collections Recovery Forensics & Analytics System — Submission

**Candidate Assignment:** Lead Data Analyst — Collections Recovery Forensics  
**Date:** 30 October 2026  
**Status:** Completed & Validated  

---

<<<<<<< HEAD
##  Executive Summary
The business claim that **"Recovery has improved by 11% month-on-month" is NOT TRUE.**
=======
## 📌 Executive Summary
The business claim that **"Recovery has improved by 11% month-on-month" is FALSE.**
>>>>>>> 6022469 (Add visualizations, fix encoding, finalize all deliverables)

Forensic analysis revealed:
1. **The 11% Improvement is a Calendar Artifact:** Comparing March 2026 (₹18.86 Cr clean) against February 2026 (₹17.00 Cr clean) yields **+10.96%** (+10.99% raw). However, February has 28 days and March has 31 days ($31/28 = +10.71\%$ operational days). On a **Daily Run Rate** basis, daily collections were virtually flat (**₹60.72 L/day vs ₹60.85 L/day, +0.25%**).
2. **Attribution Fallacy:** **79.8%** of recovered cash occurred with **zero operational touches within 7 days prior**. Last-touch attribution models were claiming credit for organic borrower self-cures.
3. **Data Quality & Schema Audit:**
   - **Payment Ingestion Inflation:** 500 duplicate payment IDs artificially inflated successful collections by **₹2.59 Cr** (₹3.84 Cr across all statuses including failed/reversed).
   - **Agent Multiplicity:** 30,000 assignment rows reflect **1,099 unique collectors (`employee_code`)** cycling across **1,000 system-generated `agent_id` identifiers** (each collector appears in 7 to 46 rows).
   - **Disposition Taxonomy:** Disposition codes split evenly between `PTP` (3,904) and `PROMISE_TO_PAY` (3,926) at ~1,300 per version across legacy, v1, and v2; there is no historical drop cliff, but harmonizing the two spellings is necessary for clean pipelines.
   - **Synthetic Channel Noise:** The 60,600 WhatsApp events are uniformly generated (~10,000 per event type). Account cure rates for borrowers who clicked payment links (44.2%) are identical to those who did not (44.5%), indicating zero empirical recovery lift.
4. **Capital Investment Strategy:** Reject unsubstantiated claims of ₹32 Cr recovery / 220% ROI. Instead, adopt an **evidence-gated deployment of the ₹10 Cr**: fund an initial ₹50L–₹1 Cr randomized controlled trial (A/B holdout test) to measure true incremental lift, allocate ₹1.5 Cr–₹2 Cr to data hygiene (idempotent ingestion, agent entity resolution, incremental attribution modeling), and conditionally release remaining funds only if digital lift proves statistically significant.

---

## Repository Structure & Deliverables

| Deliverable | File / Path | Description |
| :--- | :--- | :--- |
| **1. SQL Repository** | [`sql/`](sql/) | Production SQL covering payment cleaning, agent identity resolution, disposition harmonization, golden account grain, and monthly run rate normalization. |
| **2. Analysis Notebook** | [`analysis_notebook.ipynb`](analysis_notebook.ipynb) | End-to-end Python forensic workflow covering Parts 1 through 5, visualizations, and statistical modeling. |
| **3. Golden Dataset** | [`golden_account_dataset.csv`](golden_account_dataset.csv) | Unified account-grain analytical dataset (30,000 rows, 21 attributes) integrating loan profiles, recoveries, and multi-channel touch volumes. |
| **4. Data Quality Report** | [`data_quality_report.csv`](data_quality_report.csv) | Forensic audit of 14 specific data issues across all 16 tables, including row counts, treatments, and business impact. |
| **5. Executive Dashboard** | [`executive_dashboard.html`](executive_dashboard.html) | Single-screen executive dashboard designed for a 60-second CEO decision review. |
| **6. Executive Memo** | [`executive_memo.md`](executive_memo.md) | 2-page decision memo covering what happened, why it happened, evidence classification, and financial investment modeling. |
| **7. Architecture Diagram** | [`architecture.svg`](architecture.svg) | Production data pipeline diagram (Raw $\to$ Staging $\to$ Clean $\to$ Golden $\to$ Feature $\to$ Metrics). |

---

##  Reproducibility
- **Python:** Run `python build_notebook.py` or launch Jupyter Notebook: `jupyter notebook analysis_notebook.ipynb`.
- **SQL:** Compatible with standard PostgreSQL / Databricks / Snowflake. Scripts are located in `sql/`.
- **Dashboard:** Open `executive_dashboard.html` in any modern web browser.
