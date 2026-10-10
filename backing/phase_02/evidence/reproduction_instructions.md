# Phase 02 — Reproduction Instructions (Second Review Pass)

**Project:** Mandi_Prediction  
**Corpus:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 02 — Data Handling and Methodology Remediation (Second Review Pass)  
**Date:** 2026-10-10  
**Branch:** `main`  

---

## 1. Prerequisites and Setup

Ensure Python 3.10+ (verified on Python 3.14.0 arm64 macOS Apple Silicon) and the required numerical libraries are installed:

```bash
pip install pandas numpy scipy scikit-learn pytest
```

### Verified Dependency Environment
- **Python:** 3.14.0 (arm64, macOS Darwin 25.1.0)
- **pandas:** 2.3.3
- **numpy:** 2.2.6
- **scipy:** 1.16.3
- **scikit-learn:** 1.7.2
- **pytest:** 9.1.1

Verify that the 5 raw CSV data files exist in `data/raw/` and match the verified SHA-256 hashes in [execution_environment.txt](execution_environment.txt):
- `data/raw/Gaziabaad.csv`: `71601f993e07efa146f126747245a7fffb608a307abdea579475ba19bfeb0251` (33,740 rows)
- `data/raw/Jhansi.csv`: `7d0808d8d32555212af546004195c0ccf58e368106daad67169a231e80988a5c` (21,291 rows)
- `data/raw/Kanpur.csv`: `0eb17704ebba1f66b8c9ef660f48dabc3665ea4691ed3b8aa20a49df8528d04a` (41,208 rows)
- `data/raw/Lukhnow.csv`: `6ca52743cc2f9059bf1e3b919b25317aa367f580bbafa6f62adb9db1d759bb13` (50,917 rows)
- `data/raw/Unnao.csv`: `d4ee358b96cad3a888e4a92acd993327e56c4dc6af6eb60814193f98f591cebc` (13,036 rows)

Total Raw Records: **160,192** (Grade field is 100% complete, 0 nulls).

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

Or using the environment variable:

```bash
MANDI_REPO_ROOT=$(pwd) python3 backing/phase_02/tests/run_phase02_analysis.py
```

### Generated Output Artifacts

The analysis engine populates the following 6 verified CSV artifacts in `backing/phase_02/outputs/`:

1. `duplicate_resolution_comparison.csv` (Same-grade duplicate typology and 4 strategy evaluations)
2. `canonical_market_mapping.csv` (42 raw market names audited with consistent status, hiatus, and concurrency metrics)
3. `calendar_lag_coverage.csv` (Row-shift vs exact-calendar vs bounded-staleness coverage across 157,518 clean rows)
4. `target_definition_comparison.csv` (Continuous vs Fixed +/-2.5% [agreed convention] vs Causal Volatility vs Embargoed Quantiles at T+3 and T+7)
5. `cleaned_data_quality_summary.csv` (Quality metrics across 4 candidate pipeline stages)
6. `methodology_sensitivity_summary.csv` (One-factor-at-a-time audit sensitivity matrix)

Execution logs are automatically written to `backing/phase_02/logs/phase02_execution.log` and `backing/phase_02/logs/phase02_correction_execution.log`.

---

## 3. Running the Automated Correction Test Suite

To execute the 17 automated methodology and correction tests:

```bash
python3 -m pytest backing/phase_02/tests/ -v | tee backing/phase_02/tests/test_results.txt
```

To run the complete project audit suite (Phases 1 + 2, 25 tests):

```bash
python3 -m pytest backing/phase_01/tests/ backing/phase_02/tests/ -v
```

All 25 tests execute deterministically and independently using both full raw data audits and self-contained synthetic micro-tests. Actual test result: **25 passed in 2.56s (100% pass rate)**.
