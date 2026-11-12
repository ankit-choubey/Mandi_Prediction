# Mandi Price Forecasting Data & Feature Contract (v1.0.0)

**Task Reference:** MP-DATA-008 / Step 7 Machine Learning Preparation  
**Generated Date:** 2026-11-12 IST  
**Status:** FROZEN SPECIFICATION (Pending Remote Step 7 Benchmark Execution)  
**Implementation Modules:** `src/forecast_features.py`, `experiments/configs/price_forecast_v1.json`  

---

## 1. Executive Summary & Purpose

This contract establishes the formal temporal data, missingness, and feature engineering specifications required for continuous 7-day price forecasting across Uttar Pradesh APMC mandi markets. It permanently freezes:
1. **Target Evaluation Logic:** Continuous 7-day ahead target within a bounded $[\tau+6, \tau+8]$ calendar window with deterministic earlier tie-breaking.
2. **Missing-Data Taxonomy:** Mutually exclusive failure and denial categories separating historical unobservability from operational serving policy.
3. **Causal Feature Architecture:** Exact calendar lags, preceding rolling windows with explicit sample burn-in, and strict retrospective visibility.
4. **Reproducible Experiment Protocol:** Specification of chronological temporal folds (F1–F4), baseline rescoring, and candidate model evaluation for Step 7.

> [!IMPORTANT]
> **Zero Local Model Training:** No models are fitted and no Kaggle runs are dispatched in this task. This contract governs the exact code and configuration to be executed in authorized remote benchmarks.

---

## 2. Temporal Evaluation & Target Definition

### 2.1 Horizon 7 Target Window
For a prediction origin at calendar date $t$, the nominal forecast horizon is $H = 7$ calendar days (target date $t + 7$). In agricultural commodity markets with irregular Sunday closures, regional festivals, and sporadic trading:
- **Evaluation Target Window:** $W_{\text{target}} = [t + 6, t + 8]$.
- **Target Selection Priority:**
  1. If $t + 7$ is observed, select $t + 7$ (distance $= 0$).
  2. If $t + 7$ is unobserved, evaluate candidate dates $t + 6$ and $t + 8$ (distance $= 1$).
  3. **Tie-Breaking Rule:** **Tie earlier**. If both $t + 6$ and $t + 8$ are observed (and $t + 7$ is unobserved), select $t + 6$.
  4. If only $t + 6$ is observed, select $t + 6$.
  5. If only $t + 8$ is observed, select $t + 8$.
  6. If no observations exist in $[t + 6, t + 8]$, record `NO_TARGET_IN_WINDOW`. This origin is ineligible for evaluation scoring.

### 2.2 Sensitivity & Boundary Constraints
- **Exact $T+7$ Sensitivity:** Scored evaluation pipelines must report secondary sensitivity metrics restricted to exact $t+7$ observations to quantify any distortion introduced by $[\pm 1]$ day windowing.
- **Fold Test End Boundary:** The actual selected target date must satisfy:
  $$\text{target\_date} \le \text{fold\_test\_end}$$
  Origins where $t \le \text{fold\_test\_end}$ but whose selected target falls beyond $\text{fold\_test\_end}$ are excluded from test evaluation.
- **Training Maturation Boundary:** For training fold cutoff $T_{\text{train}}$, every training observation must have matured within the training window:
  $$\text{target\_date} \le T_{\text{train}}$$
  Because the target window extends up to $t + 8$, training origins are causally restricted to:
  $$t \le T_{\text{train}} - 8$$
  This strictly prevents target observation leakage into the test or embargo periods.

### 2.3 Retrospective Availability & Issue Time
- **Issue Time:** Declared as **06:00 IST** on origin date $t$.
- **Causal Visibility:** A prediction issued at $t$ may observe only market data dated $\le t$ that was published prior to issue time.
- **Historical Retrospective Assumption:** Historical APMC records record arrival dates but omit publication timestamps. Therefore, historical model evaluation operates under the *retrospective availability assumption* (all records dated $\le t$ are assumed available).
- **Prohibition on Synthetic Labels & Interpolation:** Linear interpolation, spline smoothing, forward-filling across future targets, or backfilling future observations to invent training labels is strictly prohibited.

---

## 3. Missing-Data Taxonomy & Serving Policies

Missing values are differentiated into six disjoint structural categories:

| Category | Definition | Operational Handling |
| :--- | :--- | :--- |
| **`NO_ORIGIN`** | Series had no market trade recorded on date $t$. | Model may produce forecast from prior state, but origin is marked unobserved. |
| **`INELIGIBLE_HISTORY`** | Series failed Tier A or Tier B thresholds in training fold. | Excluded from scored benchmark pools; reported in population coverage. |
| **`MISSING_FEATURES`** | Insufficient historical burn-in (e.g. series has no prior observations $\le t$). | Model abstains from prediction; recorded in abstention accounting. |
| **`NO_TARGET`** | No valid trade observation in $[t+6, t+8]$ window. | Evaluation origin skipped for scoring; cannot compute residuals. |
| **`MODEL_ABSTENTION`** | Model produces non-finite output, out-of-bounds forecast, or triggers confidence threshold. | Counted in abstention rate; does not count as zero error. |
| **`SERVING_DENIAL`** | Market alias under review, unknown grade, or observation older than 3 calendar days. | Active farmer price display and advisory blocked by safety gates. |

### Crop & Seasonal Gap Principles
1. **No Blanket Holiday Assertion:** Missing dates cannot be collectively attributed to holidays without verified mandi calendars. Gaps reflect an unknown mixture of market holidays, non-reporting, zero arrivals, and local administrative suspensions.
2. **Full-Panel Gap Analysis:** Comprehensive seasonal gap analysis across 1,170+ series requires full-panel processing and remains marked **Pending Remote Kaggle Execution**.

---

## 4. Series Training Eligibility & Tiers

Series qualification for historical model development follows frozen thresholds:

### 4.1 Tier A (Primary Scored Benchmark)
- **Minimum Training Observations:** $N_{\text{train}} \ge 60$ trading days.
- **Minimum Coverage:** $\text{Coverage} \ge 0.30$.
- **Coverage Span Definition:** Calculated over the inclusive calendar span between the first observed date and the last observed date within the training partition:
  $$\text{Coverage} = \frac{N_{\text{train}}}{(\text{date}_{\text{last}} - \text{date}_{\text{first}} + 1)}$$
- **Origin Recency Requirement:** At any origin $t$, series must possess at least 3 trading observations in the preceding 30 calendar days $[t - 30, t]$.

### 4.2 Tier B (High-Volume Established Benchmark)
- **Minimum Training Observations:** $N_{\text{train}} \ge 120$ trading days.
- **Minimum Coverage:** $\text{Coverage} \ge 0.30$ (calculated over first-to-last observed span).
- **Origin Recency Requirement:** Same as Tier A ($\ge 3$ observations in $[t - 30, t]$).

---

## 5. Causal Feature Architecture (`src/forecast_features.py`)

The feature pipeline produces exactly 21 deterministic price-only and temporal features from historical APMC observations:

```mermaid
flowchart TD
    Raw[Raw APMC Observations] --> Resolv[Order-Invariant Conflict Resolution]
    Resolv --> CausalCutoff[Causal Filter: Date <= Origin Date t]
    CausalCutoff --> Curr[Current Price: P_t]
    CausalCutoff --> Lags[Exact Calendar Lags: t-1, t-3, t-7, t-14, t-28]
    CausalCutoff --> Age[Last-Observation Age: Days <= t]
    CausalCutoff --> Roll[Preceding Windows: [t-7, t-1] & [t-30, t-1]]
    CausalCutoff --> Cal[Calendar Encodings: DOW, Month, DOY]
    Curr --> FeatVec[21-Dimensional Feature Vector]
    Lags --> FeatVec
    Age --> FeatVec
    Roll --> FeatVec
    Cal --> FeatVec
```

### 5.1 Declared Feature Set

| Feature Name | Type | Unit | Window / Lag | Missingness Policy | Causality |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `current_price` | `float64` | Rs./Quintal | $t$ | Preserved as `NaN` if unobserved at $t$. | Exact $t$ |
| `price_lag_1` | `float64` | Rs./Quintal | $t - 1\text{d}$ | `NaN` if unobserved; no forward-filling. | Exact $t-1$ |
| `price_lag_3` | `float64` | Rs./Quintal | $t - 3\text{d}$ | `NaN` if unobserved. | Exact $t-3$ |
| `price_lag_7` | `float64` | Rs./Quintal | $t - 7\text{d}$ | `NaN` if unobserved (same day of week). | Exact $t-7$ |
| `price_lag_14` | `float64` | Rs./Quintal | $t - 14\text{d}$ | `NaN` if unobserved. | Exact $t-14$ |
| `price_lag_28` | `float64` | Rs./Quintal | $t - 28\text{d}$ | `NaN` if unobserved. | Exact $t-28$ |
| `last_observation_age_days` | `float64` | Days | $\le t$ | $0.0$ if $t$ observed; $k$ if $t-k$; `NaN` if no history. | Strictly $\le t$ |
| `rolling_count_7d` | `int64` | Count | $[t-7, t-1]$ | Integer count in $\{0 \dots 7\}$. | Preceding exclusive of $t$ |
| `rolling_mean_7d` | `float64` | Rs./Quintal | $[t-7, t-1]$ | `NaN` if count $< 1$. | Preceding exclusive of $t$ |
| `rolling_std_7d` | `float64` | Rs./Quintal | $[t-7, t-1]$ | `NaN` if count $< 2$ (sample variance burn-in). | Preceding exclusive of $t$ |
| `rolling_count_30d` | `int64` | Count | $[t-30, t-1]$ | Integer count in $\{0 \dots 30\}$. | Preceding exclusive of $t$ |
| `rolling_mean_30d` | `float64` | Rs./Quintal | $[t-30, t-1]$ | `NaN` if count $< 1$. | Preceding exclusive of $t$ |
| `rolling_std_30d` | `float64` | Rs./Quintal | $[t-30, t-1]$ | `NaN` if count $< 2$ (sample variance burn-in). | Preceding exclusive of $t$ |
| `day_of_week` | `int64` | Index | $t$ | Deterministic calendar index ($0=\text{Mon}, 6=\text{Sun}$). | Origin date $t$ |
| `day_of_week_sin` | `float64` | Periodic | $t$ | $\sin(2\pi \cdot \text{DOW} / 7)$ | Origin date $t$ |
| `day_of_week_cos` | `float64` | Periodic | $t$ | $\cos(2\pi \cdot \text{DOW} / 7)$ | Origin date $t$ |
| `month` | `int64` | Index | $t$ | Calendar month ($1 \dots 12$). | Origin date $t$ |
| `month_sin` | `float64` | Periodic | $t$ | $\sin(2\pi \cdot (\text{Month}-1) / 12)$ | Origin date $t$ |
| `month_cos` | `float64` | Periodic | $t$ | $\cos(2\pi \cdot (\text{Month}-1) / 12)$ | Origin date $t$ |
| `day_of_month` | `int64` | Day | $t$ | Day of month ($1 \dots 31$). | Origin date $t$ |
| `day_of_year` | `int64` | Day | $t$ | Day of year ($1 \dots 366$). | Origin date $t$ |

### 5.2 Window Boundary Rules & Sample Variance Burn-In
1. **Preceding Exclusive Window:** All rolling statistics strictly evaluate $[t - W, t - 1]$ calendar days. Current price $P_t$ is separately provided in `current_price` and is **never** conflated with historical rolling window statistics.
2. **Missing Standard Deviation Burn-In:** Sample standard deviation uses Bessel-corrected divisor ($N - 1$, `ddof=1`). When fewer than 2 valid observations exist within $[t - W, t - 1]$, sample variance is mathematically undefined and strictly returns `np.nan`.

### 5.3 Batch vs Inference Equivalence
`ForecastFeatureBuilder` guarantees exact mathematical equality between:
- Batch training feature extraction: `compute_batch_features(df)`
- Single-origin live/offline inference: `compute_origin_features(history, t, series)`

---

## 6. Step 7 Reproducible Experiment Specification

The configuration in `experiments/configs/price_forecast_v1.json` defines the remote execution protocol across four temporal folds:

### 6.1 Temporal Folds

| Fold | Training Cutoff ($T_{\text{train}}$) | Max Training Origin ($t \le T - 8$) | Test Start Date | Test End Date | Embargo Span | Role |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **F1** | 2024-12-31 | 2024-12-23 | 2025-01-08 | 2025-06-30 | 7 days | Historical Development Benchmark |
| **F2** | 2025-06-30 | 2025-06-22 | 2025-07-08 | 2025-10-31 | 7 days | Historical Development Benchmark |
| **F3** | 2025-12-18 | 2025-12-10 | 2025-12-26 | 2026-03-31 | 7 days | Historical Development Benchmark |
| **F4** | 2026-03-31 | 2026-03-23 | 2026-04-08 | 2026-09-30 | 7 days | Historical Development Benchmark |

> [!NOTE]
> All test folds have been inspected in preceding audit passes and serve as **development benchmarks**. Final generalization claims require prospective evaluation on newly acquired operational observations.

### 6.2 Candidate Models
1. **Linear Regularized Baseline (`Ridge`):**
   - L2-regularized linear model on standardized price lags and calendar encodings.
   - Median imputation and standard scaling fitted strictly within training partition.
   - Inner chronological validation for penalty parameter $\alpha \in \{0.01, 0.1, 1.0, 10.0, 100.0\}$.
2. **Nonlinear Tabular Gradient Boosting (`HistGradientBoostingRegressor`):**
   - Histogram-based gradient tree boosting with native missing-value (`NaN`) routing.
   - Requires zero feature imputation, eliminating imputer leakage risks.
   - Hyperparameters tuned chronologically on training fold.
3. **Rescored Baselines:**
   - Naive $H=7$, 7-day Moving Average, Linear Drift, and 364-day Seasonal Naive rescored strictly on exact non-abstained matched cases.

### 6.3 Evaluation Metrics & MASE Stance
- **Primary Accuracy:** Mean Absolute Error ($\text{MAE}$), Root Mean Squared Error ($\text{RMSE}$), Mean Directional Bias, Median Absolute Error ($\text{MedianAE}$).
- **Paired Skill Score:**
  $$\text{Skill}_m = 1 - \frac{\sum_{j \in S_m} |y_j - \hat{y}_{m,j}|}{\sum_{j \in S_m} |y_j - \hat{y}_{\text{naive},j}|}$$
  Evaluated on strictly non-zero denominators with series-clustered 95% bootstrap confidence intervals.
- **Conventional MASE Stance:** Conventional non-seasonal $\text{MASE}$ requires a training-only 1-step naive scale ($d_s$). Because historical panel pairs have not had this scale independently verified in code, $\text{MASE}$ remains explicitly **NOT COMPUTED / NOT VALIDATED** to prevent misleading metric claims.
