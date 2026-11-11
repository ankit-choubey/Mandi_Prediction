# Suryansh — Mandi Prediction Research Workspace

**Investigator:** Suryansh  
**Focus Area:** Crop Suitability Research, Informative Feature Discovery, and Classification-Model Evaluation  
**Reference Codebase:** [`../Mandi_Prediction`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction) (Local clone, kept strictly read-only on `main`)  
**Status:** Active — Master Project Audit Completed; Awaiting User Sign-Off on Prompt 3 Decisions  

> [!IMPORTANT]
> **Consolidated Master Document:**  
> The complete, exhaustive audit report detailing every dataset, calculation, external source, crop profile, baseline metric, confusion matrix, and risk analysis is available in:  
> 📄 **[`MASTER_PROJECT_AUDIT.md`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work/MASTER_PROJECT_AUDIT.md)**

---

## 1. Project Purpose & Scope

This workspace houses independent empirical research and evaluation on agricultural market condition classification across APMC wholesale mandis in Uttar Pradesh. 

The primary objectives are:
1. **Crop Suitability Research:** Collect and analyze empirical evidence across candidate crops (**Potato**, **Onion**, **Tomato**, and **Wheat**) across historical price continuity, geographic coverage, reporting volume, volatility dynamics, and post-harvest storage feasibility.
2. **Informative Feature Discovery:** Identify and validate predictive signals (arrival volumes via CEDA, agroclimatological weather signals via NASA POWER/IMD, spatial neighbor price arbitrage, and causal momentum) while strictly avoiding lookahead leakage.
3. **Classification-Model Evaluation:** Rigorously evaluate multi-class classification models against naive baselines and decision-theoretic economic outcomes, with horizon-aware chronological validation.

---

## 2. Approved Crop Scope & Baseline Performance Summary

Evaluated on the held-out **Exploratory Test Partition** ($N = 9,551$; May 09 to August 25, 2026) using the audited Phase 5 model predictions:

| Crop | Role in Research | 7d Class Balance (DEC-015) | Naive Baseline Acc | Model Test Acc | Accuracy Lift | Balanced Acc | Macro F1 | Status & Verdict |
|---|---|---|---|---|---|---|---|---|
| **Onion** | Main Study | **Normal: 44.4%**, Unfav: 33.1%, Fav: 22.5% | 47.89% | **56.05%** | **+8.16%** | **52.21%** | **0.5070** | **Optimal multi-class benchmark; balanced detection** |
| **Potato** | Main Study | Normal: 55.2%, Unfav: 28.3%, Fav: 16.5% | 76.92% | **61.19%** | **-15.73%** | **59.51%** | **0.5368** | **Highest Macro F1; catches 73.6% of minority rallies** |
| **Tomato** | Exploratory Price Classification Only | Unfav: 41.1%, Fav: 33.6%, Normal: 25.3% | 51.17% | **53.22%** | **+2.05%** | **48.17%** | **0.4858** | **Directional only; strictly no ambient storage advice** |
| **Wheat** | Main Study (Severe Class Imbalance) | **Normal: 87.1%**, Fav: 6.5%, Unfav: 6.3% | 87.25% | **85.93%** | **-1.32%** | **34.13%** | **0.3313** | **Majority collapse; evaluate on Balanced Acc only** |

---

## 3. Raw Datasets Audited (160,192 Raw Records)

All 5 original district files in `Mandi_Prediction/data/raw/*.csv` share an identical 11-column schema:
- `Arrival_Date`, `Commodity`, `Commodity_Code`, `District`, `Grade`, `Market`, `Max_Price`, `Min_Price`, `Modal_Price`, `State`, `Variety`

| District File | Path | Size | Raw Records | Calendar Span | Missingness | Arrival Volume |
|---|---|---|---|---|---|---|
| `Gaziabaad.csv` | [`data/raw/Gaziabaad.csv`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/raw/Gaziabaad.csv) | 3.49 MB | 41,495 | 731 days (2024–2026) | 0.00% | **Absent** |
| `Jhansi.csv` | [`data/raw/Jhansi.csv`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/raw/Jhansi.csv) | 1.86 MB | 23,625 | 731 days (2024–2026) | 0.00% | **Absent** |
| `Kanpur.csv` | [`data/raw/Kanpur.csv`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/raw/Kanpur.csv) | 3.53 MB | 42,644 | 731 days (2024–2026) | 0.00% | **Absent** |
| `Lukhnow.csv` | [`data/raw/Lukhnow.csv`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/raw/Lukhnow.csv) | 1.76 MB | 21,063 | 731 days (2024–2026) | 0.00% | **Absent** |
| `Unnao.csv` | [`data/raw/Unnao.csv`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/raw/Unnao.csv) | 2.45 MB | 31,365 | 731 days (2024–2026) | 0.00% | **Absent** |
| **TOTAL** | — | **13.09 MB** | **160,192** | **731 Calendar Days** | **0.00%** | **Absent (Sourced via CEDA)** |

---

## 4. External Data Sources Investigated

1. **AGMARKNET ([data.gov.in](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)):** Verified official price source; confirms arrival volumes are absent in core price tables.
2. **CEDA Agri-Market ([api.ceda.ashoka.edu.in](https://api.ceda.ashoka.edu.in/documentation/)):** Open REST API (`POST /agmarknet/quantities`) providing daily **arrival quantities** across 2,700+ mandis.
3. **NASA POWER Agroclimatology ([power.larc.nasa.gov](https://power.larc.nasa.gov/api/temporal/daily/point)):** Open REST API providing daily precipitation (`PRECTOTCORR`) and temperatures (`T2M_MAX`, `T2M_MIN`) by lat/long coordinates.
4. **IMD Gridded Climate ([imdpune.gov.in](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_1_NetCDF.html)):** $0.25^\circ \times 0.25^\circ$ NetCDF rainfall grids; annual release latency.
5. **UPAg ([data.upag.gov.in/docs](https://data.upag.gov.in/docs)):** Area, production, yield statistics; requires registered institutional login.
6. **ICAR-CIPHET Loss Studies:** Benchmark losses: Wheat (4.9%), Potato (7.3%), Onion (8.2%), Tomato (12.4%).
7. **CWC Tariffs:** Regional UP warehouse slabs: ₹17.29 to ₹20.00 / quintal per 7-day period.

---

## 5. Workspace Directory Layout

```text
suryansh - work/
├── MASTER_PROJECT_AUDIT.md     # Comprehensive, all-inclusive master audit document
├── README.md                  # Project overview, crop summaries, and navigation dashboard
├── dataset_research/          # Data schemas, source catalogs, coverage matrices, and crop profiles
├── reports/                   # Modular investigation reports and findings
│   ├── phase_02_crop_suitability/          # Phase 02 Crop Suitability Deliverables
│   │   ├── crop_suitability_report.md
│   │   ├── crop_comparison.csv
│   │   ├── dataset_source_catalogue.csv
│   │   ├── data_quality_findings.md
│   │   ├── validation_and_execution_log.md
│   │   └── decisions_pending_approval.md
│   └── phase_03_classification_protocol/   # Phase 03 Evaluation Protocol Deliverables
│       ├── classification_evaluation_protocol.md
│       ├── baseline_evaluation.md
│       ├── crop_class_distribution.csv
│       ├── validation_risk_register.md
│       ├── metric_decision_matrix.csv
│       ├── execution_log.md
│       └── decisions_pending_approval.md
├── experiments/               # Self-contained, reproducible scripts and model configs
│   ├── profile_candidate_crops.py
│   ├── inspect_baseline_predictions.py
│   └── train_and_audit_models.py      # Live training, feature evaluation, and parameter matrix audit
├── results/                   # Tabulated performance metrics, feature rankings, and backtest results
├── figures/                   # Confusion matrices, return distributions, and diagnostic plots
│   ├── live_cm_*.png                  # Live confusion matrix heatmaps (All Crops, Onion, Potato, Tomato, Wheat)
│   └── live_feature_importance_ranking.png # Live MDI feature importance chart
├── logs/                      # Execution logs, test outputs, and run records
└── decisions/                 # Formal decision records (crop selection, validation protocols)
```

---

## 6. Key Rules & Methodological Safeguards

- **Protected Main Clone:** The upstream clone [`../Mandi_Prediction`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction) is strictly read-only. No training jobs, scripts, branch changes, or file edits may occur in the parent clone.
- **Leakage Prevention:** All features at observation date $T$ must use strictly causal data ($\le T$). Target outcomes at $T+7$ must be matched on exact calendar dates (no row-shift substitution). Chronological partitions must enforce horizon embargo buffer purging.
- **Naive Majority Baseline Benchmarking:** In all classification experiments, accuracy must be benchmarked against the majority-class baseline (~54%–59% "Normal"). Macro F1, Balanced Accuracy, and per-class recall are mandatory metrics.
- **Honest Empirical Reporting:** No synthetic data, unverified claims, or invented statistics. Unknowns are explicitly documented as unknown.

---

## 7. Next Actions Awaiting User Sign-Off

All details and decisions are documented in [`reports/phase_03_classification_protocol/decisions_pending_approval.md`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work/reports/phase_03_classification_protocol/decisions_pending_approval.md) and [`MASTER_PROJECT_AUDIT.md`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work/MASTER_PROJECT_AUDIT.md):
1. **Approve Metric Protocol:** Macro F1 and Balanced Accuracy as primary standards; Confusion Matrix mandatory; Overall Accuracy reported strictly as Lift over Naive Baseline.
2. **Approve Wheat Imbalance Handling:** Evaluate Wheat strictly on Balanced Accuracy, Macro F1, and minority recall (forbidding Overall Accuracy).
3. **Approve Baseline Freeze:** Freeze the audited Phase 5 baseline metrics to avoid redundant CPU retraining.
4. **Authorize Prompt 4:** Proceed to feature discovery and external signal validation (CEDA arrival volumes and NASA POWER weather).
