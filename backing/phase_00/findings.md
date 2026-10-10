# Phase 0 Audit Findings: Repository Discovery, Schema Verification & Setup

**Audit Phase:** Phase 0 — Discovery and Setup  
**Date:** October 10, 2026  
**Auditor:** Antigravity AI  
**Status:** **COMPLETED** (Decision: **PASS**)  
**Git Commit:** [`5d1ca17`](https://github.com/ankit-choubey/Mandi_Prediction/commit/5d1ca17ba6c7774c70b78e094d11298191b83900)  

---

## 1. Verified Facts (Directly Measured by Auditor)

1. **Raw Dataset Tracking & Location:**
   - 5 raw CSV files are tracked in Git under [`data/raw/*.csv`](../../data/raw).
   - Total files: 5; Total size: 13.09 MB; Total lines measured: **160,192 raw records**.
     - `data/raw/Gaziabaad.csv`: 41,495 rows (3.49 MB)
     - `data/raw/Jhansi.csv`: 23,625 rows (1.86 MB)
     - `data/raw/Kanpur.csv`: 42,644 rows (3.53 MB)
     - `data/raw/Lukhnow.csv`: 21,063 rows (1.76 MB)
     - `data/raw/Unnao.csv`: 31,365 rows (2.45 MB)
2. **Schema & Types:**
   - All files have identical 11 columns: `Arrival_Date`, `Commodity`, `Commodity_Code`, `District`, `Grade`, `Market`, `Max_Price`, `Min_Price`, `Modal_Price`, `State`, `Variety`.
   - Missing values: **0 nulls (0.0000%)** across all 11 columns for all 160,192 records.
3. **Temporal Bounds:**
   - Date format `%d/%m/%Y` achieved **100% parse success** (0 invalid dates).
   - Date range: **2024-09-01 to 2026-09-01** (731 continuous calendar days; 0 missing dates statewide).
4. **Price Ordering Rule ($Min \le Modal \le Max$):**
   - Compliant rows: 160,186 (**99.9963%**).
   - Violations: Exactly **6 rows (0.0037%)**, all due to `Max_Price = 0` while `Modal_Price > 0`.
5. **Kaggle Execution:**
   - The notebook [`notebooks/mandi_mathematical_audit.ipynb`](../../notebooks/mandi_mathematical_audit.ipynb) was deployed to Kaggle as kernel `theankitchoubey/mandi-math-audit-p0` with attached dataset `theankitchoubey/up-apmc-mandi-raw-dataset`.
   - Completed execution on Kaggle CPU with return code 0 (28s duration).

---

## 2. Findings Reported by the Prior Audit & Independent Reproduction Status

| Claim / Metric | Prior Reported Value | Independent Reproduction Result | Status |
|---|---|---|---|
| **Raw Records** | 160,192 | 160,192 | **REPRODUCED** |
| **Deduplicated Records** | 155,741 | 155,741 | **REPRODUCED** |
| **Exact T+7 Pairs (All Series)** | 117,176 (75.24%) | 117,176 (75.24%) | **REPRODUCED** |
| **Usable Series ($\ge 20$ T+7 pairs)** | 779 | 779 | **REPRODUCED** |
| **Filtered Dataset T+7 Pairs** | 116,361 (77.62%) | 116,361 (77.62%) | **REPRODUCED** |
| **Total Nominal Series** | 2,044 | 2,044 | **REPRODUCED** |
| **Decision Tree Test Accuracy** | 49.34% | 49.34% | **REPRODUCED** |
| **Random Forest Test Accuracy** | 53.12% | 53.23% | **REPRODUCED** |
| **Extra Trees Test Accuracy** | 52.84% | 49.95% | **DISCREPANCY (Reproduced: 49.95%)** |
| **Gradient Boosting Test Accuracy**| 58.76% | 59.88% | **REPRODUCED (~58.8%–59.9%)** |
| **Voting Ensemble Test Accuracy** | **58.42%** *(Claimed in README)* | **56.11%** (Matches Report Table 56.25%) | **FAIL (Claimed 58.42% was an error)** |
| **Naive Majority Test Baseline** | *Not reported* | **54.00%** | **DISCOVERED IN AUDIT** |

---

## 3. Critical Data Quality Warnings

1. **The "APMC" Naming Severance:**
   - In November 2025, markets were renamed from `<Market>` to `<Market> APMC` (e.g. `Lucknow` $\to$ `Lucknow APMC`).
   - This severed 2-year continuous series into two fragments, falsely creating 42 nominal mandis when only **21 physical mandis** exist.
   - It caused all exact $T+7$ merges during the transition week to fail.
2. **Observation Lag Flaw:**
   - In `src/feature_engineering.py`, `Lag_Price_7 = shift(7)`.
   - `shift(7)` is 7 calendar days ago in only **20.14%** of rows. In **79.86%** of cases, it looks back 8 to 317 calendar days (mean: 11.45 days).
3. **Baseline Deficiency:**
   - Decision Tree (49.34%), Extra Trees (49.95%), and Random Forest (53.23%) perform **worse than naive majority guessing (54.00%)**.

---

## 4. Items Not Yet Verified (Requires Subsequent Phases)

- **External Price Agreement:** Comparison against Department of Consumer Affairs (PMD) or e-NAM data has `NOT BEEN PERFORMED`.
- **Granular Gap Distributions per Commodity:** Per-commodity continuity matrices will be computed in Phase 1.
- **Cost Model Parameters:** Warehouse tariffs (CWC) and wage rates (DESAgri) remain `UNVERIFIED`.

---

## 5. Reproduction Instructions

### Run the Phase 0 Verification Test Suite
```bash
python3 backing/phase_00/tests/test_phase00_setup.py
```

### Run the Phase 0 Audit Notebook Locally
```bash
python3 -m jupyter nbconvert --to notebook --execute notebooks/mandi_mathematical_audit.ipynb \
  --output mandi_mathematical_audit.ipynb --output-dir notebooks
```

### Inspect Kaggle Execution Evidence
Review the raw execution log recorded at:
[`backing/phase_00/outputs/mandi-math-audit-p0.log`](./outputs/mandi-math-audit-p0.log)

---

## 6. Links to Evidence

- Repository Inventory: [`backing/phase_00/evidence/repository_inventory.md`](./evidence/repository_inventory.md)
- Environment Verification: [`backing/phase_00/evidence/environment_check.txt`](./evidence/environment_check.txt)
- Unresolved Questions: [`backing/phase_00/evidence/unresolved_questions.md`](./evidence/unresolved_questions.md)
- Kaggle Execution Log: [`backing/phase_00/outputs/mandi-math-audit-p0.log`](./outputs/mandi-math-audit-p0.log)
- Verification Tests: [`backing/phase_00/tests/test_phase00_setup.py`](./tests/test_phase00_setup.py)
