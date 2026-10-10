# Feasibility Consistency Verification Report

**Project:** `Mandi_Prediction`  
**Repository:** `ankit-choubey/Mandi_Prediction`  
**Branch:** `main`  
**Date:** October 10, 2026  
**Status:** **VERIFIED & CONSISTENT (PASS)**

---

## 1. Executive Summary

This report documents the resolution of consistency gaps between the feasibility audit (`src/feasibility.py` and `T7_Feasibility_Report.md`), the corrected application pipeline (`src/data_loader.py`, `src/feature_engineering.py`, `src/evaluate.py`, `run_pipeline.py`), and the master audit documentation (`backing/PROJECT_AUDIT.md`) prior to Phase 4.

The legacy feasibility module used a 4-tuple series key omitting `Grade` (`(District, Market, Commodity, Variety)`) and silently dropped duplicate series-date observations using `keep='first'`. This caused distinct commercial grades (such as FAQ vs Medium) to falsely cross-match across dates and artificially inflated or skewed metrics.

By reconciling `src/feasibility.py` to use canonical data loading and the 5-tuple canonical key (`(District, Market, Commodity, Variety, Grade)`) with Strategy 2 duplicate exclusion (DEC-008), the feasibility analysis, application pipeline, and master audit document are now in 100% agreement.

---

## 2. Files Changed and Why

1. **`src/feasibility.py`**:
   - Replaced custom raw data reading and `keep='first'` duplicate handling with canonical `from src.data_loader import load_and_clean_mandi_data(min_series_records=0)`.
   - Incorporates `Grade` into the canonical series identity: `(District, Market, Commodity, Variety, Grade)`.
   - Applies Strategy 2 (DEC-008): excludes 2,664 ambiguous same-grade conflicting quotes across 1,321 dates.
   - Enforces DEC-015 target condition boundaries: Favorable ($R > +2.5\%$), Normal ($-2.5\% \le R \le +2.5\%$, inclusive), Unfavorable ($R < -2.5\%$).
   - Safeguarded against zero-division errors when evaluating small slices or edge cases.
   - Updated report formatting to dynamically reflect canonical metrics without hardcoded legacy numbers.
2. **`run_pipeline.py`**:
   - Updated `generate_final_report` to format metrics dynamically from `feasibility_metrics` rather than hardcoding legacy figures.
   - Reconciled target class descriptions and summary tables with DEC-015 and Grade-preserving canonical series units.
3. **`tests/test_feasibility_reconciliation.py`**:
   - Created dedicated regression suite covering Requirements A, B, C, D, and E with deterministic synthetic fixtures.
4. **`backing/PROJECT_AUDIT.md`**:
   - Updated Section 2 to describe the corrected application pipeline and historical defects.
   - Updated Section 5 to DEC-015 target definitions and canonical empirical distribution ($n = 116,819$).
   - Updated Sections 6, 7, 8 to note exact calendar lags, causal rolling volatility, horizon embargo purging, and exploratory test status.
   - Updated Section 18.2 with current commit SHA and consolidation details.
   - Updated Section 19 with feasibility consistency reconciliation details, test counts (57 passing tests), and limitations.
   - Bumped document version to 1.5.0.
5. **Generated Deliverables**:
   - `T7_Feasibility_Report.md`: Regenerated with canonical numbers and synchronized to `reports/`.
   - `FINAL_REPORT.md` and `FINAL_REPORT.docx`: Regenerated and synchronized to `reports/`.

---

## 3. Methodology Comparison: Legacy vs Corrected

| Dimension | Legacy Feasibility Implementation | Corrected Reconciled Implementation |
|---|---|---|
| **Series Key** | 4-tuple: `(District, Market, Commodity, Variety)` | 5-tuple: `(District, Market, Commodity, Variety, Grade)` |
| **Grade Handling** | Collapsed distinct commercial grades on the same date | Preserves commercial grades (e.g. FAQ vs Medium) as separate series |
| **Duplicate Resolution** | Arbitrary `keep='first'` (silently dropping 4,380 rows) | Strategy 2 (DEC-008): Identical duplicates removed; 2,664 conflicting same-grade quotes excluded |
| **Exact T+7 Matching** | Matched across grades (FAQ could pair with Medium 7 days later) | Exact calendar date join ($T+7$) strictly within the same 5-tuple series |
| **Target Boundaries** | Inconsistent inequalities ($R \ge +2.5\%$ vs $R \le -2.5\%$) | Strict DEC-015: Favorable ($R > +2.5\%$), Normal ($[-2.5\%, +2.5\%]$), Unfavorable ($R < -2.5\%$) |
| **Date Continuity / Lags** | Naive division without zero-checks | Safe denominators, explicit `NaN` upon closed dates |

---

## 4. Recomputed Feasibility Metrics

All metrics recomputed deterministically on raw mandi CSV archives (`data/raw/*.csv`):

```
======================================================================
                  T+7 FEASIBILITY AUDIT SUMMARY TABLE
======================================================================
Total raw records                               : 160,192
Duplicate / excluded records removed            : 2,680
  - Ambiguous same-grade conflicting quotes     : 2,664 (across 1,321 dates)
  - Identical duplicate records (Cat A)         : 10
  - Invalid non-positive price records          : 6
Total clean records                             : 157,512
Unique districts                                : 5
Unique mandis                                   : 42
Unique commodities                              : 130
Unique varieties                                : 210
Unique commercial grades                        : 4
Unique canonical series (with Grade)            : 2,390

Records with exact T+7                          : 116,819
Records without T+7                             : 40,693
T+7 availability %                              : 74.17%

Series with >= 20 T+7 pairs                     : 794
Series with >= 50 T+7 pairs                     : 576

Possible classification samples                 : 116,819
  - Favorable samples                           : 22,088 (18.91%)
  - Normal samples                              : 69,408 (59.41%)
  - Unfavorable samples                         : 25,323 (21.68%)
======================================================================
```

### Explanation of Discrepancies from Legacy Report:
- Legacy availability was reported as **75.24%** (117,176 pairs) because omitting `Grade` caused cross-grade false pairings and `keep='first'` arbitrarily picked one quote when conflicting prices existed.
- Canonical availability is **74.17%** (116,819 pairs) with zero false cross-grade pairings and 100% price quote purity.
- Usable series ($\ge 20$ pairs) increased from 779 to **794** because grade separation properly unbundled active commercial series.

---

## 5. Automated Regression Test Execution

### 5.1 Focused Feasibility & Application Suites
Command:
```bash
python3 -m pytest tests/ -v
```
Output:
- `tests/test_feasibility_reconciliation.py`:
  - `test_feasibility_grade_preservation_distinct_series`: PASSED
  - `test_feasibility_strategy2_conflicting_same_grade_prices_excluded`: PASSED
  - `test_feasibility_exact_t7_no_substitution_when_missing`: PASSED
  - `test_feasibility_metrics_distinguish_raw_and_clean_counts`: PASSED
  - `test_dec015_target_class_boundaries`: PASSED
- `tests/test_production_pipeline.py`:
  - `test_data_loader_preserves_grade_and_key`: PASSED
  - `test_data_loader_filters_invalid_prices`: PASSED
  - `test_feature_engineering_exact_calendar_lags`: PASSED
  - `test_feature_engineering_causal_volatility_burnin`: PASSED
  - `test_chronological_split_horizon_embargo_no_cross_leakage`: PASSED
  - `test_model_selection_validation_only`: PASSED
  - `test_intelligence_system_mandatory_disclaimers`: PASSED
- **Result:** **12 passed in 2.35s (Exit Code 0)**.

### 5.2 Full Comprehensive Verification Suite
Command:
```bash
python3 -m pytest tests/ backing/phase_00/tests/ backing/phase_01/tests/ backing/phase_02/tests/ backing/phase_03/tests/ -v
```
Output:
- Phase 0 Setup: 4 passed
- Phase 1 Data Integrity: 8 passed
- Phase 2 Methodology: 17 passed
- Phase 3 Methodology & Baseline: 16 passed
- Tests (Application & Feasibility): 12 passed
- **Result:** **57 passed, 0 failed in 6.29s (Exit Code 0)**.

---

## 6. End-to-End Pipeline Execution

Command:
```bash
python3 run_pipeline.py
```
Output:
- Completed with **Exit Code 0**.
- All 8 steps executed:
  1. Feasibility Audit: Verified canonical 74.17% T+7 availability across 116,819 pairs.
  2. EDA: Generated 6 distribution and seasonality plots.
  3. Data Loader: Ingested 160,192 raw records, applied Strategy 2 exclusion, filtered series $\ge 20$ records (150,687 clean rows across 1,069 series).
  4. Feature Engineering: Constructed 27 causal features.
  5. Splitting: Chronological partitioning with 8-day purged embargo buffers.
  6. Model Evaluation: Benchmarked 5 classifiers, selected primary candidate on Validation Macro F1, evaluated exploratory test partition.
  7. Market Intelligence: Executed 5 case study cards with mandatory research prototype disclaimers.
  8. Reports: Successfully generated and synchronized `FINAL_REPORT.md`, `FINAL_REPORT.docx`, and `T7_Feasibility_Report.md`.

---

## 7. Data Integrity Verification

Command:
```bash
git diff -- data/raw/
```
Result: **0 diffs, 0 modifications**. Source raw data files in `data/raw/*.csv` remain 100% untouched.

---

## 8. Remaining Limitations

1. **Phase 4 Not Started:**
   No physical transport models, mandi cess/taxes, spoilage decay curves, or warehouse storage economics have been implemented. The system produces statistical market condition indicators only.
2. **Exploratory Test Window Status:**
   The historical test window is explicitly designated as an exploratory test partition, not an untouched holdout. Candidate model selection was performed strictly on validation.
