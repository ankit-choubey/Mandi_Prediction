# Phase 3 Findings: Leakage-Safe Baseline Modeling and Temporal Evaluation

## Executive Summary

Phase 3 constructed a rigorous, reproducible, leakage-safe empirical experiment to determine whether machine learning models can genuinely predict wholesale agricultural mandi price movements over a 7-calendar-day horizon.

### Key Finding & Verdict
**Can machine learning beat simple baselines on genuinely unseen future mandi observations?**
- **Yes, but modestly and with critical nuances.**
- On the untouched final holdout test set ($n=12,625$ future observations spanning April 8, 2026 to August 25, 2026), the strongest non-trivial baseline (the **Majority-Class Baseline**, predicting "Normal" 100% of the time) achieved an accuracy of **55.90%** with a Macro F1 score of **0.2391** and Balanced Accuracy of **33.33%** (it fails completely to detect price breakouts).
- The primary selected machine learning candidate, **LightGBM (Gradient Boosted Decision Trees)**, achieved **60.40% accuracy** (**+4.50%** improvement over majority baseline), a **Balanced Accuracy of 46.19%** (**+12.86%** improvement), and a **Macro F1 score of 0.4616** (**+0.2225** improvement over majority baseline).
- Interpretable linear models (Multinomial Logistic Regression) achieved 57.79% accuracy and 0.4147 Macro F1.
- Crucially, in a secondary continuous return regression experiment, **no machine learning model beat the simple Zero-Return Persistence benchmark on Mean Absolute Error (MAE)**. The persistence baseline achieved 11.06% test MAE, whereas Ridge Regression achieved 11.88% MAE and LightGBM Regressor achieved 13.20% MAE. This proves that wholesale mandi prices have high modal inertia, making continuous regression noisy and prone to large errors during price shocks, whereas discrete 3-class directional classification successfully captures actionable regime shifts.

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
- **Final Test Partition** ($n=12,625$):
  - Origin Dates: April 8, 2026 to August 25, 2026
  - Target Realization Dates ($T+7$): April 15, 2026 to September 1, 2026
  - Held completely untouched until model configuration was frozen.

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
| Baseline Name | Validation Acc (%) | Validation Macro F1 | Final Test Acc (%) | Final Test Balanced Acc (%) | Final Test Macro F1 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Majority-Class Baseline (Normal)** | 47.15% | 0.2136 | 55.90% | 33.33% | 0.2391 |
| **Historical Class Frequency Baseline** | 39.36% | 0.3367 | 42.78% | 33.41% | 0.3327 |
| **Simple Historical Momentum Rule** | 44.13% | 0.3422 | 52.63% | 38.81% | 0.3839 |
| **Persistence / No-Change Benchmark** | 47.15% | 0.2136 | 55.90% | 33.33% | 0.2391 |

#### Model Performance
| Candidate Model | Validation Acc (%) | Validation Macro F1 | Final Test Acc (%) | Final Test Balanced Acc (%) | Final Test Macro F1 | Test Acc Delta vs Majority | Test Macro F1 Delta vs Majority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Multinomial Logistic Regression** | 47.70% | 0.3672 | 57.79% | 43.63% | 0.4147 | +1.89% | +0.1756 |
| **Decision Tree (max_depth=5)** | 48.80% | 0.3626 | 57.63% | 41.10% | 0.3821 | +1.73% | +0.1430 |
| **Random Forest (100 trees, depth=8)** | 48.49% | 0.3362 | 56.45% | 37.48% | 0.3415 | +0.55% | +0.1024 |
| **LightGBM (100 trees, depth=5)** | **52.26%** | **0.4369** | **60.40%** | **46.19%** | **0.4616** | **+4.50%** | **+0.2225** |

#### Detailed Class-Level Performance on Final Test Set (LightGBM vs Majority)
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
| **Zero-Return Persistence Benchmark** | VALIDATION | **9.81%** | 38.76% | 0.00% | 0.00% |
| **Zero-Return Persistence Benchmark** | FINAL_TEST | **11.06%** | 35.27% | 0.00% | 0.00% |
| Mean-Return Baseline | FINAL_TEST | 11.07% | 35.27% | 36.66% | +0.02% |
| Ridge Regression ($\alpha=10.0$) | FINAL_TEST | 11.88% | 35.42% | 39.06% | +0.82% |
| LightGBM Regressor | FINAL_TEST | 13.20% | 34.82% | 35.79% | +2.14% |

**Key Regression Insight**: Machine learning regression models suffer higher mean absolute errors than simply guessing 0.0% change. Wholesale prices remain flat most weeks, but when structural changes occur, returns spike into double digits (+50% to +100%). Regression algorithms attempt to fit extreme outliers and end up degrading predictions across the sticky majority.

---

## Subgroup & Market Disaggregation

Across major commodities in the final test set:
- **Potato** ($n=2,168$): LightGBM achieved **64.21% accuracy** (Macro F1 = 0.4571).
- **Onion** ($n=1,770$): LightGBM achieved **53.84% accuracy** (Macro F1 = 0.4553).
- **Tomato** ($n=1,135$): LightGBM achieved **48.11% accuracy** (Macro F1 = 0.4287), reflecting higher perishability volatility.
- **Wheat** ($n=1,061$): LightGBM achieved **71.25% accuracy** (Macro F1 = 0.4632), reflecting staple commodity stability.

---

## Limitations and Unresolved Questions

1. **Class Asymmetry**: While LightGBM achieves 60.40% overall accuracy, recall on the Unfavorable tail remains 20.38%. A system acting on these signals would miss roughly 80% of major downward market drops.
2. **Wholesale Auction Lag vs Local Farmer Realities**: Data reflects APMC yard close prices. Transportation costs, grading arbitrations, and bag handling fees are not modeled.
3. **Absence of Exogenous Drivers**: Macro factors such as monsoon rainfall distribution, diesel transportation prices, and mandi arrival volumes are not yet integrated.
4. **Non-Stationarity**: Seasonal shifts between rabi and kharif harvesting cycles alter class prior distributions between validation and test windows.

---

## Conclusion
Phase 3 conclusively demonstrates that gradient boosted decision trees utilizing strictly past prices, lagged returns, and causal volatility **do outperform naive baselines** on unseen future mandi observations (+4.50% accuracy and +0.2225 Macro F1). However, the absolute predictive power remains moderate, and direct continuous regression is strictly inferior to persistence. No farmer-facing recommendations or synthetic storage profit models should be built on unvalidated regression point forecasts.
