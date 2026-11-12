# Step 7 Benchmark Verification & Step 8 Chronological Interval Evaluation Summary
**Task ID:** MP-FC-008
**Date:** 2026-11-13 IST
**Status:** ALL GATES PASSED (Gate A: 100% Numerical Parity Verified; Gate B: Chronological Intervals Evaluated)
**Execution Context:** Standalone local scoring and interval calibration under explicit owner exception (at most 70,000 archived prediction rows, 50 MB decoded CSV, 512 MB memory, 10 min total, 30s per stage; zero model retraining, tuning, or raw panel reading).

---

## 1. Executive Summary & Sequential Completion Gates

Task `MP-FC-008` established two sequential mathematical and uncertainty gates on the immutable 64,776-row forecast prediction archive (`master_predictions_fc007.csv.gz`, SHA-256 `a61b38328e011b2ed75dd5d814fbf697d624ac948c50a198d374bfcaff2b9970`):

1. **Gate A (Step 7 Benchmark Scorecard Numerical Parity):**
   - Corrected all underlying evaluation and metric calculations using pure Python standard library scalar arithmetic (`csv`/`gzip`, `Counter`, `math.fsum`, `statistics.median`, deterministic stdlib `random.Random(42)` cluster bootstrap).
   - Validated that the root cause of prior bias discrepancy was memory buffer reuse in NumPy 2.2 / Python 3.14 (`errors ** 2` mutating in place before `mean(errors)`). In `src/forecast_benchmark.py`, made `errors` strictly read-only and evaluated `errors * errors` separately.
   - Re-scored all 24 required slices and verified **100% numerical parity** against `experiments/reports/FC007_REFERENCE/independent_point_check.json` (max difference $\le 3.55 \times 10^{-15}$).
   - Disputed key sensitivity correctly matched the canonical 6-part tuple on all 18 prediction rows.
   - Authoritative verified scorecards, slice key inventory, and assertions are permanently saved in `experiments/reports/FC007_VERIFIED/`.

2. **Gate B (Step 8 Chronological Prediction Interval Calibration):**
   - Frozen calibration protocol defined in `experiments/configs/interval_calibration_v1.json`.
   - Primary point method: prespecified naive persistence anchor ($y_t$), which wins verified MAE (106.96 INR/q).
   - Exploratory models: Ridge and HistGradientBoosting (stored predictions only).
   - Strict chronological ordering: at each outer-fold start, calibrated using **only earlier-fold out-of-sample residuals** whose actual target dates fell within the preceding 180 calendar days strictly before fold test start.
   - Zero future leakage: Fold F1 has `NO_PRIOR_CALIBRATION`; F2 uses matured F1; F3 uses matured F1/F2; F4 uses matured F2/F3.
   - Conformal-style normalized score: $s = |y_{\text{true}} - \hat{y}| / y_t$; rank $k = \lceil(n + 1)(1 - \alpha)\rceil$ with no quantile rounding.
   - Grouping hierarchy: exact commodity ($N \ge 200, \text{series} \ge 10$) $\rightarrow$ `POOLED_FALLBACK` $\rightarrow$ `NO_CALIBRATION`.
   - Full row-level predictions (388,656 evaluations across models and levels) generated in 0.58s and compressed to git-ignored `experiments/outputs/FC008/master_intervals_fc008.csv.gz`.
   - All interval scorecards evaluated and saved in `experiments/reports/FC008/`.

---

## 2. Gate A: Authoritative Verified Benchmark Results

### Overall Combined Scorecard ($N = 64,776$ outer test origins, $N_{\text{series}} = 401$)

| Model | Scored Origins | Abstentions | Coverage | MAE (INR/q) | Bias (INR/q) | RMSE | Within 5% | Paired Naive MAE | Paired Skill Score | Diff vs Ref Check |
|---|---|---|---|---|---|---|---|---|---|---|
| **Naive Baseline ($y_t$)** | 64,776 | 0 | 100.0% | **106.9554** | **+17.1728** | 298.8337 | 76.76% | 106.9554 | **0.00%** | $< 10^{-15}$ |
| **Damped Drift** | 64,036 | 740 | 98.86% | 107.3248 | +7.8091 | 303.6659 | 76.55% | 106.5998 | -0.68% | $< 10^{-15}$ |
| **HistGradientBoosting** | 64,776 | 0 | 100.0% | 109.7489 | +26.3678 | **281.1581** | 73.97% | 106.9554 | -2.61% | $< 10^{-15}$ |
| **Ridge Regression** | 64,776 | 0 | 100.0% | 110.3247 | +26.6763 | 288.5644 | 75.44% | 106.9554 | -3.15% | $< 10^{-15}$ |
| **Moving Average (7obs/30d)** | 64,776 | 0 | 100.0% | 134.1925 | +26.3044 | 333.3659 | 70.98% | 106.9554 | -25.47% | $< 10^{-15}$ |
| **Seasonal Naive (357d)** | 59,200 | 5,576 | 91.39% | 774.3764 | +351.6901 | 1,433.7629 | 22.70% | 105.0167 | -637.38% | $< 10^{-15}$ |

### Mathematical Invariants Verified
1. **$|\text{Bias}| \le \text{MAE} \le \text{RMSE}$:** Holds strictly for all models across all slices (e.g. Naive: $|+17.17| \le 106.96 \le 298.83$).
2. **Disjoint Conservation:** Fold counts strictly sum to total ($37,858 + 23,490 + 1,413 + 2,015 = 64,776$).
3. **Finite-Value Conservation:** 100% of realized target prices ($y_{\text{true}}$) and origin prices ($y_t$) are positive finite floats.
4. **Percentage Validity:** Within-5% metrics strictly bounded in $[0, 100]\%$.
5. **Exact Scope A Disputed Key Count:** Exactly 18 rows matched canonical 6-part keys, removing which leaves 64,758 rows (`Sensitivity_ScopeA_Disputed_Excluded`).

---

## 3. Gate B: Chronological Prediction Interval Evaluation

### Calibration Windows & Available History
| Fold | Evaluation Range (Origins) | Calibration Window (Preceding 180d) | Earlier Folds Used | Available Cal Rows | Status |
|---|---|---|---|---|---|
| **F1** | 2025-01-08 to 2025-06-24 | None | None | 0 | `NO_CALIBRATION` (Abstained) |
| **F2** | 2025-07-08 to 2025-10-25 | 2025-01-09 to 2025-07-07 | F1 | 37,858 | `CALIBRATED` |
| **F3** | 2025-12-26 to 2026-03-25 | 2025-06-29 to 2025-12-25 | F1, F2 | 23,920 | `CALIBRATED` |
| **F4** | 2026-04-08 to 2026-09-24 | 2025-10-10 to 2026-04-07 | F2, F3 | 5,445 | `CALIBRATED` |

*Verification:* For every calibrated fold, $\max(\text{target\_date}_{\text{cal}}) < \min(\text{origin\_date}_{\text{eval}})$. Zero future outcomes were observed or used during calibration.

### Overall Evaluated Folds (F2–F4 Combined, $N = 26,918$ test origins, 365 unique series)

| Model | Nominal Level | Issued Count | Abstained Count | Fallback Share | Empirical Coverage | 95% Cluster Boot CI | Nominal Dev | Mean Width (INR/q) | Median Width | Rel Width ($W/y_t$) | Lower Miss | Upper Miss | Mean Interval Score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Naive** | 90% | 26,918 | 0 | 44.02% | **89.9547%** | [88.18%, 91.42%] | -0.0453% | 662.65 | 457.78 | 21.12% | 5.02% | 5.02% | 1,334.82 |
| **Naive** | 95% | 26,918 | 0 | 44.02% | **94.3829%** | [93.01%, 95.52%] | -0.6171% | 977.14 | 684.21 | 30.65% | 2.82% | 2.80% | 1,935.48 |
| **Ridge** | 90% | 26,918 | 0 | 44.02% | **89.9955%** | [88.36%, 91.48%] | -0.0045% | 651.26 | 454.78 | 20.85% | 5.31% | 4.70% | 1,306.64 |
| **Ridge** | 95% | 26,918 | 0 | 44.02% | **94.4312%** | [93.14%, 95.49%] | -0.5688% | 962.48 | 673.21 | 30.25% | 2.86% | 2.71% | 1,905.86 |
| **HGB** | 90% | 26,918 | 0 | 44.02% | **89.9955%** | [88.25%, 91.52%] | -0.0045% | 678.28 | 485.55 | 21.62% | 5.37% | 4.63% | 1,324.87 |
| **HGB** | 95% | 26,918 | 0 | 44.02% | **94.3978%** | [93.04%, 95.55%] | -0.6022% | 977.88 | 710.42 | 30.85% | 2.95% | 2.65% | 1,923.14 |

### By Fold Breakdown (Naive Model)

| Fold | Nominal Level | Issued Rows | Abstained Rows | Empirical Coverage | 95% Cluster Boot CI | Nominal Dev | Mean Width (INR/q) | Rel Width | Lower Miss | Upper Miss | Mean Interval Score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **F1** | 90% / 95% | 0 | 37,858 | N/A (`NO_CALIBRATION`) | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| **F2** | 90% | 23,490 | 0 | **92.3159%** | [90.88%, 93.60%] | +2.3159% | 718.54 | 22.28% | 3.97% | 3.72% | 1,175.81 |
| **F2** | 95% | 23,490 | 0 | **95.8961%** | [94.91%, 96.79%] | +0.8961% | 1,051.84 | 32.00% | 2.15% | 1.95% | 1,643.67 |
| **F3** | 90% | 1,413 | 0 | **75.9377%** | [69.33%, 83.40%] | -14.0623% | 379.93 | 18.14% | 11.61% | 12.46% | 1,028.68 |
| **F3** | 95% | 1,413 | 0 | **84.0764%** | [78.58%, 89.81%] | -10.9236% | 574.49 | 27.10% | 7.36% | 8.56% | 1,415.44 |
| **F4** | 90% | 2,015 | 0 | **72.2581%** | [59.92%, 81.74%] | -17.7419% | 209.41 | 9.74% | 12.70% | 15.04% | 3,403.23 |
| **F4** | 95% | 2,015 | 0 | **83.9702%** | [72.97%, 92.57%] | -11.0298% | 388.68 | 17.39% | 7.39% | 8.64% | 5,701.92 |

---

## 4. Empirical Insights & Limitations

1. **Overall Validity vs Regime Sensitivity:**
   - On the pooled F2–F4 sample, chronological conformal calibration achieves empirical coverage exceptionally close to nominal (89.95% vs 90.0%, 94.38% vs 95.0%), and both 95% series-cluster bootstrap intervals comfortably contain the nominal target.
   - However, disaggregating across chronological folds reveals substantial non-stationarity: in Fold F2 (calm/historical regime), coverage is over-conservative (92.3% and 95.9%), whereas in Folds F3 and F4 (crisis/transition and modern regime shifts), empirical coverage plummets to 72%–76% at nominal 90% and 84% at nominal 95%.
2. **Why Under-Coverage in F3/F4 is an Authentic Finding:**
   - Under causal out-of-sample calibration, the model only sees past 180-day volatility. During sudden supply-chain shocks or structural inflation shifts, past residual spreads underestimate future volatility.
   - Per the prompt's explicit instruction, under-coverage during regime shifts is an authentic finding demonstrating time-series non-exchangeability, **not permission to leak future outcomes or widen intervals retrospectively**.
3. **Commodity Disaggregation:**
   - Grain staples with high market liquidity (Wheat, Potato, Onion) achieve near-nominal coverage with modest relative widths (Wheat: 6.45% width at 90% level, 89.88% coverage).
   - High-volatility perishables (Tomato) require wide intervals (58.77% relative width) to cover price swings.
   - Commodities with sparse history (e.g. Paddy Common) utilize the prespecified pooled fallback (100% fallback share) honestly.

---

## 5. Artifact Manifest & Cryptographic Hashes

### Gate A Reports (`experiments/reports/FC007_VERIFIED/`)
| Filename | Size (Bytes) | SHA-256 Digest |
|---|---|---|
| `master_scorecards_all.csv` | 43,341 | `4e4c9656886e8a0fa626ca3d9c7ba2dc2bdafc5fbbff4a37a9163864070a248a` |
| `scorecard_overall.csv` | 2,067 | `e2a77a942daffc5c2d12e840a1b63eb4c7a52e04f052ce526017e88cf2400e93` |
| `scorecard_folds.csv` | 7,309 | `b68c92a955e429304c4f3467c9c0d127606e92cbef806dca50bf699478f79d9e` |
| `scorecard_crops.csv` | 10,774 | `b4991195669b7f52636a0d6aa027a7aa3dbe8586b51eb143d22329fb81190d79` |
| `scorecard_districts.csv` | 9,248 | `f7ca16fdf9cf97df6dbef559868c2d58d98d287bc1286eb79ccfe7058df20a11` |
| `scorecard_regimes.csv` | 5,695 | `fe331484cefa6e92b3aa9430c6a51d9d7008bc59e78eef84074ee511e4f48ff1` |
| `scorecard_sensitivities.csv` | 5,940 | `2e08cba996c5e7b2500be550dfbe8f0e0c03dbbb88c9f5835904944ec9908cf6` |
| `scorecard_tiers.csv` | 3,760 | `0e7c3e1762c2f7b198c60bc9d63c467dd93cf933ff229f6dd85eeecabf985b46` |
| `slice_key_inventory.json` | 3,068 | `36512daff9c9a8ccf3c9597ffdd9df795906d445a6c3842c3dd484666a7b7495` |
| `reconciliation_assertion_receipt.json` | 3,189 | `96a2fa80e8e6e580e660ee071661665a38a7c2957b4f51e39bbf8a595304b504` |
| `output_manifest.json` | 2,701 | `3a186414cb2a54fb18ec0e72909f2b87f465dae06c13876da11f4d9241b2aa7e` |

### Gate B Reports (`experiments/reports/FC008/`)
| Filename | Size (Bytes) | SHA-256 Digest |
|---|---|---|
| `calibration_quantiles.json` | 62,652 | `8b50d04134dd0e41ff3a5a7595d838c124a4ff2d72999c87b8c9b9d3d3883268` |
| `intervals_overall.csv` | 1,348 | `85d42e95d97ba94f8193c1c0e04c417a72faf15205a736a92f90e2291c03d069` |
| `intervals_by_fold.csv` | 3,811 | `5c5e07efaa6a73227a034fc794b8b0f110fd4bb178b9e17485a57b0f6413b8e7` |
| `intervals_by_crop.csv` | 5,878 | `bb68387650fc93f6dafffee9c787bb2ca965c3fdb6615f384f754cfe14744513` |
| `intervals_by_district.csv` | 5,325 | `a220a619ca085c6ef8a4fd8bafaaac5b9c5aa8ae1ee3d420827e84b76e0ed24d` |
| `intervals_by_regime.csv` | 3,352 | `80611ec6c87e2158bef0d88474df62b2131d713ab17f35925b8b1d3ca25c5500` |
| `master_intervals_scorecards.csv` | 18,362 | `8b9f22dd20b7dccc2d970083ae3bebe52507d6abe7cfe10b272dfacb585f2611` |
| `interval_evaluation_receipt.json` | 1,439 | `5ef3c8235a0ad2717ed57a395a83f82d77e2f7db2cbc512887832282d7e4c55c` |
| `output_manifest.json` | 1,952 | `4e2daecba6ce2faae3b9e4a3028243bece26c514841ec2272e2d8e411b021318` |

---

## 6. Project Milestone Accounting

- **Current Step:** Step 8 complete.
- **Main Milestones Remaining:**
  - Prior to independent review acceptance: 7 main milestones (Steps 7–13) remain.
  - Upon independent review confirmation of Gate A and Gate B: **5 main milestones** (Steps 9–13) plus 2 optional experiments remain.
- **Next Milestone:** Step 9 (Causal Economic Value & Decision Evaluation), with any synthetic scenario generation still requiring prior explanation and explicit owner approval.
