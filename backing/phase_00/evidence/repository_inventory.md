# Phase 0 Repository Inventory & Asset Discovery
**Project:** APMC Mandi Market Intelligence System  
**Repository:** [ankit-choubey/Mandi_Prediction](https://github.com/ankit-choubey/Mandi_Prediction)  
**Branch:** `audit/phase-00-inspection`  
**Date:** October 10, 2026  
**Auditor:** Antigravity AI  

---

## 1. Directory Structure

```text
Mandi_Prediction/
├── .git/                                # Git version control metadata
├── .gitignore                           # Git ignore rules
├── LICENSE                              # MIT License
├── README.md                            # Main project overview and claimed test results
├── FINAL_REPORT.md                      # Detailed project markdown report
├── FINAL_REPORT.docx                    # Formatted Word report (645 KB)
├── T7_Feasibility_Report.md             # Automated checklist audit report
├── convert_report_to_docx.py            # Utility script compiling markdown to DOCX
├── run_pipeline.py                      # Master pipeline orchestration script
├── data/
│   ├── docs/                            # Domain specifications and checklist
│   │   ├── District_Level_Project_Overview.pdf
│   │   └── T7_Feasibility_Checklist.txt
│   └── raw/                             # Tracked raw APMC mandi daily CSVs
│       ├── Gaziabaad.csv                (3.49 MB, 41,495 rows)
│       ├── Jhansi.csv                   (1.86 MB, 23,625 rows)
│       ├── Kanpur.csv                   (3.53 MB, 42,644 rows)
│       ├── Lukhnow.csv                  (1.76 MB, 21,063 rows)
│       └── Unnao.csv                    (2.45 MB, 31,365 rows)
├── eda/                                 # Exploratory Data Analysis module
│   ├── EDA_REPORT.md                    # Descriptive statistics summary
│   ├── eda_analysis.py                  # Standalone EDA chart generation script
│   └── plots/                           # 6 PNG charts (distributions, correlations, etc.)
├── notebooks/                           # Added in Phase 0
│   └── mandi_mathematical_audit.ipynb   # Standalone memory-conscious audit notebook
├── reports/
│   ├── FINAL_REPORT.docx
│   ├── FINAL_REPORT.md
│   ├── T7_Feasibility_Report.md
│   └── evidence/phase_00/               # Phase 0 formal evidence documents
├── results/                             # Saved artifacts and performance charts
│   ├── confusion_matrix_*.png           (6 confusion matrix plots)
│   ├── feature_importance_rf.png
│   ├── model_performance_chart.png
│   ├── sample_engineered_features.csv   (Sample of 50 engineered feature rows)
│   └── system_workflow_diagram.png
└── src/                                 # Core modular codebase
    ├── __init__.py
    ├── data_loader.py                   # Ingestion, deduplication, series filtering
    ├── feasibility.py                   # Checklist Sections A-O automated verification
    ├── feature_engineering.py           # 27 spatial & temporal features, T+7 target
    ├── models.py                        # 5 classifier architectures (0 regression)
    ├── evaluate.py                      # Chronological split & evaluation metrics
    └── intelligence_system.py           # District advisory inference engine
```

---

## 2. Core Code Modules & Functional Roles

| Module | Location | Primary Responsibilities |
|---|---|---|
| **Data Loader** | [`src/data_loader.py`](../../../src/data_loader.py) | Loads 5 CSVs, fixes district typos (`Gaziabaad` $\to$ `Ghaziabad`), parses dates (`%d/%m/%Y`), deduplicates exact series-date rows, filters series with $<20$ records. |
| **Feasibility Audit** | [`src/feasibility.py`](../../../src/feasibility.py) | Verifies Checklist Sections A–O; tests exact calendar $T+7$ availability across all series. |
| **Feature Engineering** | [`src/feature_engineering.py`](../../../src/feature_engineering.py) | Computes intraday spread, historical lags (`shift(1)`, `shift(3)`, `shift(7)`), rolling stats, spatial neighbour signals, and constructs discrete 3-class target ($\pm 2.5\%$). |
| **Model Suite** | [`src/models.py`](../../../src/models.py) | Implements Decision Tree, Random Forest, Extra Trees, Gradient Boosting, and Soft-Voting Ensemble using scikit-learn pipelines with median imputation. |
| **Evaluation** | [`src/evaluate.py`](../../../src/evaluate.py) | Chronological train (70%) / val (15%) / test (15%) split; accuracy, precision, recall, macro/weighted F1, confusion matrices, and MDI feature importances. |
| **Market Advisory** | [`src/intelligence_system.py`](../../../src/intelligence_system.py) | Rule-based decision recommendation engine mapping predicted market conditions into actionable advice. |
| **Orchestration** | [`run_pipeline.py`](../../../run_pipeline.py) | End-to-end master runner executing audit $\to$ EDA $\to$ features $\to$ models $\to$ case studies $\to$ DOCX report. |

---

## 3. Dataset Availability & Tracking Status

- **Status:** **Present locally and fully tracked in Git.**
- **Path:** [`data/raw/*.csv`](../../../data/raw)
- **Tracking:** Verified via `git ls-files data/raw`. All 5 files are committed to the repository history (`Gaziabaad.csv`, `Jhansi.csv`, `Kanpur.csv`, `Lukhnow.csv`, `Unnao.csv`).
- **Absence Check:** No external data files are currently absent; all raw data referred to by the repository pipeline is directly accessible.
- **External Dependencies:** Independent external datasets (e.g. Department of Consumer Affairs PMD wholesale series, CWC warehouse tariffs, DESAgri wage tables) are **not** present in the repository and must be formally staged in subsequent phases.

---

## 4. Existing Test Suite & Environment Files

- **Automated Tests (`pytest` / `unittest`):** **None.** There is no `tests/` directory or dedicated automated test suite in the repository.
- **Verification Scripts:** The pipeline relies entirely on procedural execution via `run_pipeline.py` and `src/feasibility.py`.
- **Environment & Dependency Files:** No `requirements.txt`, `environment.yml`, `Pipfile`, or `pyproject.toml` existed in the repository root. Package requirements were only mentioned as inline text in `README.md`.
