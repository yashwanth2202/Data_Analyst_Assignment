# Collections Recovery Forensics & Analytics System — Submission

**Candidate Assignment:** Lead Data Analyst — Collections Recovery Forensics  
**Date:** 30 October 2026  
**Status:** Completed & Validated  

---

##  Executive Summary
The business claim that **"Recovery has improved by 11% month-on-month" is NOT TRUE.**

Forensic analysis revealed:
1. **The 11% Improvement is a Calendar Artifact:** Comparing March 2026 (₹18.86 Cr clean) against February 2026 (₹17.00 Cr clean) yields **+10.96%** (+10.99% raw). However, February has 28 days and March has 31 days ($31/28 = +10.71\%$ operational days). On a **Daily Run Rate** basis, daily collections were virtually flat (**₹60.72 L/day vs ₹60.85 L/day, +0.25%**).
2. **Attribution Fallacy:** **79.8%** of recovered cash occurred with **zero operational touches within 7 days prior**. Last-touch attribution models were claiming credit for organic borrower self-cures.
3. **Data Quality & Schema Drift:** Webhook retries inflated payments by **₹3.76 Cr**; telephony dispositions drifted between `PTP` and `PROMISE_TO_PAY`; and 1,099 human agents were splintered across 30,000 ephemeral agent IDs.
4. **Capital Investment Recommendation:** Deploy the **₹10 Cr** into **Option 5: WhatsApp / Conversational Digital Engagement**, delivering an estimated **₹22.0 Cr net incremental recovery (220% ROI)** with a **3.8-month break-even**.

---

## Repository Structure & Deliverables

| Deliverable | File / Path | Description |
| :--- | :--- | :--- |
| **1. SQL Repository** | [`sql/`](file:///d:/Downloads/assignment_cr/collections_30k_submission/sql) | Production SQL covering payment cleaning, agent identity resolution, disposition harmonization, golden account grain, and monthly run rate normalization. |
| **2. Analysis Notebook** | [`analysis_notebook.ipynb`](file:///d:/Downloads/assignment_cr/collections_30k_submission/analysis_notebook.ipynb) | End-to-end Python forensic workflow covering Parts 1 through 5, visualizations, and statistical modeling. |
| **3. Golden Dataset** | [`golden_account_dataset.csv`](file:///d:/Downloads/assignment_cr/collections_30k_submission/golden_account_dataset.csv) | Unified account-grain analytical dataset (30,000 rows, 21 attributes) integrating loan profiles, recoveries, and multi-channel touch volumes. |
| **4. Data Quality Report** | [`data_quality_report.csv`](file:///d:/Downloads/assignment_cr/collections_30k_submission/data_quality_report.csv) | Forensic audit of 14 specific data issues across all 16 tables, including row counts, treatments, and business impact. |
| **5. Executive Dashboard** | [`executive_dashboard.html`](file:///d:/Downloads/assignment_cr/collections_30k_submission/executive_dashboard.html) | Single-screen executive dashboard designed for a 60-second CEO decision review. |
| **6. Executive Memo** | [`executive_memo.md`](file:///d:/Downloads/assignment_cr/collections_30k_submission/executive_memo.md) | 2-page decision memo covering what happened, why it happened, evidence classification, and financial investment modeling. |
| **7. Architecture Diagram** | [`architecture.svg`](file:///d:/Downloads/assignment_cr/collections_30k_submission/architecture.svg) | Production data pipeline diagram (Raw $\to$ Staging $\to$ Clean $\to$ Golden $\to$ Feature $\to$ Metrics). |

---

##  Reproducibility
- **Python:** Run `python build_notebook.py` or launch Jupyter Notebook: `jupyter notebook analysis_notebook.ipynb`.
- **SQL:** Compatible with standard PostgreSQL / Databricks / Snowflake. Scripts are located in `sql/`.
- **Dashboard:** Open `executive_dashboard.html` in any modern web browser.
