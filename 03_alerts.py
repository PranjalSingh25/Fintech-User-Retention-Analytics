"""
Phase 3: Burn-Rate Logic Engine & Automated Alert System
==========================================================
Calculates real-time burn rates, detects cost overruns,
and outputs executive-ready alert summaries + export files
for Power BI ingestion.

ALERT TRIGGER: Actual cumulative spend exceeds planned by >10%

Author: PMO Tracker Project
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_PATH = os.path.join(BASE_DIR, "data", "clean_telemetry.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

ALERT_THRESHOLD     = 0.10   # 10% overrun triggers CRITICAL alert
WARNING_THRESHOLD   = 0.05   # 5%  overrun triggers WARNING

REPORT_TIMESTAMP    = datetime.now().strftime("%Y%m%d_%H%M%S")


# ─────────────────────────────────────────────────────────────────────
# CORE CALCULATION — Burn Rate Metrics
# ─────────────────────────────────────────────────────────────────────
def calculate_burn_rate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds burn-rate columns to every row:
      - burn_rate_pct         : % of planned budget spent so far
      - overrun_pct           : how far over/under budget (positive = over)
      - is_critical_overrun   : True if >10% over
      - is_warning_overrun    : True if >5% but ≤10% over
      - projected_final_spend : linear projection of total spend at current rate
      - projected_overrun_usd : projected overspend vs total planned
    """
    # Burn rate: what % of the cumulative planned budget has been spent
    df["burn_rate_pct"] = (
        df["cumulative_actual_usd"] / df["cumulative_planned_usd"]
    ).replace([np.inf, -np.inf], np.nan).round(4)

    # Overrun pct: positive = over budget, negative = under budget
    df["overrun_pct"] = (df["burn_rate_pct"] - 1.0).round(4)

    # Alert flags
    df["is_critical_overrun"] = df["overrun_pct"] > ALERT_THRESHOLD
    df["is_warning_overrun"]  = (
        (df["overrun_pct"] > WARNING_THRESHOLD) &
        (df["overrun_pct"] <= ALERT_THRESHOLD)
    )

    # Projected final spend (linear extrapolation from current burn rate)
    df["projected_final_spend_usd"] = (
        df["cumulative_actual_usd"] / df["pct_timeline_elapsed"].replace(0, np.nan)
    ).round(2)

    df["projected_overrun_usd"] = (
        df["projected_final_spend_usd"] - df["total_planned_usd"]
    ).round(2)

    # Budget health score 0–100 (100 = perfect, lower = worse)
    # Penalizes both overruns and shipping delays
    overrun_penalty = (df["overrun_pct"].clip(lower=0) * 300).clip(upper=60)
    delay_penalty   = (df["shipping_delay_days"] * 2).clip(upper=20)
    df["health_score"] = (100 - overrun_penalty - delay_penalty).clip(lower=0).round(1)

    return df


# ─────────────────────────────────────────────────────────────────────
# ALERT ENGINE
# ─────────────────────────────────────────────────────────────────────
def run_alert_engine(df: pd.DataFrame) -> pd.DataFrame:
    """
    Scans every row. For each project×date combination where a
    threshold breach occurs, fires a simulated executive alert
    to the terminal and logs it to an alert dataframe.
    """
    print("\n" + "═" * 65)
    print("  🚨  AUTOMATED PMO ALERT ENGINE — RUNNING SCAN")
    print("═" * 65)

    alert_log = []

    # Get the FIRST day each project breaches each threshold
    # (avoid spamming repeated alerts for same project)
    critical_first = (
        df[df["is_critical_overrun"]]
        .groupby("project_id")
        .first()
        .reset_index()
    )

    warning_first = (
        df[df["is_warning_overrun"]]
        .groupby("project_id")
        .first()
        .reset_index()
    )

    # ── CRITICAL ALERTS ───────────────────────────────────────────────
    if len(critical_first) == 0:
        print("\n  ✅  No critical overruns detected.\n")
    else:
        print(f"\n  ⚠️   {len(critical_first)} CRITICAL OVERRUN(S) DETECTED:\n")

    for _, row in critical_first.iterrows():
        overrun_pct_str = f"{row['overrun_pct'] * 100:.1f}%"
        overrun_usd     = row["cumulative_actual_usd"] - row["cumulative_planned_usd"]
        proj_overrun    = row["projected_overrun_usd"]

        # ── SIMULATED EMAIL ALERT ──────────────────────────────────
        alert_msg = (
            f"  ┌─────────────────────────────────────────────────────┐\n"
            f"  │  🔴  CRITICAL ALERT — IMMEDIATE ACTION REQUIRED      │\n"
            f"  ├─────────────────────────────────────────────────────┤\n"
            f"  │  Project   : {row['project_id']} ({row['client']}){'':>2}│\n"
            f"  │  Region    : {row['region']:<42}│\n"
            f"  │  Date      : {str(row['date'])[:10]:<42}│\n"
            f"  │  Status    : {row['deployment_status']:<42}│\n"
            f"  ├─────────────────────────────────────────────────────┤\n"
            f"  │  Burn Rate : {overrun_pct_str} OVER BUDGET                       │\n"
            f"  │  Overrun $ : ${overrun_usd:,.0f} above cumulative plan{'':>10}│\n"
            f"  │  Projected : ${proj_overrun:,.0f} total overrun at completion{'':>3}│\n"
            f"  │  Health    : {row['health_score']}/100                               │\n"
            f"  ├─────────────────────────────────────────────────────┤\n"
            f"  │  ➤ ACTION: Escalate to PMO Director + Finance Lead   │\n"
            f"  │  ➤ Mitigation review required within 24 hours        │\n"
            f"  └─────────────────────────────────────────────────────┘"
        )
        print(alert_msg)

        # Compact version for machine parsing
        print(
            f"  CRITICAL: Project {row['project_id']} exceeds burn rate by "
            f"{overrun_pct_str}. Mitigation required.\n"
        )

        alert_log.append({
            "alert_type":         "CRITICAL",
            "project_id":         row["project_id"],
            "client":             row["client"],
            "region":             row["region"],
            "alert_date":         str(row["date"])[:10],
            "deployment_status":  row["deployment_status"],
            "overrun_pct":        round(row["overrun_pct"] * 100, 2),
            "overrun_usd":        round(overrun_usd, 2),
            "projected_overrun_usd": round(proj_overrun, 2),
            "health_score":       row["health_score"],
        })

    # ── WARNING ALERTS ────────────────────────────────────────────────
    if len(warning_first) > 0:
        print(f"\n  ⚡  {len(warning_first)} WARNING(S) — Monitor Closely:\n")

    for _, row in warning_first.iterrows():
        overrun_pct_str = f"{row['overrun_pct'] * 100:.1f}%"
        overrun_usd     = row["cumulative_actual_usd"] - row["cumulative_planned_usd"]

        print(
            f"  WARNING: Project {row['project_id']} ({row['client']}) | "
            f"+{overrun_pct_str} over budget as of {str(row['date'])[:10]} | "
            f"${overrun_usd:,.0f} variance. Monitoring escalated."
        )

        alert_log.append({
            "alert_type":         "WARNING",
            "project_id":         row["project_id"],
            "client":             row["client"],
            "region":             row["region"],
            "alert_date":         str(row["date"])[:10],
            "deployment_status":  row["deployment_status"],
            "overrun_pct":        round(row["overrun_pct"] * 100, 2),
            "overrun_usd":        round(overrun_usd, 2),
            "projected_overrun_usd": round(row["projected_overrun_usd"], 2),
            "health_score":       row["health_score"],
        })

    alert_df = pd.DataFrame(alert_log)
    print("\n" + "═" * 65)
    return alert_df


# ─────────────────────────────────────────────────────────────────────
# EXECUTIVE SUMMARY TABLE
# ─────────────────────────────────────────────────────────────────────
def build_executive_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Produces one summary row per project — the Power BI KPI feed.
    """
    latest = df.sort_values("date").groupby("project_id").last().reset_index()

    summary = latest[[
        "project_id", "client", "region", "fleet_size",
        "deployment_status", "pct_timeline_elapsed",
        "cumulative_planned_usd", "cumulative_actual_usd",
        "overrun_pct", "projected_final_spend_usd",
        "projected_overrun_usd", "total_planned_usd",
        "health_score", "is_critical_overrun", "is_warning_overrun",
    ]].copy()

    summary["overrun_pct_display"]     = (summary["overrun_pct"] * 100).round(1)
    summary["pct_timeline_display"]    = (summary["pct_timeline_elapsed"] * 100).round(1)
    summary["status_flag"] = summary.apply(
        lambda r: "🔴 CRITICAL" if r["is_critical_overrun"]
        else ("🟡 WARNING" if r["is_warning_overrun"] else "🟢 ON TRACK"),
        axis=1
    )

    return summary.sort_values("overrun_pct", ascending=False)


# ─────────────────────────────────────────────────────────────────────
# EXPORT FOR POWER BI
# ─────────────────────────────────────────────────────────────────────
def export_powerbi_files(df: pd.DataFrame, alerts: pd.DataFrame, summary: pd.DataFrame):
    """
    Exports three CSVs optimised for Power BI import:
      1. fact_daily_telemetry.csv  — full grain data
      2. dim_alert_log.csv         — alert events only
      3. kpi_executive_summary.csv — one row per project
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    telemetry_path = os.path.join(OUTPUT_DIR, "fact_daily_telemetry.csv")
    alerts_path    = os.path.join(OUTPUT_DIR, "dim_alert_log.csv")
    summary_path   = os.path.join(OUTPUT_DIR, "kpi_executive_summary.csv")

    # Power BI prefers ISO dates as strings
    df_export = df.copy()
    df_export["date"] = df_export["date"].dt.strftime("%Y-%m-%d")

    df_export.to_csv(telemetry_path, index=False)
    alerts.to_csv(alerts_path, index=False)
    summary.to_csv(summary_path, index=False)

    print("\n  📁  Power BI Export Files:")
    print(f"     → {telemetry_path}  ({len(df_export):,} rows)")
    print(f"     → {alerts_path}  ({len(alerts)} alerts)")
    print(f"     → {summary_path}  ({len(summary)} projects)")


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────
def run_alerts():
    print("=" * 65)
    print("  PMO TRACKER — Phase 3: Burn-Rate Engine & Alert System")
    print("=" * 65)

    if not os.path.exists(CLEAN_PATH):
        sys.exit("  ✗  clean_telemetry.csv not found. Run 02_pipeline.py first.")

    df = pd.read_csv(CLEAN_PATH, parse_dates=["date"])
    print(f"\n  ✓  Loaded clean dataset: {len(df):,} rows")

    df = calculate_burn_rate(df)
    print("  ✓  Burn-rate metrics calculated")

    alerts   = run_alert_engine(df)
    summary  = build_executive_summary(df)

    # Print executive summary table
    print("\n  📊  EXECUTIVE PROJECT SUMMARY")
    print("  " + "─" * 85)
    print(f"  {'ID':<9} {'CLIENT':<35} {'STATUS':<28} {'BURN':<8} {'HEALTH'}")
    print("  " + "─" * 85)
    for _, row in summary.iterrows():
        print(
            f"  {row['project_id']:<9} "
            f"{row['client'][:34]:<35} "
            f"{row['status_flag']:<28} "
            f"{row['overrun_pct_display']:>+5.1f}%  "
            f"{row['health_score']:.0f}/100"
        )
    print("  " + "─" * 85)

    export_powerbi_files(df, alerts, summary)

    print(f"\n  ✅  Alert engine complete.")
    print("=" * 65)

    return df, alerts, summary


if __name__ == "__main__":
    run_alerts()
