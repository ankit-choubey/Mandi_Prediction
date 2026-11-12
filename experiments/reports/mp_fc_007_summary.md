# MP-FC-007 Benchmark Execution & Diagnostic Report

**Task:** MP-FC-007 — First Price-Only Machine Learning Forecasting Benchmark
**Repository:** `ankit-choubey/Mandi_Prediction`
**Execution Date:** 2026-11-12 IST
**Git Baseline Commit:** `dbdfd8a17b0de6423115cecfbbf5f9d7c1463456`
**Status:** `PREPARATION_PASSED + ONE_AUTHORIZED_RUN_EXECUTED + DIAGNOSTIC_REPAIRED + READY_FOR_RERUN_APPROVAL`

---

## 1. Executive Summary

Task MP-FC-007 prepared and executed the first price-only machine learning forecasting benchmark across four chronological folds (F1–F4), comparing Ridge Regression and HistGradientBoostingRegressor against four rescored empirical baselines (Naive $H=7$, Moving Average 7 obs in 30d, Seasonal Naive 357d, Damped Drift 14d) under strict As-Of operational causality.

In accordance with owner authorization, **ONE private Kaggle CPU kernel run** was executed on dataset `theankitchoubey/mandi-prediction-audit-003b` (v1). All 7 embedded source/reference payloads decoded with confirmed byte-equality, and Panel V2 regenerated in 12.2s with exact SHA-256 confirmation (`851e7184...`). An assertion syntax error in reading nested manifest metrics halted execution at Cell 2. Per standing push rules, **zero automatic retries were pushed**. The dictionary lookup was repaired, verified locally against the downloaded manifest, and is presented for owner authorization for a single bounded rerun.

---

## 2. Preflight Corrections & Specification Alignment

1. **`src/forecast_features.py` Interface Repairs:**
   - Updated `normalize_series_identity` to inspect `entry.get("status") in ("ACCEPTED", "CANONICAL")` alongside legacy action keys, ensuring reference `data/reference/market_aliases.csv` interfaces correctly.
   - Added finite positive price filtering (`math.isfinite(p) and p > 0`) in `resolve_raw_series_records`.
2. **`experiments/configs/price_forecast_v1.json` Specification:**
   - Frozen primary input dataset as regenerated legacy panel V2 with SHA-256 `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` and row conservation $472,385 = 463,217 + 855 + 2,936 + 5,350 + 27$.
   - Frozen exact 6 focus crops: `Wheat`, `Potato`, `Onion`, `Tomato`, `Paddy(Dhan)(Common)`, `Rice`.
   - Specified candidate model hyperparameters: Ridge ($\alpha \in \{0.1, 1.0, 10.0\}$) and HGB (2 fixed depth/leaf configurations).
   - Declared response formulation: additive price change $\Delta = y_{\text{target}} - y_t$, reconstructed $\hat{y} = y_t + \hat{\Delta}$. Non-positive reconstructed forecasts abstain with `NON_POSITIVE_RECONSTRUCTED_FORECAST`.
   - Specified two expanding inner chronological splits per fold with 7-day embargo and label maturity.
3. **`documentation/FORECAST_DATA_FEATURE_CONTRACT.md` Alignment:**
   - Authored Section 6 detailing dataset inputs, response choices, inner validation protocol, and rescored baselines.
4. **Factual Corrections in Reports:**
   - Corrected focus crops definition and single-day snapshot absence notes in `experiments/reports/data_008/focus_crops_coverage.json` and `experiments/reports/mp_data_008_summary.md`.

---

## 3. Modular Benchmark Engine (`src/forecast_benchmark.py`)

Implemented clean, modular benchmark architecture:
- `TemporalFold`: Formalizes outer folds F1–F4, embargo periods, and conservative origin bounds ($t \le T_{\text{train}} - 8$).
- `InnerSplit`: Formalizes the two expanding inner validation splits per fold with explicit 7-day embargo and label maturity ($y_{\text{target\_date}} \le \text{inner\_cutoff}$).
- `extract_series_target`: Implements nearest observed target in $[t+6, t+8]$ with earlier tie-breaking and upper boundary enforcement.
- `ForecastBenchmarkEngine`: Coordinates eligibility checks, partition extraction, inner chronological tuning, outer refitting, and rescored baseline evaluation.
- `compute_slice_metrics`: Computes MAE, RMSE, MeanBias, MedianAE, MAPE, Within-5% error, and Paired Naive Skill Score on common finite evaluated origins with series-cluster bootstrap 95% CIs (1,000 resamples, seed 42).
- **Unit Test Suite:** Created `tests/test_forecast_benchmark.py` with 11 targeted tests. Full repository test suite: **281 passed in 9.33s** (0 failures across 21 test files).

---

## 4. Remote Kaggle CPU Execution & Integrity Verification

- **Kernel Slug:** `theankitchoubey/mp-fc-007-price-models`
- **Kernel Version:** `1` (Private CPU, Internet Disabled)
- **Kaggle Push Receipt:** Pushed at 2026-11-12 14:15:52 UTC.
- **Payload Verification Receipt:**
  - `src/market_identity.py` (32,138 bytes, SHA `85ce73c9edaf89bb...` — MATCH)
  - `src/data_pipeline.py` (39,484 bytes, SHA `c542f8c571fe6eb1...` — MATCH)
  - `src/baselines.py` (44,845 bytes, SHA `9cf56e5345235bc5...` — MATCH)
  - `src/forecast_features.py` (27,871 bytes, SHA `d9b55d675db7ae82...` — MATCH)
  - `src/forecast_benchmark.py` (29,949 bytes, SHA `385163bb0bb0a0fe...` — MATCH)
  - `data/reference/market_aliases.csv` (6,546 bytes, SHA `57e49682f62e6e9a...` — MATCH)
  - `experiments/configs/price_forecast_v1.json` (9,310 bytes, SHA `cd875d249a126839...` — MATCH)
- **Panel V2 Regeneration Gate:**
  - Completed in 12.2 seconds on Kaggle CPU.
  - Final clean rows: 463,217 across 1,167 unique series.
  - **Panel V2 SHA-256:** `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` (EXACT MATCH).
- **Diagnostic Finding:**
  - In Cell 2 line 53, the assertion code checked `manifest_v2.get("input_rows", 0)`.
  - In `MandiDataPipeline` v2, summary metrics are stored under `manifest_v2["summary_metrics"]`, causing top-level `.get()` to return `0` and raising:
    `RuntimeError: ROW CONSERVATION VIOLATION! Expected 472,385, got 0 (sum 0). STOPPING.`
- **Local Repair & Verification:**
  - Repaired Cell 2 and Cell 6 to inspect `manifest_v2.get("summary_metrics", manifest_v2)`.
  - Verified against downloaded `processing_manifest_v2.json`:
    $$\text{Row Conservation: } 472,385 = 463,217 + 855 + 2,936 + 5,350 + 27 \quad (\text{EXACT MATCH})$$
  - Regenerated `experiments/notebooks/mp_fc_007_price_models.ipynb` and confirmed AST validation across all code cells.

---

## 5. Compliance with Standing Rules

1. **Zero Local Heavy Processing:** All full-panel joins, feature extraction, and model fitting remain remote. Local test fixtures adhere strictly to $\le 10$ MB, $\le 50,000$ rows, $\le 30$s.
2. **Zero Automatic Retries:** No second kernel push was executed. The run was halted, outputs retrieved, diagnostics established, and the repair prepared for explicit authorization.
3. **Preservation of Journal Integrity:** `documentation/context.md` was left strictly untouched. `brain/context.md` was updated.
