# Step 7 Benchmark Prediction Recovery & Evaluation Summary
**Task ID:** MP-FC-007-SCORE
**Date:** 2026-11-12 IST
**Status:** ALL GATES PASSED (Prediction Scoring & Scorecard Recovery Complete)
**Execution Context:** Standalone local scoring under explicit owner exception (at most 70,000 archived prediction rows, 50 MB decoded CSV, 512 MB memory, 10 min total, 30s per stage; zero model retraining, tuning, or raw panel reading).

---

## 1. Executive Summary & Verification Context

Following the completion of the 4-fold outer benchmark on Kaggle CPU (`theankitchoubey/mp-fc-007-price-models`, Version 2), all 8 trained candidate models and the complete 64,776-row forecast predictions archive were successfully recovered into `experiments/outputs/FC007_recovery/`. The remote run terminated in Cell 5 line 62 due to `NameError: name 'List' is not defined` prior to scorecard generation.

Under explicit owner authorization, the predictions archive was cryptographically verified and scored locally using a standalone, non-destructive pipeline (`src/score_forecast_archive.py`). All 24 required slices—including Overall Combined, Folds F1–F4, Tiers A & B, 6 Focus Crops, 5 Target Districts, 3 Date Regimes, and 3 Sensitivity Suites—were evaluated with 1,000 series-clustered bootstrap iterations in **3.67 seconds** (exceeding the 10-minute deadline and complying with all resource bounds).

---

## 2. Cryptographic & Row Accounting Verification

### Archive File Integrity
| Archive Artifact | Size (Bytes) | Row Count | SHA-256 Digest | Verification Status |
|---|---|---|---|---|
| `master_predictions_fc007.csv.gz` | 4,889,882 | 64,776 | `a61b38328e011b2ed75dd5d814fbf697d624ac948c50a198d374bfcaff2b9970` | **MATCH (100%)** |
| `master_predictions_fc007.parquet` | 4,088,120 | 64,776 | `cc813dbd73c2631df646cc32f1ff2e86079b087bb1fcf3fb198d2e1d41e084d7` | **MATCH (100%)** |

### Row Accounting & Boundary Gates
- **Total Scored Predictions:** Exactly **64,776** rows (exact match to logged total).
- **Outer Fold Breakdown:**
  - `F1`: 37,858 rows (58.44%)
  - `F2`: 23,490 rows (36.26%)
  - `F3`: 1,413 rows (2.18%)
  - `F4`: 2,015 rows (3.11%)
- **Tier Invariant:** `is_tier_a` = 64,776 (100%), `is_tier_b` = 62,932 (97.15%). Tier B is confirmed to be a strict mathematical subset of Tier A.
- **Date Regimes:**
  - `HISTORICAL` ($< \text{2025-01-01}$): 61,348 rows (94.71%)
  - `MODERN` ($\ge \text{2026-01-01}$): 2,330 rows (3.60%)
  - `TRANSITION` ($\text{2025-01-01}$ to $\text{2025-12-31}$): 1,098 rows (1.70%)
- **Price Integrity:** 100% of realized target prices ($y_{\text{true}}$) and origin prices ($y_t$) are strictly positive finite numbers (zero negatives, zero infinities, zero nulls).
- **Temporal Strictness:** All outer test origins and target dates conform strictly to fold holdout date ranges; no lookahead or target leakage.
- **Scope A Disputed Keys:** Exactly **18 rows** matched the canonical 6-part disputed keys (confirmed exact tuple join).

---

## 3. Miniature Preflight Verification

Prior to processing the full 64,776-row archive, `run_miniature_preflight` was executed in an isolated temporary directory using real prediction samples augmented with synthetic boundary test cases:
1. **Empty Slice ($N = 0$):** Verified complete schema emission with NaNs and `unique_series = 0`, `coverage = 0.0`, `is_low_n = True`.
2. **All-Abstained Slice:** Verified complete schema emission with `coverage = 0.0`, `abstention_count = total_samples`.
3. **Zero-Denominator Slice ($y_{\text{true}} = y_{\text{naive}}$):** Verified that paired skill is strictly undefined (`NaN`), preventing division-by-zero errors.
4. **Atomic Table Serialization:** Verified atomic write, schema preservation, and 100% disk read-back equality.
5. **Preflight Result:** **ALL 5 PREFLIGHT CHECKS PASSED in 0.02s**.

---

## 4. Overall Combined Benchmark Scorecard

Evaluated across all 64,776 outer test cases ($N_{\text{series}} = 401$, 1,000 series-clustered bootstrap resamples, seed 42):

| Model | Scored Origins | Abstentions | Coverage | MAE (INR/q) | MAE 95% CI | RMSE | Median AE | Paired Naive MAE | Paired Skill Score | Skill 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|
| **Naive Baseline ($y_t$)** | 64,776 | 0 | 100.0% | **106.96** | [95.47, 119.02] | 298.83 | 40.00 | 106.96 | 0.00% | [0.00%, 0.00%] |
| **Damped Drift** | 64,036 | 740 | 98.86% | 107.32 | [96.32, 119.35] | 303.67 | 42.00 | 106.60 | -0.68% | [-3.09%, +1.76%] |
| **HistGradientBoosting** | 64,776 | 0 | 100.0% | 109.75 | [98.80, 121.19] | **281.16** | 46.44 | 106.96 | -2.61% | [-4.28%, -1.21%] |
| **Ridge Regression** | 64,776 | 0 | 100.0% | 110.32 | [99.78, 121.42] | 288.56 | 45.58 | 106.96 | -3.15% | [-4.92%, -1.72%] |
| **Moving Average (7obs/30d)** | 64,776 | 0 | 100.0% | 134.19 | [119.67, 149.96] | 333.37 | 50.71 | 106.96 | -25.47% | [-29.04%, -21.03%] |
| **Seasonal Naive (357d)** | 59,200 | 5,576 | 91.39% | 774.38 | [667.74, 890.88] | 1,433.76 | 375.00 | 105.02 | -637.38% | [-733.55%, -547.01%] |

### Key Empirical Findings
1. **The Naive Dominance Phenomenon:** In retrospective $h=7$ mandi price forecasting without external arrival or weather features, the persistence Naive baseline ($y_t$) outperforms all candidate machine learning models on MAE (106.96 vs 109.75 for HGB, 110.32 for Ridge).
2. **Skill Score Significance:** Both Ridge ($\text{Skill} = -3.15\%$, 95% CI $[-4.92\%, -1.72\%]$) and HistGradientBoosting ($\text{Skill} = -2.61\%$, 95% CI $[-4.28\%, -1.21\%]$) exhibit statistically significant negative skill relative to Naive (zero is excluded from both 95% bootstrap intervals).
3. **RMSE Advantage of Tree Models:** While HGB has slightly higher MAE than Naive, it achieves lower RMSE (281.16 vs 298.83), reflecting shrinkage on extreme price spikes.
4. **Underperformance Against Naive is an Authentic Result:** In volatile agricultural spot markets with intermittent trading, simple autoregressive and tree ML models fitted only on recent price changes frequently over-react to transitory noise. Underperformance against Naive is a valid, honest scientific finding, **not a bug or justification for unconstrained hyperparameter searching**.

---

## 5. Focus Crop Breakdown (HGB vs Naive)

| Focus Crop | Scored Count | Series Count | Naive MAE | HGB MAE | HGB Paired Skill | Skill 95% CI |
|---|---|---|---|---|---|---|
| **Wheat** | 22,253 | 11 | 37.07 | 39.46 | -6.44% | [-10.87%, -1.82%] |
| **Potato** | 10,750 | 15 | 87.21 | 91.30 | -4.68% | [-7.78%, -1.33%] |
| **Tomato** | 6,368 | 8 | 321.46 | 319.24 | **+0.69%** | [-2.33%, +3.83%] |
| **Onion** | 6,036 | 10 | 196.22 | 199.19 | -1.51% | [-4.96%, +2.05%] |
| **Paddy(Dhan)(Common)**| 1,223 | 5 | 55.43 | 61.27 | -10.53% | [-21.37%, -0.42%] |
| **Rice** | 3,118 | 8 | 49.33 | 53.64 | -8.74% | [-16.03%, -2.67%] |

*Observation:* Tomato is the sole focus crop where HGB achieves positive point skill (+0.69%), though its 95% CI $[-2.33\%, +3.83\%]$ spans zero. For all major grain staples (Wheat, Paddy, Rice), Naive decisively dominates.

---

## 6. Sensitivity Analyses

1. **Exact $T+7$ Calendar Observation:** Evaluated on origins with an exact observation on day $t+7$ (35,972 rows, 55.53% of sample). HGB MAE: 99.44 vs Naive MAE: 96.65 ($\text{Skill} = -2.89\%$).
2. **Retrospective Realized $>2\%$ Movement:** Evaluated on non-stationary regimes where price moved $>2\%$ over 7 days (48,237 rows, 74.47% of sample). HGB MAE: 141.43 vs Naive MAE: 137.94 ($\text{Skill} = -2.53\%$).
3. **Scope A Canonical Disputed Keys Exclusion:** Evaluated with the 18 disputed rows removed (64,758 rows). Metrics are identical to 3 decimal places (HGB MAE: 109.75 vs Naive: 106.96, $\text{Skill} = -2.61\%$).
4. **Scope B Historical Removal Sensitivity:** Marked **PENDING_RECOMPUTATION_BUDGET_EXCLUDED**. Recomputed forecasts without historical aliases were not generated in this run and require dedicated budget.

---

## 7. Audit of Missing Evidence & Traceability

- **Inner Hyperparameter Tuning Scores Trace:** **NOT RECOVERED**. Tuning scores across candidate parameter grids were unpersisted prior to the Cell 5 crash. Selected configurations and sample sizes were recovered from the execution log, but per-grid scores remain unpersisted.
- **Model Binaries:** 8 scikit-learn models (`hgb_F1.joblib` .. `F4`, `ridge_F1.joblib` .. `F4`) are preserved in `experiments/outputs/FC007_recovery/models/`. In accordance with safety rules, they were **not deserialized locally**; all scoring proceeded directly from the verified prediction archives.

---

## 8. Output Manifest & Cryptographic Receipts

All recovered scorecards and receipts have been atomically written to `experiments/reports/FC007_RECOVERED/`:

```
master_scorecards_all.csv           (43,227 bytes, SHA256: 59f51d7da9140ee402467516c121ae53b7b022d03676599908edd6dbeba91b6e)
scorecard_overall.csv               ( 2,062 bytes, SHA256: 02e35fc24e0d3bbe71ed9c2201cb24698c45debf452275d7c3351b357fa9901a)
scorecard_folds.csv                 ( 7,277 bytes, SHA256: 98cd7e0c73537832da251522e32fccd6a2a9cce766c3855b0db25715b3c3cca7)
scorecard_tiers.csv                 ( 3,749 bytes, SHA256: e8db3ceb4be7e38435d2d0b57140e6c568ae98e8f81395b058141444155106e2)
scorecard_crops.csv                 (10,746 bytes, SHA256: 6de6a472e2bfb6d649022a7d98122e8989b64f6b8e34a74f878ce31ea3688b2c)
scorecard_districts.csv             ( 9,206 bytes, SHA256: 49feddecf2d84b4a493a37ef647efc33b888de0de0fc74ba8a7151b1241662fe)
scorecard_regimes.csv               ( 5,693 bytes, SHA256: dac9847dcec075e05bf5e0c5d2f1c30e79e70f657d77996de61ddfa741317f2b)
scorecard_sensitivities.csv         ( 5,940 bytes, SHA256: cf5f5518b55a5574f28fc5e156b862ce65c65a638bbad724115b18a5d124b42b)
reconciliation_assertion_receipt.json(1,231 bytes, SHA256: f30d2807f102cafb6d0954925e9a35625fe1a50d0912efff8154052d0e7764a0)
output_manifest.json                ( 2,228 bytes, SHA256: 5e64811f5d6f199738018bf0a08e1ec2cb4b3f81e37b2d56e29783f6f1faad28)
```
