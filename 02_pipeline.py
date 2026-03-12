"""
Phase 2: Processing Pipeline
==============================
Ingests raw telemetry CSV, performs full data cleaning,
normalization, and outputs a master dataframe ready for
burn-rate logic and Power BI consumption.

Author: PMO Tracker Project
"""

import pandas as pd
import numpy as np
import os
import sys

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH    = os.path.join(BASE_DIR, "data", "raw_telemetry.csv")
CLEAN_PATH  = os.path.join(BASE_DIR, "data", "clean_telemetry.csv")
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")


# ─────────────────────────────────────────────
# STEP 1 — INGEST
# ─────────────────────────────────────────────
def ingest(path: str) -> pd.DataFrame:
    print("\n[1/5] Ingesting raw telemetry...")
    if not os.path.exists(path):
        sys.exit(f"  ✗  File not found: {path}\n  Run 01_generate_data.py first.")
    df = pd.read_csv(path, low_memory=False)
    print(f"  ✓  Loaded {len(df):,} rows × {len(df.columns)} columns")
    print(f"  ⚠  Null values detected: {df.isnull().sum().sum()}")
    return df


# ─────────────────────────────────────────────
# STEP 2 — CLEAN
# ─────────────────────────────────────────────
def clean(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[2/5] Cleaning & normalizing...")

    original_len = len(df)

    # Normalize dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    invalid_dates = df["date"].isnull().sum()
    if invalid_dates > 0:
        print(f"  ⚠  Dropping {invalid_dates} rows with unparseable dates")
        df = df.dropna(subset=["date"])

    # Sort by project + date for cumulative calculations
    df = df.sort_values(["project_id", "date"]).reset_index(drop=True)

    # ── Fill numeric nulls with group median (forward-fill strategy) ──
    numeric_cols = [
        "actual_daily_spend_usd",
        "hw_cost_actual_usd",
        "labor_hours",
        "shipping_delay_days",
    ]
    for col in numeric_cols:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            # Group median fill — preserves project-level cost patterns
            df[col] = df.groupby("project_id")[col].transform(
                lambda x: x.fillna(x.median())
            )
            print(f"  ✓  {col}: filled {null_count} nulls with group median")

    # ── Clip extreme outliers (>3 SD from project mean) ─────────────
    for col in ["actual_daily_spend_usd", "hw_cost_actual_usd"]:
        grp = df.groupby("project_id")[col]
        mean = grp.transform("mean")
        std  = grp.transform("std")
        outlier_mask = (df[col] - mean).abs() > 3 * std
        outlier_count = outlier_mask.sum()
        if outlier_count:
            df.loc[outlier_mask, col] = mean + 2.5 * std  # cap, don't drop
            print(f"  ✓  {col}: capped {outlier_count} statistical outliers (>3σ)")

    # ── Standardize text columns ──────────────────────────────────────
    df["client"]            = df["client"].str.strip()
    df["region"]            = df["region"].str.strip().str.upper()
    df["deployment_status"] = df["deployment_status"].str.strip()

    # ── Derived columns ───────────────────────────────────────────────
    df["month"]           = df["date"].dt.to_period("M").astype(str)
    df["week"]            = df["date"].dt.isocalendar().week.astype(int)
    df["day_of_week"]     = df["date"].dt.day_name()
    df["is_weekend"]      = df["date"].dt.weekday >= 5

    # Daily variance
    df["daily_spend_variance_usd"] = (
        df["actual_daily_spend_usd"] - df["planned_daily_spend_usd"]
    ).round(2)

    print(f"  ✓  Cleaned: {original_len:,} → {len(df):,} rows")
    print(f"  ✓  Remaining nulls: {df.isnull().sum().sum()}")
    return df


# ─────────────────────────────────────────────
# STEP 3 — RECALCULATE CUMULATIVE SPEND
# ─────────────────────────────────────────────
def recalculate_cumulative(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[3/5] Recalculating cumulative spend (post-cleaning)...")
    df["cumulative_actual_usd"] = (
        df.groupby("project_id")["actual_daily_spend_usd"]
        .cumsum()
        .round(2)
    )
    df["cumulative_planned_usd"] = (
        df.groupby("project_id")["planned_daily_spend_usd"]
        .cumsum()
        .round(2)
    )
    print("  ✓  Cumulative spend columns refreshed")
    return df


# ─────────────────────────────────────────────
# STEP 4 — ENRICH WITH PROJECT METADATA
# ─────────────────────────────────────────────
def enrich(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[4/5] Enriching with project-level metadata...")

    project_meta = df.groupby("project_id").agg(
        project_start_date = ("date", "min"),
        project_end_date   = ("date", "max"),
        total_planned_usd  = ("planned_daily_spend_usd", "sum"),
    ).reset_index()

    df = df.merge(project_meta, on="project_id", how="left")

    df["days_elapsed"] = (df["date"] - df["project_start_date"]).dt.days + 1
    df["project_duration_days"] = (
        (df["project_end_date"] - df["project_start_date"]).dt.days + 1
    )
    df["pct_timeline_elapsed"] = (
        df["days_elapsed"] / df["project_duration_days"]
    ).round(4)

    print("  ✓  Added: project start/end, duration, timeline %, total planned budget")
    return df


# ─────────────────────────────────────────────
# STEP 5 — VALIDATE & SAVE
# ─────────────────────────────────────────────
def validate_and_save(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[5/5] Validating & saving clean master dataset...")

    assert df["date"].isnull().sum() == 0,              "DATE nulls remain"
    assert df["project_id"].isnull().sum() == 0,        "PROJECT_ID nulls remain"
    assert df["actual_daily_spend_usd"].isnull().sum() == 0, "SPEND nulls remain"
    assert (df["actual_daily_spend_usd"] >= 0).all(),   "Negative spend values"

    os.makedirs(os.path.dirname(CLEAN_PATH), exist_ok=True)
    df.to_csv(CLEAN_PATH, index=False)
    print(f"  ✓  Saved clean CSV → {CLEAN_PATH}")

    # Summary stats
    print("\n  ── Dataset Summary ──────────────────────────────────")
    print(f"  Total rows          : {len(df):,}")
    print(f"  Projects            : {df['project_id'].nunique()}")
    print(f"  Date range          : {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  Total planned spend : ${df.groupby('project_id')['planned_daily_spend_usd'].sum().sum():,.0f}")
    print(f"  Total actual spend  : ${df.groupby('project_id')['actual_daily_spend_usd'].sum().sum():,.0f}")
    print(f"  Regions             : {sorted(df['region'].unique())}")
    print("  ─────────────────────────────────────────────────────")

    return df


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def run_pipeline() -> pd.DataFrame:
    print("=" * 60)
    print("  PMO TRACKER — Phase 2: Processing Pipeline")
    print("=" * 60)

    df = ingest(RAW_PATH)
    df = clean(df)
    df = recalculate_cumulative(df)
    df = enrich(df)
    df = validate_and_save(df)

    print(f"\n  ✅  Pipeline complete. Master dataframe: {df.shape}")
    print("=" * 60)
    return df


if __name__ == "__main__":
    run_pipeline()
