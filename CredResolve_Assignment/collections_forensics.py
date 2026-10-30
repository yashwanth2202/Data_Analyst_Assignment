"""
Collections recovery forensics pipeline.
Builds the golden account dataset and all audit artefacts from raw_data/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw_data"
OBS_START = pd.Timestamp("2026-01-01")
OBS_END = pd.Timestamp("2026-08-08 23:59:59")
DAYS_IN_MONTH = {
    "2026-01": 31,
    "2026-02": 28,
    "2026-03": 31,
    "2026-04": 30,
    "2026-05": 31,
    "2026-06": 30,
    "2026-07": 31,
    "2026-08": 8,  # truncated observation window, not calendar August
}

RPC_CODES = {"PROMISE_TO_PAY", "PTP", "PAID", "CALLBACK", "DISPUTE", "REFUSED", "PTP_BROKEN"}
NO_CONTACT_CODES = {"NO_CONTACT", "WRONG_NUMBER", "UNREACHABLE"}
FIELD_EFFECTIVE = {"PAID", "PTP", "CONTACTED"}


def dpd_bucket(dpd: float) -> str:
    if pd.isna(dpd):
        return "UNKNOWN"
    if dpd <= 30:
        return "0-30 DPD"
    if dpd <= 60:
        return "31-60 DPD"
    if dpd <= 90:
        return "61-90 DPD"
    return "90+ DPD"


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW / name)


def parse_ts(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")


def clean_payments(payments_raw: pd.DataFrame) -> dict:
    raw_n = len(payments_raw)
    exact_dups = int(payments_raw.duplicated().sum())
    dedup = payments_raw.drop_duplicates().copy()
    conflict_mask = dedup.duplicated(subset=["payment_id"], keep=False)
    conflicts = dedup.loc[conflict_mask]
    n_conflict_ids = int(conflicts["payment_id"].nunique())
    n_conflict_rows = int(len(conflicts))
    extra_id_rows = int(payments_raw.duplicated(subset=["payment_id"]).sum())

    clean = dedup.loc[~conflict_mask].copy()
    clean["event_at"] = parse_ts(clean["event_at"])
    success = clean.loc[clean["payment_status"] == "SUCCESS"].copy()

    refs = payments_raw.dropna(subset=["payment_reference"])
    ref_acct = refs.groupby("payment_reference")["account_id"].nunique()
    n_cross_account_refs = int((ref_acct > 1).sum())
    n_cross_account_ref_rows = int(refs[refs["payment_reference"].isin(ref_acct[ref_acct > 1].index)].shape[0])

    dup_keep_first = payments_raw[payments_raw.duplicated(subset=["payment_id"], keep="first")]
    succ_inflation = float(dup_keep_first.loc[dup_keep_first["payment_status"] == "SUCCESS", "amount"].sum())
    all_inflation = float(dup_keep_first["amount"].sum())
    raw_success_amt = float(payments_raw.loc[payments_raw["payment_status"] == "SUCCESS", "amount"].sum())
    clean_success_amt = float(success["amount"].sum())

    return {
        "payments_raw": payments_raw,
        "clean": clean,
        "success": success,
        "conflicts": conflicts,
        "stats": {
            "raw_payment_rows": raw_n,
            "exact_duplicate_rows": exact_dups,
            "extra_payment_id_rows": extra_id_rows,
            "conflicting_payment_ids": n_conflict_ids,
            "quarantined_conflict_rows": n_conflict_rows,
            "clean_unique_payment_rows": int(len(clean)),
            "valid_successful_payment_rows": int(len(success)),
            "raw_success_amount": raw_success_amt,
            "clean_success_amount": clean_success_amt,
            "success_dup_row_inflation": succ_inflation,
            "all_status_dup_row_inflation": all_inflation,
            "raw_minus_clean_success": raw_success_amt - clean_success_amt,
            "cross_account_payment_references": n_cross_account_refs,
            "cross_account_payment_reference_rows": n_cross_account_ref_rows,
        },
    }


def clean_borrowers(borrowers_raw: pd.DataFrame) -> dict:
    exact_dups = int(borrowers_raw.duplicated().sum())
    dedup = borrowers_raw.drop_duplicates().copy()
    dedup["updated_at"] = parse_ts(dedup["updated_at"])
    conflict_mask = dedup.duplicated(subset=["borrower_id"], keep=False)
    n_conflict_ids = int(dedup.loc[conflict_mask, "borrower_id"].nunique())
    n_conflict_rows = int(conflict_mask.sum())
    canonical = (
        dedup.sort_values(["borrower_id", "updated_at"], na_position="first")
        .drop_duplicates(subset=["borrower_id"], keep="last")
        .copy()
    )
    canonical["borrower_conflict_flag"] = canonical["borrower_id"].isin(
        dedup.loc[conflict_mask, "borrower_id"]
    ).astype(int)
    missing_phone = int(canonical["phone"].isna().sum())
    missing_email = int(canonical["email"].isna().sum())
    missing_either = int((canonical["phone"].isna() | canonical["email"].isna()).sum())
    return {
        "canonical": canonical,
        "stats": {
            "borrower_raw_rows": int(len(borrowers_raw)),
            "borrower_exact_duplicates": exact_dups,
            "unique_borrower_ids": int(canonical["borrower_id"].nunique()),
            "conflicting_borrower_ids": n_conflict_ids,
            "conflicting_borrower_rows": n_conflict_rows,
            "missing_phone": missing_phone,
            "missing_email": missing_email,
            "missing_phone_or_email": missing_either,
        },
    }


def clean_agents(agents_raw: pd.DataFrame) -> dict:
    agents = agents_raw.copy()
    agents["joined_at"] = parse_ts(agents["joined_at"])
    agents["updated_at"] = parse_ts(agents["updated_at"])
    canonical = (
        agents.sort_values(["employee_code", "updated_at"])
        .drop_duplicates(subset=["employee_code"], keep="last")
        .copy()
    )
    first_join = agents.groupby("employee_code", as_index=False)["joined_at"].min()
    canonical = canonical.drop(columns=["joined_at"]).merge(first_join, on="employee_code", how="left")
    return {
        "canonical": canonical,
        "stats": {
            "agent_rows": int(len(agents)),
            "unique_employee_codes": int(agents["employee_code"].nunique()),
            "unique_agent_ids": int(agents["agent_id"].nunique()),
            "agent_ids_with_multiple_employees": int(
                (agents.groupby("agent_id")["employee_code"].nunique() > 1).sum()
            ),
            "employees_with_multiple_agent_ids": int(
                (agents.groupby("employee_code")["agent_id"].nunique() > 1).sum()
            ),
            "rows_per_employee_min": int(agents["employee_code"].value_counts().min()),
            "rows_per_employee_max": int(agents["employee_code"].value_counts().max()),
        },
    }


def build_golden(accounts, borrowers, success, calls, wa, sms, fv, ptp, dt, camp, complaints) -> pd.DataFrame:
    pay = success.groupby("account_id").agg(
        net_successful_recovery=("amount", "sum"),
        successful_payment_count=("payment_id", "nunique"),
        first_paid=("event_at", "min"),
        last_paid=("event_at", "max"),
    ).reset_index()

    call_sum = calls.groupby("account_id").agg(
        call_count=("call_id", "nunique"),
        answered_calls=("call_status", lambda s: int((s == "ANSWERED").sum())),
    ).reset_index()
    wa_sum = wa.groupby("account_id").agg(wa_count=("whatsapp_event_id", "nunique")).reset_index()
    sms_sum = sms.groupby("account_id").agg(sms_count=("sms_event_id", "nunique")).reset_index()
    fv_sum = fv.groupby("account_id").agg(
        fv_count=("visit_id", "nunique"),
        successful_field_contacts=("outcome", lambda s: int(s.isin(FIELD_EFFECTIVE).sum())),
    ).reset_index()
    ptp_sum = ptp.groupby("account_id").agg(
        ptp_count=("ptp_id", "nunique"),
        kept_ptp_count=("status", lambda s: int((s == "KEPT").sum())),
    ).reset_index()

    dt2 = dt.merge(camp[["campaign_id", "strategy_version"]], on="campaign_id", how="left")
    dt2["target_date"] = parse_ts(dt2["target_date"])
    first_strat = (
        dt2.sort_values(["account_id", "target_date"])
        .groupby("account_id", as_index=False)
        .agg(
            first_strategy_version=("strategy_version", "first"),
            n_strategies=("strategy_version", "nunique"),
            targeting_days=("target_id", "nunique"),
        )
    )
    exclusive = dt2.groupby("account_id")["strategy_version"].nunique().reset_index(name="n_strat")
    exclusive_ids = set(exclusive.loc[exclusive["n_strat"] == 1, "account_id"])
    first_strat["exclusive_strategy_flag"] = first_strat["account_id"].isin(exclusive_ids).astype(int)

    comp_acc = complaints.groupby("account_id").size().reset_index(name="complaint_count")

    golden = accounts.copy()
    golden["opened_at"] = parse_ts(golden["opened_at"])
    golden["dpd_bucket"] = golden["dpd"].map(dpd_bucket)
    golden["borrower_missing_flag"] = golden["borrower_id"].isna().astype(int)
    golden = golden.merge(
        borrowers[["borrower_id", "city", "state", "borrower_conflict_flag"]],
        on="borrower_id",
        how="left",
    )
    golden["borrower_unmatched_flag"] = (
        golden["borrower_id"].notna() & golden["city"].isna() & golden["state"].isna()
    ).astype(int)
    golden["borrower_conflict_flag"] = golden["borrower_conflict_flag"].fillna(0).astype(int)

    for frame in (pay, call_sum, wa_sum, sms_sum, fv_sum, ptp_sum, first_strat, comp_acc):
        golden = golden.merge(frame, on="account_id", how="left")

    golden["net_successful_recovery"] = golden["net_successful_recovery"].fillna(0.0)
    golden["successful_payment_count"] = golden["successful_payment_count"].fillna(0).astype(int)
    golden["paid_flag"] = (golden["successful_payment_count"] > 0).astype(int)
    for col in [
        "call_count", "answered_calls", "wa_count", "sms_count", "fv_count",
        "successful_field_contacts", "ptp_count", "kept_ptp_count",
        "n_strategies", "targeting_days", "exclusive_strategy_flag", "complaint_count",
    ]:
        golden[col] = golden[col].fillna(0).astype(int)
    golden["targeted_flag"] = (golden["targeting_days"] > 0).astype(int)
    golden["complaint_flag"] = (golden["complaint_count"] > 0).astype(int)

    # Aliases used in earlier artefacts
    golden["total_recovered"] = golden["net_successful_recovery"]
    golden["payment_count"] = golden["successful_payment_count"]
    return golden


def monthly_from_success(success: pd.DataFrame) -> pd.DataFrame:
    s = success.copy()
    s["month"] = s["event_at"].dt.to_period("M").astype(str)
    m = s.groupby("month").agg(
        successful_payment_count=("payment_id", "nunique"),
        recovery_amount=("amount", "sum"),
    ).reset_index()
    m["days"] = m["month"].map(DAYS_IN_MONTH)
    m["daily_run_rate"] = m["recovery_amount"] / m["days"]
    m["mom_change_pct"] = m["recovery_amount"].pct_change() * 100
    m["normalized_mom_pct"] = m["daily_run_rate"].pct_change() * 100
    m["recovery_cr"] = m["recovery_amount"] / 1e7
    m["daily_run_rate_lakh"] = m["daily_run_rate"] / 1e5
    return m


def attribution_7d(success, calls, wa, sms, fv) -> pd.DataFrame:
    touches = pd.concat(
        [
            calls[["account_id", "event_at"]].assign(channel="VOICE"),
            wa[["account_id", "event_at"]].assign(channel="WHATSAPP"),
            sms[["account_id", "event_at"]].assign(channel="SMS"),
            fv[["account_id", "event_at"]].assign(channel="FIELD"),
        ],
        ignore_index=True,
    )
    touches["event_at"] = parse_ts(touches["event_at"])
    touches = touches.dropna(subset=["event_at", "account_id"]).sort_values("event_at")
    pay = success[["payment_id", "account_id", "event_at", "amount"]].dropna(subset=["event_at"]).sort_values("event_at")
    attr = pd.merge_asof(
        pay,
        touches,
        by="account_id",
        on="event_at",
        direction="backward",
        tolerance=pd.Timedelta(days=7),
    )
    attr["channel"] = attr["channel"].fillna("ORGANIC_SELF_CURE")
    return attr


def local_hour(series: pd.Series, tzs: pd.Series) -> pd.Series:
    """Interpret naive timestamps as UTC, then convert using the row timezone."""
    utc = parse_ts(series).dt.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT")
    hours = np.full(len(series), np.nan, dtype=float)
    for tz in pd.unique(tzs.dropna()):
        mask = (tzs == tz).to_numpy()
        converted = utc.loc[mask].dt.tz_convert(str(tz))
        hours[mask] = converted.dt.hour.to_numpy(dtype=float, na_value=np.nan)
    return pd.Series(hours, index=series.index)


def metric_definitions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["Contact rate", "ANSWERED calls / total unique call_id after exact-dup drop", "Answered is the only status that implies a live ring pickup in this schema"],
            ["RPC rate", "Dispositions in {PTP, PROMISE_TO_PAY, PAID, CALLBACK, DISPUTE, REFUSED, PTP_BROKEN} / all dispositions", "Harmonizes PTP synonyms; excludes NO_CONTACT and WRONG_NUMBER"],
            ["PTP rate", "Canonical PTP dispositions / RPC dispositions", "Promise intensity among right-party contacts, not among all dials"],
            ["PTP kept rate", "promises_to_pay.status = KEPT / all PTP rows", "Includes OPEN/CANCELLED in the denominator so forecasts are not optimistic"],
            ["Recovery rate", "Accounts with ≥1 clean SUCCESS payment / all snapshot accounts (30,000)", "Does not drop WRITEOFF/CLOSED; avoids denominator manipulation"],
            ["Recovery per account", "Clean SUCCESS amount / 30,000 snapshot accounts", "Portfolio productivity, not payer-only average"],
            ["Recovery per agent-hour", "Clean SUCCESS amount / sum(session logout-login hours)", "Payments have no agent_id; this is a portfolio-level proxy only"],
            ["Cost per ₹ recovered", "Not observed in data; scenario costs are labeled assumptions", "Do not treat unit-cost folklore as empirical"],
            ["Channel conversion", "Accounts with a channel touch who later have a clean SUCCESS, vs 7-day last-touch cash share", "Last-touch is association; conversion is not incremental lift"],
            ["Daily run rate", "Clean SUCCESS in month / observed days in month (Aug = 8, not 31)", "Removes calendar-length distortion"],
        ],
        columns=["metric", "definition", "why"],
    )


def build_dq_report(pay_stats, brw_stats, ag_stats, golden, calls, wa, cd, hist, accounts) -> pd.DataFrame:
    rows = [
        ["payments", "Exact duplicate rows", pay_stats["raw_payment_rows"], pay_stats["exact_duplicate_rows"],
         "Drop identical webhook retries", "High: part of SUCCESS inflation"],
        ["payments", "Extra rows sharing a payment_id (500 extra rows, 25,000 unique IDs)", pay_stats["raw_payment_rows"], pay_stats["extra_payment_id_rows"],
         "Keep first exact copy; quarantine conflicting payloads", f"High: SUCCESS extra-row inflation ₹{pay_stats['success_dup_row_inflation']/1e7:.2f} Cr; raw−clean SUCCESS ₹{pay_stats['raw_minus_clean_success']/1e7:.2f} Cr"],
        ["payments", "Conflicting payment_id payloads", pay_stats["clean_unique_payment_rows"] + pay_stats["quarantined_conflict_rows"], pay_stats["quarantined_conflict_rows"],
         "Quarantine all rows for those 14 IDs", "High: unverified ledger events excluded from recovery"],
        ["payments", "payment_reference reused across distinct accounts", pay_stats["raw_payment_rows"], pay_stats["cross_account_payment_reference_rows"],
         "Do not use payment_reference as a unique key; grain is payment_id", f"High: {pay_stats['cross_account_payment_references']} references span multiple accounts"],
        ["payments", "Non-success statuses (FAILED, PENDING, REVERSED)", pay_stats["clean_unique_payment_rows"],
         pay_stats["clean_unique_payment_rows"] - pay_stats["valid_successful_payment_rows"],
         "Recovery metrics use SUCCESS only", "Critical: attempts overstate collected cash"],
        ["borrowers", "Exact duplicate borrower rows", brw_stats["borrower_raw_rows"], brw_stats["borrower_exact_duplicates"],
         "Drop identical rows", "Medium"],
        ["borrowers", "Conflicting profiles for the same borrower_id", brw_stats["borrower_raw_rows"] - brw_stats["borrower_exact_duplicates"], brw_stats["conflicting_borrower_rows"],
         "Keep latest updated_at per borrower_id; flag conflict", f"Critical: {brw_stats['conflicting_borrower_ids']} IDs are not unique entities"],
        ["borrowers", "Missing phone or email on canonical borrowers", brw_stats["unique_borrower_ids"], brw_stats["missing_phone_or_email"],
         "Flag uncontactable; skip-trace before queueing", "Medium: delivery wastage"],
        ["accounts", "Null borrower_id", len(accounts), int(accounts["borrower_id"].isna().sum()),
         "Keep in golden; do not drop from recovery denominator", "High: orphan loans"],
        ["accounts", "borrower_id not present in borrowers table", len(accounts), int(golden["borrower_unmatched_flag"].sum()),
         "Left-join; city/state unknown", "High: geo analysis is incomplete"],
        ["agents", "Many-to-many employee_code and agent_id", ag_stats["agent_rows"], ag_stats["agent_rows"],
         "Scorecards must use employee_code; agent_id is not an identity", f"Critical: {ag_stats['unique_employee_codes']} collectors and {ag_stats['unique_agent_ids']} agent_ids; every ID aliases"],
        ["call_dispositions", "PTP and PROMISE_TO_PAY concurrent synonyms", len(cd), int(cd["disposition_code"].isin(["PTP", "PROMISE_TO_PAY"]).sum()),
         "Map both to canonical PTP; no version cliff detected", "High: fragmented PTP reporting if unharmonized"],
        ["calls", "Missing agent_id", 91350, int(calls["agent_id"].isna().sum()),
         "Attribute to IVR/dialer pool, not human scorecards", "Medium"],
        ["calls", "Exact duplicate call events", 91350, int(pd.read_csv(RAW / "calls.csv").duplicated().sum()),
         "Drop identical dialer retries", "Medium: inflates attempt volume"],
        ["calls", "Naive event_at plus timezone column (UTC / Kolkata / Dubai)", 91350, 91350,
         "Report calling-hour metrics under both 'already local' and 'UTC stored naive' interpretations", "High: hour-of-day targeting can be wrong by 4.0–5.5 hours"],
        ["whatsapp_events", "Uniform synthetic-looking event mix", len(wa), len(wa),
         "Do not treat PAYMENT_CLICK as a causal conversion signal", "High: ~10k rows per event type"],
        ["attribution", "7-day last-touch window leaves most cash unattributed", pay_stats["valid_successful_payment_rows"], None,
         "Report organic self-cure separately from channel last-touch", "Critical"],
        ["reporting", "Calendar MoM (Feb 28d vs Mar 31d)", 8, 2,
         "Primary KPI = daily run rate / observed days", "Critical: explains the +11% claim"],
        ["reporting", "Truncated August window (8 days, not 31)", 8, 1,
         "Do not use calendar-month length for Aug; do not publish -75% MoM", "High"],
        ["targeting", "Accounts absent from daily_targeting (denominator risk)", len(golden), int((golden["targeted_flag"] == 0).sum()),
         "Keep untargeted accounts in recovery rate denominator", "High: conversion would look better if they were dropped"],
        ["account_status_history", "Multiple status rows per account (possible overwrite/late events)", len(hist), len(hist),
         "Use event_at ordered history; snapshot status is not a closed population", "Medium: survivorship risk"],
    ]
    df = pd.DataFrame(rows, columns=["dataset", "issue", "rows_examined", "rows_affected", "treatment", "business_impact"])
    return df


def run(save: bool = True) -> dict:
    payments_raw = load_csv("payments.csv")
    borrowers_raw = load_csv("borrowers.csv")
    accounts = load_csv("accounts.csv")
    agents_raw = load_csv("agents.csv")
    calls_raw = load_csv("calls.csv")
    wa_raw = load_csv("whatsapp_events.csv")
    sms_raw = load_csv("sms_events.csv")
    fv_raw = load_csv("field_visits.csv")
    ptp_raw = load_csv("promises_to_pay.csv")
    dt = load_csv("daily_targeting.csv")
    camp = load_csv("campaigns.csv")
    complaints = load_csv("complaints.csv")
    cd = load_csv("call_dispositions.csv")
    hist = load_csv("account_status_history.csv")
    sessions = load_csv("agent_sessions.csv")
    attempts = load_csv("call_attempts.csv")
    vendors = load_csv("vendor_telephony.csv")

    pay = clean_payments(payments_raw)
    brw = clean_borrowers(borrowers_raw)
    ag = clean_agents(agents_raw)

    calls = calls_raw.drop_duplicates().copy()
    calls["event_at"] = parse_ts(calls["event_at"])
    wa = wa_raw.drop_duplicates().copy()
    wa["event_at"] = parse_ts(wa["event_at"])
    sms = sms_raw.copy()
    sms["event_at"] = parse_ts(sms["event_at"])
    fv = fv_raw.copy()
    fv["event_at"] = parse_ts(fv["event_at"])
    ptp = ptp_raw.copy()
    ptp["event_at"] = parse_ts(ptp["event_at"])

    golden = build_golden(accounts, brw["canonical"], pay["success"], calls, wa, sms, fv, ptp, dt, camp, complaints)
    monthly = monthly_from_success(pay["success"])
    attr = attribution_7d(pay["success"], calls, wa, sms, fv)
    attr_sum = attr.groupby("channel").agg(n=("payment_id", "count"), amount=("amount", "sum")).reset_index()
    attr_sum["pct_cash"] = attr_sum["amount"] / attr_sum["amount"].sum() * 100
    self_cure_pct = float(attr_sum.loc[attr_sum["channel"] == "ORGANIC_SELF_CURE", "pct_cash"].sum())

    # Independent operational metrics
    contact_rate = float((calls["call_status"] == "ANSWERED").mean())
    cd = cd.copy()
    cd["canonical"] = np.where(cd["disposition_code"].isin(["PTP", "PROMISE_TO_PAY"]), "PTP", cd["disposition_code"])
    rpc = cd["disposition_code"].isin(RPC_CODES)
    rpc_rate = float(rpc.mean())
    ptp_among_rpc = float((cd.loc[rpc, "canonical"] == "PTP").mean())
    ptp_kept = float((ptp["status"] == "KEPT").mean())
    recovery_rate = float(golden["paid_flag"].mean())
    recovery_per_account = float(golden["net_successful_recovery"].mean())

    sessions = sessions.copy()
    sessions["login_at"] = parse_ts(sessions["login_at"])
    sessions["logout_at"] = parse_ts(sessions["logout_at"])
    sessions["hours"] = (sessions["logout_at"] - sessions["login_at"]).dt.total_seconds() / 3600.0
    total_agent_hours = float(sessions["hours"].clip(lower=0).sum())
    recovery_per_agent_hour = float(pay["stats"]["clean_success_amount"] / total_agent_hours) if total_agent_hours else np.nan

    field_eff = float(fv["outcome"].isin(FIELD_EFFECTIVE).mean())
    complaint_rate = float(golden["complaint_flag"].mean())

    click_acc = set(wa.loc[wa["event_type"] == "PAYMENT_CLICK", "account_id"])
    paid_acc = set(pay["success"]["account_id"])
    all_acc = set(golden["account_id"])
    no_wa = all_acc - set(wa["account_id"])
    other_wa = set(wa["account_id"]) - click_acc
    wa_click_cure = len(click_acc & paid_acc) / len(click_acc)
    wa_other_cure = len(other_wa & paid_acc) / len(other_wa)
    wa_none_cure = len(no_wa & paid_acc) / len(no_wa)

    # Timezones
    calls["hour_as_local"] = calls["event_at"].dt.hour
    calls["hour_if_utc"] = local_hour(calls["event_at"], calls["timezone"])
    tz_hour = (
        calls.groupby("timezone")
        .agg(
            n=("call_id", "count"),
            answer_rate=("call_status", lambda s: (s == "ANSWERED").mean()),
            mean_hour_naive=("hour_as_local", "mean"),
            mean_hour_as_utc=("hour_if_utc", "mean"),
        )
        .reset_index()
    )
    hour_answer_naive = calls.groupby("hour_as_local").agg(
        n=("call_id", "count"),
        answer_rate=("call_status", lambda s: (s == "ANSWERED").mean()),
    ).reset_index()
    hour_answer_utc = calls.groupby("hour_if_utc").agg(
        n=("call_id", "count"),
        answer_rate=("call_status", lambda s: (s == "ANSWERED").mean()),
    ).reset_index()

    # Vendor mapping
    calls_v = calls.merge(vendors, on="vendor_id", how="left", suffixes=("", "_vendor"))
    vendor_perf = calls_v.groupby(["vendor_name", "schema_version"], dropna=False).agg(
        calls=("call_id", "nunique"),
        answer_rate=("call_status", lambda s: (s == "ANSWERED").mean()),
        missing_agent=("agent_id", lambda s: s.isna().mean()),
    ).reset_index()

    # Attempt frequency
    attempts = attempts.copy()
    att_acc = attempts.groupby("account_id").agg(
        attempt_count=("attempt_id", "nunique"),
        connected=("attempt_status", lambda s: int((s == "CONNECTED").sum())),
    ).reset_index()
    att_join = golden.merge(att_acc, on="account_id", how="left")
    att_join["attempt_count"] = att_join["attempt_count"].fillna(0)
    att_join["attempt_bucket"] = pd.cut(
        att_join["attempt_count"],
        bins=[-0.1, 0, 2, 5, 10, 999],
        labels=["0", "1-2", "3-5", "6-10", "11+"],
    )
    attempt_recovery = att_join.groupby("attempt_bucket", observed=False).agg(
        accounts=("account_id", "count"),
        recovery_rate=("paid_flag", "mean"),
        avg_recovery=("net_successful_recovery", "mean"),
    ).reset_index()

    # Mix / geo / DPD
    mix_dpd = golden.groupby("dpd_bucket").agg(
        accounts=("account_id", "count"),
        recovery_rate=("paid_flag", "mean"),
        recovered=("net_successful_recovery", "sum"),
    ).reset_index()
    mix_loan = golden.groupby("loan_type").agg(
        accounts=("account_id", "count"),
        recovery_rate=("paid_flag", "mean"),
        recovered=("net_successful_recovery", "sum"),
    ).reset_index()
    mix_risk = golden.groupby("risk_segment").agg(
        accounts=("account_id", "count"),
        recovery_rate=("paid_flag", "mean"),
        recovered=("net_successful_recovery", "sum"),
    ).reset_index()
    geo = golden.dropna(subset=["state"]).groupby("state").agg(
        accounts=("account_id", "count"),
        recovery_rate=("paid_flag", "mean"),
        recovered=("net_successful_recovery", "sum"),
    ).reset_index().sort_values("recovered", ascending=False)

    succ_acc = pay["success"].merge(
        golden[["account_id", "dpd_bucket", "loan_type", "risk_segment", "state"]],
        on="account_id",
        how="left",
    )
    succ_acc["month"] = succ_acc["event_at"].dt.to_period("M").astype(str)
    mix_month = succ_acc.groupby(["month", "dpd_bucket"])["amount"].sum().unstack(fill_value=0)
    mix_month_share = mix_month.div(mix_month.sum(axis=1), axis=0) * 100

    # Simpson-style: recovery rate is account-level snapshot, not monthly. Use amount mix instead.
    # Cohort: opened month
    golden["opened_month"] = golden["opened_at"].dt.to_period("M").astype(str)
    cohort = golden.groupby("opened_month").agg(
        accounts=("account_id", "count"),
        recovery_rate=("paid_flag", "mean"),
        recovered=("net_successful_recovery", "sum"),
    ).reset_index()

    targeted = golden.groupby("targeted_flag").agg(
        accounts=("account_id", "count"),
        recovery_rate=("paid_flag", "mean"),
        recovered=("net_successful_recovery", "sum"),
    ).reset_index()

    # Agent tenure at call time (min joined_at per employee, map via agent_id — many-to-many so flag as weak)
    agent_map = agents_raw.copy()
    agent_map["joined_at"] = parse_ts(agent_map["joined_at"])
    emp_join = agent_map.groupby("agent_id")["joined_at"].min()
    calls_t = calls.copy()
    calls_t["agent_joined"] = calls_t["agent_id"].map(emp_join)
    calls_t["tenure_days"] = (calls_t["event_at"] - calls_t["agent_joined"]).dt.days
    calls_t["tenure_bucket"] = pd.cut(
        calls_t["tenure_days"],
        bins=[-1e6, 30, 90, 180, 365, 1e6],
        labels=["<=30d", "31-90d", "91-180d", "181-365d", "365d+"],
    )
    tenure_answer = calls_t.groupby("tenure_bucket", observed=False).agg(
        calls=("call_id", "count"),
        answer_rate=("call_status", lambda s: (s == "ANSWERED").mean()),
    ).reset_index()

    # Part 4: exclusive first-strategy + matching
    excl = golden.loc[golden["exclusive_strategy_flag"] == 1].copy()
    strat_excl = excl.groupby("first_strategy_version").agg(
        accounts=("account_id", "nunique"),
        recovery_rate=("paid_flag", "mean"),
        avg_recovery=("net_successful_recovery", "mean"),
        mean_dpd=("dpd", "mean"),
    ).reset_index()

    first_all = golden.loc[golden["targeted_flag"] == 1].groupby("first_strategy_version").agg(
        accounts=("account_id", "nunique"),
        recovery_rate=("paid_flag", "mean"),
        avg_recovery=("net_successful_recovery", "mean"),
    ).reset_index()

    # Coarse matching: exclusive legacy vs exclusive v3 on dpd_bucket x loan_type x risk_segment
    def matched_lift(df, treated_ver, control_ver="legacy"):
        t = df[df["first_strategy_version"] == treated_ver]
        c = df[df["first_strategy_version"] == control_ver]
        keys = ["dpd_bucket", "loan_type", "risk_segment"]
        t_g = t.groupby(keys)["paid_flag"].agg(["mean", "count"])
        c_g = c.groupby(keys)["paid_flag"].agg(["mean", "count"])
        joined = t_g.join(c_g, lsuffix="_t", rsuffix="_c", how="inner")
        joined = joined[(joined["count_t"] >= 20) & (joined["count_c"] >= 20)]
        if joined.empty:
            return {"treated": treated_ver, "pp_lift": np.nan, "cells": 0, "treated_n": 0}
        w = joined["count_t"]
        lift = float(((joined["mean_t"] - joined["mean_c"]) * w).sum() / w.sum())
        return {
            "treated": treated_ver,
            "pp_lift": lift * 100,
            "cells": int(len(joined)),
            "treated_n": int(w.sum()),
            "control_n": int(joined["count_c"].sum()),
        }

    matching = pd.DataFrame([matched_lift(excl, v) for v in ["v1", "v2", "v3"]])

    # Survivorship: accounts whose latest history status is WRITEOFF vs paid_flag
    hist = hist.copy()
    hist["event_at"] = parse_ts(hist["event_at"])
    latest = hist.sort_values("event_at").groupby("account_id").tail(1)
    latest_status = latest[["account_id", "status"]].rename(columns={"status": "latest_history_status"})
    surv = golden.merge(latest_status, on="account_id", how="left")
    surv_tab = surv.groupby(surv["latest_history_status"].fillna("NO_HISTORY")).agg(
        accounts=("account_id", "count"),
        recovery_rate=("paid_flag", "mean"),
    ).reset_index()

    disp_xtab = pd.crosstab(cd["disposition_code"], cd["disposition_version"])

    feb = monthly.loc[monthly["month"] == "2026-02"].iloc[0]
    mar = monthly.loc[monthly["month"] == "2026-03"].iloc[0]
    raw_success = pay["payments_raw"]
    raw_success = raw_success[raw_success["payment_status"] == "SUCCESS"].copy()
    raw_success["event_at"] = parse_ts(raw_success["event_at"])
    raw_monthly = (
        raw_success.assign(month=lambda d: d["event_at"].dt.to_period("M").astype(str))
        .groupby("month")["amount"].sum()
    )
    raw_feb_mar = float(raw_monthly.get("2026-03", np.nan) / raw_monthly.get("2026-02", np.nan) - 1) * 100

    dq = build_dq_report(pay["stats"], brw["stats"], ag["stats"], golden, calls, wa, cd, hist, accounts)
    # fill attribution rows_affected
    dq.loc[dq["issue"].str.contains("7-day last-touch"), "rows_affected"] = int(
        (attr["channel"] == "ORGANIC_SELF_CURE").sum()
    )

    metrics_df = metric_definitions()

    summary = {
        **pay["stats"],
        **brw["stats"],
        **ag["stats"],
        "observation_start": "2026-01-01",
        "observation_end": "2026-08-08",
        "account_count": int(len(golden)),
        "clean_success_cr": pay["stats"]["clean_success_amount"] / 1e7,
        "feb_clean_cr": float(feb["recovery_cr"]),
        "mar_clean_cr": float(mar["recovery_cr"]),
        "feb_mar_reported_mom_pct": float(mar["mom_change_pct"]),
        "feb_mar_normalized_mom_pct": float(mar["normalized_mom_pct"]),
        "feb_daily_lakh": float(feb["daily_run_rate_lakh"]),
        "mar_daily_lakh": float(mar["daily_run_rate_lakh"]),
        "raw_feb_mar_mom_pct": raw_feb_mar,
        "self_cure_rate_7d_attribution_pct": self_cure_pct,
        "contact_rate_pct": contact_rate * 100,
        "rpc_rate_pct": rpc_rate * 100,
        "ptp_rate_among_rpc_pct": ptp_among_rpc * 100,
        "ptp_kept_rate_pct": ptp_kept * 100,
        "recovery_rate_pct": recovery_rate * 100,
        "recovery_per_account": recovery_per_account,
        "total_agent_hours": total_agent_hours,
        "recovery_per_agent_hour": recovery_per_agent_hour,
        "field_effective_contact_rate_pct": field_eff * 100,
        "complaint_unique_accounts": int(golden["complaint_flag"].sum()),
        "complaint_rate_pct": complaint_rate * 100,
        "wa_click_cure_rate_pct": wa_click_cure * 100,
        "wa_other_cure_rate_pct": wa_other_cure * 100,
        "wa_no_contact_cure_rate_pct": wa_none_cure * 100,
        "untargeted_accounts": int((golden["targeted_flag"] == 0).sum()),
        "targeted_accounts": int((golden["targeted_flag"] == 1).sum()),
        "untargeted_recovery_rate_pct": float(golden.loc[golden["targeted_flag"] == 0, "paid_flag"].mean() * 100),
        "targeted_recovery_rate_pct": float(golden.loc[golden["targeted_flag"] == 1, "paid_flag"].mean() * 100),
        "exclusive_strategy_accounts": int((golden["exclusive_strategy_flag"] == 1).sum()),
        "multi_strategy_accounts": int(((golden["targeted_flag"] == 1) & (golden["exclusive_strategy_flag"] == 0)).sum()),
        "call_exact_duplicates": int(calls_raw.duplicated().sum()),
        "whatsapp_rows": int(len(wa_raw)),
        "whatsapp_exact_duplicates": int(wa_raw.duplicated().sum()),
        "language_field_present": False,
        "client_field_present": False,
    }

    if save:
        golden_out_cols = [
            "account_id", "borrower_id", "loan_type", "principal_amount", "outstanding_amount",
            "dpd", "dpd_bucket", "risk_segment", "status", "opened_at", "timezone", "schema_version",
            "city", "state", "borrower_missing_flag", "borrower_unmatched_flag", "borrower_conflict_flag",
            "net_successful_recovery", "successful_payment_count", "paid_flag", "first_paid", "last_paid",
            "call_count", "answered_calls", "wa_count", "sms_count", "fv_count", "successful_field_contacts",
            "ptp_count", "kept_ptp_count", "targeted_flag", "first_strategy_version", "n_strategies",
            "exclusive_strategy_flag", "complaint_flag", "complaint_count",
            "total_recovered", "payment_count",
        ]
        golden[golden_out_cols].to_csv(ROOT / "golden_account_dataset.csv", index=False)
        monthly.to_csv(ROOT / "monthly_recovery.csv", index=False)
        dq.to_csv(ROOT / "data_quality_report.csv", index=False)
        metrics_df.to_csv(ROOT / "metric_definitions.csv", index=False)
        attr_sum.to_csv(ROOT / "attribution_7d.csv", index=False)
        with open(ROOT / "analysis_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)

        extras = ROOT / "derived"
        extras.mkdir(exist_ok=True)
        mix_dpd.to_csv(extras / "mix_dpd.csv", index=False)
        mix_loan.to_csv(extras / "mix_loan.csv", index=False)
        mix_risk.to_csv(extras / "mix_risk.csv", index=False)
        geo.to_csv(extras / "geo_state.csv", index=False)
        mix_month_share.to_csv(extras / "dpd_recovery_share_by_month.csv")
        targeted.to_csv(extras / "targeted_vs_untargeted.csv", index=False)
        strat_excl.to_csv(extras / "exclusive_strategy_outcomes.csv", index=False)
        first_all.to_csv(extras / "first_strategy_outcomes.csv", index=False)
        matching.to_csv(extras / "strategy_matched_lift.csv", index=False)
        vendor_perf.to_csv(extras / "vendor_performance.csv", index=False)
        attempt_recovery.to_csv(extras / "attempt_frequency.csv", index=False)
        tenure_answer.to_csv(extras / "agent_tenure_answer.csv", index=False)
        tz_hour.to_csv(extras / "timezone_hours.csv", index=False)
        hour_answer_naive.to_csv(extras / "hour_answer_naive.csv", index=False)
        hour_answer_utc.to_csv(extras / "hour_answer_if_utc.csv", index=False)
        cohort.to_csv(extras / "open_cohort.csv", index=False)
        surv_tab.to_csv(extras / "survivorship_latest_status.csv", index=False)
        disp_xtab.to_csv(extras / "disposition_crosstab.csv")

    return {
        "summary": summary,
        "golden": golden,
        "monthly": monthly,
        "dq": dq,
        "attr": attr,
        "attr_sum": attr_sum,
        "matching": matching,
        "strat_excl": strat_excl,
        "first_all": first_all,
        "targeted": targeted,
        "mix_dpd": mix_dpd,
        "mix_loan": mix_loan,
        "geo": geo,
        "vendor_perf": vendor_perf,
        "attempt_recovery": attempt_recovery,
        "tz_hour": tz_hour,
        "metrics_df": metrics_df,
        "disp_xtab": disp_xtab,
        "calls": calls,
        "success": pay["success"],
        "wa": wa,
        "cd": cd,
    }


if __name__ == "__main__":
    out = run(save=True)
    s = out["summary"]
    print("Golden accounts", s["account_count"])
    print("Clean SUCCESS Cr", round(s["clean_success_cr"], 2))
    print("Feb-Mar reported", round(s["feb_mar_reported_mom_pct"], 2), "normalized", round(s["feb_mar_normalized_mom_pct"], 2))
    print("Self-cure % cash", round(s["self_cure_rate_7d_attribution_pct"], 2))
    print("Matching\n", out["matching"])
    print("Exclusive strategy\n", out["strat_excl"])
    print("Targeted vs not\n", out["targeted"])
