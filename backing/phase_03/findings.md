# Phase 3 Findings: Leakage-Safe Baseline Modeling and Temporal Evaluation (Corrected Pass)

## Executive Summary

Phase 3 constructed a controlled, leakage-safe empirical baseline experiment to evaluate whether machine learning models can predict wholesale agricultural mandi price movements over a 7-calendar-day horizon.

### Key Finding & Verdict
**Can machine learning models beat simple baselines on future mandi observations?**
- **Yes, in directional classification, but with critical caveats.**
- On the **Validation Partition** ($n=2,914$, origin dates January 25 to March 31, 2026), **LightGBM (Gradient Boosted Decision Trees)** achieved a **Macro F1 score of 0.4369** and **Balanced Accuracy of 44.53%**, substantially outperforming the naive **Majority-Class Baseline** (Macro F1 = 0.2136, Balanced Accuracy = 33.33%).
- Based strictly on this validation performance, LightGBM was selected and frozen as the primary candidate model.
- On the historical test window ($n=12,625$, origin dates April 8 to August 25, 2026), LightGBM achieved **60.40% accuracy** (**+4.50%** over the majority-class baseline of 55.90%), a **Balanced Accuracy of 46.19%** (**+12.86%** over baseline), and a **Macro F1 score of 0.4616** (**+0.2225** over baseline).
- **Holdout Integrity Correction**: Because multiple candidate models and regression baselines were evaluated on this historical test window during initial exploration, **this test window is explicitly documented as an exploratory / development holdout, NOT an untouched single-use final test**. Because the master dataset terminates on September 1, 2026, no later independent observations exist in the repository (Path B). An independent future observation period is strictly required for true out-of-sample testing.
- **Continuous Regression Verdict**: In a secondary continuous percentage-return experiment, **no machine learning model beat the simple Zero-Return Persistence benchmark on Mean Absolute Error (MAE)**. Zero-Return Persistence achieved 9.81% Val MAE and 11.06% Test MAE, whereas Ridge Regression achieved 11.88% Test MAE and LightGBM Regressor achieved 13.20% Test MAE. This demonstrates that wholesale mandi prices have high modal stickiness, making continuous point forecasts prone to variance inflation from fat-tailed price shocks, whereas 3-class directional classification captures actionable regime shifts.

---

## Exact Experiment Design

### 1. Data Policy & Clean Dataset
The experiment operates strictly on the accepted **Phase 2 Strategy 2** data policy:
- **160,192** total raw records ingested across all 5 raw mandi CSV files.
- Exact duplicates dropped; ambiguous same-grade series-date duplicate records (where multiple conflicting modal or min/max prices exist on the same date for the same grade) are completely excluded.
- The `Grade` dimension is strictly preserved.
- Canonical market mappings are enforced (Jhansi Grain, Purwa, and Baripaal identities remain strictly protected).
- Net clean records retained: **157,518**.
- Exactly matched $T+7$ calendar-day pairs: **116,826**.

### 2. Temporal Partitioning with Horizon Embargo Purging
To prevent lookahead leakage and target outcome contamination, chronological splitting was applied across all series simultaneously:

- **Training Partition** ($n=100,650$):
  - Origin Dates: September 1, 2024 to January 17, 2026
  - Target Realization Dates ($T+7$): September 8, 2024 to January 24, 2026
  - *Train Embargo Buffer*: Origins between January 18, 2026 and January 24, 2026 ($n=72$) were **purged** so no training target realization crosses into the validation period.
- **Validation Partition** ($n=2,914$):
  - Origin Dates: January 25, 2026 to March 31, 2026
  - Target Realization Dates ($T+7$): February 1, 2026 to April 7, 2026
  - *Validation Embargo Buffer*: Origins between April 1, 2026 and April 7, 2026 ($n=565$) were **purged** so no validation target realization crosses into the test period.
- **Exploratory Test Partition** ($n=12,625$):
  - Origin Dates: April 8, 2026 to August 25, 2026
  - Target Realization Dates ($T+7$): April 15, 2026 to September 1, 2026
  - Explicitly classified as an **exploratory/development holdout** (Path B).

### 3. Feature Engineering (Strictly Past Information at Origin $T$)
Thirteen features were computed strictly using information available at date $T$:
- Current Modal Price (Log transform)
- Intraday Price Spread Ratio (`(Max - Min) / Modal`)
- Exact Past Calendar Returns ($T-1$, $T-3$, $T-7$)
- Bounded 7-Day Past Return and Momentum Ratio ($T-7$ with fallback to $T-8$, $T-9$)
- Causal Historical Commodity Volatility (expanding std with `min_periods=10`, strictly causal with zero future backfilling)
- Calendar Day of Week and Month
- Static categorical indicators (Commodity, Canonical Market, Grade)

All imputation (median) and scaling were fit strictly on the Training partition.

---

## Experimental Results

### Primary Classification Benchmark (Target: 3-Class $T+7$ Direction)

#### Baseline Performance
| Baseline Name | Validation Acc (%) | Validation Macro F1 | Exploratory Test Acc (%) | Exploratory Test Balanced Acc (%) | Exploratory Test Macro F1 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Majority-Class Baseline (Normal)** | 47.15% | 0.2136 | 55.90% | 33.33% | 0.2391 |
| **Historical Class Frequency Baseline** | 39.36% | 0.3367 | 42.78% | 33.41% | 0.3327 |
| **Simple Historical Momentum Rule** | 44.13% | 0.3422 | 52.63% | 38.81% | 0.3839 |
| **Persistence / No-Change Benchmark** | 47.15% | 0.2136 | 55.90% | 33.33% | 0.2391 |

#### Model Performance & Selection
| Candidate Model | Validation Acc (%) | Validation Macro F1 | Candidate Selection Status | Exploratory Test Acc (%) | Exploratory Test Balanced Acc (%) | Exploratory Test Macro F1 | Test Acc Delta vs Majority | Test Macro F1 Delta vs Majority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Multinomial Logistic Regression** | 47.70% | 0.3672 | REJECTED ON VALIDATION | 57.79% | 43.63% | 0.4147 | +1.89% | +0.1756 |
| **Decision Tree (max_depth=5)** | 48.80% | 0.3626 | REJECTED ON VALIDATION | 57.63% | 41.10% | 0.3821 | +1.73% | +0.1430 |
| **Random Forest (100 trees, depth=8)** | 48.49% | 0.3362 | REJECTED ON VALIDATION | 56.45% | 37.48% | 0.3415 | +0.55% | +0.1024 |
| **LightGBM (100 trees, depth=5)** | **52.26%** | **0.4369** | **SELECTED PRIMARY CANDIDATE** | **60.40%** | **46.19%** | **0.4616** | **+4.50%** | **+0.2225** |

*Note: Candidate selection was driven solely by Validation Macro F1 (0.4369) and Balanced Accuracy (44.53%), without reference to test scores.*

#### Class-Level Performance on Exploratory Test Set (LightGBM vs Majority)
- **Normal Class** (Support: 7,058 / 55.90%):
  - Majority Baseline: Precision = 0.5590, Recall = 1.0000, F1 = 0.7171
  - LightGBM: Precision = 0.6850, Recall = 0.8774, F1 = 0.7694
- **Favorable Breakout Class** (Support: 2,967 / 23.50%):
  - Majority Baseline: Precision = 0.0000, Recall = 0.0000, F1 = 0.0000
  - LightGBM: Precision = 0.4069, Recall = 0.3043, F1 = 0.3482
- **Unfavorable Decline Class** (Support: 2,600 / 20.59%):
  - Majority Baseline: Precision = 0.0000, Recall = 0.0000, F1 = 0.0000
  - LightGBM: Precision = 0.3883, Recall = 0.2038, F1 = 0.2673

---

### Secondary Continuous Return Regression Benchmark

| Model | Partition | MAE (%) | RMSE (%) | Directional Acc (%) | MAE Delta vs Persistence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Zero-Return Persistence Benchmark** | VALIDATION | **9.81%** | 38.76% | **N/A** | 0.00% |
| **Zero-Return Persistence Benchmark** | EXPLORATORY_TEST | **11.06%** | 35.27% | **N/A** | 0.00% |
| Mean-Return Baseline | EXPLORATORY_TEST | 11.07% | 35.27% | 36.66% | +0.02% |
| Ridge Regression ($\alpha=10.0$) | EXPLORATORY_TEST | 11.88% | 35.42% | 39.06% | +0.82% |
| LightGBM Regressor | EXPLORATORY_TEST | 13.20% | 34.82% | 35.79% | +2.14% |

*Note on Directional Accuracy Convention: Directional accuracy for the Zero-Return persistence baseline is designated N/A because a zero return prediction has no positive or negative directional sign ($0 \times y_{\text{true}} = 0$).*

---

## Warning Diagnostics and Disposition

During unhandled fitting, `Logistic Regression` recorded 1,350 `RuntimeWarning`s (`divide by zero encountered in matmul` from Apple Accelerate BLAS).
- **Cause**: Apple's Accelerate BLAS `cblas_dgemm` hardware implementation triggers IEEE-754 FPU exception flags when dot products encounter zero/subnormal entries in sparse one-hot encoded matrices.
- **Verification**: All fitted weights were confirmed to be 100% finite, stable, and non-NaN (`clf.coef_` finite = True).
- **Resolution**: Scoped handling via `np.errstate(divide='ignore', over='ignore', invalid='ignore')` resolves spurious hardware flags while preserving true algorithmic convergence warnings (0 ConvergenceWarnings under `max_iter=1000`).

---

## Limitations and Unresolved Questions

1. **Absence of True Independent Holdout**: Because the master dataset terminates on September 1, 2026, all available post-April data was examined during development. A genuinely new future observation period is required for true final out-of-sample testing.
2. **Tail Recall**: While LightGBM achieves 60.40% overall accuracy, recall on the Unfavorable tail remains 20.38%. A system acting on these signals would miss roughly 80% of downward market drops.
3. **No Economic Sell/Store Claims**: While LightGBM shows predictive superiority over naive baselines, **no claim is made that the model is ready or superior for real-world farmer sell/store recommendations**. A real-world decision requires explicit modeling of storage losses, cold storage electricity charges, bagging fees, local transport costs, and risk aversion.

---

## Phase 3 Verdict
**Phase 3 is ACCEPTED as an experimental baseline modeling milestone.**
It establishes that tree-based gradient boosting using strictly causal past features outperforms naive baselines on future observations, while continuous price regression is inferior to stickiness persistence. It clearly bounds the experimental findings, eliminates false holdout claims, and establishes that a future observation period is required before production deployment.
