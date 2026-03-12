"""
Phase 1: Data Simulation Engine
================================
Generates 10,000+ rows of synthetic AMR deployment telemetry
for 7 concurrent hardware projects. Intentionally injects dirty data
(nulls, spikes, delays) to simulate real operational chaos.

Author: PMO Tracker Project
"""

import pandas as pd
import numpy as np
import random
import os
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "raw_telemetry.csv")

# ─────────────────────────────────────────────
# PROJECT DEFINITIONS
# ─────────────────────────────────────────────
PROJECTS = [
    {
        "project_id": "AMR-001",
        "client":     "Ford Motor - Michigan Facility",
        "start_date": "2024-01-15",
        "end_date":   "2024-07-31",
        "planned_daily_budget": 4200,
        "fleet_size": 12,
        "region": "North America",
    },
    {
        "project_id": "AMR-002",
        "client":     "Coca-Cola - Atlanta Warehouse",
        "start_date": "2024-02-01",
        "end_date":   "2024-08-15",
        "planned_daily_budget": 3800,
        "fleet_size": 8,
        "region": "North America",
    },
    {
        "project_id": "AMR-003",
        "client":     "DHL - Singapore Hub",
        "start_date": "2024-03-10",
        "end_date":   "2024-09-30",
        "planned_daily_budget": 5100,
        "fleet_size": 20,
        "region": "APAC",
    },
    {
        "project_id": "AMR-004",
        "client":     "Bosch - Stuttgart Plant",
        "start_date": "2024-01-20",
        "end_date":   "2024-06-30",
        "planned_daily_budget": 4700,
        "fleet_size": 15,
        "region": "EMEA",
    },
    {
        "project_id": "AMR-005",
        "client":     "Amazon - Dallas FC",
        "start_date": "2024-04-01",
        "end_date":   "2024-10-15",
        "planned_daily_budget": 6200,
        "fleet_size": 30,
        "region": "North America",
    },
    {
        "project_id": "AMR-006",
        "client":     "Unilever - Rotterdam DC",
        "start_date": "2024-02-15",
        "end_date":   "2024-08-31",
        "planned_daily_budget": 3500,
        "fleet_size": 10,
        "region": "EMEA",
    },
    {
        "project_id": "AMR-007",
        "client":     "Foxconn - Shenzhen Assembly",
        "start_date": "2024-05-01",
        "end_date":   "2024-12-31",
        "planned_daily_budget": 5800,
        "fleet_size": 25,
        "region": "APAC",
    },
]

DEPLOYMENT_STATUSES = [
    "Planning", "Hardware Procurement", "Staging & Config",
    "Site Installation", "UAT", "Go-Live", "Monitoring", "Closed"
]

STATUS_PROGRESSION = {
    0.00: "Planning",
    0.10: "Hardware Procurement",
    0.25: "Staging & Config",
    0.40: "Site Installation",
    0.65: "UAT",
    0.80: "Go-Live",
    0.90: "Monitoring",
    1.00: "Closed",
}


def get_status(progress: float) -> str:
    for threshold, status in sorted(STATUS_PROGRESSION.items(), reverse=True):
        if progress >= threshold:
            return status
    return "Planning"


# ─────────────────────────────────────────────
# ROW GENERATOR
# ─────────────────────────────────────────────
def generate_project_rows(project: dict) -> list[dict]:
    rows = []
    start = datetime.strptime(project["start_date"], "%Y-%m-%d")
    end   = datetime.strptime(project["end_date"],   "%Y-%m-%d")
    total_days = (end - start).days
    planned_daily = project["planned_daily_budget"]

    # Inject spike events on random days (supply chain shocks)
    spike_days = set(random.sample(range(total_days), k=max(3, total_days // 30)))
    # Inject null rows on random days (sensor dropout)
    null_days  = set(random.sample(range(total_days), k=max(5, total_days // 25)))

    cumulative_actual = 0.0
    cumulative_planned = 0.0

    for day_offset in range(total_days):
        current_date = start + timedelta(days=day_offset)
        progress     = day_offset / total_days
        status       = get_status(progress)

        planned_spend_today = planned_daily * np.random.normal(1.0, 0.05)

        # Base actual spend with natural variance
        actual_spend_today = planned_daily * np.random.normal(1.02, 0.08)

        # Inject cost overrun spike
        if day_offset in spike_days:
            actual_spend_today *= np.random.uniform(1.15, 1.45)  # 15-45% spike

        # Hardware cost breakdown
        hw_actual  = actual_spend_today  * np.random.uniform(0.55, 0.70)
        hw_planned = planned_spend_today * 0.60

        # Labor hours (8-12 hrs/unit/day)
        labor_hours = project["fleet_size"] * np.random.uniform(8, 12)

        # Shipping delays (0 normally, spike during supply chain events)
        if day_offset in spike_days and "Hardware Procurement" in status:
            shipping_delay = int(np.random.choice([3, 5, 7, 10, 14]))
        else:
            shipping_delay = int(np.random.choice([0, 0, 0, 1, 2], p=[0.75, 0.10, 0.07, 0.05, 0.03]))

        cumulative_actual  += actual_spend_today
        cumulative_planned += planned_spend_today

        row = {
            "date":                    current_date.strftime("%Y-%m-%d"),
            "project_id":              project["project_id"],
            "client":                  project["client"],
            "region":                  project["region"],
            "fleet_size":              project["fleet_size"],
            "deployment_status":       status,
            "planned_daily_spend_usd": round(planned_spend_today, 2),
            "actual_daily_spend_usd":  round(actual_spend_today,  2),
            "hw_cost_actual_usd":      round(hw_actual,  2),
            "hw_cost_planned_usd":     round(hw_planned, 2),
            "labor_hours":             round(labor_hours, 1),
            "shipping_delay_days":     shipping_delay,
            "cumulative_planned_usd":  round(cumulative_planned, 2),
            "cumulative_actual_usd":   round(cumulative_actual,  2),
            "is_spike_day":            day_offset in spike_days,
        }

        # ── INJECT DIRTY DATA (null rows) ──────────────────
        if day_offset in null_days:
            dirty_field = random.choice([
                "actual_daily_spend_usd",
                "labor_hours",
                "shipping_delay_days",
                "hw_cost_actual_usd",
            ])
            row[dirty_field] = None  # simulate sensor dropout / missing report

        rows.append(row)

    return rows


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  PMO TRACKER — Phase 1: Data Simulation")
    print("=" * 60)

    all_rows = []
    for project in PROJECTS:
        rows = generate_project_rows(project)
        all_rows.extend(rows)
        print(f"  ✓  {project['project_id']} ({project['client']}) → {len(rows):,} rows generated")

    df = pd.DataFrame(all_rows)

    # Shuffle to simulate real ingestion chaos
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\n  Total rows generated : {len(df):,}")
    print(f"  Projects             : {df['project_id'].nunique()}")
    print(f"  Null values injected : {df.isnull().sum().sum()}")
    print(f"  Spike days injected  : {df['is_spike_day'].sum()}")
    print(f"\n  ✅  Saved → {OUTPUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
