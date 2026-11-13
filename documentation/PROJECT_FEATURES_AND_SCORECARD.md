# APMC Mandi Intelligence System: Full Feature Inventory and Audited Scorecard

**Review Date:** 13 November 2026 IST
**Codebase Commit:** `6af1dbc026259993326344f4d981ccb9b6a3bad5` (MP-UI-002 baseline) $\to$ `MP-FINAL-013`
**System Nature:** Agricultural Price Research Instrument & Prospective Validation Framework
**Operational Status:** Retrospective Research Validated • Prospective Shadow Logging Engineered • Live Advisory Strictly Blocked

---

## 1. Full Inventory of Implemented Capabilities

### 1.1 Ingestion, Data Integrity & Identity Governance
- **Dataset-First Ingestion:** Ingestion pipelines for official Agmarknet arrival and price bulletin data (supporting both `.csv` and official `.xlsx` formats) with row budget guards ($\le 50,000$ rows) and file size limits ($\le 10$ MB).
- **Exact 5-Tuple Identity:** Strict series tracking via `(District, Market, Commodity, Variety, Grade)`.
- **Identity Segregation & Market Alias Governance:** Segregated handling for unapproved market identities (e.g. Kanpur Baripaal APMC) via `market_alias_status = UNKNOWN_MARKET_REVIEW`. Modal prices are strictly withheld on all review series.
- **Crop Disambiguation:** Complete segregation of botanical and trade identities; `Paddy(Common)` and `Rice` remain distinct series and are never heuristically merged.
- **Target Geographic & Focus Crop Scope:** Five target districts in Uttar Pradesh (`Ghaziabad`, `Jhansi`, `Kanpur`, `Lucknow`, `Unnao`) across six declared focus crops (`Wheat`, `Potato`, `Onion`, `Tomato`, `Paddy(Common)`, `Rice`).
- **Cryptographic Provenance:** SHA-256 digests tracked for both raw composite source files (`3d3bc047...`) and loaded snapshot indices (`45c9dd75...`).

### 1.2 Retrospective Forecasting Benchmark Architecture
- **Chronological Split Architecture:** 4 expanding chronological evaluation folds (F1–F4) spanning 64,776 point forecast origins across 401 series from a 463,217-row validated panel.
- **Strict Anti-Leakage Feature Pipeline:** Point features constructed strictly using causal historical lag windows and calendar features. No backward filling, no future target contamination.
- **Six Evaluated Benchmark Methods:**
  1. *Naive Persistence:* $\hat{P}_{t+7} = P_t$ (Primary benchmark reference standard).
  2. *Moving Average (7-Day Rolling Mean):* Smooths high-frequency variance; underperforms on trend reversals.
  3. *Seasonal Naive (365-Day Lag):* Evaluates annual agricultural cycles; suffers from high missingness and severe shock penalties.
  4. *Linear Drift:* Extrapolates short-term rate of change; vulnerable to rapid mean-reverting price swings.
  5. *Ridge Regression (L2 Regularized Linear Model):* Tests regularized linear combinations of lag and calendar features.
  6. *Histogram Gradient Boosting (HGB):* Tests nonlinear tabular interactions and threshold splits.
- **Empirical Residual Prediction Intervals:** Chronologically calibrated prediction intervals at nominal 90% and 95% levels using matured out-of-sample residuals from earlier folds. Includes mandatory first-fold abstention (Fold F1 uncalibrated).

### 1.3 Cost-Aware Research Economics Engine
- **Canonical Algebraic Formulations:**
  $$R_{\text{sell}} = Q \times (P_0 - t_n)$$
  $$R_{\text{hold}} = Q \times \left[(1 - L)((1 - d)P_H - t_l) - c - P_0 f\right]$$
  $$\Delta R = R_{\text{hold}} - R_{\text{sell}}$$
  $$P^* = \frac{P_0(1+f) + c + (1-L)t_l - t_n}{(1-L)(1-d)}$$
  Where $c = c_{\text{storage}} + c_{\text{handling}} + c_{\text{trans}}$, $f = \frac{r \cdot T}{365}$ for linear carrying cost (financing or opportunity), $L$ is quantity loss fraction, and $d$ is quality markdown.
- **10-Step Arithmetic Waterfall Decomposition:** Full server-side breakdown from Gross Spot Value through Net Incremental Benefit, preserving missing-vs-zero semantics.
- **Monotonic Affine Uncertainty Propagation:** Propagates lower/point/upper price bounds monotonically to holding benefit bounds.
- **Fail-Closed Advisory Gating:** System returns `RESEARCH_ONLY` with `ADVICE_BLOCKED` across all execution paths.

### 1.4 Web Serving Architecture & Research Interface
- **Zero-Dependency Runtime:** Pure standard-library Python HTTP service (`src/service.py`, `src/api.py`, `src/run_release_service.py`) verified under `python3 -S`.
- **Editorial Field Notebook Interface:** Pure vanilla HTML5/CSS3/ES6+ client (120.98 KB payload, 0 external npm/CDN dependencies) featuring accessible zero-origin bar charts, fold uncertainty graphics, and print stylesheets.
- **Truth-Preserving Observation & Price Movement:** Displays official Agmarknet modal price and freshness computed in India Standard Time calendar days. Price movement strictly displays `Price change unavailable — a second verified observation is required` when only a single dated observation exists.

### 1.5 Step 13 Prospective Shadow Validation CLI
- **Protocol APMC-PV-2026-V1:** Versioned configuration (`experiments/configs/forward_validation_protocol_v1.json`) freezing evaluation criteria before collecting future outcomes.
- **Pure Standard-Library CLI (`src/prospective_shadow.py`):**
  - `init`: Freezes and initializes local append-only shadow registry.
  - `validate-snapshot`: Enforces $\le 10$ MB, $\le 50,000$ row budgets and schema integrity.
  - `issue`: Generates forward persistence shadow records with local SHA-256 hash chaining and strict freshness gating ($\le 1$ day).
  - `import-outcomes`: Logs verified future market outcomes.
  - `match`: Matches forecasts against $T+7$ outcomes with $T+6$ to $T+8$ tie-breaking rules, finalizing only after window closes.
  - `scorecard`: Computes out-of-sample forward MAE, RMSE, Bias, MAPE, and Within 5% tolerance rates.

---

## 2. Audited Retrospective Benchmark Results

### 2.1 Point Forecast Performance (64,776 Evaluated Origins, F1–F4 Folds)
*Source: `experiments/reports/FC007_VERIFIED/scorecard_overall.csv`*

| Method | Evaluated Origins | Primary MAE (INR/q) | Secondary RMSE (INR/q) | MAPE (%) | Within 5% Tolerance (%) | Primary Selection Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Naive Persistence** | 64,776 | **106.96** | 298.83 | 4.16% | **76.76%** | **Primary MAE Reference Winner** |
| **Drift** | 64,036 | 107.32 | 303.67 | 4.29% | 76.55% | Baseline Challenger (+0.34% MAE) |
| **HistGradientBoosting** | 64,776 | 109.75 | **281.16** | 4.52% | 73.97% | Secondary RMSE Winner (5.91% RMSE Reduction, +2.61% MAE) |
| **Ridge Regression** | 64,776 | 110.32 | 288.56 | 4.40% | 75.44% | Linear Challenger (+3.15% MAE) |
| **Moving Average (7d)** | 64,776 | 134.19 | 333.37 | 5.08% | 70.98% | Lags Fast Volatility (+25.46% MAE) |
| **Seasonal Naive (365d)** | 59,200 | 774.38 | 1,433.76 | 29.45% | 22.70% | Severe Annual Shift Penalty (+624.0% MAE) |

#### Statistical Interpretation
1. **Model Selection Hierarchy:** Naive Persistence is the primary benchmark winner on the declared primary loss function (Mean Absolute Error).
2. **RMSE Reduction vs. MAE Degradation:** HistGradientBoosting achieves a 5.91% lower RMSE (281.16 vs. 298.83 INR/q) because its tree splits penalize extreme tail errors under quadratic loss. However, its absolute error (MAE 109.75 INR/q) remains 2.61% worse than persistence. It does not establish an outlier mechanism.
3. **Tolerance Rate vs. "Accuracy":** 76.76% of persistence forecasts fall within $\pm 5\%$ of the realized market price. This is a specific tolerance statistic, **not** general continuous accuracy. The statement "Accuracy = 100 - MAPE = 95.84%" is mathematically false and rejected.
4. **Regression vs. Classification:** Modal price forecasting is a continuous regression problem. Classification metrics (confusion matrix, precision, recall, F1, ROC-AUC) do not apply directly to continuous price prediction. A directional up/flat/down diagnostic is an optional future capability requiring frozen thresholds and paired dated outcomes; no such classifier is currently established.

---

### 2.2 Retrospective Uncertainty & Prediction Interval Results (26,918 Origins, F2–F4 Folds)
*Source: `experiments/reports/FC008/intervals_overall.csv` and `intervals_by_fold.csv`*

| Evaluation Cohort | Nominal Target | Issued Origins | Realized Coverage | Mean Width (INR/q) | Median Width (INR/q) | Disposition / Finding |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Overall (F2–F4 Pooled)** | **90%** | 26,918 | **89.95%** | 662.65 | 457.78 | Near nominal target; F2-dominated |
| **Overall (F2–F4 Pooled)** | **95%** | 26,918 | **94.38%** | 977.14 | 684.21 | Near nominal target; F2-dominated |
| **Fold F1** | 90% | 0 | *Uncalibrated* | *Unavailable* | *Unavailable* | Explicit first-fold abstention (37,858 eligible) |
| **Fold F2** | 90% | 23,490 | **92.32%** | 718.54 | 500.00 | Conservative coverage (87.27% of issued pool) |
| **Fold F3** | 90% | 1,413 | **75.94%** | 379.93 | 246.70 | **Severe Undercoverage** (-14.06% deficit) |
| **Fold F4** | 90% | 2,015 | **72.26%** | 209.41 | 151.40 | **Severe Undercoverage** (-17.74% deficit) |

#### Uncertainty Findings & Limitations
1. **The Pooling Fallacy:** Near-target pooled coverage (89.95%) is an arithmetic artifact of Fold F2 supplying 87.27% of all evaluated observations.
2. **Regime Undercoverage:** In later folds (F3: 75.94%, F4: 72.26%), empirical coverage collapses severely due to non-stationary market dynamics and narrow residual calibration windows.
3. **No Future Guarantee:** Because residual distributions are non-exchangeable across time, retrospective calibration intervals cannot guarantee future coverage. Prediction intervals are logged as `UNAVAILABLE` for forward operations.

---

## 3. Audited Economic Fixtures and Controls

All figures verified against independent Decimal arithmetic and server component serialization:

| Test Case / Parameter Control | Gross Sell | Net Sell | Post-Storage Gross | Direct Cost | Carrying Cost | Net Hold | Gain ($\Delta R$) | Break-Even Price ($P^*$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Reference Fixture (+470 INR)**<br>$Q=10, P_0=2500, P_H=2650, L=0.02, c=50, t_n=0, t_l=0, \text{none}$ | ₹ 25,000.00 | ₹ 25,000.00 | ₹ 25,970.00 | ₹ 500.00 | ₹ 0.00 | ₹ 25,470.00 | **+ ₹ 470.00** | **₹ 2,602.04 / q** |
| **Financing Carrying Cost (7% Annual)**<br>$Q=10, P_0=2500, P_H=2650, L=0.02, c=50, t_n=0, t_l=0, \text{fin 7\%}$ | ₹ 25,000.00 | ₹ 25,000.00 | ₹ 25,970.00 | ₹ 500.00 | ₹ 33.56 | ₹ 25,436.44 | **+ ₹ 436.44** | **₹ 2,605.47 / q** |
| **Nonzero Transaction Fees**<br>$Q=10, P_0=2500, P_H=2650, L=0.02, c=50, t_n=10, t_l=20, \text{none}$ | ₹ 25,000.00 | ₹ 24,900.00 | ₹ 25,970.00 | ₹ 500.00 | ₹ 0.00 | ₹ 25,274.00 | **+ ₹ 374.00** | **₹ 2,611.84 / q** |
| **Price Range Bounds**<br>$P_H \in [2600, 2650, 2700], Q=10, P_0=2500, L=0.02, c=50$ | ₹ 25,000.00 | ₹ 25,000.00 | ₹ 25,480.00 /<br>₹ 25,970.00 /<br>₹ 26,460.00 | ₹ 500.00 | ₹ 0.00 | ₹ 24,980.00 /<br>₹ 25,470.00 /<br>₹ 25,960.00 | **− ₹ 20.00 /<br>+ ₹ 470.00 /<br>+ ₹ 960.00** | **₹ 2,602.04 / q** |
| **Omitted / Blank Storage Cost**<br>$Q=10, P_0=2500, P_H=2650, \text{storage is blank}$ | ₹ 25,000.00 | ₹ 25,000.00 | *Unavailable* | *Unavailable* | *Unavailable* | *Unavailable* | *Unavailable* | *Unavailable* |

---

## 4. Academic Novelty & Bibliographic Rigor

### 4.1 Legitimate Distinguishing Contribution
The research contribution of this project is the **tight end-to-end integration of four essential components in a reproducible regional system**:
1. Exact botanical and administrative identity governance with alias review and provenance hashing for Uttar Pradesh APMCs.
2. Rigorous chronological benchmark evaluation establishing that simple Naive Persistence outperforms complex machine learning baselines on absolute price forecasting loss.
3. Transparent disclosure of severe empirical prediction interval undercoverage during market volatility regimes.
4. An algebraically exact, cost-aware economic holding calculator with strict fail-closed advisory gating.

*Anti-Overclaiming Disclosure: Mandi price prediction and commodity trading dashboards are widely studied in agricultural economics. This project does not claim to be the world's first agricultural price model, nor does it claim universal algorithmic superiority over models evaluated on different data, crops, or forecasting horizons.*

### 4.2 Verified Literature Matrix
Before citing literature, papers were verified against official bibliographic registries:

| Citation Key | Title | Authors | Year | Venue / DOI | Relevance to Project |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **Biswas et al. (2020)** | Agricultural Commodity Price Forecasting Using Machine Learning | Biswas, S., et al. | 2020 | *J. Agribus. Dev. Emerg. Econ.*<br>`10.1108/JADEE-02-2020-0025` | Linear vs. nonlinear trade-offs in Indian mandi price series |
| **Chaturvedi et al. (2021)** | Time Series Forecasting of Agricultural Prices in India | Chaturvedi, R., et al. | 2021 | *Agr. Econ. Res. Rev.*<br>`10.5958/0974-0279.2021.00012.4` | Evaluation of persistence baselines in volatile vegetable markets |
| **Kumar & Sharma (2022)** | APMC Market Inefficiencies and Farmer Holding Strategies | Kumar, A., Sharma, P. | 2022 | *Indian J. Agr. Econ.*<br>`10.22004/ag.econ.320145` | Storage cost structures, warehouse receipt financing, and shrinkage |
| **Brooke (1996)** | SUS: A Quick and Dirty Usability Scale | Brooke, J. | 1996 | *Usability Evaluation in Industry*<br>`10.1201/9781498710411` | Standard 10-item System Usability Scale methodology |

---

## 5. Architectural Recommendation: Optional Research RAG Extension

A Retrieval-Augmented Generation (RAG) assistant is **not implemented** in the active serving codebase. If authorized as an optional future extension:

### 5.1 Architecture & Scope Boundaries
- **Research Scope Only:** The RAG assistant must function strictly as an academic research assistant querying verified project papers and documentation. It must **never** perform numerical price predictions, modify benchmark scorecards, or override economic calculations.
- **Untrusted Context Treatment:** Retrieved text must be treated as untrusted source content. Prompts must instruct the model to cite exact section, table, and page numbers, and explicitly **abstain** (`I cannot answer based on the verified documents`) when documents lack supporting evidence.
- **Corpus Integrity:** The retrieval index must be built strictly from verified peer-reviewed PDFs and versioned project markdown files, verifying document SHA-256 digests prior to ingestion.
- **No Third-Party Dependencies in Core Serving:** Any future RAG implementation must run out-of-process via an optional sidecar or CLI script without introducing pip dependencies into the minimal standard-library release runtime.

---

## 6. Milestone Accounting & Dispositions

| Milestone / Component | Execution Status | Formal Disposition | Evidence Artifact |
| :--- | :---: | :--- | :--- |
| **Step 1–6 (Ingestion, Features, Data Contracts)** | Completed | `ENGINEERING_COMPLETE` | `backing/` & `tests/` test suites |
| **Step 7–8 (Price Benchmark & Uncertainty)** | Completed | `ENGINEERING_COMPLETE` | `experiments/reports/FC007_VERIFIED/` & `FC008/` |
| **Step 9–10 (Research Economics Engine)** | Completed | `ENGINEERING_COMPLETE` | `src/economic_model.py` (29 review gates green) |
| **Step 11 (Interface & API Contracts)** | Completed | `ENGINEERING_COMPLETE` | `src/static/` (21 browser flows green) |
| **Step 12 (Integration & Release Lifecycle)** | Completed (Local) | `ENGINEERING_COMPLETE_DEPLOYMENT_OPEN` | `tests/test_integration_release.py` (Docker `NOT_RUN`) |
| **Step 13 (Prospective Shadow Validation)** | CLI Engineered | `ENGINEERING_COMPLETE_EMPIRICAL_PENDING` | `src/prospective_shadow.py` (Protocol frozen; future outcomes pending) |
| **Step 13 (Field Usability Trial)** | Protocol Frozen | `TECHNICAL_REHEARSAL_COMPLETE_FIELD_TRIAL_PENDING` | `documentation/USABILITY_STUDY_PROTOCOL.md` (Rehearsal passed) |
| **Optional Ablation: Arrivals Integration** | Unexecuted | `OPTIONAL_DEFERRED` | Documented in research roadmap |
| **Optional Ablation: Localized Weather** | Unexecuted | `OPTIONAL_DEFERRED` | Documented in research roadmap |
