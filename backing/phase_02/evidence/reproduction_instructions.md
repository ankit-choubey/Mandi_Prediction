# Phase 02 — Reproduction Instructions (Correction Pass)

**Project:** Mandi_Prediction  
**Corpus:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 02 — Data Handling and Methodology Remediation (Correction Pass)  
**Date:** 2026-10-10  
**Branch:** `audit/phase-02-correction-pass`  

---

## 1. Prerequisites and Setup

Ensure Python 3.10+ (tested on Python 3.14.0 arm64 macOS) and the required numerical libraries are installed:

```bash
pip install pandas numpy scipy scikit-learn pytest
```

Verify that the 5 raw CSV data files exist in `data/raw/` and match the verified SHA-256 hashes in [execution_environment.txt](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/evidence/execution_environment.txt).

---

## 2. Executing the Portable Phase 2 Analysis Engine

The analysis script automatically derives the repository root dynamically from its file location, eliminating any hardcoded paths. You can also supply an explicit repository path via `--repo-root` or the `MANDI_REPO_ROOT` environment variable.

From the repository root:

```bash
python3 backing/phase_02/tests/run_phase02_analysis.py
```

Or specifying the repository path explicitly:

```bash
python3 backing/phase_02/tests/run_phase02_analysis.py --repo-root /path/to/Mandi_Prediction
```

### Generated Output Artifacts

The analysis engine populates the following 6 verified CSV artifacts in `backing/phase_02/outputs/`:

1. `duplicate_resolution_comparison.csv` (Same-grade duplicate typology and 4 strategy evaluations)
2. `canonical_market_mapping.csv` (42 raw market names audited with consistent status, hiatus, and concurrency metrics)
3. `calendar_lag_coverage.csv` (Row-shift vs exact-calendar vs bounded-staleness coverage across 157,518 clean rows)
4. `target_definition_comparison.csv` (Continuous vs Fixed +/-2.5% vs Leak-Free Volatility vs Embargoed Quantiles at T+3 and T+7)
5. `cleaned_data_quality_summary.csv` (Quality metrics across 4 candidate pipeline stages)
6. `methodology_sensitivity_summary.csv` (One-factor-at-a-time audit sensitivity matrix)

Execution logs are automatically written to `backing/phase_02/logs/phase02_execution.log` and `backing/phase_02/logs/phase02_correction_execution.log`.

---

## 3. Running the Automated Correction Test Suite

To execute the 14 automated methodology and correction tests:

```bash
python3 -m pytest backing/phase_02/tests/ -v | tee backing/phase_02/tests/test_results.txt
```

To run the complete project audit suite (Phases 1 + 2):

```bash
python3 -m pytest backing/phase_01/tests/ backing/phase_02/tests/ -v
```

All tests execute deterministically and independently using both full raw data audits and self-contained synthetic micro-tests.
