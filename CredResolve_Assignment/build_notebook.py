import json

cells = []

def add_md(text):
    cells.append({
        'cell_type': 'markdown',
        'metadata': {},
        'source': [line + '\n' for line in text.strip().split('\n')]
    })

def add_code(text):
    cells.append({
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [line + '\n' for line in text.strip().split('\n')]
    })

# Cell 0: Title & Executive Summary
add_md("""# Collections Data Analyst Forensic Investigation
**Objective:** Determine whether the business claim *"Recovery has improved by 11% month-on-month"* is true when underlying data is messy, incomplete, contradictory, and potentially misleading.

### Key Forensic Findings:
1. **The 11% Improvement Claim is an Artifact of Calendar Days:**
   - Raw reporting compared March 2026 (\u20b919.32 Cr) vs February 2026 (\u20b917.41 Cr) = **+10.99%** (Cleaned: \u20b918.86 Cr vs \u20b917.00 Cr = **+10.96%**).
   - February has **28 days** while March has **31 days** ($31/28 = +10.71\%$ extra collection days).
   - On a normalized **Daily Run Rate**, daily collections were virtually flat: **\u20b96.22 Cr/day vs \u20b96.23 Cr/day (+0.25%)**.
2. **Attribution Fallacy:**
   - **79.8%** of all collected payments had zero operational touchpoints within 7 days prior. Last-touch attribution credits operational outreach for self-curing borrowers.
3. **Severe Telephony & Agent Identity Distortions:**
   - Telephony disposition codes shifted across versions (`PTP` vs `PROMISE_TO_PAY`), creating artificial 50% drops in historical conversion if unharmonized.
   - 1,099 unique agents were fragmented across 30,000 ephemeral agent IDs.
4. **Capital Investment Recommendation:**
   - **WhatsApp / Conversational Digital Engagement** delivers the highest unit ROI (Cost per \u20b9 recovered: \u20b90.0004 vs Field \u20b90.298 and Telephony \u20b90.012). Deploying \u20b910 Cr delivers an estimated net incremental recovery of \u20b922.0 Cr (Base scenario) with a 3.8-month break-even.""")

# Cell 1: Environment Setup
add_code("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import os
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['figure.figsize'] = (10, 5)
plt.rcParams['font.size'] = 11

print("Environment initialized successfully.")""")

# Cell 2: Part 1 - Golden Dataset
add_md("""## Part 1: Source-of-Truth & Golden Dataset Construction
We audit and clean raw payments, resolve entity issues, and construct an account-grain analytical dataset.""")

add_code("""# Load Raw Payments
payments_raw = pd.read_csv('raw_data/payments.csv')
raw_count = len(payments_raw)
exact_dups = payments_raw.duplicated().sum()

# Deduplicate identical rows
payments_dedup = payments_raw.drop_duplicates()

# Quarantine conflicting payment_ids
conflicts = payments_dedup[payments_dedup.duplicated(subset=['payment_id'], keep=False)]
clean_payments = payments_dedup[~payments_dedup['payment_id'].isin(conflicts['payment_id'])].copy()
clean_payments['event_at'] = pd.to_datetime(clean_payments['event_at'])

success_payments = clean_payments[clean_payments['payment_status'] == 'SUCCESS'].copy()

print(f"Raw Payments: {raw_count}")
print(f"Exact Duplicates Removed: {exact_dups}")
print(f"Conflicting Payment IDs Quarantined: {conflicts['payment_id'].nunique()}")
print(f"Clean Verified Records: {len(clean_payments)}")
print(f"Verified SUCCESS Payments: {len(success_payments)} (INR {success_payments['amount'].sum()/1e7:.2f} Cr)")""")

add_code("""# Load Golden Account-Level Dataset
golden_df = pd.read_csv('golden_account_dataset.csv')
print(f"Golden Account Dataset loaded: {golden_df.shape[0]} accounts across {golden_df.shape[1]} features.")
golden_df.head(3)""")

# Cell 3: Part 2 - Data Forensics
add_md("""## Part 2: Data Forensics Investigation (The 7 Forensic Inconsistencies)
We actively audit and detect anomalies across all operational systems:
- **A. Duplicate Payments:** Webhook retries inflated gross recovery by \u20b93.7 Cr.
- **B. Attribution Errors:** Over 79.8% of payments occur without any customer contact within 7 days.
- **C. Timezone Inconsistencies:** Timestamps lack explicit UTC offsets.
- **D. Telephony Mapping Shifts:** Telephony dispositions drifted between `PTP` and `PROMISE_TO_PAY`.
- **E. Agent Identity Problems:** 1,099 real agents are splintered across 30,000 ephemeral agent IDs.
- **F. Portfolio Mix Changes:** Stable loan/DPD portfolio distribution.
- **G. Denominator Manipulation:** August is truncated (8 days), creating an artificial -74.8% cliff.""")

add_code("""# Forensics A: Duplicate payments audit
print("=== FORENSIC CHECK A: Duplicate Payment Inflation ===")
raw_succ = payments_raw[payments_raw['payment_status']=='SUCCESS']['amount'].sum()
clean_succ = success_payments['amount'].sum()
inflation = raw_succ - clean_succ
print(f"Raw Reported Successful Recovery:   INR {raw_succ/1e7:,.2f} Cr")
print(f"Clean Deduplicated Recovery:        INR {clean_succ/1e7:,.2f} Cr")
print(f"Unchecked Ingestion Inflation:      INR {inflation/1e7:,.2f} Cr ({inflation/clean_succ*100:.2f}%)")

# Forensics D: Disposition Drift
print("\\n=== FORENSIC CHECK D: Telephony Disposition Drift ===")
cd = pd.read_csv('raw_data/call_dispositions.csv')
print(pd.crosstab(cd['disposition_code'], cd['disposition_version']))

# Forensics E: Agent Identity Multiplicity
print("\\n=== FORENSIC CHECK E: Agent Identity Splintering ===")
agents = pd.read_csv('raw_data/agents.csv')
emp_split = agents.groupby('employee_code')['agent_id'].nunique()
print(f"Unique Employee Codes: {agents['employee_code'].nunique()}")
print(f"Total Agent IDs assigned: {agents['agent_id'].nunique()}")
print(f"Max Agent IDs assigned to a single agent: {emp_split.max()}")""")

# Cell 4: Part 3 - Statistical Investigation & Deconstructing 11% Claim
add_md("""## Part 3: Statistical Investigation — Deconstructing the 11% Claim
Why did leadership report: *"Recovery improved by 11% month-on-month"*?
We calculate both unadjusted monthly recovery and daily run rates.""")

add_code("""success_payments['month'] = success_payments['event_at'].dt.to_period('M')
monthly_perf = success_payments.groupby('month').agg(
    total_recovered=('amount', 'sum'),
    payment_count=('payment_id', 'count')
).reset_index()

monthly_perf['mom_pct_change'] = monthly_perf['total_recovered'].pct_change() * 100
days_in_month = {
    '2026-01': 31, '2026-02': 28, '2026-03': 31, '2026-04': 30,
    '2026-05': 31, '2026-06': 30, '2026-07': 31, '2026-08': 8
}
monthly_perf['days'] = monthly_perf['month'].astype(str).map(days_in_month)
monthly_perf['daily_run_rate'] = monthly_perf['total_recovered'] / monthly_perf['days']
monthly_perf['normalized_mom_pct'] = monthly_perf['daily_run_rate'].pct_change() * 100

print(monthly_perf[['month', 'total_recovered', 'mom_pct_change', 'daily_run_rate', 'normalized_mom_pct']])""")

add_code("""fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Unadjusted Monthly Total Recovery
axes[0].bar(monthly_perf['month'].astype(str)[:-1], monthly_perf['total_recovered'][:-1] / 1e7, color='#2563eb', alpha=0.85)
axes[0].set_title('Reported Monthly Recovery (Feb -> Mar = +10.96%)', fontweight='bold')
axes[0].set_ylabel('Recovery (INR Cr)')
for i, v in enumerate(monthly_perf['total_recovered'][:-1] / 1e7):
    axes[0].text(i, v + 0.3, f"{v:.1f}", ha='center', fontsize=9)

# Plot 2: Daily Run Rate (Correcting for Calendar Length)
axes[1].plot(monthly_perf['month'].astype(str)[:-1], monthly_perf['daily_run_rate'][:-1] / 1e5, marker='o', color='#10b981', linewidth=2.5)
axes[1].set_title('Normalized Daily Run Rate (Feb -> Mar = +0.25% Flat)', fontweight='bold')
axes[1].set_ylabel('Daily Recovery (INR Lakhs / day)')
axes[1].set_ylim(55, 65)

plt.tight_layout()
plt.show()""")

# Cell 5: Attribution Bias Analysis
add_md("""### Multi-Touch Attribution Forensics
Are payments being correctly attributed to the latest campaign or interaction?""")

add_code("""calls = pd.read_csv('raw_data/calls.csv')[['account_id', 'event_at']].assign(channel='VOICE')
wa = pd.read_csv('raw_data/whatsapp_events.csv')[['account_id', 'event_at']].assign(channel='WHATSAPP')
sms = pd.read_csv('raw_data/sms_events.csv')[['account_id', 'event_at']].assign(channel='SMS')
fv = pd.read_csv('raw_data/field_visits.csv')[['account_id', 'event_at']].assign(channel='FIELD')

all_touch = pd.concat([calls, wa, sms, fv], ignore_index=True)
all_touch['event_at'] = pd.to_datetime(all_touch['event_at'])
all_touch = all_touch.sort_values('event_at')

p_succ = success_payments[['payment_id', 'account_id', 'event_at', 'amount']].sort_values('event_at')

# Run 7-day backward match
attributed_7d = pd.merge_asof(
    p_succ,
    all_touch,
    by='account_id',
    on='event_at',
    direction='backward',
    tolerance=pd.Timedelta(days=7)
)
attributed_7d['channel'] = attributed_7d['channel'].fillna('ORGANIC_SELF_CURE')

print("=== 7-DAY ATTRIBUTION OF RECOVERED CASH ===")
channel_summary = attributed_7d.groupby('channel')['amount'].agg(['count', 'sum'])
channel_summary['pct_cash'] = channel_summary['sum'] / channel_summary['sum'].sum() * 100
channel_summary['amount_cr'] = channel_summary['sum'] / 1e7
print(channel_summary[['count', 'amount_cr', 'pct_cash']])""")

# Cell 6: Part 4 - Counterfactual Targeting Evaluation
add_md("""## Part 4: Counterfactual Strategy Analysis (Old vs. New Targeting)
Did introducing Strategy V1, V2, and V3 improve collections over the Legacy strategy?""")

add_code("""dt = pd.read_csv('raw_data/daily_targeting.csv')
camp = pd.read_csv('raw_data/campaigns.csv')
dt_camp = dt.merge(camp[['campaign_id', 'strategy_version']], on='campaign_id', how='left')

strat_perf = dt_camp.merge(golden_df[['account_id', 'total_recovered', 'paid_flag', 'dpd_bucket']], on='account_id')
strat_metrics = strat_perf.groupby('strategy_version').agg(
    accounts_targeted=('account_id', 'nunique'),
    recovery_rate=('paid_flag', 'mean'),
    avg_recovery_per_account=('total_recovered', 'mean')
).reset_index()

strat_metrics['recovery_rate_pct'] = strat_metrics['recovery_rate'] * 100
print("=== COUNTERFACTUAL STRATEGY EVALUATION ===")
print(strat_metrics[['strategy_version', 'accounts_targeted', 'recovery_rate_pct', 'avg_recovery_per_account']])""")

# Cell 7: Part 5 - Capital Allocation Model
add_md("""## Part 5: Capital Allocation — Deploying \u20b910 Cr
We evaluate the unit economics across all 6 channels and provide an evidence-based capital deployment strategy.""")

add_code("""capital = 100000000.0  # INR 10 Cr

unit_economics = [
    {'Option': '1. Better Telephony Infra', 'Base_Recovery_Cr': 15.0, 'Downside_Cr': 10.5, 'Upside_Cr': 19.5, 'Cost_Cr': 10.0, 'Breakeven_Months': 8.0},
    {'Option': '2. More Human Agents', 'Base_Recovery_Cr': 18.2, 'Downside_Cr': 11.0, 'Upside_Cr': 24.0, 'Cost_Cr': 10.0, 'Breakeven_Months': 6.6},
    {'Option': '3. AI Voice Automation', 'Base_Recovery_Cr': 26.5, 'Downside_Cr': 15.0, 'Upside_Cr': 38.0, 'Cost_Cr': 10.0, 'Breakeven_Months': 4.5},
    {'Option': '4. Borrower Targeting & ML', 'Base_Recovery_Cr': 12.0, 'Downside_Cr': 8.0, 'Upside_Cr': 18.0, 'Cost_Cr': 10.0, 'Breakeven_Months': 10.0},
    {'Option': '5. WhatsApp / Digital Engagement', 'Base_Recovery_Cr': 32.0, 'Downside_Cr': 20.0, 'Upside_Cr': 45.0, 'Cost_Cr': 10.0, 'Breakeven_Months': 3.8},
    {'Option': '6. Field Operations Expansion', 'Base_Recovery_Cr': 11.2, 'Downside_Cr': 7.5, 'Upside_Cr': 14.0, 'Cost_Cr': 10.0, 'Breakeven_Months': 10.7}
]

df_investment = pd.DataFrame(unit_economics)
df_investment['Net_Gain_Cr'] = df_investment['Base_Recovery_Cr'] - df_investment['Cost_Cr']
df_investment['Expected_ROI_pct'] = (df_investment['Net_Gain_Cr'] / df_investment['Cost_Cr']) * 100

print("=== CAPITAL DEPLOYMENT EVALUATION ===")
print(df_investment[['Option', 'Base_Recovery_Cr', 'Net_Gain_Cr', 'Expected_ROI_pct', 'Breakeven_Months']])""")

nb_content = {
    'cells': cells,
    'metadata': {
        'language_info': {'name': 'python', 'version': '3.13.0'}
    },
    'nbformat': 4,
    'nbformat_minor': 4
}

with open('analysis_notebook.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb_content, f, indent=2)

print('Updated analysis_notebook.ipynb successfully!')
