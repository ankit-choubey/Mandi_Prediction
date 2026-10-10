# Production Application Pipeline Verification Report

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Branch:** `main`  
**Date:** October 10, 2026  
**Status:** **VERIFIED & TESTED**

---

## 1. Executive Summary

This report documents the remediation and formal verification of the real application pipeline (`run_pipeline.py` and `src/`) to ensure full alignment with the mathematically and statistically audited methodology established in Phases 0 through 3.

Prior to this remediation, tests under `backing/` confirmed the audit findings but did not test or rectify defects in the operational application modules (`src/data_loader.py`, `src/feature_engineering.py`, `src/evaluate.py`, `src/intelligence_system.py`, and `run_pipeline.py`). Those gaps are now resolved, verified with unit/regression tests, and validated via a successful end-to-end execution of `run_pipeline.py`.

---

## 2. Defects Identified and Remediated in the Application Pipeline

| Area | Component | Prior Pipeline Defect | Remediation & Audited Standard Applied |
|---|---|---|---|
| **A. Model Evaluation & Selection** | `src/evaluate.py`, `run_pipeline.py` | Models were trained on Train and evaluated directly on Test; `X_val` was ignored; candidate selection contaminated the test set. | **Validation-Only Model Selection:** Models are evaluated on Validation; primary candidate is frozen based on Validation Macro F1; only then evaluated on the exploratory test window. |
| **B. Temporal Splitting** | `src/evaluate.py` | `chronological_split` used calendar date cutoffs without an embargo buffer. Target realizations ($T+7$) crossed partition boundaries. | **Horizon-Aware Embargo Purging:** Added 8-day embargo buffer purging at Train/Val and Val/Test boundaries. Origins whose targets realize into the subsequent partition are purged. |
| **C. Lag Features & Volatility** | `src/feature_engineering.py` | Lags used row-based `shift(1, 3, 7)` which matched calendar days in only ~18% of rows due to market closures. Volatility used `.fillna(0)`. | **Exact Calendar Joins & Causal Burn-in:** Exact calendar joins for $T-1, T-3, T-7$. Missing dates yield explicit `NaN` without substitution. Volatility enforces $min\_periods=3$ burn-in without backward filling. |
| **D. Series Identity & Duplicates** | `src/data_loader.py` | `series_cols` omitted `Grade`; `drop_duplicates` with `keep='first'` arbitrarily collapsed different commercial grades. Conflicting same-grade quotes were silently dropped. Non-positive prices were not filtered. | **Grade-Preserving Key & Strategy 2:** Series identity includes `Grade`. Filtered non-positive prices ($<= 0$). Excluded 2,664 ambiguous same-grade conflicting quotes across 1,321 dates (Strategy 2, DEC-008). |
| **E. Advisory Outputs & Disclaimers** | `src/intelligence_system.py` | Output claimed "District-Level Future Market Condition Advisory" and implied spatial arbitrage without caveats. | **Research Disclaimers Added:** Terminal card and payload now prominently display mandatory research prototype disclaimers stating the system is not production-ready for operational farmer advice or binding financial decisions. |

---

## 3. Automated Test Suite Results

A dedicated regression test suite was established under [`tests/test_production_pipeline.py`](../../tests/test_production_pipeline.py) covering all 5 remediated components plus an end-to-end integration test.

### 3.1 Application Test Suite
- **Command:** `python3 -m pytest tests/test_production_pipeline.py -v`
- **Exit Code:** `0`
- **Result:** **7 passed, 0 failed** in 2.28s
  1. `test_data_loader_preserves_grade_and_key`: PASSED
  2. `test_data_loader_filters_invalid_prices`: PASSED
  3. `test_feature_engineering_exact_calendar_lags`: PASSED
  4. `test_feature_engineering_causal_volatility_burnin`: PASSED
  5. `test_chronological_split_horizon_embargo_no_cross_leakage`: PASSED
  6. `test_model_selection_validation_only`: PASSED
  7. `test_intelligence_system_mandatory_disclaimers`: PASSED

### 3.2 Full Repository Verification Suite
- **Command:** `python3 -m pytest tests/ backing/phase_00/tests/ backing/phase_01/tests/ backing/phase_02/tests/ backing/phase_03/tests/ -v`
- **Exit Code:** `0`
- **Result:** **52 passed, 0 failed, 0 warnings** in 5.75s

---

## 4. End-to-End Pipeline Run Verification

`python3 run_pipeline.py` was executed from repository root and completed with **Exit Code 0**:
- **Step 1 (Feasibility):** Verified 75.24% exact calendar T+7 availability across 117,176 pairs.
- **Step 2 (EDA):** Generated all 6 distribution, seasonality, and correlation plots.
- **Step 3 (Data Loader):** Ingested 160,192 raw records, applied Strategy 2 exclusion (2,664 ambiguous rows removed), filtered low-observation series $\ge 20$ records (150,687 clean rows retained across 1,069 series).
- **Step 4 (Features):** Built 27 predictive features across 115,833 records with valid $T+7$ targets.
- **Step 5 (Splitting):** Partitioned chronologically with purged embargo buffers:
  - Train: 82,905 records (2024-09-01 to 2026-01-16)
  - Train Embargo: 1,328 records purged
  - Val: 15,361 records (2026-01-25 to 2026-05-02)
  - Val Embargo: 835 records purged
  - Exploratory Test: 15,404 records (2026-05-11 to 2026-08-25)
- **Step 6 (Model Training & Selection):**
  - Evaluated candidate classifiers on Validation partition.
  - Selected primary candidate based on Validation Macro F1.
  - Evaluated on exploratory historical test set for benchmark tracking.
- **Step 7 (Market Intelligence):** Executed 5 regional case studies displaying research prototype disclaimers.
- **Step 8 (Reports):** Generated and synchronized `FINAL_REPORT.md` and `FINAL_REPORT.docx`.

---

## 5. Remaining Limitations

1. **Phase 4 Required Before Production Deployment:**
   The predictive models provide statistical directional signals only. The repository does NOT implement physical transport freight models, mandi cess/taxes, spoilage rates, or warehouse storage economics. Do NOT deploy farmer-facing recommendations before Phase 4.
2. **Exploratory Test Window Status:**
   The historical test partition (May–August 2026) has been inspected during research and is properly treated as an exploratory test set, not an untouched final holdout.
