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

   *Calendar Days & Missing Trading Days Rule:*
   The horizon $h$ is defined strictly in **calendar days** (e.g. $h = 7$ calendar days) with date-matched historical lags ($y_t$ vs $y_{t-h}$). Mandis close on Sundays, gazetted holidays, and strike hiatuses. When $t-h$ falls on a market closure or missing trading date, the lag benchmark pairs $t$ with the nearest prior active trading day within an allowable backward embargo window (up to 2 calendar days, $[t-h-2, t-h]$). If no active trading day exists within this window, the observation pair is excluded from the scaling denominator rather than interpolating synthetic prices.

   *Special Case ($h = 1$, one-step-ahead):*
   $$\text{MASE}_1 = \frac{\frac{1}{N} \sum_{t=1}^N |y_t - \hat{y}_t|}{\frac{1}{T_{\text{train}} - 1} \sum_{t=2}^{T_{\text{train}}} |y_t - y_{t-1}|}$$
   *A value of $\text{MASE}_h < 1$ indicates that the forecasting model outperforms the $h$-step naive persistence benchmark.*

5. **Skill Score vs. Naive Baseline:**
   $$\text{Skill}_{\text{naive}} = 1 - \frac{\text{Metric}_{\text{model}}}{\text{Metric}_{\text{naive}}}$$
   *Evaluates relative percentage error reduction against naive persistence. Positive values indicate superior forecasting power.*

6. **Directional Accuracy (DA):**
   $$\text{DA} = \frac{1}{N} \sum_{t=1}^N \mathbb{I}\Big(\text{sign}(y_t - y_{t-h}) == \text{sign}(\hat{y}_t - y_{t-h})\Big)$$
   *Percentage of test periods where the predicted price movement direction correctly matches realized trajectory over horizon $h$ calendar days.*

   *Missing Trading Days Rule:* When $t-h$ falls on a market closure, the baseline reference price $y_{t-h}$ uses the nearest prior trading day within the backward embargo window $[t-h-2, t-h]$, matching the MASE pairing rule.

   *Zero-Change Convention:* When realized market change is zero ($y_t - y_{t-h} = 0$), $\text{sign}(0) = 0$. The prediction is scored as directionally correct ($\mathbb{I} = 1$) if and only if the model also predicts zero movement ($\hat{y}_t - y_{t-h} = 0$). If the model predicts an upward or downward movement while actual price remains unchanged, it is scored as an incorrect directional prediction ($\mathbb{I} = 0$).

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
* **Interpretation:** Even under low storage costs and minimal weight loss (0.5%), a farmer requires a price appreciation of at least $₹28.97$/quintal (+1.21%) in 7 calendar days to break even. Crucially, this required +1.21% gain **includes the 0.5% physical weight loss ($L = 0.005$, which directly accounts for $₹12.00$/quintal of the total break-even gap)** alongside storage fees ($₹4.70$/qtl), handling friction ($₹9.00$/qtl), financing carrying interest ($₹3.22$/qtl), and differential transport ($-₹0.10$/qtl); it is not merely a reflection of fees and interest alone.

---

### 1.4 Dataset Verification Dimensions

Every data source and panel evaluated in this project is characterized across six orthogonal dimensions recorded as separate fields:

1. **`provenance`:** Upstream institutional source, verifiable download session receipt, publisher identity (e.g. Directorate of Marketing & Inspection, MoA&FW via data.gov.in), and authentic domain origin.
2. **`quality`:** Schema integrity, absence of non-positive prices ($P \le 0$), compliance with physical bounds ($P_{\min} \le P_{\text{modal}} \le P_{\max}$), format consistency, and null rate.
3. **`availability`:** Endpoint uptime, public accessibility, automated pagination reliability, and offline persistence.
4. **`usage_rights`:** Formal legal license (e.g. National Data Sharing and Accessibility Policy — NDSAP, to be verified on the portal), commercial redistribution terms, and mandatory attribution requirements.
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

### 5.1 Step 6 Classifier Baselines & Macro-F1 Mandate
Before any candidate classifier is considered viable, it must be benchmarked against two non-trivial, zero-skill reference baselines on the chronological test partition:
1. **Majority-Class Baseline:** Always predicts the historical mode class across the training window (typically Class 1: Normal, which represents ~49.8% of historical periods across the 5 target districts).
2. **Always-Normal Baseline:** Always predicts Normal ($\Delta P \in (-2.5\%, +2.5\%)$), reflecting market inertia.

*Macro-F1 Metric Mandate:*
Because the 3-state target distribution is imbalanced (Normal ~50%, Favorable ~25%, Unfavorable ~25%), trivial majority prediction achieves an apparent ~50% raw accuracy while failing completely on trend shifts and risk extremes. Macro-F1:
$$\text{Macro-F1} = \frac{1}{3} \sum_{c \in \{0, 1, 2\}} \text{F1}_c$$
evaluates unweighted harmonic mean across all three classes. A trivial Always-Normal classifier achieves a Macro-F1 of only $\approx 0.22$. Candidate classifiers must surpass **both** the accuracy and the Macro-F1 of the majority-class baseline to demonstrate genuine predictive utility.

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
* If any parameter in the net proceeds calculation is a `SCENARIO_ASSUMPTION`, downstream application outputs must carry a distinct `SCENARIO_ESTIMATE` status and display:
  `"SCENARIO_ESTIMATE — Costs reflect illustrative scenario assumptions (simulation/demo), not verified facility quotes."`
* Note that "DEMO" denotes exploratory simulation rather than commercial operational advisory.
* Actionable farmer advisories are strictly prohibited when operating under unverified scenario assumptions.

---

## 7. Scorecard History

*(Append-only record of formal benchmark evaluations executed on Kaggle.)*

| Evaluation Date | Kaggle Run ID | Model Name | Dataset Version | Horizon | MAE (₹/q) | RMSE (₹/q) | MAPE (%) | MASE | Skill vs. Naive | Share $\le 5\%$ (%) | Abstain (%) | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-12 | `mp-fc-006-baselines` | Naive ($y(t)$) | Panel v2 (Provisional) | $h=7$ | 106.96 | 298.83 | 4.16% | 1.000 | 0.0000 | 76.76% | 0.00% | **BENCHMARK ANCHOR** |
| 2026-11-12 | `mp-fc-006-baselines` | Moving Average (MA-7) | Panel v2 (Provisional) | $h=7$ | 134.19 | 333.37 | 5.08% | 1.255 | -0.2547 | 70.98% | 0.00% | **BENCHMARK (Lagging)** |
| 2026-11-12 | `mp-fc-006-baselines` | Seasonal Naive ($t-357$) | Panel v2 (Provisional) | $h=7$ | 774.38 | 1433.76 | 29.45% | 7.240 | -6.3738 | 22.70% | 8.61% | **REJECTED (Annual Drift)** |
| 2026-11-12 | `mp-fc-006-baselines` | Drift (14d Anchor) | Panel v2 (Provisional) | $h=7$ | 107.32 | 303.67 | 4.29% | 1.003 | -0.0068 | 76.55% | 1.14% | **RETAINED (+0.0695 on >2% move)** |

*(No fabricated results. Rows added strictly upon verification of Kaggle job outputs.)*

---

## 8. Data Reconciliation & Unit Ingestion Standards

### 8.1 Partition Accounting Identity (with Cross-File Conflicts)
Every ingestion pipeline in this repository must enforce mathematical conservation of rows across within-file and cross-file transformations. For every individual input file and aggregated across the collection:
$$\text{rows\_in} = \text{rows\_out} + \text{duplicates} + \text{conflicts} + \text{rejected}$$
Where:
* **$\text{rows\_in}$:** Total raw records parsed from the physical source file on disk.
* **$\text{rows\_out}$:** Clean, valid, standardized records accepted into published output partitions (`agmarknet_arrivals_up_consolidated.csv` and `{District}_{Commodity}.csv`).
* **$\text{duplicates}$:** Redundant identical rows eliminated during within-file deduplication plus cross-file exact deduplication on the canonical series identity natural key:
  $$\text{Natural Key} = (\text{District\_Std}, \text{Market}, \text{Commodity\_Std}, \text{Variety}, \text{Grade}, \text{Arrival\_Date})$$
* **$\text{conflicts}$:** Rows sharing the exact same natural key but exhibiting differing quantities (`Arrivals_Raw`) or prices (`Min_Price`, `Max_Price`, `Modal_Price`). All conflicting rows are partitioned to `conflicts.csv` in `output_dir` (never summed, averaged, or arbitrarily selected).
* **$\text{rejected}$:** Records excluded prior to merging, categorized by explicit primary rejection reason:
  1. `missing_district`: Missing or blank district value (handled via pandas string dtype, preventing literal `"nan"` casts).
  2. `missing_commodity`: Missing or blank commodity value.
  3. `unparseable_date`: Date string failing explicit formats (`%d/%m/%Y`, `%d-%m-%Y`, `%Y-%m-%d`). Datetime/Timestamp cells are handled directly before string conversion.
  4. `missing_quantity`: Missing or blank arrival quantity (price-only rows are rejected because they do not represent physical market arrivals).

*Independent Read-Back Reconciliation Check:* After writing outputs to disk, pipeline runs must re-read all written master CSVs, per-district-crop CSVs, and `conflicts.csv`, independently verifying that file row counts match $\text{rows\_out}$ and $\text{conflicts}$. Discrepancies raise explicit `ValueError` exceptions rather than suppressible runtime assertions.

### 8.2 Arrival Quantity & Unit Resolution Standard
1. **Preservation of Raw Values:** The original raw numerical quantity is permanently stored in `Arrivals_Raw`.
2. **Explicit Unit Categorization (Exact Set Matching Only):** The detected source unit is stored in `Arrival_Unit_Source`:
   * `'Tonnes'`: Derived from an explicit column header naming tonnes (e.g. `Arrivals (Tonnes)`) or an `Arrival_Unit` column exactly matching the normalized set `{'tonne', 'tonnes', 'ton', 'tons', 'mt', 'metric tonne', 'metric tonnes'}`. Substring matching is strictly prohibited to prevent false positives (e.g. 'cotton').
   * `'Quintals'`: Derived from an explicit column header naming quintals (e.g. `Arrivals (Qtl)`) or an `Arrival_Unit` column exactly matching `{'quintal', 'quintals', 'qtl', 'qtls'}`.
   * `'UNVERIFIED'`: Assigned when source column is generic (`qty`, `arrivals`, `arrival quantity`) and no explicit unit column exists, or unit text falls outside recognized sets.
3. **Standardized Tonnes Export:**
   * If `Arrival_Unit_Source == 'Tonnes'`: $\text{Arrivals\_Tonnes} = \text{Arrivals\_Raw}$.
   * If `Arrival_Unit_Source == 'Quintals'`: $\text{Arrivals\_Tonnes} = \text{Arrivals\_Raw} / 10.0$ ($1 \text{ Tonne} = 10 \text{ Quintals}$).
   * If `Arrival_Unit_Source == 'UNVERIFIED'`: $\text{Arrivals\_Tonnes} = \text{NaN}$ (never guessed or mapped to tonnes without explicit documentation).

### 8.3 Quality Defect Register (MP-DATA-002B)

| Defect # | Ingestion Defect Description | Remediation Implemented | Status |
|---|---|---|---|
| **D1** | `District`/`Commodity` `astype(str)` turns `NaN` into `"nan"` | Replaced with pandas string dtype (`"string"`); `NaN` preserved as `<NA>`; rejected with explicit reasons | **FIXED** |
| **D2** | In-place title-casing alters source identities | `District_Raw`/`Commodity_Raw` preserved in source casing; `District_Std`/`Commodity_Std` mapped via explicit dictionary; unmapped tracked with `mapped=False` | **FIXED** |
| **D3** | Cross-file duplicates and conflicting values unhandled | Natural key grouping detects exact cross-file duplicates (deduplicated) and differing quantity/price (partitioned to `conflicts.csv`) | **FIXED** |
| **D4** | Monolithic rejection without reason attribution | Row classification emits exact counts for `missing_district`, `missing_commodity`, `unparseable_date`, and `missing_quantity` | **FIXED** |
| **D5** | Missing independent disk reconciliation | Post-write verification re-reads master and per-pair files from disk, asserting row counts with explicit `ValueError` | **FIXED** |
| **D6** | Excel date objects distorted by string casting | Datetime/Timestamp objects formatted directly via `.strftime('%Y-%m-%d')` before string conversion; openpyxl integration and native datetime tests fully verified | **implemented, now verified** |
| **D7** | Substring matching on unit strings falsely matches words like 'cotton' | Replaced with exact set membership (`TONNE_UNITS`, `QUINTAL_UNITS`); non-matches set to `UNVERIFIED` | **FIXED** |
| **D8** | Duplicate source columns mapping to same alias cause silent dataframe duplicate columns | Alias collision detection raises `AliasCollisionError` and marks file as failed in `failed_files` | **FIXED** |
| **D9** | Single input directory constraint and symlink path traversal risks | Accepted multiple `--input-dir` arguments; recorded per-file `source_dir` in manifest; path containment verified with `os.path.realpath` | **FIXED** |
| **D10** | Disparate discovery logic and error swallowing in audit | Unified `discover_input_files()` function shared between audit and organize; `audit_arrivals_folder()` reports `failed_files` and `PARTIAL` status | **FIXED** |

### 8.4 Ingestion Task Scorecard

| Task ID | Component Audited / Refactored | Tests Added / Total Passing | Files Discovered / Excluded / Failed | Real-Data Dry-Run Rows (In / Out / Dups / Conflicts / Rej) | Units Verified (Tonnes / Qtl / Unverified) | Pipeline Status |
|---|---|---|---|---|---|---|
| **MP-DATA-002** | `src/ingest_agmarknet_arrivals.py` (Non-destructive arrivals) | 12 new / 133 passing (1 skipped) | 3 valid / 28 excluded / 0 failed | In: 481 / Out: 481 / Dups: 0 / Conflicts: 0 / Rej: 0 | Tonnes: 0 / Qtl: 0 / Unverified: 481 (CEDA files) | **VERIFIED & IMMUTABLE** |
| **MP-DATA-002B** | `src/ingest_agmarknet_arrivals.py` (Quality & robustness fixes) | 5 new (17 total) / 138 passing (1 skipped: openpyxl BLOCKED) | 10 found (5 valid, 5 failed) / 28 excluded / 5 failed (xlsx openpyxl missing) | In: 1,690 / Out: 999 / Dups: 97 / Conflicts: 0 / Rej: 594 (missing_quantity) | Tonnes: 0 / Qtl: 0 / Unverified: 1,690 | **VERIFIED & DETERMINISTIC (PARTIAL)** |
| **MP-DATA-003A** | `src/ingest_agmarknet_arrivals.py` (Excel ingestion & source register) | 2 new (19 total) / 141 passing (0 skipped) | 10 valid / 28 excluded / 0 failed | In: 17,720 / Out: 17,028 / Dups: 97 / Conflicts: 0 / Rej: 595 (594 price, 1 null qty) | Tonnes: 16,029 / Qtl: 0 / Unverified: 999 | **VERIFIED & IMMUTABLE (100% OPERATIONAL, 0 FAILED)** |

---

## 9. Line-Anchored Master Specification Audit Checklist (MP-SETUP-003)

The eleven architectural corrections introduced under Task `MP-SETUP-003` are permanently anchored to the corresponding line numbers in [`documentation/PROJECT_MASTER_SPECIFICATION.md`](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/documentation/PROJECT_MASTER_SPECIFICATION.md):

1. **Dated Audit Baseline Table:** Lines 898–906 (Section 18.1: records commit `82a0e8bb`, 2026-11-12, row counts: 472,385 raw, 462,350 accepted, 160,192 2-year raw, 122 tests passed).
2. **Four-Tier Baseline Evidence Breakdown:** Lines 908–940 (Section 18.2: disaggregates claims into Remote Baseline, Local Baseline, Executed Evidence, and Independent Review Pending).
3. **Roadmap Supersession & Task Mapping:** Lines 1042–1050 (Section 21.1: establishes 10-phase roadmap superseding 9-phase outline, mapping `MP-AUDIT-001/001R`, `MP-SETUP-002`, `MP-SETUP-003`, `MP-DATA-002`).
4. **Capability-Specific Readiness Gates:** Lines 1064–1068, 1102–1110, 1698–1702 (Phasing & Section 23: decouples Release 1 price forecasting from cold storage survey, IMD weather, and production statistics).
5. **Series Identity Natural Key Definition:** Lines 361–369 (Section 8.4: defines canonical natural key tuple `(Source Market, Commodity, Variety, Grade, Price Unit)`).
6. **Ingestion & Publication Architecture Contract:** Lines 371–385 (Section 8.5: mandates immutable raw storage, separate input/output paths, no re-reading generated files, deterministic reruns, distinct observation vs retrieval timestamps).
7. **Scenario Cost Framework Policy:** Lines 387–411 (Section 8.6: defines `SCENARIO_ASSUMPTION` parameters, low/base/high bounds, literature anchors, and informational advisory capping).
8. **Decoupled Serving Architecture Options:** Lines 683–710 (Section 11.4: defines lightweight batch export / serverless deployment decoupled from training compute).
9. **Prospective Logging & Explicit Abstention Reporting:** Lines 545–560 (Section 9.8: mandates real-time request logging and explicit abstention when staleness $> 5$ days or data is missing).
10. **Scoped Academic Literature Review Criteria:** Lines 1024–1035, 1160–1170 (Section 19.7 & 23: replaces rigid 18-paper quota with scoped domain-relevant review criteria).
11. **Cryptographic Integrity vs. Source Authenticity:** Lines 920–938 (Section 18.2: establishes that SHA-256 proves bit-level file integrity on disk, not institutional origin authenticity).

---

## 10. Kaggle Remote Execution Scorecard (Price Profile & Corroboration: MP-DATA-003B)

### 10.1 Remote Kernel Execution Audit Record
* **Task ID:** `MP-DATA-003B`
* **Kernel ID:** [`theankitchoubey/mp-data-003b-price-profile`](https://www.kaggle.com/code/theankitchoubey/mp-data-003b-price-profile) (Version 2)
* **Dataset ID:** [`theankitchoubey/mandi-prediction-audit-003b`](https://www.kaggle.com/datasets/theankitchoubey/mandi-prediction-audit-003b) (Version 1, 30 files, 101.32 MB)
* **Hardware & Runtime:** Kaggle Linux CPU Kernel (2 vCPUs), Internet Disabled, Python 3.13.18, GCC 13.3.0, Random Seed: 42
* **Execution Status:** `KernelWorkerStatus.COMPLETE` (Exit Code 0)
* **Full Summary Report:** [`experiments/reports/mp_data_003b_kaggle_summary.md`](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/experiments/reports/mp_data_003b_kaggle_summary.md)

### 10.2 Mathematical Conservation & Multiset Verification
$$\text{Total Raw Rows (472,385)} = \text{Accepted (462,350)} + \text{Invalid (27)} + \text{Conflicting (2,936)} + \text{Low-Obs Dropped (7,072)} + \text{Exact Dupes (0)}$$

* **Conservation Check:** $462,350 + 27 + 2,936 + 7,072 + 0 = 472,385$ (**VERIFIED TRUE**)
* **Multiset Identity Proof:** Surviving pipeline records matched committed `data/processed/mandi_5year_validated.csv` with **0 discrepancies across all 462,350 rows** (**VERIFIED TRUE**).
* **Quarantine Partition Breakdown:**
  * Non-positive price invalid drops: 27 rows (Ghaziabad 4, Jhansi 13, Kanpur 9, Lucknow 0, Unnao 1).
  * Strategy 2 conflicting price quotes on identical date: 2,936 rows.
  * Low observation series ($<20$ observations): 7,072 rows (partitioned to `low_obs_dropped_rows.csv`).
  * Exact duplicate rows dropped: 0 rows.

### 10.3 Series Eligibility Empirical Profile (1,297 Retained Series)
Evaluated across 5 districts, 41 markets, and 108 commodities:
* **Observation Count:** Min: 20.0, Median: 139.0, Mean: 356.5, P90: 1,177.4, Max: 1,426.0
* **Calendar Span:** Min: 21 days, Median: 334.0 days, Mean: 706.9 days, P90: 1,525.0 days, Max: 1,527.0 days
* **Coverage Share:** Min: 0.0198, Median: 0.4663, Mean: 0.4784, P90: 0.8228, Max: 0.9720
* **Longest Gap:** Min: 2 days, Median: 21.0 days, Mean: 94.1 days, P90: 283.8 days, Max: 1,289.0 days
* **Missing Days:** Min: 1 day, Median: 174.0 days, Mean: 350.4 days, P90: 986.0 days, Max: 1,468.0 days

### 10.4 Price Corroboration Concordance
* **Agmarknet Daily Excel Reports (5 files, 16,030 rows):**
  * Post-panel dates (`2026-10-01` to `2026-11-06`, 27 dates): 1,289 rows.
  * Natural key matches within panel window: 12,602 rows.
  * Exact modal price concordance: **12,525 rows (99.39%)**, median difference = ₹0.00.
  * Non-zero differences: 77 rows (0.61%, captured in `corroboration_diff_sample.csv`).
* **CEDA Price Data (594 rows, Lucknow Wheat):**
  * Natural key matches within panel window: 591 rows.
  * Exact modal price concordance: **591 rows (100.00%)**, mean difference = ₹0.0000.
  * Unmatched CEDA rows: 3 rows (`2024-11-07`, `2025-03-24`, `2025-06-27`), all proven to be quarantined in `quarantined_conflicting_records.csv` under Strategy 2 due to conflicting same-grade price quotes.

### 10.5 Verified Output Artifacts & Checksums

| Artifact Filename | Size (Bytes) | Line Count | SHA-256 Digest |
|---|---|---|---|
| `low_obs_dropped_rows.csv` | 1,107,461 | 7,073 | `b0f0ea08e67c67f41acbab18e7239fafb9641b33d9cbf528c52950d1facf158c` |
| `series_eligibility.csv` | 174,644 | 1,298 | `deaca152a5db96d7edc0deb009034a463c1110448591360aec4ad5591c516b48` |
| `corroboration_diff_sample.csv` | 6,385 | 78 | `e82ab3bb4e1a6a7058d20032b915513594bea0a51edf83d7d6f2a88880e828c7` |
| `disposition_summary.json` | 1,710 | N/A | `362c7923cf77dd17cec1ef722eabf7bef1d1d59a52438afc3737435da068c7b6` |
| `series_profile_summary.json` | 1,330 | N/A | `3690179c2a2f07ca88b6c5fcfc22b7ea236a880614037ecaa3d3b5e532d39d9f` |
| `excel_corroboration_summary.json` | 7,164 | N/A | `05fefe69f9dd783f18ecd2ef9788aeafab8196127de58107bcb63ed92d67c32e` |
| `ceda_corroboration_summary.json` | 1,424 | N/A | `5dc430161519139e9e42c2183ecf7d1a3523959666248d9d8992e06601b4e172` |

### 10.6 Execution Environment Discrepancy & Trained Artifact Version Policy
*Full Specification & Compatibility Record:* [`experiments/kaggle/ENVIRONMENT.md`](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/experiments/kaggle/ENVIRONMENT.md)

A comparison of the Kaggle remote environment vs the local development environment reveals differences in OS and package versions:

| Component / Package | Kaggle Remote Kernel (Linux) | Local Environment (macOS Darwin) | Compatibility Status |
|---|---|---|---|
| OS / Platform | Linux (x86_64, GCC 13.3.0) | macOS Darwin (arm64) | Differing host OS |
| Python | 3.13.18 | 3.14.0 | Minor version difference |
| pandas | 2.3.3 | 2.3.3 | Exact match |
| numpy | 2.1.3 | 2.2.6 | Minor version difference (C-API / ABI caution) |
| scikit-learn | 1.6.1 | 1.7.2 | Minor version difference (pickle serialization risk) |
| scipy | 1.16.3 | 1.16.3 | Exact match |
| openpyxl | 3.1.5 | 3.1.5 | Exact match |

**Trained Artifact Version Storage Policy:**
To prevent silent deserialization failures, numerical drift, or pickle incompatibilities across platforms:
1. Every trained model artifact (e.g. weights, serialized joblib/pickle models, preprocessor pipelines) MUST persist a companion metadata record (JSON manifest or embedded dictionary) containing:
   - `python_version` (full `sys.version`)
   - `platform` (`sys.platform` and architecture)
   - Exact versions of `numpy`, `scipy`, `scikit-learn`, `pandas`, and other modelling dependencies derived via `importlib.metadata`.
   - Training commit hash, random seed, dataset checksum, and training timestamp.
2. Incompatible deserializations must fail fast with an explicit error rather than silently loading drifted estimators.

---

## 11. Target Availability, Eligibility Grids & Corroboration Gaps (MP-DATA-004)

### 11.1 Remote Kernel Execution Audit Record
* **Task ID:** `MP-DATA-004`
* **Kernel ID:** [`theankitchoubey/mp-data-004-eligibility-grids`](https://www.kaggle.com/code/theankitchoubey/mp-data-004-eligibility-grids) (Version 2)
* **Dataset ID:** [`theankitchoubey/mandi-prediction-audit-003b`](https://www.kaggle.com/datasets/theankitchoubey/mandi-prediction-audit-003b) (Version 1, 30 files, 101.32 MB)
* **Hardware & Runtime:** Kaggle Linux CPU Kernel (2 vCPUs), Internet Disabled, Python 3.13.18, Random Seed: 42
* **Execution Status:** `KernelWorkerStatus.COMPLETE` (Exit Code 0)
* **Full Summary Report:** [`experiments/reports/mp_data_004_summary.md`](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/experiments/reports/mp_data_004_summary.md)

### 11.2 Forward Target Availability
Evaluated across all 462,350 origin observations in the validated 5-year panel:

| Target Horizon Definition | Qualifying Origins | Overall Share (%) | Monday–Saturday Mean (%) | Sunday Share (%) |
|---|---|---|---|---|
| **Exact $T+7$ Observation** | 378,572 | **81.88%** | ~82.6% | 74.59% |
| **Window $T+6 \dots T+8$ Observation** | 431,003 | **93.22%** | ~93.4% | 91.86% |
| **Window $T+5 \dots T+9$ Observation** | 443,070 | **95.83%** | ~95.9% | 95.65% |
| **Next Observation within 10 Days** | 455,831 | **98.59%** | ~98.5% | 99.12% |

*Market Closure Pattern:* Sunday volume is lower (40,508 origins vs ~70,000 on weekdays) due to customary Sunday APMC market closures. Expanding the forecasting target window to $\pm 1$ day ($T+6 \dots T+8$) absorbs weekend closures, raising availability from 81.88% to 93.22%.

### 11.3 Quarantine Adjudication Test (Report Only)
Evaluated across 329 conflicting groups overlapping Agmarknet Excel and CEDA reference quotes:
* `last` (last entry in portal): **58.05%** concordance (191 / 329)
* `max` (highest quote): **52.89%** concordance (174 / 329)
* `min` (lowest quote): **46.50%** concordance (153 / 329)
* `first` (first entry in portal): **41.64%** concordance (137 / 329)
* `median` (median quote): **0.91%** concordance (3 / 329)
* `mean` (arithmetic mean quote): **0.61%** concordance (2 / 329)

### 11.4 Multi-Dimensional Eligibility Grids (90 Combinations)
Sample slices from the 90-cell grid across all 1,297 series:

| Min Obs ($N_{obs}$) | Min Coverage ($\text{cov}$) | Max Gap ($\text{gap}_{max}$) | Recency Cutoff | Qualifying Series | Qualifying Observations | Qualifying Series Share (%) |
|---|---|---|---|---|---|---|
| **30** | 0.3 | 60 days | 60 days | 192 | 22,641 | 14.80% |
| **60** | 0.3 | 60 days | 60 days | 183 | 22,206 | 14.11% |
| **120** | 0.3 | 60 days | 60 days | 79 | 12,704 | 6.09% |
| **120** | 0.5 | 30 days | 30 days | 74 | 12,056 | 5.71% |
| **250** | 0.5 | 60 days | 60 days | 2 | 536 | 0.15% |
| **500** | 0.3 | 60 days | 60 days | 0 | 0 | 0.00% |

*The Inter-Season Gap Phenomenon:* In multi-year agricultural series, requiring $\text{gap}_{max} \le 60$ days eliminates seasonal crops undergoing normal 3–5 month inter-season dormancy. Thresholds should not be chosen globally without accounting for crop seasonality.

### 11.5 Chronological Train/Test Split Feasibility (7-Date Embargo for h = 7)
* **Embargo Formalization ($h = 7$):**
  $$T_{train\_end} = T_{test\_start} - (h + 1) = T_{test\_start} - 8$$
  $$\text{Excluded Origin Dates} = [T_{train\_end} + 1, \dots, T_{test\_start} - 1] = [\text{2025-12-19}, \dots, \text{2025-12-25}] \quad (\text{exactly } 7 \text{ origin dates})$$
  This strict 7-date exclusion ensures that the final forecast origin evaluated in training ($T_{train\_end} = \text{2025-12-18}$) has target date $T_{train\_end} + 7 = \text{2025-12-25} < T_{test\_start}$, eliminating target label leakage into test evaluation origins commencing on $T_{test\_start} = \text{2025-12-26}$.
* **Training window:** `2021-09-01` to `2025-12-18` (85% date threshold minus 8 calendar days).
* **Embargo window:** `2025-12-19` to `2025-12-25` (exactly 7 excluded origin dates).
* **Test evaluation period (Final 15%):** `2025-12-26` to `2026-09-30` (279 calendar days).
* **Inclusive Tier ($N_{obs} \ge 60, \text{cov} \ge 0.3, \text{gap} \le 60, \text{rec} \le 60$):** 183 qualifying series; **183 (100.0%)** have $\ge 20$ test origins; **183 (100.0%)** have $\ge 50$ test origins (mean test origins: 119.6).
* **Balanced Tier ($N_{obs} \ge 120, \text{cov} \ge 0.3, \text{gap} \le 60, \text{rec} \le 60$):** 79 qualifying series; **79 (100.0%)** have $\ge 20$ test origins; **79 (100.0%)** have $\ge 50$ test origins (mean test origins: 160.8).

### 11.6 Verified Output Artifacts & Checksums

| Artifact Filename | Size (Bytes) | Line Count | SHA-256 Digest |
|---|---|---|---|
| `unmatched_excel_sample.csv` | 161,802 | 2,001 | `5d3e4c96381c299abace06f524a6178da343ab33b18307d1335075009ce5581a` |
| `unmatched_excel_summary.json` | 4,177 | N/A | `07e38e6c09f523ca28bec04a9a35141cc0d261cde073f50351a139e6294428e7` |
| `diff_77_analysis.json` | 27,628 | N/A | `ff5e30d5c83b647895aff5a16ca49ddb68cde53f3e794fb4f5e9992e2c4b5de3` |
| `quarantine_adjudication_summary.json` | 144,747 | N/A | `1f2b75813f83f982e06afe660ab772edc065bdfb5e59d7e4f4733997834803cb` |
| `target_availability_summary.json` | 10,318 | N/A | `131ed243c1591686a6346d62f099159bbb1c7967d843b6d3b521d1e9d8116099` |
| `target_availability_breakdown.csv` | 36,816 | 374 | `d3da54ec594875e743d3b5deaed9e7a6afb8176c9b0e73f9bb74f9fd14d3e589` |
| `eligibility_grids.csv` | 2,539 | 91 | `cb3b6d5a8fa831e9610ec5cd4ec3c7f4e75dfbe9d06df240c6fb938cd2c403d4` |
| `focus_crops_eligibility.csv` | 25,232 | 580 | `b4a5bb7d63a5d3d2e47687d6cf91c4106799d8f316659fa11ff148766f1d3076` |
| `chronological_split_feasibility.json` | 1,296 | N/A | `0b213e7b6d67179b90293f07c09d071987338cd823c7e804a229a3bebe6e7366` |

---

## 12. Remote Execution Scorecard: Price Discrepancies, Anomaly Scan, Train-Only Eligibility, and Rolling Origins (MP-DATA-005)

* **Execution Date:** 2026-11-12
* **Execution Environment:** Kaggle CPU Kernel (`theankitchoubey/mp-data-005-quality`, internet disabled). See [ENVIRONMENT.md](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/experiments/kaggle/ENVIRONMENT.md) for pinned library versions.
* **Evaluated Dataset:** `theankitchoubey/mandi-prediction-audit-003b` (v1 private, unchanged).
* **Execution Status:** Complete (`KernelWorkerStatus.COMPLETE`, exit code 0, 32.2s runtime).
* **Detailed Task Report:** [mp_data_005_summary.md](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/experiments/reports/mp_data_005_summary.md).

### 12.1 Deep Dive into the 77 Price Differences

Natural-key inner join between 5 official Agmarknet Excel files (`raw_downloads/*.xlsx`, 2,525 rows) and the validated panel (`data/processed/mandi_5year_validated.csv`, 462,350 rows) matched 1,939 records.
* **Exact modal price match rate ($0.00 difference):** 96.03% (1,862 / 1,939 rows).
* **Non-zero price difference count:** Exactly **77 rows** (3.97%).
* **Ratio distribution ($\text{Modal}_{\text{Excel}} / \text{Modal}_{\text{Panel}}$):** Min 0.2632, P10 0.9284, P25 0.9839, Median 1.0128, P75 1.1454, P90 1.5627, Max 2.5492, Mean 1.1386.
* **Constant factor candidate test:** Candidate multipliers ($0.001, 0.01, 0.1, 0.5, 2.0, 10.0, 100.0, 1000.0$) matched **exactly 0 rows** (0.00% within 1% tolerance).
* **Units:** Both source Excel and validated panel specify standard **₹/Quintal** (and arrival quantities in Tonnes).
* **Decimals:** 100% of Excel quotes (77/77) have non-zero decimal fractions; 58.44% of panel quotes (45/77) have non-zero decimal fractions.

### 12.2 Cluster Scope Analysis (2026-02-15 to 2026-04-07)

* **Total Excel records in window:** 2,098 rows.
* **Matched in validated panel:** 1,579 rows (75.26% match rate).
* **Exact price match rate:** 95.12% (1,502 exact matches).
* **Discrepancy peak:** 30 discrepancies in the week of 2026-02-23 (exact match drops to 73.45%) and 23 discrepancies in the week of 2026-03-23 (exact match 93.39%). All other weeks exhibit $\ge 97.0\%$ exact agreement.

### 12.3 Panel-Wide Anomaly Scan (462,350 Rows)

A full non-destructive diagnostic scan across all 462,350 validated panel rows revealed:
* **Day-over-day price jumps ($<0.5$ or $>2.0$):** 1,677 rows (0.36%).
* **Fractional (non-integer) prices:** 13,061 rows (2.82%).
* **Outside $3\times$ series median:** 1,468 rows (0.32%).
* **Min/Max internal inconsistency ($\text{Min} > \text{Max}$ or $\text{Modal} \notin [\text{Min}, \text{Max}]$):** **0 rows (0.00%)**.
* **Any anomaly flag:** 14,845 rows (3.21%).
* **March 2026 Anomaly Spike:** Historical anomaly rates averaged $<0.8\%$ (0.00% in Jan 2026). In March 2026, the anomaly rate surged to **41.03%** (1,686 flagged rows out of 4,109 total obs), driven by 1,649 non-integer fractional prices and 49 extreme day-over-day jumps, persisting at 40–45% through September 2026.

### 12.4 Train-Only Eligibility ($T \le 2025-12-18$)

Evaluated across the 1,570-day training window (439,077 observations, 921 series):
* **As-Is Tier A ($N_{\text{obs, train}} \ge 60, \text{cov} \ge 0.30$):** 496 series across 20 markets (384,887 observations).
* **As-Is Tier B ($N_{\text{obs, train}} \ge 120, \text{cov} \ge 0.30$):** 473 series across 20 markets (383,037 observations).
* **Canonical Tier A (market trailing ` APMC` normalized):** 495 series across 20 markets (385,821 observations).
* **Canonical Tier B (market trailing ` APMC` normalized):** 472 series across 20 markets (383,971 observations).

### 12.5 Serving-Time Rule & Forward Availability

* **Market Naming Discontinuity:** In late 2025/2026, Agmarknet raw data appended ` APMC` to market names. Because `Market` is in `series_cols`, non-APMC series ceased after Nov 2025, and APMC series only had up to 43 observations in training.
* **Serving Rule Feasibility:**
  * Under as-is `series_id`: 0 test origins match Tier A in 2026.
  * Under canonical `series_id_canonical`: 4,418 test origins evaluated ($T \ge 2025-12-26$); **99.00% (4,374 / 4,418) pass the 14-day serving recency requirement** ($[T-14, T)$ has an observation).
* **Unweighted Series-Level Forward Availability (Canonical Tier A, 495 series):**
  * Exact $T+7$ presence: Median **86.75%**, Mean 83.19% (Min 41.58%, Max 96.89%).
  * Near-horizon $T \in [6, 8]$ presence: Median **96.02%**, Mean 94.21% (Min 65.62%, Max 99.73%).

### 12.6 Rolling-Origin Cross-Validation Feasibility (4 Expanding Folds)

Four expanding 60-day folds ending `2026-09-30` with 7-date embargoes:
* **Fold 1 (Test: 2026-02-03..2026-04-03, Train: 2021-09-01..2026-01-26, Embargo: 7 dates):** Overlaps Feb–Mar discrepancy in test window. 22 canonical Tier A series have $\ge 20$ origins.
* **Fold 2 (Test: 2026-04-04..2026-06-02, Train: 2021-09-01..2026-03-27, Embargo: 7 dates):** Overlaps discrepancy in training window. 18 canonical Tier A series have $\ge 20$ origins.
* **Fold 3 (Test: 2026-06-03..2026-08-01, Train: 2021-09-01..2026-05-26, Embargo: 7 dates):** Overlaps discrepancy in training window. 16 canonical Tier A series have $\ge 20$ origins.
* **Fold 4 (Test: 2026-08-02..2026-09-30, Train: 2021-09-01..2026-07-25, Embargo: 7 dates):** Overlaps discrepancy in training window. 15 canonical Tier A series have $\ge 20$ origins.

### 12.7 Discrepancy Resolution Determination

* **Conclusion:** The Feb–Mar 2026 price discrepancy is **(d) an unresolved data-entry / post-aggregation revision anomaly** accompanied by **(b) format and naming shifts** (sudden emergence of fractional prices and market suffix renaming), and is **definitively NOT (a) a unit conversion error**.

### 12.8 Output Artifacts & Checksums

| Artifact File | Size (Bytes) | Lines | SHA-256 Digest |
|---|---|---|---|
| `diff_77_deep_analysis.csv` | 10,087 | 78 | `93341b3c3b4b4f7571b67b467025f86a53cc439cf198a6bd36ee18097975b5c1` |
| `diff_77_deep_analysis.json` | 38,364 | N/A | `e323a5bb6d9ad19f530b258557204dca808a8145172a638e95346360c771a3b4` |
| `feb_mar_cluster_weekly.csv` | 402 | 10 | `9d983e9d1d6b593a4d11d89673ee8bed2f738b3985c818a9a6d63d0e11e56686` |
| `feb_mar_cluster_summary.json` | 3,159 | N/A | `fd771157403c5e20989951619947a20464d210edb4f738a2694baff4296557b9` |
| `monthly_anomaly_distribution.csv` | 1,977 | 62 | `660e793534e3ae0d476a88e0e930896c7b0989d6b9fc4f0e190511d49e025899` |
| `panel_anomalies_sample.csv` | 277,485 | 2,001 | `b60f28d2b482b0f31c3ebaf5cffc623285df4199e0915581e80b3e9cab7c9a85` |
| `anomaly_scan_summary.json` | 704 | N/A | `053841504142492f1093686701ea666cc3686a5e0243b20c14782ace324cafb3` |
| `train_eligibility_tiers.csv` | 135,881 | 922 | `c407311b210c29c8cd71d8d3740f0b9b78ca0cd9965e2e98cce0c2d52cfe753a` |
| `focus_crops_train_eligibility.csv` | 6,367 | 161 | `2df773a912ea3e9ed2738260430fda34fd7210b9c880248131b98f8dc4a9e7a3` |
| `serving_rule_feasibility.json` | 1,023 | N/A | `b9f149c5de57be5023240f3a504f17d7b43d0af3df350bc401888ae25e839b35` |
| `series_level_availability_summary.json` | 999 | N/A | `c1484fe3da9377448261e081829219c84fd4591fbca0ed68a0bd70d809dc6829` |
| `rolling_origin_feasibility.json` | 2,619 | N/A | `dddab43dbb193adc2c9fa668964376e1800520e3a2b07007d132f251ac2358fc` |

---

## 13. Evidence-Based Market Identity, Provisional Panel v2, and Regime Diagnostics (Task MP-DATA-006)

* **Execution Date:** 2026-11-12
* **Execution Environment:** Kaggle CPU Kernel (`theankitchoubey/mp-data-006-panel-v2`, version 3, internet disabled).
* **Evaluated Dataset:** `theankitchoubey/mandi-prediction-audit-003b` (v1 private, unchanged).
* **Execution Status:** Complete (`KernelWorkerStatus.COMPLETE`, exit code 0).
* **Detailed Task Report:** [mp_data_006_summary.md](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/experiments/reports/mp_data_006_summary.md).
* **Panel Status:** Panel v2 is designated **PROVISIONAL** (SHA-256: `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`).

### 13.1 Market Inventory & Suffix Prevalence
Across the 472,385 raw historical records, exactly 42 distinct raw market strings were cataloged across the 5 target districts (Ghaziabad: 8, Jhansi: 15, Kanpur: 9, Lucknow: 4, Unnao: 6). In the recent external snapshot (`9ef84268-...csv`, 2026-11-11), 14 of 14 target district markets (100.0%) carry the `" APMC"` suffix, consistent with the hypothesis from external reports that national platform migration altered reporting nomenclature.

### 13.2 Evidence Rule Adjudication
To prevent ungrounded fuzzy merging, 22 candidate alias pairs (21 APMC variants + 1 cross-phonetic pair) were evaluated under the strict Evidence Rule:
* **Rule A (Chronological Migration):** Accepted if normalized tokens match and overlap $\le 5$ days.
  * **21 APMC transitions accepted:** 20 standard APMC variants (e.g., `Ghaziabad APMC` $\rightarrow$ `Ghaziabad`, overlap 4d; `Purwa APMC` $\rightarrow$ `Purwa`, overlap 0d) plus `Jhansi Grain APMC` $\rightarrow$ `Jhansi (Grain)` (overlap 0d).
* **Unmapped / Review Preservation:**
  * `Baripaal APMC` vs `Varipaal` (Kanpur): Normalized mismatch (`'baripaal'` vs `'varipaal'`). Preserved unmerged as `UNMAPPED/REVIEW`.

### 13.3 Pipeline v2 Disposition & Rescued Rows
Pipeline v2 canonicalizes market identity before series-id creation, duplicate filtering, and low-observation thresholding:
* **Raw Records Ingested:** 472,385
* **Invalid Records Quarantined:** 27
* **Strategy 2 Conflicting Records:** 2,936
* **Exact Duplicates Deduplicated:** 855 (feed overlap during transition)
* **Low-Observation Dropped Rows (< 20 obs):** 5,350 in v2 vs 7,072 in v1 (**+1,722 rescued rows**)
* **Final Accepted Clean Records:** **463,217 rows** across 1,167 series (**+867 net clean rows** vs v1's 462,350 rows)
* **Unique Markets:** Consolidated from 41 in v1 to 21 in v2.
* **Transition Concordance Evidence:** The presence of 855 exact duplicates alongside unchanged conflicts (2,936) provides empirical evidence that overlapping pre-transition and post-transition feeds agree on price quotes.

### 13.4 Re-evaluation of Corroboration on Panel v2
* **Agmarknet Daily Excel Corroboration (14,741 in-window rows):** Matched rows increase from 85.5% (12,602 rows in v1) to 87.14% (12,846 rows in v2), a net gain of +244 matched rows due to canonical market identity unification. **12,769 exact modal price matches (99.40%)**; exactly **77 non-zero price differences (0.60%)**.
* **CEDA Price Data Corroboration (594 rows, Lucknow Wheat):** Matched 591 rows (99.49%); **591 exact modal price matches (100.00% concordance)**; 3 unmatched rows confirmed quarantined under Strategy 2.

### 13.5 Date-Shift Analysis of the 77 Differences
Evaluating all 77 discrepancies across moving calendar shifts $k \in \{-3, -2, -1, 0, 1, 2, 3\}$ days yielded **0 of 77 matches (0.00%)**. The hypothesis of calendar lag or date mismatch is rejected; the underlying cause of the 77 differences remains **UNRESOLVED**.

### 13.6 Monthly Regime Diagnostics (61 Months: 2021-09 to 2026-09)
Data-derived monthly breakdown across 61 months (causes hypothesized from external reports):
* **Historical Regime (2021-09 to 2025-10, 50 mos):** Mean 8,452.4 rows/mo; **0.00% APMC suffix**; **0.00% fractional prices**.
* **Transition Regime (2025-11 to 2026-02, 4 mos):** First `" APMC"`-named row appears in data on `2025-11-01`. Mean 2,249.5 rows/mo; **93.34% APMC suffix**; **4.14% fractional prices** (external reports hypothesize Agmarknet 2.0 system rollout).
* **Fractional Modern Regime (2026-03 to 2026-09, 7 mos):** Mean 4,514.4 rows/mo; **100.00% APMC suffix**; **40.89% fractional prices** (external reports hypothesize UP mandi automated API integration).

### 13.7 Train-Only Eligibility & Cross-Validation on Panel v2
* **Training Window ($T \le 2025-12-18$):** 492 Tier A series (obs $\ge 60$, cov $\ge 0.30$) and 470 Tier B series (obs $\ge 120$, cov $\ge 0.30$).
* **Post-Migration Window Feasibility ($T \ge 2025-11-07$):** **231 Tier A series and 92 Tier B series** across 39,417 observations (vs only 3 Tier A series on v1).
* **4-Fold Expanding Rolling-Origin Feasibility ($h=7$ embargo):** Fold 1 (22 Tier A origins $\ge 20$), Fold 2 (18 series), Fold 3 (16 series), Fold 4 (15 series).

### 13.8 Output Artifacts & Checksums

| Artifact File | Size (Bytes) | Lines | SHA-256 Digest |
|---|---|---|---|
| `market_inventory_raw.csv` | 2,798 | 43 | `5e273de64d0f8505d9a1a700421573336b627ebb418d5136afc333be42d79e09` |
| `market_alias_candidates.csv` | 3,520 | 22 | `fc219b117638e3039c0aa76045988601674c1c9c4872a32f757f46247e981eef` |
| `market_aliases_accepted.csv` | 6,361 | 43 | `e86609247db1706f09db688c3c87cc903471aaf43888666dd5fac626eb33f519` |
| `market_aliases_review.csv` | 297 | 2 | `7b34aa29f23d7a665b1ea010870d8b1ebef236f98d604b87206f23ef0fa836dc` |
| `pipeline_disposition_summary.json` | 706 | N/A | `d5349dd6064d92d7b3483af9e096df04c4f3036a1cc49b2397a760d89ef41e71` |
| `panel_v1_vs_v2_comparison.csv` | 1,286 | 62 | `20e0b77177040f716d5c7ea59c4bab9452b77fc0de5794036ab76e2ac79c04a1` |
| `corroboration_v2_summary.json` | 345 | N/A | `bacd95a93823d72419f1dce2a3949fef2677597de87d652ffdcb55de7ee76913` |
| `regime_diagnostics_monthly.csv` | 3,823 | 62 | `2a62c9d883df3c7a85460fa224b8ce260dcc56f60f4756663e513a78e056bfde` |
| `regime_diagnostics_summary.json` | 578 | N/A | `839ae4d843a097a1d03752d1f9ea93fe8214467db3593824b6efea232211bdaa` |
| `diff_77_date_alignment.csv` | 8,522 | 78 | `b1b5b751e8baf4748d58712beae164e616447300ea9a9082eee7ad7243155bb1` |
| `diff_77_date_alignment_summary.json` | 290 | N/A | `d2b07c5a20fa35ab0acb09500f792b77339b971cf2408b05ff57173df3e86666` |
| `train_eligibility_tiers_v2.csv` | 108,769 | 805 | `f6b9e3847229afe5eccc7b209947c0c2d19a46968367e0a673ebbdd8b63b914a` |
| `focus_crops_train_eligibility_v2.csv` | 4,668 | 118 | `ab072a2e3f6f189d4e2828b4161621a4f4647c2e64b9ec7a1ef256945603867f` |
| `rolling_origin_feasibility_v2.json` | 2,167 | N/A | `98245b1ed7f46ec37187998bb3a134f01f4fbe457cc8d3d78c7bf96a8735b1c9` |
| `processing_manifest_v2.json` | 5,136 | N/A | `c6f7089b94d2deaa7ca75f4ec85319d82d99fb8c1cd1be6c488398277a3518c1` |
| `mandi_5year_validated_v2.csv` | 67,455,377 | 463,218 | `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` |
| `kernel_execution_manifest.json` | 3,245 | N/A | `d558b34f8286ca3f707f43a0a19001cbe0ce194fa1f9747c04aa60b13ba8a230` |

---

## 14. Provisional-v2 Gates & Baseline Forecasting Scorecard (MP-FC-006)

* **Execution Date:** 2026-11-12
* **Kaggle Kernel ID:** `theankitchoubey/mp-fc-006-baselines` (v3, CPU, Internet Disabled)
* **Dataset:** `theankitchoubey/mandi-prediction-audit-003b` (v1 private, unchanged)
* **Status:** Complete, 100% hash verified.

### 14.1 Integrity Gate & Forensic Gates Summary (Part B1)
1. **Assertion Gate:** Regenerated Panel v2 and confirmed SHA-256 == `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`.
2. **Alias Transition Forensics:** Evaluated 24 candidate pairs. All 19 standard accepted pairs with overlapping quotes during the 2025-11-01 to 2025-11-05 transition window exhibit **100.00% exact price agreement** across 758 overlapping natural keys. Special evaluation of Kanpur `Baripaal APMC` vs `Varipaal APMC` revealed 52 overlap days, 462 keys, and **95.67% exact price agreement**. `Jhansi Grain APMC` vs `Jhansi (Grain) APMC` showed 10 overlap days, 23 keys, and **100.00% exact price agreement**.
3. **Excel Unmatched In-Window Rows Reclassification (1,895 rows):**
   * `low_obs_dropped`: 923 rows (48.71%) — series dropped due to $< 20$ historical observations across 5 years.
   * `other`: 420 rows (22.16%) — unmapped market naming variations in Excel (e.g., 379 in Kanpur).
   * `quarantined_strategy2`: 323 rows (17.05%) — dropped due to conflicting/invalid price quotes ($\text{Min} > \text{Max}$ or Modal outside $[\text{Min}, \text{Max}]$).
   * `absent_from_raw`: 197 rows (10.40%) — quotes present in Excel reports but completely absent from raw historical download CSVs.
   * `spelling_unmapped`: 32 rows (1.69%) — minor variety/grade naming differences.
4. **Tier A Training Observations Reconciliation ($T \le 2025-12-18$):**
   * v1 Tier A: 496 series, 384,887 observations.
   * v2 Tier A: 492 series, 387,242 observations ($\le 2025-12-18$, net gain of +2,355 rows from pre-migration and post-migration feed merger).
   * v2 Tier A across full 5-year panel: 492 series, 404,498 observations.
   * Set transitions: 2 series entered (+571 obs), 6 series left (-1,408 obs), 490 common series (+3,192 obs).
5. **Fractional Pricing Diagnostics (Post 2026-03):**
   * First month exceeding 5% fractional quotes: `2026-02` (8.73%).
   * Post 2026-03 fractional share: **40.89%** (12,923 fractional, 18,678 integer).
   * Adjacent-day test: 78.22% of fractional quotes have an observation on day $t \pm 1$; **38.83% of those adjacent observations are exact integers**.
   * Commodity median price ratio (post vs pre 2026-03): Median ratio is **1.0000** (mean: 1.0788), confirming no shift in statutory reporting units.
6. **Monthly Reporting Depth Diagnostics:**
   * Active reporting markets remained stable across all 61 months (18 to 20 markets).
   * Reporting varieties collapsed from ~85 down to ~35-40 in mid-2026, halving multi-variety quotes per market and explaining the drop from ~8.5k to ~4.5k monthly records.

### 14.2 Baseline Evaluation Protocol & Mathematics (Part B2)
* **Strict As-Of Operational Constraint:** For any origin date $t$, predictions use exclusively observations dated $\le t$.
* **Target Definition:** Modal price in $[t+6, t+8]$ closest to $t+7$ (tie-break earlier). Target date must be $\le \text{fold\_end}$.
* **Serving-Time Recency Condition:** Origin is evaluated only if the series has $\ge 3$ observations in $[t-30\text{d}, t]$.
* **Baseline Models:**
  $$\hat{y}_{\text{naive}}(t+7) = y(t)$$
  $$\hat{y}_{\text{ma}}(t+7) = \frac{1}{K} \sum_{k=1}^K y(t_k), \quad K = \min(7, N_{[t-30\text{d}, t]}), \quad \text{abstain if } K < 3$$
  $$\hat{y}_{\text{snaive}}(t+7) = y(t^*), \quad t^* = \arg\min_{t_s \in [t-360, t-354]} |t_s - (t - 357)|, \quad \text{abstain if none}$$
  $$\hat{y}_{\text{drift}}(t+7) = y(t) + 0.5 \times \frac{y(t) - y(t_a)}{t - t_a} \times 7, \quad t_a = \arg\min_{t_k \in [t-17, t-11]} |t_k - (t - 14)|, \quad \text{abstain if none}$$
* **Statistical Metrics:** MAE (Rs/qtl), RMSE, MAPE (%), Median AE, Bias, Share within 5% (%), Abstention rate (%), Skill vs Naive ($1 - \text{MAE} / \text{MAE}_{\text{naive}}$).
* **Cluster Bootstrap:** 1,000 resamples over unique series clusters with seed 42 for 95% confidence intervals.

### 14.3 Overall Baseline Scorecard Summary (Tier A, 64,776 Origins)

| Model | N Origins | N Series | MAE (Rs/qtl) | 95% CI (MAE) | RMSE | MAPE (%) | Median AE | Bias | $\le 5\%$ (%) | Abstain (%) | Skill vs Naive | 95% CI (Skill) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Naive** | 64,776 | 401 | **106.96** | [96.35, 119.03] | 298.83 | 4.16% | 40.00 | +17.17 | 76.76% | 0.00% | 0.0000 | [0.0000, 0.0000] |
| **Moving Average** | 64,776 | 401 | 134.19 | [120.73, 149.35] | 333.37 | 5.08% | 50.71 | +26.30 | 70.98% | 0.00% | -0.2547 | [-0.2909, -0.2105] |
| **Seasonal Naive** | 59,200 | 401 | 774.38 | [661.02, 895.07] | 1433.76 | 29.45% | 375.00 | +351.69 | 22.70% | 8.61% | -6.3738 | [-7.2432, -5.5137] |
| **Drift** | 64,036 | 401 | 107.32 | [95.82, 119.13] | 303.67 | 4.29% | 42.00 | +7.81 | 76.55% | 1.14% | -0.0068 | [-0.0303, 0.0191] |

### 14.4 Focus Crop Highlights & Sensitivities
* **Wheat:** Naive MAE is **29.77 Rs/qtl** (95% CI: [24.85, 35.21]); Moving Average MAE is 35.42 Rs/qtl; Seasonal Naive MAE is 152.42 Rs/qtl.
* **Potato:** Naive MAE is **49.87 Rs/qtl** (95% CI: [43.46, 57.58]); Drift MAE is 52.17 Rs/qtl.
* **Onion:** Drift outperforms Naive! Drift MAE is **76.86 Rs/qtl** vs Naive 83.89 Rs/qtl (**Skill: +0.0818**, 95% CI: [0.0315, 0.1294]).
* **Rice:** Moving Average outperforms Naive! MA MAE is **138.71 Rs/qtl** vs Naive 163.54 Rs/qtl (**Skill: +0.1518**, 95% CI: [0.0984, 0.2085]).
* **Paddy(Dhan)(Common):** Moving Average achieves MAE of **27.51 Rs/qtl** vs Naive 32.67 Rs/qtl (**Skill: +0.1579**, flagged `LOW-N` due to 5 series).
* **Volatile Origins ($> 2\%$ Target Move, 27,858 origins):** Drift demonstrates significant skill over Naive, reducing MAE from 217.38 to **202.10 Rs/qtl** (**Skill: +0.0695**, 95% CI: [0.0401, 0.0982]).
* **Excluding 77 Disputed Keys (64,776 origins):** Metrics are identical to full Tier A, proving that the disputed quotes have zero impact on baseline evaluation.

### 14.5 Output Artifacts & Checksums (MP-FC-006)

| Artifact File | Size (Bytes) | Lines | SHA-256 Digest |
|---|---|---|---|
| `scorecard_fold_x_tier.csv` | 5,086 | 41 | `ee109061f8e2e30f281ef5ce61d42529e82a365c6f3bba0645b0e047e68cbff9` |
| `scorecard_fold_x_focus_crop.csv` | 13,308 | 121 | `2b548724e6d3b2d191f7106cac7151b337a256dc9ea964456e4081ab118c7b4d` |
| `scorecard_sensitivities.csv` | 8,449 | 61 | `20678dce03e771b3ed0589e874b27547539609c310cc981aac4801f430e0a2b3` |
| `alias_transition_forensics.csv` | 3,731 | 25 | `5e45350e47013a31a1fe61f0dfee859ea1cc956409d0982f5ab52a174373895d` |
| `excel_unmatched_reclassification_v2.csv` | 2,757 | 85 | `97a54efe60748f24d6b20a2782b7baec7b8a259f256537773266f55be0d0ee18` |
| `excel_unmatched_summary_v2.json` | 1,062 | N/A | `8d95409e8f9bd8ace3881ee52f08fe644e3e193a8ead894cd2f600707fbcfda8` |
| `tier_a_reconciliation_v1_vs_v2.json` | 929 | N/A | `bb76c92f85eadc71ab220d2cbe04f6d5c02570687d91b8849797d787e05d3b0b` |
| `tier_a_series_deltas.csv` | 39,298 | 491 | `96df1275440d2f823754e8d9228f8e192aa29a41f5cb9230da20aff7e70c1248` |
| `fractional_part_distribution.csv` | 309 | 21 | `2080aebcaf3d3b30767f2123e4c11438182a66f609d0cc1877114a15cdf500fd` |
| `fractional_pricing_diagnostics.json` | 437 | N/A | `d382b38db6055efc9af7d61a9f2dbe3eb4a2c8ce546bd3956decfe54f57b9429` |
| `monthly_reporting_depth_diagnostics.csv` | 2,401 | 62 | `57835ad459f401a674230599e62c62fa6f3f0c21812d98ae62ae164ad1acbab2` |
| `baseline_predictions_sample.csv` | 954,096 | 5,001 | `c3b805a98e63fa7da14eaea14d2a9214f456c0fd367c13db9e93e61e92f9219b` |
| `mandi_5year_validated_v2.csv` | 67,455,377 | 463,218 | `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` |
| `processing_manifest_v2.json` | 5,136 | N/A | `c61202b741a31749bca86bd7fb4f59ea82bc6041007626a2d13a6734043d5e60` |
| `kernel_execution_manifest.json` | 3,115 | N/A | `5e89d18b628ec2c1c984920677536d5ba4b0a7c49b6b9075d55e8869b207559e` |









---

## 15. Independent FC-006 audit and continuing mathematical contract — 2026-11-12 IST

**Status: CHANGES REQUIRED.** This dated adjudication supersedes conflicting acceptance language, MASE values and causal claims in earlier sections; prior text is retained as history. See `FC006_INDEPENDENT_AUDIT.md` for claim evidence, `PROJECT_EXECUTION_LEDGER.md` for the roadmap and `prompts/MP-AUDIT-007.md` for the next task. Every subsequent executor prompt must update this document and the ignored local `brain/context.md`.

### 15.1 Verification and test receipt

GitHub connector independently verified FC-006 commit `7931caaf01ee9e53ea2f18b823d710b8c61851ff`. Thirteen small execution-manifest artifacts matched recorded hashes locally. The full panel and end-to-end scoring were not independently regenerated. Targeted verification command:

```text
python3 -m pytest tests/test_baselines.py tests/test_market_identity.py tests/test_recommendation_safety_gate.py -q -o cache_dir=/tmp/mandi_audit_pytest_cache --basetemp=/tmp/mandi_audit_pytest_tmp
```

Result: **33 passed in 11.62 seconds**, exit 0. This validates selected fixture tests, not full-panel forecasting, optimized notebook equivalence or live readiness. The previous full-suite claim of 160 passes remains REPORTED, not rerun here. Whitespace check identified a pre-existing extra blank line at the end of the FC006 summary; it was preserved.

### 15.2 Mandatory corrections to interpretations

- All 77 disputed source keys have APMC market names; accepted mappings change all 77. The notebook compares these unmapped names against canonical market keys. The identical-metrics sensitivity therefore does not establish zero impact. Missing discrepancy evidence currently falls back to an empty set, which must fail closed instead.
- Artifact-backed set reconciliation is 6 leaving / 2 entering / 490 common, not 9 / 5. Thresholds are >=60 Tier A and >=120 Tier B with coverage >=0.30, not >=200. Row reconciliation: 571 - 1408 + 3192 = 2355.
- Pasted report metrics and selected documentation CIs disagree with the CSVs. Artifact values are recorded in the audit, still provisional pending corrections. Drift overall paired skill is -0.0068 with CI [-0.0303, 0.0191]. Its >2% realized-move subset skill is +0.0695 with CSV CI [0.0432, 0.0950]. That subset is known only after the outcome and cannot select live decisions.
- F1/F2 contribute 94.7079% of pooled Tier A origins. A pooled score is not sufficient evidence of modern-regime performance. The 5000-row prediction sample is F1-only.
- The scored-series count and LOW-N flag must use each model's non-abstained cases; separately report candidate eligibility and target availability. Current notebook counts slice-level series before model abstention.
- Source units cannot be proved by median price ratios. The register's exact November 7 platform go-live claim remains unverified. Declining variety counts are associated with reduced reporting volume; causal attribution remains unresolved.

### 15.3 Point metrics and correct scaling

For each model m, let S_m contain cases with valid observed targets, valid m forecasts, and valid naive forecasts. Paired skill is:

$$Skill_m=1-\frac{\sum_{j\in S_m}|y_j-\hat y_{m,j}|}{\sum_{j\in S_m}|y_j-\hat y_{naive,j}|}.$$

Declare undefined skill when the denominator is zero; do not silently turn it into zero or perfect performance. MAE is the sum of absolute errors divided by the number scored. RMSE is the square root of mean squared error. MAPE excludes nonpositive targets using an explicitly reported denominator; within-5% and all other percentage scores must state their valid denominator. Finite-value and zero-denominator handling must be tested.

**MASE correction:** conventional nonseasonal MASE uses a training-only one-step naive scale; seasonal MASE uses a training-only seasonal naive scale. The earlier assertion that matching the forecast horizon is required for valid MASE is withdrawn. A horizon-matched scale can be a separately named project metric, with its lag-matching rules declared. For series s with complete equally spaced training data and scaling lag a:

$$d_s=\frac{1}{T_s-a}\sum_{i=a+1}^{T_s}|y_{s,i}-y_{s,i-a}|,\qquad MASE_s=\frac{MAE_{s,test}}{d_s}.$$

For irregular dates, define the actual allowed historical pairs and divide by their count, not T_s-a. Exact calendar matching and observation-step matching are different estimands. Series with insufficient pairs or zero scale have undefined MASE and must be counted. State any cross-series aggregation weighting. Pooled test MAE / pooled test naive MAE is a relative MAE ratio, not conventional MASE. Earlier FC006 MASE table entries are **NOT VALIDATED / NOT COMPUTED** until this implementation exists. Source: [Hyndman and Athanasopoulos, evaluating forecast accuracy](https://otexts.com/fpp3/toolbox.html#evaluating-point-forecast-accuracy).

Bootstrap confidence intervals quantify uncertainty in aggregate historical scores, not prediction intervals for individual future prices. Series-cluster resampling permits within-series dependence but does not automatically account for correlated shocks across markets; assess time-block/common-shock sensitivity before strong significance claims. State observation versus series weighting and multiplicity. Deterministic iteration order is needed in addition to a seed.

### 15.4 Forecasting and model-development contract

Issue time must be defined. Observation date <= origin date is necessary but does not prove publication by the issue time. Without historical retrieval timestamps, evaluation is retrospective under declared availability assumptions. Future data mutation tests must cover the actual notebook/scoring path as well as preprocessing, eligibility and identity decisions. Full-history alias evidence and low-observation filtering require a lookahead assessment.

Keep the current nearest-observed target in [t+6,t+8], tie earlier, with actual target date and an exact-t+7 sensitivity. For future ML training, every training label must have matured by its training cutoff; a seven-day embargo alone may be insufficient at an eight-day target boundary. Check actual target dates explicitly.

Baseline rationale and proposed candidate rationale are in the execution ledger. The old classification pipeline is a separate task from continuous seven-day price forecasting. Begin ML only after baseline corrections; tune within chronological training/validation windows and compare on matched origins. Already inspected test folds are development evidence, not a fresh untouched test. A prospective forward evaluation must remain independent. Reference for lagged tabular forecasting and temporal evaluation: [scikit-learn lagged-features example](https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html). This is methodological guidance, not a request to upgrade pinned packages.

### 15.5 Synthetic economics: approved scenario direction, not observed tariffs

Owner permits realistic synthetic storage/cost scenarios where empirical quotations are unavailable. This permits completing a simulation feature and stress-testing the engine. It does not establish that costs are observed, current, locally available, or that simulated profits are realized farmer gains.

Every scenario must contain `is_synthetic`, `scenario_id`, `scenario_version`, seed, crop, storage technology/conditions, location scope, holding duration, currency/unit, parameter ranges/distributions, source citations or ASSUMPTION, creation timestamp and assumed effective period. Creation time is not a quotation/retrieval time. Use explicit low/base/high and adverse scenarios; use correlated bounded simulation only where dependence is justified, otherwise label dependence assumptions. Do not invent named providers or market survey evidence. Crop suitability and storage availability remain separate constraints. There are no numeric commercial tariff ranges approved by this audit.

Under the current code's convention, Q is initial quintals; P0/P1 are rupees per quintal; L is physical loss; q is quality markdown; cs/ch are period storage/handling rupees per initial quintal; c0 is current transaction rupees per initial quintal; c1 is future transaction rupees per remaining quintal; r is the annual financing OR opportunity rate; h is calendar days. Let k = r*h/365 when a carrying charge applies, else zero:

$$R_{now}=Q(P_0-c_0),$$
$$R_{store}=Q(1-L)(1-q)P_1-Q(c_s+c_h)-QP_0k-Q(1-L)c_1,$$
$$\Delta R=R_{store}-R_{now},$$
$$P_{BE}=\frac{P_0(1+k)+c_s+c_h+(1-L)c_1-c_0}{(1-L)(1-q)}.$$

These equations align with the inspected calculation and break-even paths; they are not proof of realistic input values. Test that delta R is zero at P_BE, units agree, quantity scaling is consistent, costs/losses move the result in the expected direction, and invalid/NaN/infinite inputs fail safely. Define whether transport is a transaction-cost component or separately added; avoid double counting. Hourly/monthly/bag tariffs need documented conversion to the chosen holding period and initial quantity. Evaluate both h=6/7/8 when actual target dates vary, or restrict economic backtests to exact h=7.

For uncertainty-aware simulation, propagate forecast uncertainty and assumption uncertainty separately, retaining their dependence assumptions. Report break-even probability under the named scenario, adverse-case net benefit, decision coverage and regret versus sell-now after outcomes. Such probabilities are model/scenario outputs, not calibrated real-world profitability claims. Simulated costs must keep economics labelled SCENARIO / SIMULATION_ONLY, even with live observed prices. Empirical price-forecast scoring remains separate. Later commercial quotations or user-entered costs can replace assumptions with their own provenance and validation.

---

## 16. Task MP-AUDIT-007 Execution & Adjudication Record — 2026-11-12 IST

**Status:** **LOCAL REPAIRS COMPLETE; BASELINE SCORECARD RERUN REQUIRED**
**Audit Baseline Commit:** `7931caaf01ee9e53ea2f18b823d710b8c61851ff`
**Execution Context:** Local Light Audit, Fixture Regression Tests, Source & Notebook Corrections. Zero remote heavy compute, zero data uploads.

### 16.1 Adjudication of Audit Findings (A007-01 to A007-10)

1. **A007-01 (Disputed-Key Market Identity Mismatch):**
   - *Adjudication:* **REPAIRED / PENDING REMOTE RERUN**. In the original FC-006 run, raw market names with `" APMC"` from `diff_77_deep_analysis.csv` were checked against canonical market names in the panel, matching exactly 0 keys. The reported identical metrics was an artifact of identity mismatch. Implemented `load_canonical_disputed_keys()` in `src/baselines.py` with fail-closed schema/row validation and canonicalization via `market_aliases.csv`. Verified that 100% of raw market names ($77/77$) transform to canonical names and yield 77 unique canonical keys. Defined dual sensitivity scopes (Scope a: row filter; Scope b: historical intervention). Notebook updated; full panel rescoring designated **RERUN REQUIRED**.
2. **A007-02 (Claim-to-Artifact Numerical Reconciliation):**
   - *Adjudication:* **RECONCILED & CORRECTED**. Corrected all metrics in documentation and reports to match `scorecard_fold_x_tier.csv`. Tier A MA RMSE is 333.37 (not 321.46), MAPE is 5.08% (not 5.25%), Median AE is 50.71 (not 61.29), Share $\le 5\%$ is 70.98% (not 67.86%). Tier A Seasonal Naive RMSE is 1433.76 (not 1297.86), MAPE is 29.45% (not 32.74%), Median AE is 375.0 (not 468.0), Share $\le 5\%$ is 22.70% (not 18.06%). Tier A Drift RMSE is 303.67 (not 300.56), Median AE is 42.0 (not 40.0), Paired Skill is -0.0068 (95% CI: [-0.0303, 0.0191]). Drift $>2\%$ target move skill 95% CI is **[0.0432, 0.0950]** (not [0.0401, 0.0982]). Flagged `baseline_predictions_sample.csv` (5,000 rows) as F1-only and prepared full predictions archive export.
3. **A007-03 (Series Reconciliation Narrative):**
   - *Adjudication:* **CORRECTED**. Reconciled narrative with `tier_a_reconciliation_v1_vs_v2.json`: exactly **6 leaving series** (-1,408 obs), **2 entering series** (+571 obs), **490 common series** (+3,192 obs), net observation delta = **+2,355 rows** ($384,887 \rightarrow 387,242$). Documented eligibility threshold as $N \ge 60$ and coverage $\ge 0.30$ for Tier A; $N \ge 120$ and coverage $\ge 0.30$ for Tier B.
4. **A007-04 (MASE Label Withdrawn):**
   - *Adjudication:* **WITHDRAWN / NOT COMPUTED**. The baseline engine does not compute in-sample training-only naive scaling denominators. Test-relative metrics are officially named **Skill vs Naive** ($1 - \text{MAE} / \text{MAE}_{\text{naive}}$). MASE is marked **NOT COMPUTED**.
5. **A007-05 (Scoring Path & Loop Equivalence):**
   - *Adjudication:* **VERIFIED & TESTED**. Authored `tests/test_fc006_audit.py` (10 tests, 100% pass) verifying exact float equivalence between modular functions in `src/baselines.py` and the optimized array operations across dense daily, irregular, missing anchor, and seasonal tie-breaking fixtures. Verified future price change, row insertion, and row deletion invariance.
6. **A007-06 (Scored-Series & LOW-N Accounting):**
   - *Adjudication:* **REPAIRED**. Updated `evaluate_model_slice()` to report both eligible and scored origins/series. Evaluated `low_n_flag` strictly on scored cases ($N_{\text{scored\_origins}} < 200$ or $N_{\text{scored\_series}} < 10$).
7. **A007-07 (Lookahead in Panel Harmonization):**
   - *Adjudication:* **DOCUMENTED**. Documented that market alias acceptance and $<20$ observation filtering used full 5-year data (retrospective data harmonization). In prospective live evaluation, alias mappings and series eligibility must be fixed strictly as of the forecast issue timestamp.
8. **A007-08 (Causal Wording Qualified):**
   - *Adjudication:* **QUALIFIED**. Stable commodity median ratios ($1.0000$) are consistent with no unit change, but do not statutory prove units. Variety consolidation is empirically associated with volume reduction, but causal attribution remains an external hypothesis.
9. **A007-09 (Retrospective Diagnostic Subgroup):**
   - *Adjudication:* **QUALIFIED**. The $>2\%$ target move subset ($N = 27,858$ origins) where Drift outperforms Naive (+0.0695 skill) is defined retrospectively by realization. It serves as a diagnostic benchmark, but cannot select live models at prediction time.
10. **A007-10 (Trust Policy Alignment):**
    - *Adjudication:* **PRESERVED**. Capability gating strictly separates Release 1 (price forecasting benchmarks on price data alone) from Release 2 (storage economics). Simulated costs remain simulation-only.

---

### 16.2 Formal Equations and Estimator Specifications

#### 1. Point Forecasting Metrics (on Scored Set $S_m$)
Let $S_m = \{j : y_j \text{ observed}, \hat{y}_{m, j} \text{ valid}, \hat{y}_{\text{naive}, j} \text{ valid}\}$ be the set of scored origin instances for model $m$.

$$\text{MAE}_m = \frac{1}{|S_m|} \sum_{j \in S_m} |y_j - \hat{y}_{m, j}|$$

$$\text{RMSE}_m = \sqrt{\frac{1}{|S_m|} \sum_{j \in S_m} (y_j - \hat{y}_{m, j})^2}$$

$$\text{MAPE}_m = \frac{1}{|S_m^+|} \sum_{j \in S_m^+} \frac{|y_j - \hat{y}_{m, j}|}{y_j} \times 100\%, \quad S_m^+ = \{j \in S_m : y_j > 0\}$$

$$\text{Median AE}_m = \text{median}\left(\{|y_j - \hat{y}_{m, j}| : j \in S_m\}\right)$$

$$\text{Bias}_m = \frac{1}{|S_m|} \sum_{j \in S_m} (\hat{y}_{m, j} - y_j)$$

$$\text{Share}_{\le 5\%} = \frac{|\{j \in S_m^+ : |y_j - \hat{y}_{m, j}| / y_j \le 0.05\}|}{|S_m^+|} \times 100\%$$

#### 2. Paired Skill vs Naive
$$\text{Skill}_m = 1 - \frac{\sum_{j \in S_m} |y_j - \hat{y}_{m, j}|}{\sum_{j \in S_m} |y_j - \hat{y}_{\text{naive}, j}|} = 1 - \frac{\text{MAE}_m}{\text{MAE}_{\text{naive}, S_m}}$$

*Zero-Denominator Policy:* If $\sum_{j \in S_m} |y_j - \hat{y}_{\text{naive}, j}| = 0$ or $|S_m| = 0$, $\text{Skill}_m = \text{NaN}$. It is never silently imputed as 0 or 1.

#### 3. Ratio-of-Means Cluster Bootstrap Estimator
Let $C = \{c_1, c_2, \dots, c_K\}$ be the set of $K$ unique series clusters, sorted deterministically. In each resample $b \in \{1, \dots, B\}$ ($B = 1,000$, seed 42):
Draw clusters $C^*_b = \{c_{k_1}, \dots, c_{k_K}\}$ with replacement.

$$\text{MAE}_b = \frac{\sum_{c \in C^*_b} E_{m, c}}{\sum_{c \in C^*_b} N_c}, \quad \text{MAE}_{\text{naive}, b} = \frac{\sum_{c \in C^*_b} E_{\text{naive}, c}}{\sum_{c \in C^*_b} N_c}$$

$$\text{Skill}_b = 1 - \frac{\text{MAE}_b}{\text{MAE}_{\text{naive}, b}} = 1 - \frac{\sum_{c \in C^*_b} E_{m, c}}{\sum_{c \in C^*_b} E_{\text{naive}, c}}$$

The 95% bootstrap confidence interval is obtained from the empirical 2.5th and 97.5th percentiles of $\{\text{MAE}_b\}$ and $\{\text{Skill}_b\}$.
*Dependence Assumptions:* Errors for observations within the same series are assumed dependent (autocorrelated time series). Series across distinct market-commodity identities are assumed independent.

---

### 16.3 Reconciled Artifact-Backed Baseline Scorecard (Overall Tier A)

The table below presents the verified, artifact-backed scorecard results from `scorecard_fold_x_tier.csv` ($N = 64,776$ eligible Tier A origins across 401 series):

| Model | N Scored | Scored Series | Abstain (%) | MAE (₹/qtl) | 95% CI (MAE) | RMSE | MAPE (%) | Median AE | Bias | $\le 5\%$ (%) | Skill vs Naive | 95% CI (Skill) | Low-N Flag |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Naive ($y(t)$)** | 64,776 | 401 | 0.00% | 106.96 | [96.35, 119.03] | 298.83 | 4.16% | 40.00 | +17.17 | 76.76% | 0.0000 | [0.0000, 0.0000] | False |
| **Moving Avg (MA-7)** | 64,776 | 401 | 0.00% | 134.19 | [120.73, 149.35] | 333.37 | 5.08% | 50.71 | +26.30 | 70.98% | -0.2547 | [-0.2909, -0.2105] | False |
| **Seasonal Naive ($t-357$)** | 59,200 | 401 | 8.61% | 774.38 | [661.02, 895.07] | 1433.76 | 29.45% | 375.00 | +351.69 | 22.70% | -6.3738 | [-7.2432, -5.5137] | False |
| **Drift (14d Anchor)** | 64,036 | 401 | 1.14% | 107.32 | [95.82, 119.13] | 303.67 | 4.29% | 42.00 | +7.81 | 76.55% | -0.0068 | [-0.0303, 0.0191] | False |

*(All numbers above match the saved scorecard CSV artifacts. Prior prose summaries containing rounded or discrepant metrics are superseded).*



## 17. Independent review of MP-AUDIT-007 — 2026-11-12 IST

Commit 250eb45e10e8accc614f7c9334a19b9042a5b8f7 verified on GitHub. Targeted command `python3 -m pytest tests/test_baselines.py tests/test_fc006_audit.py -q -o cache_dir=/tmp/mandi_audit008_cache --basetemp=/tmp/mandi_audit008_tmp`: 18 passed in 0.37s, exit 0. Full 170-pass receipt remains REPORTED; not independently rerun here. Verdict: useful partial repairs, CHANGES REQUIRED before remote execution.

New findings: notebook retains inline prediction implementation instead of invoking tested predict_series_vectorized; Scope B recomputes MA/drift but not seasonal naive; cleaned history does not reapply general recency eligibility; boundary test asserts standalone date arithmetic rather than actual evaluator. Shared scorer counts three-way validity but metric routine uses a different mask when naive is missing. The real-key integration test depends on ignored outputs and can skip. documentation/context.md is an untracked, unignored journal duplicate; preserve without syncing or committing.

Pasted fold counts are incorrect: actual Tier A naive F1/F2/F3/F4 are 37,858 / 23,490 / 1,413 / 2,015. Legacy overall MA/seasonal/drift MAE CIs remain [120.7251,149.3536] / [661.0247,895.0745] / [95.8185,119.1334]. Other values in the completion message are unsupported by unchanged artifacts. Volatile subgroup 27,858 is eligible; drift scores 27,451. Do not call matching pair totals verification of each fold.

Next: documentation/prompts/MP-AUDIT-008.md, local-only repair pass. No Kaggle rerun approved, no new model training, no panel freeze. Scope B must remove history for all baselines and compare paired cases with explicit exclusions. Existing retrospective/lookahead limitations remain open.



## 18. Unified Production Scoring Engine & Scope B Sensitivity (MP-AUDIT-008)

**Document Reference:** `MP-AUDIT-008`
**Date:** `2026-11-12` (Asia/Kolkata)
**Status:** **LOCAL REPAIRS COMPLETE; BASELINE SCORECARD RERUN REQUIRED**
**Audit Baseline Commit:** `250eb45e10e8accc614f7c9334a19b9042a5b8f7`

### 18.1 Mathematical Formulation of Unified Production Scoring Path
To eliminate the architectural discrepancy between modular tests and the high-performance notebook loop (Finding A007-05 / Section 17 Review), the scoring logic is encapsulated into `score_series_origin()` in `src/baselines.py`.

Given a series array of dates $D = (d_1, \dots, d_N)$ and clean prices $P = (p_1, \dots, p_N)$ sorted chronologically ($d_1 < d_2 < \dots < d_N$), for an origin date $t$ and fold test window $[T_{\text{test\_start}}, T_{\text{test\_end}}]$:

1. **Test Window Containment:**
   $$t \in [T_{\text{test\_start}}, T_{\text{test\_end}}]$$
2. **Origin Observation:**
   $$\exists i : d_i = t, \quad y(t) = p_i$$
3. **Serving-Time Recency Rule:**
   $$N_{\text{recency}}(t) = \sum_{k=1}^N \mathbf{1}_{\{t - 30\text{d} \le d_k \le t\}} \ge 3$$
4. **Target Extraction & Tie-Breaking:**
   $$\mathcal{T}(t) = \{k : t + 6\text{d} \le d_k \le t + 8\text{d}\}$$
   If $\mathcal{T}(t) \ne \emptyset$, select $k^* = \arg\min_{k \in \mathcal{T}(t)} (|d_k - (t+7\text{d})|, d_k)$ (breaking distance ties to earlier calendar date).
   The target date $d_{k^*}$ must strictly obey the fold boundary:
   $$d_{k^*} \le T_{\text{test\_end}}$$
   If $d_{k^*} > T_{\text{test\_end}}$, the origin is dropped (`drop_reason = "dropped_target_after_fold_end"`).

### 18.2 Scope B Sensitivity Formulation for All Baselines
Scope B models an interventionist policy where disputed discrepancy observations are excised from historical series data:

$$\mathcal{K}_{77} = \{(d_i, m_i, c_i, v_i, g_i, \tau_i)\}_{i=1}^{77}$$

For an origin instance with metadata $(d, m, c, v, g)$ at date $t$ and target date $t_{\text{target}}$:
1. **Explicit Origin/Target Exclusion:**
   - If $(d, m, c, v, g, t) \in \mathcal{K}_{77}$: $\mathtt{scope\_b\_eligible} = \text{False}$, $\mathtt{reason} = \text{"disputed\_origin"}$.
   - If $(d, m, c, v, g, t_{\text{target}}) \in \mathcal{K}_{77}$: $\mathtt{scope\_b\_eligible} = \text{False}$, $\mathtt{reason} = \text{"disputed\_target"}$.
2. **Counterfactual Clean History Construction:**
   $$\mathcal{H}_{\text{clean}}(t) = \{k : d_k \le t \land (d, m, c, v, g, d_k) \notin \mathcal{K}_{77}\}$$
3. **Clean Recency Verification:**
   $$N_{\text{clean\_recency}}(t) = \sum_{k \in \mathcal{H}_{\text{clean}}(t)} \mathbf{1}_{\{t - 30\text{d} \le d_k \le t\}} \ge 3$$
   If $N_{\text{clean\_recency}}(t) < 3$, $\mathtt{scope\_b\_eligible} = \text{False}$, $\mathtt{reason} = \text{"recency\_failure\_after\_removal"}$.
4. **Counterfactual Predictions on $\mathcal{H}_{\text{clean}}(t)$:**
   - **Naive:** $\hat{y}_{\text{naive}, B}(t+7) = y(t)$
   - **Moving Average:** Mean of last $\le 7$ observations in $\mathcal{H}_{\text{clean}}(t) \cap [t-30\text{d}, t]$
   - **Seasonal Naive:** Nearest observation to $t - 357$ in $\mathcal{H}_{\text{clean}}(t) \cap [t-360, t-354]$
   - **Damped Drift:** Anchor nearest $t - 14$ in $\mathcal{H}_{\text{clean}}(t) \cap [t-17, t-11]$, slope $\frac{y(t) - y_{\text{anchor}}}{\Delta t}$

### 18.3 Shared Scorer Denominators & Joint Finite Masking
In `evaluate_model_slice()`, evaluation is strictly performed on the joint finite intersection:

$$\mathcal{S}_{\text{scored}} = \{i \in \mathcal{S}_{\text{eligible}} : y_{\text{true}, i} \in \mathbb{R} \land \hat{y}_{\text{model}, i} \in \mathbb{R} \land \hat{y}_{\text{naive}, i} \in \mathbb{R}\}$$

- **Observation Conservation:** $N_{\text{scored}} = |\mathcal{S}_{\text{scored}}| \le N_{\text{eligible}} = |\mathcal{S}_{\text{eligible}}|$.
- **Abstention Rate:** $\text{Abstention} = \frac{N_{\text{eligible}} - N_{\text{scored}}}{N_{\text{eligible}}} \times 100\%$.
- **Skill vs Naive:** Computed on the exact matching paired sample:
  $$\text{Skill} = 1 - \frac{\sum_{i \in \mathcal{S}_{\text{scored}}} |\hat{y}_{\text{model}, i} - y_{\text{true}, i}|}{\sum_{i \in \mathcal{S}_{\text{scored}}} |\hat{y}_{\text{naive}, i} - y_{\text{true}, i}|}$$
- **Low-N Flag:** Evaluated strictly on scored counts:
  $$\mathtt{low\_n\_flag} = (N_{\text{scored}} < 200) \lor (N_{\text{scored\_series}} < 10)$$

### 18.4 Reconciled Fold Counts & Confidence Intervals

From `scorecard_fold_x_tier.csv`, exact fold counts and confidence intervals for Tier A Naive are:
- **Fold F1 (Train $\le$ 2024-12-31):** $N = 37,858$ origins across 359 series. MAE $= 101.59$ (95% CI: $[89.35, 114.11]$).
- **Fold F2 (Train $\le$ 2025-06-30):** $N = 23,490$ origins across 346 series. MAE $= 106.46$ (95% CI: $[93.44, 118.92]$).
- **Fold F3 (Train $\le$ 2025-12-18):** $N = 1,413$ origins across 102 series. MAE $= 108.11$ (95% CI: $[87.32, 131.00]$).
- **Fold F4 (Train $\le$ 2026-03-31):** $N = 2,015$ origins across 37 series. MAE $= 212.84$ (95% CI: $[46.91, 458.94]$).
- **Overall Tier A:** $N = 64,776$ origins across 401 series. MAE $= 106.96$ (95% CI: $[96.3545, 119.0323]$).

Overall Tier A MAE 95% Confidence Intervals from persisted artifacts:
- **Naive:** $[96.3545, 119.0323]$
- **Moving Average:** $[120.7251, 149.3536]$
- **Seasonal Naive:** $[661.0247, 895.0745]$
- **Damped Drift:** $[95.8185, 119.1334]$

Volatile Subgroup ($|y(t+7) - y(t)| / y(t) > 0.02$):
- Eligible origins: $N = 27,858$.
- Drift scored origins: $N = 27,451$ (1.46% abstention).
- Drift Skill vs Naive: $+0.0695$ (95% CI: $[0.0429, 0.0937]$, correcting legacy $[0.0432, 0.0950]$).
- Scorecard row reconciliation: 240 total scorecard rows ($40 + 120 + 80$); exactly 224 finite paired skill identities and 16 undefined (NaN) focus-crop rows with $N_{\text{eligible\_origins}} = 0$ (F3 Paddy, F4 Onion, F4 Tomato, F4 Paddy across 4 models). Undefined skill is mathematically preserved, not set to zero.

*(Prior pasted counts 45,958 / 15,390 / 1,791 / 1,637 and unexecuted alternate CIs are officially superseded).*



## MP-AUDIT-008 independent review — 2026-11-12 IST
Commit 078ab38b5872615f30647f8ef4dba37f06fcb0c3 independently verified on GitHub. Targeted tests independently rerun: python3 -m pytest tests/test_baselines.py tests/test_fc006_audit.py -q -o cache_dir=/tmp/mandi_review008_cache --basetemp=/tmp/mandi_review008_tmp => 21 passed in 0.39s, exit 0. Five code cells AST-parsed. Notebook now calls shared score_series_origin and train eligibility; Scope B covers all four baselines with clean-history recency. Local repairs conditionally accepted for a bounded retrospective rerun; full 173-test receipt remains REPORTED, not independently rerun here. No panel/ML/live approval.
Remaining corrections: 27,858 - 27,451 = 407, not 398; paired-naive MAE 217.1723 is unsupported and should be withdrawn/recomputed from paired predictions; Scope B finite-to-NaN changes need explicit transition counts (current change flags require both finite). documentation/context.md was synced contrary to MP-AUDIT-008; preserve and stop syncing. Exact future run version/runtime is not yet known. Next prompt documentation/prompts/MP-FC-006R.md requires explicit owner approval for one private CPU kernel run, no upload/retry. No Kaggle run performed by reviewer.

Follow-up blocking verification: notebook embedded baselines.py decoded to 24,453 bytes and does NOT match current source (AST differs too). It lacks check_serving_recency, evaluate_series_train_eligibility, extract_target_vectorized and score_series_origin; five existing functions also differ. Reject reported embedded equality. Notebook would fail importing the new helpers. Conditional rerun readiness is withdrawn until Part A rebuild/equality/import smoke checks pass. MP-FC-006R prompt now explicitly requires repair before any authorized push.



## 19. Bounded Corrected Baseline Rerun Execution Record (MP-FC-006R)

**Document Reference:** `MP-FC-006R`
**Date:** `2026-11-12` (Asia/Kolkata)
**Execution Environment:** Kaggle CPU, Internet Off, Private, Single Execution
**Dataset Input:** Existing private dataset `theankitchoubey/mandi-prediction-audit-003b` (v1)
**Kernel ID & Version:** `theankitchoubey/mp-fc-006-baselines` (Version 4)
**Kernel Execution Status:** `KernelWorkerStatus.COMPLETE`
**Execution Runtime:** 149.04 seconds
**Audit Baseline Commit:** `078ab38b5872615f30647f8ef4dba37f06fcb0c3`
**Audit Status:** **AUDITED BASELINE RERUN COMPLETE & VERIFIED**

### 19.1 Preflight Verification & Embedded Payload Repair
In accordance with Part A preflight gating, the stale embedded source payload was repaired:
- Rebuilt `src/baselines.py` embedded payload from working source (44,845 bytes, SHA-256: `9cf56e5345235bc593f3bdf62df90e39a56be794edfb5e36fed1b94588c20718`).
- Byte equality confirmed: 100% byte-for-byte identity between decoded payloads and working tree modules (`src/market_identity.py`, `src/data_pipeline.py`, `src/ingest_agmarknet_arrivals.py`, `src/baselines.py`, `data/reference/market_aliases.csv`, `experiments/outputs/005/diff_77_deep_analysis.csv`).
- Symbol import verified: All 9 production scoring and eligibility helpers confirmed present and importable.
- AST syntax parsed: 100% syntax success across all 5 notebook code cells.
- Isolated bootstrap smoke test: Subprocess test in clean temporary sandbox passed without errors.
- Full local test suite: 175 tests collected and passed in 4.76s.

### 19.2 Fail-Closed In-Kernel Gate Receipts
1. **Panel v2 Conservation & SHA-256 Gate:**
   - Raw 5-year rows: 472,385 $\rightarrow$ Accepted rows: 463,217.
   - SHA-256: `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` (exact match to master gate).
2. **Canonical Disputed Keys Audit:**
   - Exactly 77 unique canonical 6-tuples loaded via accepted alias table. Archived in `canonical_disputed_keys_audit.csv` (SHA-256: `73b77067650601ae9bacf1ce7bddc6eb16aea350a08297628a66df6cbf759fa6`).
3. **Full Prediction Archive:**
   - Exported `baseline_predictions_all_folds.csv` (23,655,431 bytes, 64,777 lines, SHA-256: `c44ff42506f6af9e627635c8a80203d1ead30bc5d2a8559fc7a9a17f13af7ff9`).
   - Retained `baseline_predictions_sample.csv` (1,864,963 bytes, 5,001 lines) for backward compatibility.
4. **Test Window Observation Accounting:**
   - Total raw test window observations: 71,626.
   - Dropped serving recency $<3$: 317.
   - Dropped missing target in window: 3,624.
   - Dropped target after fold end: 2,909.
   - Evaluated Tier A test origins: $71,626 - 317 - 3,624 - 2,909 = 64,776$.

### 19.3 Verified Baseline Scorecard Results (Tier A)

Metrics evaluated on joint finite predictions with ratio-of-means cluster bootstrap 95% confidence intervals (1,000 resamples over unique series, seed 42).

#### Overall Tier A Summary ($N_{\text{origins}} = 64,776$, $N_{\text{series}} = 401$):
- **Naive Benchmark:**
  - $N_{\text{scored}} = 64,776$, Abstention: 0.00%.
  - MAE: **106.9554 Rs/qtl** (95% CI: $[95.4708, 119.0189]$).
  - Paired Naive MAE: 106.9554 Rs/qtl. Skill vs Naive: 0.0000.
  - RMSE: 298.8337, MAPE: 4.16%, Median AE: 40.00, Bias: +17.1728, Share $\le 5\%$: 76.76%.
- **Moving Average (30d window, $\le 7$ obs):**
  - $N_{\text{scored}} = 64,776$, Abstention: 0.00%.
  - MAE: **134.1925 Rs/qtl** (95% CI: $[119.6715, 149.9628]$).
  - Paired Naive MAE: 106.9554 Rs/qtl. Skill vs Naive: **-0.2547** (95% CI: $[-0.2904, -0.2103]$).
  - RMSE: 333.3659, MAPE: 5.08%, Median AE: 50.71, Bias: +26.3044, Share $\le 5\%$: 70.98%.
- **Seasonal Naive (357d lag, $\pm 3$d window):**
  - $N_{\text{scored}} = 59,200$, Abstention: 8.61% (5,576 unscored origins).
  - MAE: **774.3764 Rs/qtl** (95% CI: $[667.7389, 890.8767]$).
  - Paired Naive MAE: 105.0167 Rs/qtl. Skill vs Naive: **-6.3738** (95% CI: $[-7.3355, -5.4701]$).
  - RMSE: 1433.7629, MAPE: 29.45%, Median AE: 375.00, Bias: +351.6901, Share $\le 5\%$: 22.70%.
- **Damped Drift (14d lag, $\pm 3$d window, factor 0.5):**
  - $N_{\text{scored}} = 64,036$, Abstention: 1.14% (740 unscored origins).
  - MAE: **107.3248 Rs/qtl** (95% CI: $[96.3202, 119.3452]$).
  - Paired Naive MAE: 106.5998 Rs/qtl. Skill vs Naive: **-0.0068** (95% CI: $[-0.0309, +0.0176]$).
  - RMSE: 303.6659, MAPE: 4.29%, Median AE: 42.00, Bias: +7.8091, Share $\le 5\%$: 76.55%.

#### Tier A Fold Origin Distribution:
- **Fold F1 (Train $\le$ 2024-12-31):** $N = 37,858$ origins across 359 series. Naive MAE $= 101.59$ (95% CI: $[89.65, 115.40]$).
- **Fold F2 (Train $\le$ 2025-06-30):** $N = 23,490$ origins across 346 series. Naive MAE $= 106.46$ (95% CI: $[93.67, 120.38]$).
- **Fold F3 (Train $\le$ 2025-12-18):** $N = 1,413$ origins across 102 series. Naive MAE $= 108.11$ (95% CI: $[85.99, 131.60]$).
- **Fold F4 (Train $\le$ 2026-03-31):** $N = 2,015$ origins across 37 series. Naive MAE $= 212.84$ (95% CI: $[46.46, 459.71]$).
- **Sum Conservation:** $37,858 + 23,490 + 1,413 + 2,015 = 64,776$.

### 19.4 Volatile Subgroup & Paired Naive Arithmetic Reconciliation
For origins where the target price moves by $>2\%$ relative to origin price ($|y(t+7) - y(t)| / y(t) > 0.02$):
- **Eligible Origins:** $N = 27,858$.
- **Scored Instances:** Naive: 27,858; MA: 27,858; Seasonal Naive: 25,660; Drift: 27,451.
- **Drift Unscored Arithmetic:** Exactly $27,858 - 27,451 = 407$ unscored instances ($1.46098\% \approx 1.46\%$).
  *(The prior figure of 398 is superseded as an arithmetic typo. All 407 abstained due to missing anchor in $[t-17\text{d}, t-11\text{d}]$).*
- **Exact Paired Naive MAE:** On the 27,451 Drift-scored instances, Naive MAE is exactly **217.1854 Rs/qtl**.
  *(The prior reverse-engineered claim of 217.1723 is withdrawn and superseded by this verified value).*
- **Drift Performance on Volatile Moves:**
  - Drift MAE: **202.1012 Rs/qtl** (95% CI: $[182.15, 226.89]$).
  - Paired Skill: $\text{Skill} = 1 - (202.1012 / 217.1854) = +0.069453 \approx \mathbf{+0.0695}$ (95% CI: $[+0.0429, +0.0937]$, superseding legacy reported $[+0.0432, +0.0950]$).
- **Scorecard Rows & Undefined Skill Verification:** The three scorecard artifacts comprise $40$ (tier) $+ 120$ (focus-crop) $+ 80$ (sensitivities) $= 240$ rows. Exactly 224 rows have finite skill identities. Exactly 16 focus-crop rows have undefined (`NaN`) skill due to empty evaluation slices ($N_{\text{eligible\_origins}} = 0$; Fold F3 Paddy, Fold F4 Onion, Fold F4 Tomato, Fold F4 Paddy across Naive, MA, Seasonal, Drift). These rows are flagged `low_n_flag = True` and must remain undefined rather than coerced to zero.
- **Overall Drift Skill CI Verification:** Overall Tier A Drift skill vs Naive is $-0.0068$ with 95% bootstrap CI $[-0.0309, +0.0176]$ (superseding legacy reported $[-0.0303, +0.0191]$).

### 19.5 Scope B Sensitivity Forensic Accounting
Scope B excising was evaluated across all four models on counterfactual clean history $\mathcal{H}_{\text{clean}}(t)$:
- **Scope A Exclusions:** 18 origins excluded (10 disputed origin, 10 disputed target, 2 having both).
- **Clean Recency Failures:** 2 origins in Fold F3 had $<3$ observations in $[t-30\text{d}, t]$ after excising the disputed observation.
- **Scope B Eligible Origins:** $64,776 - 18 - 2 = 64,756$.
- **Historical Observations Excised:** 610 origins had historical values removed (F3: 51, F4: 559).
- **Prediction Modifications:**
  - Moving Average: 13 finite price changes (F3: 12, F4: 1).
  - Damped Drift: 8 finite price changes (F3: 6, F4: 2) and **1 finite-to-NaN transition** in Fold F3 (excised observation was the sole drift anchor).
  - Seasonal Naive: 0 changes (lag is $t-357$ days in 2025; disputed discrepancies occurred in Feb–Mar 2026).
- **Scope B Overall MAE:** Naive: 106.90, MA: 134.18, Seasonal: 774.47, Drift: 107.25.

### 19.6 Methodological Decisions & Limitations
1. **Bootstrap Uncertainty Interpretation:** Confidence intervals on MAE represent cluster-bootstrap estimator sampling distributions over unique series identities; they are **NOT** forecast prediction intervals.
2. **Deterministic Reproducibility:** Unique series clusters are sorted lexicographically prior to index sampling; seed 42 ensures exact numerical reproducibility across runs.
3. **Panel Status:** Panel v2 remains **PROVISIONAL**. Market alias evidence and lookahead considerations remain OPEN pending Task 2 (`MP-DATA-007`).
4. **Data Freshness Safety Gate:** Operational farmer advisory remains blocked by `src/health_status.py` due to 43-day data lag (latest date `2026-09-30`).
5. **No ML Approval:** Completion of baseline benchmarking does not authorize training machine learning models or live advisory deployments.
6. **MASE:** Conventional MASE is unimplemented in the baseline scoring engine and is designated **NOT COMPUTED**.



## Independent FC006R decision — 2026-11-12 IST
Accept corrected FC006R as a retrospective benchmark for Step 2 only. Remote commit b4861ee6441ae492483157d47ec8c3431d3a3fb1 verified; four embedded modules match; 16 small hashes passed; 224 finite skill identities reconciled, 16 undefined; 23 targeted tests passed in 0.30s. Scope A excludes 18; Scope B excludes 20 total, with actual prediction changes. Full large panel/archive not independently recomputed; 175 full-suite passes executor-reported. Current overall drift skill CI [-0.0309,0.0176] and volatile CI [0.0429,0.0937] supersede legacy CIs in current prose. Detailed evidence/limitations: documentation/FC006R_REVIEW.md. Next: documentation/prompts/MP-DATA-007.md, local identity policy and panel-freeze readiness, no remote run authorized. Panel PROVISIONAL, no ML/live approval.



## 20. Market Identity Candidate Policy & Freeze Readiness (MP-DATA-007)

**Document Reference:** `MP-DATA-007`
**Date:** `2026-11-12` (Asia/Kolkata)
**Execution Environment:** Local Analysis Only (Rules: $\le 10$ MB/file, $\le 50,000$ rows, $\le 30$s compute)
**Status:** **DATA POLICY PREPARED / PANEL FREEZE PENDING EXECUTION**

### 20.1 Purpose & Execution Boundaries
1. **Retrospective Benchmark Accepted:** FC006R is accepted as an immutable retrospective reference. Panel v2 hash `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` is maintained as the baseline replication anchor.
2. **Local Bounded Preparation:** This task performs local forensic reconciliation and prepares a candidate identity policy (`src/market_identity.py`, `data/reference/market_alias_candidates_v21.csv`). Zero remote Kaggle runs were performed, zero datasets uploaded, zero ML models trained, and **no panel freeze is declared without remote execution evidence**.

### 20.2 Market Identity Adjudications
Based on the 24 evaluated transitions from `alias_transition_forensics.csv`:
- **19 Standard APMC Migrations:** Early November 2025 transitions (gap $-4\text{d}$ to $-1\text{d}$, overlap $2\text{d}$ to $4\text{d}$) exhibit **100.0% exact modal price match** across all overlapping keys ($N = 5$ to $103$ keys). Confirmed **ACCEPTED** under Candidate Rule A.
- **Jhansi Grain Variants (Jhansi):** The 59-day gap between `Jhansi Grain APMC` and historical pre-APMC `Jhansi (Grain)` is reconciled via **transitive concordance with `Jhansi (Grain) APMC`** (co-existed 2026-01-01..14 with 23 keys, **100.0% exact price match**). Status: **ACCEPTED** under Candidate Rule B (transitive concordance).
- **Purwa (Unnao):** Historical `Purwa` ceased 2025-07-31; modern `Purwa APMC` commenced 2026-02-21 (**205-day hiatus**, 0 overlap days, 0 keys). Fails Candidate Rule A ($205\text{d} > 14\text{d}$ limit) and Rule B ($N=0$). Reclassified to **UNMAPPED/REVIEW** in candidate v2.1. Physical market yard identity is plausible, but empirical transition concordance is unverified.
- **Baripaal APMC vs Varipaal (Kanpur):** Co-existed for 52 calendar days (2026-03-01..04-26) with 462 keys; 442 matched (95.67%), but **20 keys had conflicting prices**, accompanied by normalized base token mismatch (`baripaal` vs `varipaal`). Status: **UNMAPPED/REVIEW**; retained as distinct canonical market `Baripaal APMC` to prevent artificial conflict injection.

### 20.3 Candidate Policy v2.1 Mathematical & Structural Gates
Implemented pure functions in `src/market_identity.py`:
- `evaluate_alias_evidence_v21()`:
  - Enforces `abs(gap_days) <= max_migration_gap_days` (default 14d) and `overlap_days <= max_migration_overlap_days` (default 7d) for Candidate Rule A.
  - Enforces `min_concordance_keys >= 5` and `min_price_agreement >= 0.95` for Candidate Rule B.
  - Rejects missing fields, different districts, and normalized token mismatches.
- `validate_alias_table()`:
  - Rejects inverted date ranges ($t_{\text{first}} > t_{\text{last}}$).
  - Rejects conflicting duplicate mappings (same raw market mapped to multiple canonical targets with status ACCEPTED).
  - Detects cyclic mappings ($A \rightarrow B$ and $B \rightarrow A$).
- `build_causal_alias_mapping()`:
  - Filters active aliases strictly by $t_{\text{evidence\_known}} \le T_{\text{cutoff}}$, preventing lookahead bias in historical forecasting folds.

### 20.4 Unmatched Excel Reclassification & Stage Conservation
The 1,895 unmatched Excel rows from FC006R reconcile exactly across pipeline ingestion stages:
$$\text{Total} = 923 (\text{low-obs}) + 420 (\text{other}) + 323 (\text{quarantine}) + 197 (\text{absent}) + 32 (\text{spelling}) = 1,895$$
- `low_obs_dropped` (923): Pipeline filter pruned series with $<20$ full-history observations.
- `quarantined_strategy2` (323): Multi-modal conflicting price records quarantined; denotes conflicting observations, not invalid rows.
- `other` (420): Residual matching failures (Kanpur 379, Jhansi 20, Lucknow 19, Ghaziabad 1, Unnao 1) designated **PENDING REMOTE CHECK**.

### 20.5 Causal Sensitivity (<20 Floor vs >=60 Train Eligibility)
- **Mathematical Invariant (Fixed Identity):** $N_{\text{full}} \ge N_{\text{train}}$ holds strictly for every series when market identity and cleaning policies are held fixed, because training records are a mathematical subset of full-history records. Therefore, holding identity fixed, the $<20$ full-history floor cannot prune any series that independently satisfies the $\ge 60$ training threshold.
- **Correction on Historical Alias Effect:** The initial claim that aliases cannot alter counts before `2025-12-18` is **retracted**. November 2025 chronologically precedes December 18, 2025, and in `MP-FC-006R`, alias canonicalization added $+2,355$ net training rows to Tier A at Fold F3 (`384,887` $\rightarrow$ `387,242`). In strict fail-closed causal mode (`evidence_mode="verified"`), absent dated publication receipts, nonidentity merges are strictly withheld as of historical cutoffs (yielding zero verified historical merges prior to present adjudication). Assumed observation handover timings (`2025-11-05`) are evaluated strictly as an explicit sensitivity analysis (`evidence_mode="assumed"`).

### 20.6 Prepared Remote Kernel Execution Request
- Prepared notebook: `experiments/notebooks/mp_data_007_identity_review.ipynb`
- Metadata: `experiments/kaggle/007/kernel-metadata.json`
- Invariant Gate 1: Panel v2 SHA-256 == `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` (fail-closed).
- Expected outputs: `identity_comparison_v2_vs_v21.csv`, `excel_unmatched_reclassification_v21.json`, `manifest_v21.json`.
- Status: **Awaiting explicit owner approval; zero self-approval.**


## MP-DATA-007 independent review — 2026-11-12 IST
Commit 4cef31a1c4658b0a45504deda9b276e5771736fa remotely verified; 24 targeted identity tests passed in 0.50s. Full 189-pass receipt reported only. CHANGES REQUIRED: notebook hardcodes legacy unmatched counts as v21 results and lacks requested causal reconstruction; missing knowledge date falls back to first observation; malformed alias dates pass validation (both independently reproduced). Candidate historical evidence_known_date entries lack historical provenance; false F3 no-alias-effect narrative contradicted by prior +2355 rows. Gap/range/shared-day definitions and hypothesis wording need repair. documentation/context.md modified again contrary to instruction. Two EOF-only working edits preserved. See documentation/DATA007_REVIEW.md. Next local-only prompt documentation/prompts/MP-DATA-007B.md. No Kaggle execution/panel freeze/ML authorization.


---

## 21. Section 21: MP-DATA-007B Mathematical Validation & Gate Repair

### 21.1 Definitions and Count Separations
- **Inclusive Calendar Date-Range Overlap:** $\max(0, (\min(ld_1, ld_2) - \max(fd_1, fd_2)).\text{days} + 1)$. For Jhansi Grain APMC (2026-01-01 to 2026-01-14) vs Jhansi (Grain) APMC (2025-11-02 to 2026-01-14), the inclusive range overlap is exactly **14 calendar days**.
- **Shared Observation Dates:** The count of unique calendar dates on which quotes actually appeared in both series feeds. For Jhansi Grain APMC and Jhansi (Grain) APMC, this count is exactly **10 dates**.
- **Overlapping Natural Keys:** Unique tuples of `(Arrival_Date, Commodity, Variety, Grade)`. Evaluated as unique natural keys; duplicate many-to-many joined rows are deduplicated prior to sample size evaluation ($N_{\text{unique}} \ge 5$).
- **Modal Price Agreement:** Proportion of unique natural keys where modal prices match exactly: $\frac{\sum \mathbf{1}(p_1 = p_2)}{N_{\text{unique}}}$. Certified for modal prices only, not full quotes.
- **Candidate Policy Limits as Assumptions:** The 14-day migration hiatus limit, 7-day migration overlap limit, 5 unique keys minimum, and 95% modal concordance threshold are declared engineering assumptions subject to sensitivity analysis, not empirical physical laws.

### 21.2 Fail-Closed Identity and Manifest Gates
- **Defensive Table Validation (`validate_alias_table`):**
  - Schema conformity to `MARKET_ALIAS_COLUMNS`.
  - Non-null/non-empty identity fields (`district`, `market_raw`, `market_canonical`, `status`), strictly rejecting pandas `NaN`, `None`, `""`, and string representations `"nan"`, `"none"`, `"null"`.
  - Strict date parsing across all date columns (`first_date`, `last_date`, `evidence_known_date`, `assumed_known_date`), failing closed on malformed strings (`"not-a-date"`) or NaT values.
  - Inverted date range detection: $fd \le ld$.
  - Detection of conflicting duplicate mappings under `status == 'ACCEPTED'`.
  - Detection of nonterminal mapping chains ($A \rightarrow B$ and $B \rightarrow C$ where $A \ne B$ and $B \ne C$) and multi-hop cycles.
- **Nested Manifest Dispositions (`extract_manifest_dispositions`):**
  - Parses `manifest["summary_metrics"]` directly without literal fallback constants.
  - Strictly asserts row conservation:
    $$\text{accepted\_rows} + \text{duplicates} + \text{conflicts} + \text{low\_obs} + \text{invalid\_dropped} = \text{total\_raw\_rows}$$
    $$463,217 + 855 + 2,936 + 5,350 + 27 = 472,385$$
  - Raises `KeyError` on missing schema fields; raises `ValueError` on conservation violation.

### 21.3 Pre-Floor Causal Sensitivity & Future Mutation Invariance
- **Causal Sensitivity Formulation (`evaluate_causal_train_eligibility_sensitivity`):**
  - Reconstructs training series identities BEFORE the $<20$ full-history filter across cutoffs F1 (`2024-12-31`), F2 (`2025-06-30`), F3 (`2025-12-18`), and F4 (`2026-03-31`).
  - Evaluates in `verified` mode (missing gazette receipts withhold nonidentity merges, yielding 0 historical merges) and `assumed` mode (evaluating sensitivity to assumed Nov 2025 APMC handover dates).
  - Asserts that holding identity and cleaning fixed, $N_{\text{full}} \ge N_{\text{train}}$ holds across all series.
- **Future Mutation Invariance (`verify_future_mutation_invariance`):**
  - Mutates observations dated strictly after `cutoff_date` (corrupting prices, changing names, injecting synthetic future rows).
  - Asserts that training series keys, observation counts, and Tier A eligibility sets as of `cutoff_date` are bit-for-bit invariant ($I_{\text{mut}} = I_{\text{base}}$).

### 21.4 Verification & Test Receipts
- `tests/test_identity_policy_v21.py`: **19 passed in 0.19s**
- `tests/test_identity_comparison.py`: **8 passed in 0.17s**
- `tests/test_market_identity.py`: **12 passed in 0.16s**
- Entire test suite: **204 passed in 4.69s**, exit code 0.
- Bit-level byte equality verified across all 7 embedded payloads in `experiments/notebooks/mp_data_007_identity_review.ipynb`.
- Isolated miniature end-to-end smoke test executed and passed in temporary workspace.
- **Panel v2 Status:** **PROVISIONAL** (reproduction hash `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`).
- **Authorization Note:** Zero remote compute executed; zero ML trained; zero panel freeze declared.


## MP-DATA-007B review and tonight priority — 2026-11-12 IST
Owner wants same quality with faster completion tonight, clear achieved/open/next after every report, and detailed prompts reducing repair cycles. Treat this as delivery priority, not authorization to fabricate evidence or skip checks; prospective field outcomes cannot be obtained before they occur. Batch reusable checks and final full-suite validation, focus integrated Release 1 plus labelled scenario economics. No claim all 13 packages+optional experiments will be validated tonight.
Commit a78f4a0995aabeb02d2510c35054e16e930d1fc4 remotely verified; independent 39 targeted tests passed in 0.67s. Full 204-pass receipt reported only. Partial repairs accepted, actual run not ready: classifier strips APMC and falsely matches reviewed Purwa names; TierA helper omits 30% coverage; notebook June cutoff/partial Excel discovery and absent disposition inputs; cutoff helper fed already-pruned panel; aggregate-only mutation checks. Independent small fixtures reproduced false Purwa match and sparse series erroneously accepted. See documentation/DATA007B_REVIEW.md.
Next prompt documentation/prompts/MP-DATA-007R.md combines exact repair tests with ONE conditional remote run requiring explicit owner approval. Preserve pre-existing EOF-only source/test edits and documentation/context.md untouched. Panel provisional, no ML/live approval.


## 22. MP-DATA-007R Remote Run & Mathematical Verification Record — 2026-11-12 IST

### 22.1 Execution Envelope & Preflight
- **Task ID:** `MP-DATA-007R`
- **Authorized Execution:** Exactly ONE remote kernel run on existing dataset `theankitchoubey/mandi-prediction-audit-003b` (v1).
- **Kernel ID:** `theankitchoubey/mp-data-007-identity-review` (Version 1)
- **Status:** `KernelWorkerStatus.COMPLETE` (Runtime: 1,017.4s / ~16.9 min)
- **Preflight Diff Hash:** `9ae433496515f421caa36f57b42084affbcbe7793b0f9030d812d369531581b7`
- **Unit Test Receipts:** 215 tests passed in 4.45s (including 19 targeted identity comparison and reconstruction tests).
- **Decoded Payload Equality:** All 7 embedded modules verified bit-for-bit identical to working files.

### 22.2 Mathematical Panel v2 Gate & Row Conservation
- **Panel v2 Computed SHA-256:** `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` (**EXACT MATCH**)
- **Gate 1 Status:** **PASSED** (fail-closed check confirmed).
- **Row Conservation Identity:**
  $$\text{Raw In (472,385)} = \text{Accepted (463,217)} + \text{Dups (855)} + \text{Conflicts (2,936)} + \text{Low-Obs (5,350)} + \text{Invalid (27)}$$
  $$463,217 + 855 + 2,936 + 5,350 + 27 = 472,385 \quad (\text{Strictly Verified})$$

### 22.3 Candidate Panel v2.1 Metrics & Dispositions
- **Candidate Panel v2.1 Computed SHA-256:** `a299536914b5683613f7a0aa242e447f832a33894a476d73401e49fa24449c14`
- **Candidate Panel Status:** **PROVISIONAL** (unapproved for final freeze).
- **Dispositions:** Identical row counts to v2 (463,217 accepted rows across 472,385 raw in).
- **Unique Series:** 1,170 series (+3 series in Unnao: 165 $\to$ 168) due to withholding unverified `Purwa APMC` $\to$ `Purwa` merge.

### 22.4 In-Window Excel Dispositions (14,741 Rows $\le$ 2026-09-30)
- Total Ingested Excel Rows: `16,030` across 5 official Agmarknet report files.
- In-Window Observations: `14,741` rows.
- Strict Category Conservation ($14,741 = 12,769 + 77 + 326 + 920 + 325 + 324$):
  - `matched_exact`: **12,769 rows** (86.62%) — modal difference = 0.00.
  - `matched_different`: **77 rows** (0.52%) — exactly the 77 disputed Feb–Mar 2026 rows.
  - `conflicting`: **326 rows** (2.21%) — quarantined under Strategy 2.
  - `low_obs`: **920 rows** (6.24%) — dropped due to series $< 20$ records.
  - `absent`: **325 rows** (2.20%) — market recognized, but natural key absent from daily feed.
  - `spelling-review`: **324 rows** (2.20%) — isolated from review markets (`Purwa APMC`: 4, `Varipaal`: 320).
  - `invalid`: **0 rows** (0.00%).
  - `other`: **0 rows** (0.00%).

### 22.5 Causal Cutoff Reconstruction & Invariance Verification
- Reconstructed folds F1, F2, F3, F4 from pre-canonicalization cleaned raw arrivals (`472,358` rows).
- Applied Tier A ($\ge 60$ obs and coverage $\ge 0.30$) and Tier B ($\ge 120$ obs and coverage $\ge 0.30$).
- Evaluated verified, assumed, and retrospective modes:
  - F1 (2024-12-31): active aliases = 21, train obs = 340,032, Tier A series = 451, Tier B series = 438, subset violations = 0.
  - F2 (2025-06-30): active aliases = 21, train obs = 392,708, Tier A series = 487, Tier B series = 451, subset violations = 0.
  - F3 (2025-12-18): active aliases = 21 (verified) / 40 (assumed) / 41 (retrospective), subset violations = 0.
  - F4 (2026-03-31): active aliases = 21 (verified) / 41 (assumed) / 41 (retrospective), subset violations = 0.
- Mathematical subset invariant strictly holds ($N_{\text{train}} \ge 60 \implies N_{\text{full}} \ge 20$, 0 violations).
- Future mutation invariance test strictly holds under value corruptions and adversarial conflicting quotes.
