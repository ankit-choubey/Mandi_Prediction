# Model & Mathematical Validation Protocol

> **Purpose:** Authoritative record of mathematical definitions, evaluation protocols, model decision records, and validation scorecards for the Mandi Market Intelligence System.  
> **Update Rule:** Append-only for decision records and scorecard history. Any change to a formula, evaluation protocol, or decision threshold requires an explicit audit justification and date-stamped record. Never fabricate results.

---

## 1. Scorecard Definitions & Mathematical Formulas

All forecasting models and economic decision policies are evaluated against strict mathematical definitions. All price metrics operate in standard Indian Agricultural Marketing units (**₹ per Quintal**), and percentage metrics are normalized decimals or percentages.

### 1.1 Point Forecast Accuracy Metrics

Given actual observed price series $y_t$ and point forecast $\hat{y}_t$ over an evaluation window of $N$ observations:

1. **Mean Absolute Error (MAE):**
   $$\text{MAE} = \frac{1}{N} \sum_{t=1}^N |y_t - \hat{y}_t|$$
   *Measures absolute error in ₹/quintal; robust to extreme price spikes.*

2. **Root Mean Squared Error (RMSE):**
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{t=1}^N (y_t - \hat{y}_t)^2}$$
   *Penalizes large forecast errors heavily; sensitive to outliers.*

3. **Weighted Absolute Percentage Error (WAPE):**
   $$\text{WAPE} = \frac{\sum_{t=1}^N |y_t - \hat{y}_t|}{\sum_{t=1}^N y_t}$$
   *Scale-independent percentage error avoiding zero-division issues common to MAPE on agricultural series.*

4. **Mean Absolute Scaled Error (MASE):**
   $$\text{MASE}_h = \frac{\frac{1}{N} \sum_{t=1}^N |y_t - \hat{y}_t|}{\frac{1}{T_{\text{train}} - h} \sum_{t=h+1}^{T_{\text{train}}} |y_t - y_{t-h}|}$$
   *The scale is defined as the in-sample mean absolute error of the $h$-step naive forecast $(y_t - y_{t-h})$ matching the evaluated forecast horizon $h$. Comparing a multi-step forecast ($h > 1$) to a one-step naive error artificially inflates MASE; matching the denominator horizon to $h$ preserves scale validity across multi-day horizons.*

   *Special Case ($h = 1$, one-step-ahead):*
   $$\text{MASE}_1 = \frac{\frac{1}{N} \sum_{t=1}^N |y_t - \hat{y}_t|}{\frac{1}{T_{\text{train}} - 1} \sum_{t=2}^{T_{\text{train}}} |y_t - y_{t-1}|}$$
   *A value of $\text{MASE}_h < 1$ indicates that the forecasting model outperforms the $h$-step naive persistence benchmark.*

5. **Skill Score vs. Naive Baseline:**
   $$\text{Skill}_{\text{naive}} = 1 - \frac{\text{Metric}_{\text{model}}}{\text{Metric}_{\text{naive}}}$$
   *Evaluates relative percentage error reduction against naive persistence. Positive values indicate superior forecasting power.*

6. **Directional Accuracy (DA):**
   $$\text{DA} = \frac{1}{N} \sum_{t=1}^N \mathbb{I}\Big(\text{sign}(y_t - y_{t-h}) == \text{sign}(\hat{y}_t - y_{t-h})\Big)$$
   *Percentage of test periods where the predicted price movement direction correctly matches realized trajectory.*

---

### 1.2 Probabilistic & Uncertainty Metrics

For probabilistic forecasts emitting prediction intervals $[\hat{L}_t^{(\alpha)}, \hat{U}_t^{(\alpha)}]$ or quantile estimates $\hat{q}_\tau$:

1. **Prediction Interval Coverage Probability (PICP):**
   $$\text{Coverage} = \frac{1}{N} \sum_{t=1}^N \mathbb{I}\Big(\hat{L}_t^{(\alpha)} \le y_t \le \hat{U}_t^{(\alpha)}\Big)$$
   *Targeted nominal coverage $(1 - \alpha)$. Coverage below nominal indicates overconfident intervals; coverage significantly above indicates overly wide, uninformative bounds.*

2. **Mean Prediction Interval Width (MPIW):**
   $$\text{Width} = \frac{1}{N} \sum_{t=1}^N \Big(\hat{U}_t^{(\alpha)} - \hat{L}_t^{(\alpha)}\Big)$$
   *Measures the sharpness / informativeness of the interval in ₹/quintal.*

3. **Pinball Loss (Quantile Loss at level $\tau \in (0, 1)$):**
   $$\mathcal{L}_\tau(y_t, \hat{q}_\tau) = \frac{1}{N} \sum_{t=1}^N \max\Big(\tau(y_t - \hat{q}_\tau), (\tau - 1)(y_t - \hat{q}_\tau)\Big)$$
   *Evaluates calibrated asymmetric quantile forecasts for downside and upside risk assessment.*

---

### 1.3 Supply Chain Net Proceeds & Economic Formulas

For evaluating immediate sale versus tactical holding over duration $h$:

1. **Immediate Sale Net Proceeds ($R_{\text{sell}}$):**
   $$R_{\text{sell}}(Q, P_T) = Q \cdot P_T - Q \cdot c_{\text{trans\_now}} = Q (P_T - c_{\text{trans\_now}})$$

2. **Tactical Storage Net Proceeds ($R_{\text{store}}$):**
   $$R_{\text{store}}(Q, P_T, P_{T+h}) = Q(1 - L)(1 - d_q) P_{T+h} - Q(c_s + c_{\text{handling}}) - Q \cdot P_T \left(\frac{i \cdot h}{365}\right) - Q(1 - L) c_{\text{trans\_later}}$$

3. **Break-Even Future Price ($P_{\text{break-even}}$):**
   Setting $R_{\text{store}} = R_{\text{sell}}$:
   $$P_{\text{break-even}} = \frac{P_T \left(1 + \frac{i \cdot h}{365}\right) + (c_s + c_{\text{handling}}) + \Delta_{\text{trans}}}{(1 - L)(1 - d_q)}$$
   $$\text{where } \Delta_{\text{trans}} = c_{\text{trans\_later}}(1 - L) - c_{\text{trans\_now}}$$

#### Precise Terms and Unit Definitions
* $Q$: Initial quantity delivered or harvested in **Quintals** (1 Quintal = 100 kg).
* $P_T$: Spot market price at origin date $T$ in **₹ / Quintal**.
* $P_{T+h}$: Realized or expected future market price at date $T+h$ in **₹ / Quintal**.
* $c_s$: **TOTAL storage cost per quintal for the full holding duration $h$** in **₹ / Quintal** (defined either as $c_{\text{daily\_rate}} \times h$ or as a flat facility slab reservation tariff).
* $c_{\text{handling}}$: Incremental loading, unloading, and labour handling fees in **₹ / Quintal**.
* $i$: Annual carrying rate expressed as a decimal per year (e.g. $0.07$ for 7.0% p.a.). Represents either formal financing interest (e.g. Kisan Credit Card) OR opportunity cost of liquid cash; non-compounded over $h$ calendar days.
* $h$: Tactical holding duration in **Calendar Days**.
* $c_{\text{trans\_now}}$: Current transport haulage and market transaction fees per quintal sold at date $T$ in **₹ / Quintal**.
* $c_{\text{trans\_later}}$: Future transport haulage and market transaction fees per quintal sold at date $T+h$ in **₹ / Quintal**.
* $\Delta_{\text{trans}} = c_{\text{trans\_later}}(1 - L) - c_{\text{trans\_now}}$: Differential transaction friction per initial quintal in **₹ / Quintal**.
* $L$: Physical quantity loss fraction ($0 \le L < 1$, dimensionless fraction).
* $d_q$: Quality markdown discount fraction ($0 \le d_q < 1$, dimensionless fraction).

#### Crucial Note on Loss Decoupling (Zero Double-Counting)
Physical quantity loss ($L$) and quality markdown ($d_q$) must never double-count the same underlying deterioration:
* **Quantity Loss ($L$):** Represents physical mass shrinkage or biomass loss (moisture evaporation, mold rotted cull, insect boring discard). It strictly reduces the **physical volume** weighed at the mandi scales: $Q_{\text{sold}} = Q \cdot (1 - L)$.
* **Quality Markdown ($d_q$):** Represents commercial auction price discounting applied by buyers to surviving sound produce due to cosmetic blemishes, skin softening, partial sprouting, or solanine greening: $P_{\text{realized}} = P_{T+h} \cdot (1 - d_q)$.
* **Separation Rule:** An affected potato or tomato must either be discarded as physical cull (counted in $L$) or sold at a commercial markdown (counted in $d_q$), never both.

#### Worked Numeric Example (ILLUSTRATIVE — Not Empirical Data)
The following step-by-step arithmetic illustrates how $P_{\text{break-even}}$ is calculated for a 7-day tactical holding scenario ($h = 7$):
* **Inputs:**
  * $P_T = ₹2,400.00$ / quintal
  * $h = 7$ calendar days
  * $i = 7.0\%$ per annum ($0.07$) $\implies \text{rate factor} = \frac{0.07 \times 7}{365} = \frac{0.49}{365} \approx 0.00134247$
  * $L = 0.5\%$ physical weight loss ($0.005$) $\implies 1 - L = 0.995$
  * $d_q = 0.0\%$ quality markdown ($0.000$) $\implies 1 - d_q = 1.000$
  * $c_s = ₹4.70$ / quintal (total 7-day storage fee)
  * $c_{\text{handling}} = ₹9.00$ / quintal (loading and unloading fee)
  * $c_{\text{trans\_now}} = ₹20.00$ / quintal
  * $c_{\text{trans\_later}} = ₹20.00$ / quintal
* **Step 1: Calculate Differential Transaction Cost ($\Delta_{\text{trans}}$):**
  $$\Delta_{\text{trans}} = 20.00 \times 0.995 - 20.00 = 19.90 - 20.00 = -₹0.10 \text{ / quintal}$$
* **Step 2: Calculate Carrying Capital Cost:**
  $$\text{Capital Cost} = 2,400.00 \times 0.00134247 = ₹3.2219 \text{ / quintal}$$
* **Step 3: Calculate Numerator:**
  $$\text{Numerator} = 2,400.00 + 3.2219 + (4.70 + 9.00) + (-0.10) = 2,400.00 + 3.2219 + 13.70 - 0.10 = 2,416.8219 \text{ ₹/quintal}$$
* **Step 4: Calculate Denominator:**
  $$\text{Denominator} = (1 - L)(1 - d_q) = 0.995 \times 1.000 = 0.995$$
* **Step 5: Compute Break-Even Future Price:**
  $$P_{\text{break-even}} = \frac{2,416.8219}{0.995} \approx ₹2,428.97 \text{ / quintal}$$
* **Step 6: Required Price Increase:**
  $$\Delta P_{\text{required}} = \frac{2,428.97 - 2,400.00}{2,400.00} \times 100\% = \frac{28.97}{2,400.00} \times 100\% = +1.207\% \approx +1.21\%$$
* **Interpretation:** Even under low storage costs and minimal weight loss (0.5%), a farmer requires a price appreciation of at least $₹28.97$/quintal (+1.21%) in 7 days simply to cover storage fees, handling friction, and capital carrying interest.

---

### 1.4 Dataset Verification Dimensions

Every data source and panel evaluated in this project is characterized across six orthogonal dimensions recorded as separate fields:

1. **`provenance`:** Upstream institutional source, verifiable download session receipt, publisher identity (e.g. Directorate of Marketing & Inspection, MoA&FW via data.gov.in), and authentic domain origin.
2. **`quality`:** Schema integrity, absence of non-positive prices ($P \le 0$), compliance with physical bounds ($P_{\min} \le P_{\text{modal}} \le P_{\max}$), format consistency, and null rate.
3. **`availability`:** Endpoint uptime, public accessibility, automated pagination reliability, and offline persistence.
4. **`usage_rights`:** Formal legal license (e.g. National Data Sharing and Accessibility Policy — NDSAP Open Government Data License India), commercial redistribution terms, and mandatory attribution requirements.
5. **`data_nature`:** Categorization as empirical transaction record (`EMPIRICAL_OBSERVATION`), published statutory benchmark (`OFFICIAL_STATISTICS`), derived analytical feature (`DERIVED_FEATURE`), or hypothetical parameter (`SCENARIO_ASSUMPTION`).
6. **`freshness`:** Calendar lag between the newest observation timestamp and the execution reference date (Current: $\le 2$ days lag; Delayed: $3 \text{ to } 5$ days lag; Stale: $> 5$ days lag).

---

### 1.5 File Integrity versus Origin Authenticity

A critical architectural distinction is enforced between file integrity and origin authenticity:
* **File Integrity (Proven by Checksums):** Cryptographic hashes (e.g. SHA-256) prove strictly that a local byte stream on disk has not been corrupted, truncated, or altered since the hash was generated.
* **Origin Authenticity (Not Proven by Checksums):** A SHA-256 hash provides **zero proof** that the data inside the file originated from an authentic government source or reflects true commercial transactions. A fabricated, synthetic, or corrupted CSV produces a valid, permanent SHA-256 checksum.
* **Authenticity Rule:** Origin authenticity requires external verification: signed HTTP responses, direct API logs, verified government portal receipts, or cryptographically verifiable publisher attestations. Checksums must never be cited as proof of source authenticity.

---

## 2. Evaluation Protocol & Anti-Leakage Safeguards

All model comparisons and candidate assessments must strictly adhere to the following protocol:

1. **Strict Chronological Ordering:**
   * Random row splitting or standard $k$-fold cross-validation is strictly **PROHIBITED** on time-series data.
   * Split structure: Earliest 70% dates for Training, subsequent 15% dates for Validation, final 15% dates reserved as held-out historical Test window.
2. **Horizon-Aware Embargo Purging:**
   * For forecasting horizon $h$ (e.g. $h = 7$ calendar days), train partition origin dates within $h + 1$ days of the validation cutoff MUST be purged.
   * This prevents target realization leakage across split boundaries (an observation at $T_{\text{split}} - 2$ realizing at $T_{\text{split}} + 5$ must not leak into validation).
3. **Walk-Forward Out-of-Sample Backtesting:**
   * Sequential expanding-window or rolling-window evaluation where feature calculation uses only information strictly available at or prior to origin date $T$.
   * Volatility burn-in and rolling means must be causal (strictly backwards-looking).
4. **Pre-Test Threshold Freezing:**
   * Classification boundaries, probability thresholds, and hurdle rates must be fitted or selected strictly on the Validation set.
   * Test partition evaluation is strictly single-pass exploratory verification with zero tuning on test metrics.

---

## 3. Model Decision Record (MDR) Template

Every candidate model introduced or tested must complete an MDR before deployment or benchmark comparison:

```markdown
### MDR-[ID]: [Model Name / Variant]
- **Date:** [YYYY-MM-DD]
- **Author / Investigator:** [Name]
- **Kaggle Run ID:** [Kaggle Notebook / Kernel ID]
- **Dataset Checksums:** [SHA-256 of training input files]
- **Method & Rationale:** [Why this model is being evaluated]
- **Target Variable & Horizon:** [e.g. Modal_Price at T+7, or Target_Class (0, 1, 2)]
- **Feature Set:** [List of input features; lag steps; calendar features]
- **Split Configuration:** [Train / Val / Test date bounds; embargo buffer days]
- **Leakage Controls Applied:** [Causal features; scaler fit on train only; embargo purge]
- **Hyperparameter Search Space & Best Seed:** [Tuning details and seeds used]
- **Performance vs. Baselines (Per series & horizon):**
  - Model MAE / WAPE / Accuracy:
  - Naive Baseline MAE / WAPE / Accuracy:
  - Skill Score vs. Naive:
- **Decision:** [ACCEPTED as candidate / REJECTED / RETIRED]
- **Decision Rationale:** [Clear empirical justification for the decision]
```

---

## 4. Candidate Model Ladder

*(All architectures below are CANDIDATES for evaluation; none are accepted as validated production results until evaluated on Kaggle.)*

| Tier | Candidate Model Architecture | Inputs / Feature Strategy | Target Horizon | Status | Notes |
|---|---|---|---|---|---|
| **L0** | Naive Persistence Baseline | $P_{T+h} = P_T$ | $T+1, T+3, T+7$ | **CANDIDATE** | Benchmark floor; all models must beat this to be viable. |
| **L1** | Seasonal Naive / Moving Average | Mean of last 7/14 days; seasonal lag | $T+7$ | **CANDIDATE** | Baseline for seasonal crop cycles. |
| **L2** | Univariate ETS / AutoARIMA | Historical price series per canonical mandi-crop | $T+7$ | **CANDIDATE** | Classical econometric benchmark; requires handling irregular trading hiatuses. |
| **L3** | Global Gradient Boosted Trees (LightGBM / XGBoost) | Lag prices ($T-1, T-3, T-7$), calendar/month cyclical, spatial neighbor prices | $T+7$ | **CANDIDATE** | Cross-district panel model predicting either continuous price or 3-state condition. |
| **L4** | Arrivals & Weather Ablation Models | L3 features + empirical Agmarknet arrivals volume + NASA POWER weather | $T+7$ | **CANDIDATE** | Evaluates incremental predictive uplift of arrivals and agroclimatic variables. |
| **L5** | Conformal Prediction & Quantile Regressors | Quantile Loss / Split-conformal calibration | $T+7$ | **CANDIDATE** | Emits calibrated coverage bounds $[\hat{L}, \hat{U}]$ for farmer risk hedging. |

---

## 5. Existing T+7 3-State Classifier Status

*(Summary based on repository static code inspection; awaiting formal Kaggle reproduction.)*

* **Architecture:** 5 classifiers in [`src/models.py`](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/src/models.py) (Decision Tree, Random Forest, Extra Trees, Gradient Boosting, Soft-Voting Ensemble).
* **Target Formulation:**
  $$\Delta P = \left(\frac{P_{T+7} - P_T}{P_T}\right) \times 100$$
  * Unfavorable (0): $\Delta P \le -2.5\%$
  * Normal (1): $-2.5\% < \Delta P < +2.5\%$
  * Favorable (2): $\Delta P \ge +2.5\%$
* **Reported Historical Metrics (from README / Final Report):**
  * Gradient Boosting accuracy: 58.76% (Macro F1: 0.5209) on chronological test window.
  * Soft-Voting Ensemble accuracy: 58.42% (Macro F1: 0.5245).
* **Current Status:** **NOT INDEPENDENTLY REPRODUCED**. Model artifacts do not exist on disk; metrics represent previous in-memory execution logs. Formal reproduction on Kaggle required.

---

## 6. Scenario Cost Model Framework

### 6.1 Cost Classification Rules
1. Every economic input must carry a clear provenance label:
   * `EMPIRICAL_OBSERVATION`: Verified actual quote from an active local provider or invoice receipt.
   * `OFFICIAL_STATISTICS`: Published statutory rate or government benchmark (e.g. CWC statutory tariff schedule).
   * `SCENARIO_ASSUMPTION`: Illustrative or literature-calibrated estimate (e.g. ICAR-CIPHET loss rates).
2. For all `SCENARIO_ASSUMPTION` parameters:
   * Must define low, base, and high bounds.
   * Must reference an authoritative published anchor document.
   * Must be overridden immediately upon receipt of verified empirical market quotes.

### 6.2 Safety & Advisory Cap
* If any parameter in the net proceeds calculation is a `SCENARIO_ASSUMPTION`, downstream application outputs must display:
  `"INFORMATIONAL / DEMO MODE ONLY — Costs reflect illustrative scenario assumptions, not verified facility quotes."`
* Actionable farmer advisories are strictly prohibited when operating under unverified scenario assumptions.

---

## 7. Scorecard History

*(Append-only record of formal benchmark evaluations executed on Kaggle.)*

| Evaluation Date | Kaggle Run ID | Model Name | Dataset Version | Horizon | MAE (₹/q) | RMSE (₹/q) | WAPE (%) | MASE | Skill vs. Naive | Directional Acc (%) | 90% Coverage (%) | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| *None* | *None* | *None* | *None* | *None* | *None* | *None* | *None* | *None* | *None* | *None* | *None* | *Awaiting Run* |

*(No fabricated results. Rows added strictly upon verification of Kaggle job outputs.)*

