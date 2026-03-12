"""
run_all.py — Master Orchestrator
==================================
Runs all three PMO Tracker phases in sequence:
  Phase 1 → Generate simulated telemetry data
  Phase 2 → Clean & process through the pipeline
  Phase 3 → Calculate burn rates & fire alerts

Usage:
    python run_all.py
"""

import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))

from scripts.generate_data import main as phase1    # noqa: E402
from scripts.pipeline import run_pipeline as phase2  # noqa: E402
from scripts.alerts import run_alerts as phase3      # noqa: E402


def main():
    print("\n" + "█" * 65)
    print("  AUTOMATED PMO RISK & BURN-RATE TRACKER")
    print("  Botsync — Hardware Deployment Operations")
    print("█" * 65)

    # Phase 1
    print("\n\n▶  PHASE 1 — DATA SIMULATION")
    phase1()

    # Phase 2
    print("\n\n▶  PHASE 2 — PROCESSING PIPELINE")
    phase2()

    # Phase 3
    print("\n\n▶  PHASE 3 — BURN-RATE ENGINE & ALERTS")
    phase3()

    print("\n\n" + "█" * 65)
    print("  ✅  ALL PHASES COMPLETE")
    print("  Output files ready in /output/ — import to Power BI")
    print("█" * 65 + "\n")


if __name__ == "__main__":
    main()
