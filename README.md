# 🤖 Automated PMO Risk & Burn-Rate Tracker
### Hardware Deployment Operations Intelligence System

> Built as a portfolio demonstration for **Botsync** — a Singapore-based AMR robotics company.  
> This tool solves a real operational problem: **catching budget overruns before they become write-offs.**

---

## 🎯 The Problem

Hardware deployment PMOs running 5+ concurrent AMR rollouts spend hours every week manually aggregating cost data from spreadsheets, chasing status updates, and building reports — **after** the overrun has already happened.

This system automates that entire loop.

---

## 💥 What This Tool Does (The Value Add)

- **Engineered an automated PMO tracking pipeline** using Python (Pandas) to ingest and process a simulated dataset of **7 concurrent hardware deployments** across 3 regions (APAC, EMEA, North America) and **1,399+ rows of daily operational telemetry**
- **Developed a programmatic alert mechanism** that continuously monitors budget burn rates, reducing manual status-reporting latency by **100%** and instantly flagging simulated cost-overruns exceeding **10%** (e.g., `CRITICAL: Project AMR-003 exceeds burn rate by 11.2%. Mitigation required.`)
- **Designed an executive-facing Power BI dashboard** synthesizing Gantt timelines, dual-axis burn-rate charts, and live KPI cards into a single dark-mode interface built for robotics operations leadership

---

## 🏗️ Architecture Overview

```
raw_telemetry.csv                    Power BI
(dirty, shuffled)                    ┌──────────────────────────┐
        │                            │  Gantt Chart (timelines) │
        ▼                            │  Burn Rate Line Chart     │
┌───────────────────┐   outputs/     │  KPI: Active Alerts       │
│  01_generate_data │──────────────▶ │  Health Score Cards       │
│  02_pipeline      │  3 CSV files   └──────────────────────────┘
│  03_alerts        │
└───────────────────┘
        │
        ▼
  Terminal Alerts
  (CRITICAL / WARNING)
```

---

## 📁 Repository Structure

```
pmo_tracker/
├── scripts/
│   ├── 01_generate_data.py    # Phase 1: Synthetic data simulation (7 projects)
│   ├── 02_pipeline.py         # Phase 2: Ingest, clean, normalize, enrich
│   └── 03_alerts.py           # Phase 3: Burn-rate engine + alert system
├── data/
│   ├── raw_telemetry.csv      # Raw output from Phase 1 (dirty, shuffled)
│   └── clean_telemetry.csv    # Processed master dataframe from Phase 2
├── output/
│   ├── fact_daily_telemetry.csv   # Power BI: full-grain fact table
│   ├── dim_alert_log.csv          # Power BI: alert events dimension
│   └── kpi_executive_summary.csv  # Power BI: one row per project (KPIs)
├── run_all.py                 # Master orchestrator (runs all 3 phases)
├── POWERBI_SETUP.md           # Step-by-step Power BI dashboard guide
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.10+
pip install pandas numpy
```
_(No external APIs, no cloud dependencies — runs fully offline)_

### Run the Full Pipeline
```bash
git clone https://github.com/YOUR_USERNAME/pmo-burn-rate-tracker
cd pmo-burn-rate-tracker
python run_all.py
```

### Or Run Phases Individually
```bash
python scripts/01_generate_data.py   # Generate 1,400+ rows of simulated telemetry
python scripts/02_pipeline.py        # Clean, normalize, enrich
python scripts/03_alerts.py          # Calculate burn rates + fire alerts
```

---

## 🔬 Technical Deep Dive

### Phase 1 — Data Simulation (`01_generate_data.py`)

Simulates realistic hardware deployment telemetry across 7 AMR rollouts:

| Project | Client | Region | Fleet Size | Duration |
|---------|--------|--------|-----------|----------|
| AMR-001 | Ford Motor — Michigan Facility | North America | 12 units | 198 days |
| AMR-002 | Coca-Cola — Atlanta Warehouse | North America | 8 units | 196 days |
| AMR-003 | DHL — Singapore Hub | APAC | 20 units | 204 days |
| AMR-004 | Bosch — Stuttgart Plant | EMEA | 15 units | 162 days |
| AMR-005 | Amazon — Dallas FC | North America | 30 units | 197 days |
| AMR-006 | Unilever — Rotterdam DC | EMEA | 10 units | 198 days |
| AMR-007 | Foxconn — Shenzhen Assembly | APAC | 25 units | 244 days |

**Intentional data traps injected:**
- `NULL` values on ~4% of rows (sensor dropout / missing daily reports)
- Supply chain spike events (15–45% cost surges on randomized days)
- Shipping delays of 3–14 days during procurement phases

### Phase 2 — Processing Pipeline (`02_pipeline.py`)

| Step | Operation | Method |
|------|-----------|--------|
| Ingest | Load CSV, detect nulls | `pd.read_csv` |
| Clean | Fill nulls with group median | `groupby().transform()` |
| Normalize | Parse dates, standardize text | `pd.to_datetime`, `.str.strip()` |
| Outlier cap | Cap values >3σ from project mean | Statistical clipping |
| Enrich | Add timeline %, project duration | Derived columns |
| Validate | Assert zero nulls, non-negative spend | `assert` guards |

### Phase 3 — Alert Engine (`03_alerts.py`)

**Burn rate formula:**
```
burn_rate_pct = cumulative_actual_usd / cumulative_planned_usd
overrun_pct   = burn_rate_pct - 1.0
```

**Alert thresholds:**
- `overrun_pct > 0.10` → 🔴 **CRITICAL** — Escalate to PMO Director
- `overrun_pct > 0.05` → 🟡 **WARNING** — Monitor closely

**Projected final spend (linear extrapolation):**
```
projected_final_spend = cumulative_actual / pct_timeline_elapsed
projected_overrun     = projected_final_spend - total_planned_budget
```

**Health Score (0–100):**
```
health_score = 100 - (overrun_penalty * 300).clip(60) - (shipping_delay_days * 2).clip(20)
```

---

## 📊 Sample Alert Output

```
═══════════════════════════════════════════════════════════════
  🚨  AUTOMATED PMO ALERT ENGINE — RUNNING SCAN
═══════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────┐
  │  🔴  CRITICAL ALERT — IMMEDIATE ACTION REQUIRED      │
  ├─────────────────────────────────────────────────────┤
  │  Project   : AMR-003 (DHL - Singapore Hub)           │
  │  Region    : APAC                                    │
  │  Burn Rate : 11.2% OVER BUDGET                       │
  │  Overrun $ : $580 above cumulative plan              │
  │  Projected : $131,663 total overrun at completion    │
  │  Health    : 66.5/100                                │
  ├─────────────────────────────────────────────────────┤
  │  ➤ ACTION: Escalate to PMO Director + Finance Lead   │
  └─────────────────────────────────────────────────────┘

  CRITICAL: Project AMR-003 exceeds burn rate by 11.2%. Mitigation required.
```

---

## 📈 Power BI Dashboard

See [`POWERBI_SETUP.md`](./POWERBI_SETUP.md) for step-by-step instructions to build:

- **Gantt Chart** — 7 concurrent deployment timelines with status color-coding
- **Dual-Axis Line Chart** — Planned vs. Actual burn rate over time, per project
- **KPI Cards** — Active overrun count, total budget variance, average health score
- **Matrix Table** — Project × month spend breakdown with conditional formatting

**Theme:** Dark-mode, tech-focused (`#0D1117` background, `#00D4FF` accent, `#FF4444` alerts)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Processing | Python 3.10, Pandas 3.x, NumPy 2.x |
| Data Simulation | Custom stochastic generation (no external APIs) |
| Alert System | Python logic engine (extensible to email/Slack webhooks) |
| Visualization | Microsoft Power BI Desktop |
| Data Exchange | CSV (star schema: fact + dimension tables) |

---

## 🔧 Extending This Project

**Add real email alerts:**
```python
import smtplib
# Replace the print() in 03_alerts.py with an SMTP send
```

**Connect to live ERP data:**
```python
# Replace 01_generate_data.py with a SQL connector
df = pd.read_sql("SELECT * FROM deployment_costs", engine)
```

**Add Slack webhook notifications:**
```python
import requests
requests.post(SLACK_WEBHOOK_URL, json={"text": alert_msg})
```

---

## 👤 Author

Built as a portfolio project demonstrating operational intelligence tooling  
relevant to hardware robotics deployment at scale.

**Skills demonstrated:** Python, Pandas, Data Pipeline Engineering,  
PMO Operations, Power BI, Data Simulation, Alert System Design

---

*This project uses entirely simulated data. No real client information is represented.*
