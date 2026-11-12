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

| Evaluation Date | Kaggle Run ID | Model Name | Dataset Version | Horizon | MAE (₹/q) | RMSE (₹/q) | WAPE (%) | MASE | Skill vs. Naive | Directional Acc (%) | 90% Coverage (%) | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| *None* | *None* | *None* | *None* | *None* | *None* | *None* | *None* | *None* | *None* | *None* | *None* | *Awaiting Run* |

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

## 13. Evidence-Based Market Identity, Panel v2, and Regime Diagnostics (Task MP-DATA-006)

* **Execution Date:** 2026-11-12
* **Execution Environment:** Kaggle CPU Kernel (`theankitchoubey/mp-data-006-panel-v2`, version 3, internet disabled).
* **Evaluated Dataset:** `theankitchoubey/mandi-prediction-audit-003b` (v1 private, unchanged).
* **Execution Status:** Complete (`KernelWorkerStatus.COMPLETE`, exit code 0).
* **Detailed Task Report:** [mp_data_006_summary.md](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/experiments/reports/mp_data_006_summary.md).

### 13.1 Market Inventory & Suffix Prevalence
Across the 472,385 raw historical records, exactly 42 distinct raw market strings were cataloged across the 5 target districts (Ghaziabad: 8, Jhansi: 15, Kanpur: 9, Lucknow: 4, Unnao: 6). In the recent external snapshot (`9ef84268-...csv`, 2026-11-11), **14 of 14 target district markets (100.0%)** carry the `" APMC"` suffix, confirming that Agmarknet 2.0 systematically renamed reporting mandis.

### 13.2 Evidence Rule Adjudication
To prevent ungrounded fuzzy merging, market aliases were evaluated under the strict Evidence Rule:
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

### 13.4 Re-evaluation of Corroboration on Panel v2
* **Agmarknet Daily Excel Corroboration (14,741 in-window rows):** Matched 12,846 rows (87.14%); **12,769 exact modal price matches (99.40%)**; exactly **77 non-zero price differences (0.60%)**.
* **CEDA Price Data Corroboration (594 rows, Lucknow Wheat):** Matched 591 rows (99.49%); **591 exact modal price matches (100.00% concordance)**; 3 unmatched rows confirmed quarantined under Strategy 2.

### 13.5 Rejection of Calendar Lag on 77 Differences
Evaluating all 77 discrepancies across moving calendar shifts $k \in \{-3, -2, -1, 0, 1, 2, 3\}$ days yielded **0 of 77 matches (0.00%)**, demonstrating that the Feb–Mar 2026 discrepancies are not reporting lags or timestamp offsets.

### 13.6 Monthly Regime Diagnostics (61 Months: 2021-09 to 2026-09)
* **Historical Regime (2021-09 to 2025-10, 50 mos):** Mean 8,452.4 rows/mo; **0.00% APMC suffix**; **0.00% fractional prices**.
* **Transition Regime (2025-11 to 2026-02, 4 mos):** Mean 2,249.5 rows/mo; **93.34% APMC suffix**; **4.14% fractional prices**. Marked by Agmarknet 2.0 go-live (`2025-11-07`).
* **Fractional Modern Regime (2026-03 to 2026-09, 7 mos):** Mean 4,514.4 rows/mo; **100.00% APMC suffix**; **40.89% fractional prices**. Marked by UP 251 mandis integration (`2026-09-29`).

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






