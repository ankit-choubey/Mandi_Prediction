# Phase 02 — Reproduction Instructions

**Project:** Mandi_Prediction  
**Corpus:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 02 — Data Handling and Methodology Remediation  
**Date:** 2026-10-10  
**Branch:** `audit/phase-02-methodology`  

---

## 1. Prerequisites and Setup

Ensure Python 3.10+ (tested on Python 3.14.0 arm64 macOS) and the required numerical libraries are installed:

```bash
pip install pandas numpy scipy scikit-learn pytest
```

Verify that the raw CSV data files exist in `data/raw/` and match the SHA-256 hashes listed in [execution_environment.txt](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/evidence/execution_environment.txt).

---

## 2. Executing the Phase 2 Methodology Analysis

The audit analysis engine computes all duplicate breakdowns, canonical market mappings, calendar lag audits, target comparisons, and sensitivity summaries without altering raw datasets or production source files.

Run the analysis runner from the workspace root:

```bash
python3 backing/phase_02/tests/run_phase02_analysis.py
```

### Expected Output Files

The runner creates the following verified artifacts in `backing/phase_02/outputs/`:

1. `duplicate_resolution_comparison.csv` (5 candidate strategies evaluated across 160,192 rows)
2. `canonical_market_mapping.csv` (42 raw market names evaluated for physical canonical identity)
3. `calendar_lag_coverage.csv` (Row-shift vs exact-calendar vs bounded-staleness coverage across 155,741 rows)
4. `target_definition_comparison.csv` (Continuous vs Fixed +/-2.5% vs Volatility vs Quantile targets at T+3 and T+7)
5. `cleaned_data_quality_summary.csv` (Quality metrics across 4 candidate pipeline stages)
6. `methodology_sensitivity_summary.csv` (One-factor-at-a-time audit sensitivity matrix)

A real execution log is saved to `backing/phase_02/logs/phase02_execution.log`.

---

## 3. Running the Phase 2 Automated Pytest Suite

To execute the 13 automated methodology test specifications and capture the execution output:

```bash
python3 -m pytest backing/phase_02/tests/test_phase02_methodology.py -v | tee backing/phase_02/tests/test_results.txt
```

All tests run deterministically and independently using both full raw data checks and self-contained synthetic micro-tests.
