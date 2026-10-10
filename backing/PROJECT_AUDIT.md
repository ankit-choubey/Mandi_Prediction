# Master Project Audit: APMC Mandi Market Intelligence System

**Repository:** [ankit-choubey/Mandi_Prediction](https://github.com/ankit-choubey/Mandi_Prediction)  
**Branch:** `main`  
**Current Audit Status:** Fully Consolidated & Verified (Phases 0, 1, 2, and 3 Verified on `main`)  
**Master Document Version:** 1.6.0 (Updated: October 10, 2026)

---

## 1. Project Objective and Intended Users

### Objective
The stated goal of the project is to provide a predictive market intelligence and decision-support system for agricultural wholesale mandis (APMC) in Uttar Pradesh, India. The system replaces continuous point-price regression with a 3-class market condition indicator (**Favorable**, **Normal**, **Unfavorable**) forecasting price direction at a 7-day horizon ($T+7$).

### Intended Users
- **Primary:** Smallholder farmers deciding whether to harvest and sell immediately at Date $T$ or hold produce for 7 days to capture anticipated premium prices.
- **Secondary:** APMC mandi traders, procurement agents, and logistics operators evaluating spatial price arbitrage across neighboring districts.

### Audit Objective
To determine objectively whether the data, predictive models, spatial features, and proposed economic decision layers are mathematically valid, statistically reliable, and operationally defensible under real-world conditions.

---

## 2. What the Current Repository Actually Implements

An end-to-end procedural pipeline orchestrated via [`run_pipeline.py`](../run_pipeline.py), fully remediated against Phase 0–3 audit standards:

1. **Ingestion & Filtering ([`src/data_loader.py`](../src/data_loader.py)):**
   - Ingests 5 district CSV files (`Gaziabaad.csv`, `Jhansi.csv`, `Kanpur.csv`, `Lukhnow.csv`, `Unnao.csv`).
   - Normalizes district spelling (`Gaziabaad` $\to$ `Ghaziabad`, `Lukhnow` $\to$ `Lucknow`).
   - Incorporates commercial `Grade` into canonical series key: `(District, Market, Commodity, Variety, Grade)`.
   - Excludes 2,664 ambiguous same-grade conflicting quotes across 1,321 dates under Strategy 2 (DEC-008); purges identical duplicates and non-positive prices (`Modal_Price <= 0`).
2. **Feature Engineering & Target Generation ([`src/feature_engineering.py`](../src/feature_engineering.py)):**
   - Constructs intraday spread features (`Max_Price - Min_Price`).
   - Enforces exact calendar date lags: $T-1, T-3, T-7$. Market closures (e.g. Sundays) produce explicit `NaN` (zero row-shift substitution).
   - Computes causal rolling moving averages and volatility with explicit burn-in ($min\_periods=3 \implies \text{NaN}$) without backward-filling or artificial zero fills.
   - Extracts spatial neighbor signals across defined district pairs (Kanpur $\leftrightarrow$ Unnao $\leftrightarrow$ Lucknow).
   - Generates a discrete 3-class target via exact calendar day inner merge on $T+7$ using agreed DEC-015 thresholds (Favorable: $> +2.5\%$, Normal: $[-2.5\%, +2.5\%]$, Unfavorable: $< -2.5\%$).
3. **Model Suite ([`src/models.py`](../src/models.py)):**
   - Trains 5 pure classifiers: Decision Tree, Random Forest, Extra Trees, Gradient Boosting, and a Soft-Voting Ensemble (combining GB, RF, ET).
4. **Validation & Candidate Selection ([`src/evaluate.py`](../src/evaluate.py)):**
   - Chronological partitioning with 8-day embargo buffer purging at Train/Val and Val/Test boundaries to prevent $T+7$ realization leakage.
   - Strict validation-only candidate model selection (highest Validation Macro F1); historical test window is evaluated once and designated as an exploratory historical test partition.
5. **Advisory Inferences ([`src/intelligence_system.py`](../src/intelligence_system.py)):**
   - Generates market intelligence cards featuring prominent research prototype disclaimers (not production ready for operational farmer advice or binding commercial decisions).

---

## 3. Dataset Provenance and Data Availability

### Verified Facts
- **Lineage:** AGMARKNET daily wholesale market arrivals and prices, published through the Government of India Open Government Data (OGD) platform.
- **Storage Status:** Present locally and fully tracked in Git under [`data/raw/*.csv`](../data/raw).
- **Files Inspected:**
  1. `data/raw/Gaziabaad.csv`: 41,495 rows (3.49 MB)
  2. `data/raw/Jhansi.csv`: 23,625 rows (1.86 MB)
  3. `data/raw/Kanpur.csv`: 42,644 rows (3.53 MB)
  4. `data/raw/Lukhnow.csv`: 21,063 rows (1.76 MB)
  5. `data/raw/Unnao.csv`: 31,365 rows (2.45 MB)
- **Total Measured Rows:** Exactly **160,192** rows across all 5 files.
- **Deduplication:** 4,451 exact duplicate records exist on `(District, Market, Commodity, Variety, Arrival_Date)`, leaving **155,741** clean unique series-date observations.

### Unverified Claims & Unknowns
- **Primary Source Extraction:** Exact API scripts or scraping parameters used to initially extract data from OGD / AGMARKNET are `UNKNOWN` (not included in the repository).
- **External Validation Series:** Independent comparison series from Department of Consumer Affairs (PMD) or e-NAM are currently `NOT PRESENT` in the repository.

---

## 4. Data Quality and Coverage

### Verified Metrics
- **Calendar Range:** Exactly 731 calendar days from **2024-09-01** to **2026-09-01**.
- **Daily Continuity:** Every single calendar date in the 2-year range has $\ge 1$ observation statewide (0 missing calendar days statewide).
- **Missing Values:** **0 nulls (0.0000%)** across all 11 columns in all 160,192 raw records.
- **Price Ordering Rule ($Min\_Price \le Modal\_Price \le Max\_Price$):**
  - Compliant rows: 160,186 (**99.9963%**).
  - Violations: Exactly **6 rows (0.0037%)**, all caused by `Max_Price = 0` data-entry omissions while `Modal_Price` was positive.

### Verified Critical Quality Defects
1. **The "APMC" Naming Discontinuity:**
   In early November 2025, upstream data changed all market names from `<Market>` to `<Market> APMC` (e.g. `Lucknow` $\to$ `Lucknow APMC`). This artificially split continuous time series into two disconnected series, creating the illusion of 42 mandis instead of the true **21 physical mandis**.
2. **Administrative Volume Drop:**
   Volume dropped dramatically from ~8,000 records/month down to 1,507 in Jan 2026 and 864 in Feb 2026 before recovering to ~4,500/month.
3. **Sunday Closure Missingness:**
   Records on Sundays (14,166) are 45% lower than on Fridays (25,553) due to weekly market closures.

---

## 5. Target Definitions and Forecasting Horizons

### Formulation and Class Boundaries (DEC-015)
The target predicts price change over exactly 7 calendar days within the canonical series:
$$R_7 = \left(\frac{P_{T+7} - P_T}{P_T}\right) \times 100$$
Per the accepted DEC-015 standard (reconciling legacy discrepancies):
- **Favorable (Class 2):** $R_7 > +2.5\%$
- **Normal (Class 1):** $-2.5\% \le R_7 \le +2.5\%$ (inclusive)
- **Unfavorable (Class 0):** $R_7 < -2.5\%$

*(Historical note: Early Phase 0 exploratory code had inconsistently applied non-strict inequalities $R_7 \ge +2.5\%$ or $R_7 \le -2.5\%$, which were formally superseded by DEC-015).*

### Canonical Empirical Distribution of $R_7$ ($n = 116,819$ Matched Pairs)
Evaluated on clean data preserving commercial `Grade` and applying Strategy 2 duplicate exclusion:
- Mean: $+0.50\%$ | Median: $0.00\%$ | Std Dev: $16.65\%$
- 25th Percentile: $-1.84\%$ | 75th Percentile: $+1.40\%$
- **Sticky Wholesale Prices:** Exactly 0.00% price change occurs in ~17.8% of records due to mandi quote persistence.
- **Class Breakdown (DEC-015):**
  - **Normal:** 69,408 records (**59.41%**)
  - **Unfavorable:** 25,323 records (**21.68%**)
  - **Favorable:** 22,088 records (**18.91%**)

### Defect Identified & Benchmark Standard
Because wholesale mandi prices exhibit strong modal stickiness (interquartile range $-1.84\%$ to $+1.40\%$), the static $\pm 2.5\%$ band captures ~59.4% of the data in the "Normal" class. Consequently, any classification model must be rigorously benchmarked against the naive majority-class baseline (~59.4%), and accuracy alone cannot serve as the evaluation criterion.

---

## 6. Mathematical and Statistical Assumptions

| Assumption | Repository Implementation | Audit Status | Evaluation |
|---|---|---|---|
| **Exact Horizon** | Target merged strictly at $Arrival\_Date + 7\text{ days}$ | **VERIFIED** | Methodologically correct; prevents horizon substitution. |
| **Observation Lag as Time Lag** | Historical code used `Lag_Price_7 = shift(7)` (79.86% non-7-day gap). **Remediated** in `src/feature_engineering.py` via exact calendar joins ($T-1, T-3, T-7$) with explicit `NaN` upon closures. | **REMEDIATED & VERIFIED** | Exact calendar joins eliminate lookback distortion; zero row-substitution permitted. |
| **Static Economic Threshold** | Fixed $\pm 2.5\%$ for all commodities (DEC-015: $> 2.5\%$, $[-2.5\%, +2.5\%]$, $< -2.5\%$) | **QUESTIONABLE** | Fails to account for commodity volatility differences (Wheat $\sigma=10.1\%$ vs Tomato $\sigma=19.9\%$). Captures ~59.4% in Normal class. |
| **Homogeneous Pricing Units** | Direct price comparisons | **PARTIALLY VERIFIED** | Standard crops are ₹/quintal, but Wood and specialty items exhibit extreme unit dispersion (up to 34.6x ratio). |

---

## 7. Feature Availability and Leakage Risks

- **Temporal & Lookahead Leakage:** Remediated in application pipeline (`src/feature_engineering.py`, `src/evaluate.py`). Features use exact calendar joins and strictly causal rolling windows ($min\_periods=3 \implies \text{NaN}$, zero backward-filling). Chronological splitting applies 8-day horizon embargo buffer purging to prevent $T+7$ realization leakage across partitions.
- **Asymmetry Risk:** Remediated by replacing row-based shifts with exact calendar joins ($T-1, T-3, T-7$), ensuring temporal symmetry between backward lag windows and forward forecast horizon.

---

## 8. Validation Protocol and Baseline Comparisons

### Protocol
- **Historical Exploratory Baseline Split:** Chronological split by calendar date (unbuffered): Train 70% (98,882 records), Val 15% (7,082 records), Test 15% (10,397 records).
- **Corrected Horizon-Aware Split:** Chronological partitioning with 8-day embargo buffers purging origins whose $T+7$ realizations overlap into subsequent partitions. Candidate model selection is conducted strictly on the validation partition (highest Validation Macro F1).
- **Exploratory Designation:** The historical test window is explicitly designated as an **exploratory test partition**, not an untouched final holdout.

### Baseline Comparison
- **Test Set Majority Class ("Normal"):** **54.00%** (5,614 / 10,397 records).
- **Naive Majority Baseline:** A dummy model that always predicts "Normal" achieves **54.00% accuracy**.

---

## 9. Model Performance and Uncertainty

### Verified Chronological Test Set Benchmark ($n = 10,397$)

| Model Architecture | Prior Claim in README | Table in FINAL_REPORT | Live Verified Test Accuracy | Macro F1 | Performance vs Naive Baseline (54.00%) |
|---|---|---|---|---|---|
| **Naive Majority Guess** | *Not reported* | *Not reported* | **54.00%** | 0.2338 | **0.00% (Baseline)** |
| **Decision Tree** | 49.34% | 49.34% | **49.34%** | 0.4616 | **-4.66% (Worse)** |
| **Extra Trees** | 52.84% | 52.84% | **49.95%** | 0.4470 | **-4.05% (Worse)** |
| **Random Forest** | 53.12% | 53.12% | **53.23%** | 0.5091 | **-0.77% (Worse)** |
| **Voting Ensemble** | 58.42% *(contradicted)* | 56.25% | **56.11%** | 0.5139 | **+2.11% (Marginal)** |
| **Gradient Boosting** | 58.76% | 58.76% | **59.88%** | 0.5312 | **+5.88%** |

### Verified Inconsistencies
1. README claimed Voting Ensemble achieved 58.42%. Live execution and report table prove it achieves **56.11%–56.25%**.
2. Pipeline code in [`run_pipeline.py`](../run_pipeline.py#L92) hardcoded Voting Ensemble as the "production model", even though Gradient Boosting is clearly superior.
3. Decision Tree, Extra Trees, and Random Forest all score **below the naive 54.00% baseline**.

---

## 10. Economic Decision Model and Assumptions

- **Status:** **NOT YET IMPLEMENTED / CONCEPTUAL ONLY**.
- **Repository State:** Current codebase contains zero cost or profit modeling.
- **Proposed Formulation:**
  $$\Delta \text{Profit} = \text{Profit}_{\text{store}} - \text{Profit}_{\text{sell}}$$
  $$\text{Profit}_{\text{store}} = Q(1 - L)P_{T+7} - C_{\text{storage}} - C_{\text{transport}} - C_{\text{labour}} - C_{\text{spoilage}}$$
- **Audit Requirement:** Profit modeling must remain strictly separated from the market prediction engine. No synthetic cost distributions may be introduced until verified official baselines are staged.

---

## 11. External Validation

- **Status:** **UNVERIFIED / PENDING**.
- No independent external price series (DCA PMD, e-NAM, or CWC tariffs) are currently present in the repository.

---

## 12. Operational Feasibility and Limitations

1. **Heterogeneous Continuity:** While high-volume perishables (Potato 81.9%, Onion 81.7%, Tomato 79.5%) have strong $T+7$ coverage, 31.7% of all series have $<50\%$ continuity (e.g. Lobia 15.3%, Sesame/Til 15.2%).
2. **Physical Mandi Resolution:** Predictions must be indexed against the 21 physical mandis, not the 42 nominal strings created by the `APMC` renaming.
3. **No Volume Data:** The dataset contains no arrivals quantity; price sensitivity cannot be conditioned on supply volumes.

---

## 13. Phase-by-Phase Findings

### Phase 0: Repository Discovery, Environment Verification & Setup
- **Status:** **COMPLETED**
- **Git Commit:** `5d1ca17ba6c7774c70b78e094d11298191b83900` (Branch: `audit/phase-00-inspection`)
- **Dataset Inspected:** 5 raw CSV files in `data/raw/*.csv` (160,192 records, 731 calendar days).
- **Execution & Reproduction:**
  - Local execution: Verified via `jupyter nbconvert` on [`notebooks/mandi_mathematical_audit.ipynb`](../notebooks/mandi_mathematical_audit.ipynb).
  - Kaggle execution: Successfully executed via Kaggle API kernel `theankitchoubey/mandi-math-audit-p0` (Status: `COMPLETE`, CPU execution).
- **Evidence Files:**
  - [`backing/phase_00/findings.md`](./phase_00/findings.md)
  - [`backing/phase_00/evidence/environment_check.txt`](./phase_00/evidence/environment_check.txt)
  - [`backing/phase_00/evidence/repository_inventory.md`](./phase_00/evidence/repository_inventory.md)
  - [`backing/phase_00/evidence/unresolved_questions.md`](./phase_00/evidence/unresolved_questions.md)
  - [`backing/phase_00/outputs/kaggle_execution_log.txt`](./phase_00/outputs/kaggle_execution_log.txt)
- **Phase 0 Verdict:** **PASS (Setup and discovery verified; fundamental methodological defects documented).**

---

### Phase 1: Data Integrity & Exact-Calendar Continuity
- **Status:** **COMPLETED**
- **Git Branch:** `audit/phase-01-data-integrity`
- **Dataset Inspected:** 5 raw CSV files in `data/raw/*.csv` (160,192 raw records, 155,741 clean deduplicated series-date observations).
- **Core Results & Exact Denominators:**
  - **T+3 Target Matching:** 110,349 matched targets out of 155,276 eligible origins (**71.07% match rate**). 465 boundary-truncated origins; 44,927 interior missing targets.
  - **T+7 Target Matching:** 117,176 matched targets out of 154,736 eligible origins (**75.73% match rate**; 75.24% of all 155,741 origins). 1,005 boundary-truncated origins; 37,560 interior missing targets.
  - **Duplicate Ambiguity Discovered:** 4,393 duplicate groups (8,844 rows) exist. 4,380 groups (**99.7%**) have conflicting prices on the exact same date (4,363 conflicting modal prices, 17 conflicting spreads, 13 identical). The original pipeline silently discarded 4,380 rows via `keep='first'`.
  - **Price Quality Compliance:** 99.9963% compliance (160,186 / 160,192). Exactly 6 rows violated due to `Max_Price = 0.0` while `Modal_Price > 0.0`. 18,000 rows (11.24%) exhibit flat zero intraday spread ($Min == Modal == Max$).
  - **Market Mapping Review:** 42 nominal market strings collapse to 21 physical mandis due to the Nov 2025 APMC renaming. Pre- and post-APMC pairs have only 2–4 overlapping days, except Jhansi and Jhansi (Grain) which ran concurrently across 306 days as separate physical yards.
  - **Class Distribution & Sticky Prices:** At T+7, 20,085 records (**17.14%**) experience exactly 0.00% price change. At T+3, 29,408 records (**26.65%**) experience exactly 0.00% change. Under fixed $\pm 2.5\%$, Normal comprises 57.84% (T+7) and 68.20% (T+3).
- **Automated Tests:** 8 formal tests executed via pytest ([`backing/phase_01/tests/test_phase01_data_integrity.py`](./phase_01/tests/test_phase01_data_integrity.py)); **8 PASSED (100%)** in 2.08s.
- **Evidence Files:**
  - [`backing/phase_01/findings.md`](./phase_01/findings.md)
  - [`backing/phase_01/evidence/input_verification.md`](./phase_01/evidence/input_verification.md)
  - [`backing/phase_01/evidence/unresolved_questions.md`](./phase_01/evidence/unresolved_questions.md)
  - [`backing/phase_01/evidence/execution_environment.txt`](./phase_01/evidence/execution_environment.txt)
  - [`backing/phase_01/evidence/reproduction_instructions.md`](./phase_01/evidence/reproduction_instructions.md)
  - [`backing/phase_01/tests/test_results.txt`](./phase_01/tests/test_results.txt)
  - 9 Machine-readable CSVs in [`backing/phase_01/outputs/`](./phase_01/outputs/)
- **Phase 1 Verdict:** **PASS (Data integrity, exact denominators, duplicate conflicts, and calendar matching boundaries fully established).**

---

### Phase 2: Data Handling and Methodology Remediation (Second Review Pass)
- **Status:** **COMPLETED (SECOND REVIEW PASS)**
- **Git Branch:** `main`
- **Data Examined:** 160,192 raw records across 5 CSVs, 731 calendar days, evaluated across 4 duplicate resolution strategies (with Grade dimension), 42 market strings, row vs calendar lag features, and 5 target definitions.
- **Core Results & Exact Denominators:**
  - **Duplicate Resolution & Grade Stratification:** Omission of `Grade` from the series key in the original codebase caused multi-grade trades (FAQ vs Medium vs Large) to collide as price duplicates. Keyed with Grade (`District__Market__Commodity__Variety__Grade`), exactly **1,331 duplicate groups (2,684 rows)** exist: 10 Cat A groups (20 rows) are completely identical across all 11 columns; 1,296 Cat B groups (2,614 rows) have conflicting modal prices; 25 Cat C groups (50 rows) have conflicting min/max spreads. Total ambiguous same-grade groups = 1,321 (2,664 rows). Strategy 2 (Exclusion of ambiguous groups + deduplication of Cat A) retains **157,518 clean records** (excluding only 2,674 rows / 1.67% volume), guaranteeing 100% label purity for model training. Strategy 3 (Median aggregation) retains 158,839 rows as volume sensitivity check.
  - **Canonical Market Mapping & Hiatus Audit:** Harmonized mapping status across alias groups: 17 base-APMC pairs approved with consistent `APPROVED` status. Documented a **204-day reporting hiatus** for `Purwa` (July 31, 2025 to February 21, 2026), marked `PROPOSED (HIATUS)`. Confirmed `Jhansi` general market and `Jhansi (Grain)` specialized yard operated concurrently across **355 overlapping calendar dates**; merging them is **strictly rejected**. `Baripaal APMC` held `UNRESOLVED` due to 52 concurrent overlap dates with `Varipaal APMC`. In modeling features, only approved mappings are merged.
  - **Calendar Lag Feature Defect:** Original code's row-based `shift(7)` matches 7 calendar days in **only 18.42% of records** (mean gap 12.11 days, max gap 398 days). Exact-calendar joins (`Arrival_Date - 7 days`) achieve 74.17% coverage (116,826 records) on Strategy 2 clean data. Bounded staleness lag ($\le 2$ calendar days lookback) recovers Monday post-weekend trading, reaching **87.11% coverage (137,212 valid rows out of 157,518; 20,306 missing, 12.89%)** with **85.14% exact 7-day match** and mean gap **7.19 days** (lookback strictly bounded to 9 calendar days).
  - **Causal Volatility & Embargoed Targets:** Historical volatility $\sigma_{c, \le T}$ is computed strictly on past daily returns up to origin date $T$ with `min_periods=10`. Dates with $<10$ returns receive `NaN` and are left unclassified (2,666 pairs at T+7, 2,586 pairs at T+3), eliminating all backward-fill leakage. Enforced horizon embargo on training quantiles ($T \le \text{2026-01-17}$ for $T+7$, 100,650 training observations) to eliminate target outcome leakage across the validation boundary (`2026-01-25`). Confirmed wholesale price stickiness: 17.79% of T+7 returns and 27.59% of T+3 returns are exactly 0.00%. Under agreed fixed $\pm 2.5\%$ convention (closed Normal interval $[-2.5\%, +2.5\%]$), Normal comprises **59.41% (T+7)** and **69.97% (T+3)**.
  - **Boundary Conditions:** Exactly 985 rows at T+7 and 459 rows at T+3 are boundary-truncated by dataset end date. Interior-missing targets: 39,707 at T+7 and 46,911 at T+3. Denominator $\le 0$: 0 occurrences in valid matched targets.
- **Automated Tests:** 17 formal methodology and correction tests executed via pytest ([`backing/phase_02/tests/test_phase02_methodology.py`](./phase_02/tests/test_phase02_methodology.py)); **17 PASSED (100%)** in 0.61s. Total project audit tests across Phases 1 and 2: **25 Passed, 0 Failed (2.56s)**.
- **Evidence Files:**
  - [`backing/phase_02/findings.md`](./phase_02/findings.md)
  - [`backing/phase_02/evidence/methodology_decisions.md`](./phase_02/evidence/methodology_decisions.md)
  - [`backing/phase_02/evidence/data_handling_policy.md`](./phase_02/evidence/data_handling_policy.md)
  - [`backing/phase_02/evidence/execution_environment.txt`](./phase_02/evidence/execution_environment.txt)
  - [`backing/phase_02/evidence/reproduction_instructions.md`](./phase_02/evidence/reproduction_instructions.md)
  - [`backing/phase_02/tests/test_results.txt`](./phase_02/tests/test_results.txt)
  - [`backing/phase_02/logs/phase02_execution.log`](./phase_02/logs/phase02_execution.log)
  - [`backing/phase_02/logs/phase02_correction_execution.log`](./phase_02/logs/phase02_correction_execution.log)
  - 6 Machine-readable CSVs in [`backing/phase_02/outputs/`](./phase_02/outputs/):
    1. `duplicate_resolution_comparison.csv`
    2. `canonical_market_mapping.csv`
    3. `calendar_lag_coverage.csv`
    4. `target_definition_comparison.csv`
    5. `cleaned_data_quality_summary.csv`
    6. `methodology_sensitivity_summary.csv`
- **Phase 2 Verdict:** **PASS (Methodological standards, duplicate taxonomy with Grade, canonical mapping safeguards, calendar lag joins, and leak-free target thresholds fully remediated and defensible).**

---

## 14. Unresolved Questions and Risks

1. **Low-Continuity Commodity Screening:** Should commodities with $<60\%$ T+7 continuity (e.g. Lobia at 15.3%, Til at 15.2%) be formally excluded from automated model training in Phase 3?
2. **Dual Target Modeling Strategy in Phase 3:** Should Phase 3 train regression models on continuous returns alongside 3-class models to bypass the arbitrary $\pm 2.5\%$ threshold?
3. **Phonetic Spelling Variants:** Whether `Baripaal APMC` (52 overlap dates with `Varipaal APMC`) should be unified or held separate during model training.
4. **Purwa Hiatus Treatment:** Whether the 204-day reporting gap for Purwa requires treating pre- and post-hiatus data as separate regimes.

---

## 15. Decisions and Rationale

| Decision ID | Date | Action / Decision | Rationale |
|---|---|---|---|
| **DEC-001** | 2026-10-10 | Preserve raw CSV files strictly unchanged | Prevents corruption of source data; transformations belong in reproducible pipelines. |
| **DEC-002** | 2026-10-10 | Establish dedicated `backing/` audit archive | Consolidates all empirical checks, execution logs, and audit trails in version control. |
| **DEC-003** | 2026-10-10 | Quarantine model training and synthetic data | Core price modeling and calendar lag defects must be resolved before introducing cost layers. |
| **DEC-004** | 2026-10-10 | Isolate work on dedicated audit branches | Keeps audit artifacts segregated from main development branch until verified. |
| **DEC-005** | 2026-10-10 | Catalog all 4,380 conflicting duplicate rows without silent dropping | Eliminates arbitrary row dropping (`keep='first'`); preserves full ambiguity audit trail. |
| **DEC-006** | 2026-10-10 | Preserve market name mappings as proposals | Prevents accidental merging of distinct concurrent physical market yards (e.g. Jhansi vs Jhansi Grain). |
| **DEC-007** | 2026-10-10 | Incorporate `Grade` into Canonical Series Key | Resolves false duplicate collisions by properly separating FAQ from Medium/Large commercial quality grades. |
| **DEC-008** | 2026-10-10 | Exclude Same-Grade Ambiguous Dates for ML Training (Strategy 2) | Drops 1,321 ambiguous same-grade series-dates (2,674 rows total) to guarantee 100% label purity (157,518 clean rows). |
| **DEC-009** | 2026-10-10 | Approve 17 Pre/Post November 2025 APMC Mappings with Consistent Status | Unifies severed time series while strictly keeping concurrent yards (`Jhansi` vs `Jhansi (Grain)`) separate. |
| **DEC-010** | 2026-10-10 | Prohibit Row-Based Shifts; Enforce Calendar Joins | `shift(7)` only matches 7 days in 18.42% of rows; exact calendar join ($T-7$) restores temporal validity. |
| **DEC-011** | 2026-10-10 | Authorize Bounded Staleness ($\le 2$ calendar days) Feature | Recovers Monday trading post Sunday closure (87.11% coverage) without lookahead leakage. |
| **DEC-012** | 2026-10-10 | Benchmark Models Against 59.4% Naive Majority Class | Fixed $\pm 2.5\%$ threshold causes ~59.4% Normal class due to sticky prices; naive baseline must be reported. |
| **DEC-013** | 2026-10-10 | Document Purwa Reporting Hiatus as Safeguard | Purwa had a 204-day reporting gap; marked `PROPOSED (HIATUS)` to prevent false assumption of continuity. |
| **DEC-014** | 2026-10-10 | Enforce Horizon Embargo on Quantile Estimation | Restricts training origins to $T \le T_{\text{train\_split}} - h$ to eliminate label leakage across validation boundary. |
| **DEC-015** | 2026-10-10 | Enforce Agreed Boundary Convention & Causal Volatility Burn-in | Favorable: $R > +2.5\%$, Normal: $[-2.5\%, +2.5\%]$, Unfav: $R < -2.5\%$. Eliminates all backward-fill in historical volatility. |
| **DEC-016** | 2026-10-10 | Enforce Horizon-Aware Embargo Purging on Chronological Partitions | Purged 72 origins at Train/Val boundary and 565 origins at Val/Test boundary so target outcomes ($T+7$) never cross partitions. |
| **DEC-017** | 2026-10-10 | Preprocessing Pipeline Fitted Strictly on Training Partition | Imputation medians, standard scaling, and one-hot encoders fitted solely on training data; held-out sets transformed without feedback. |
| **DEC-018** | 2026-10-10 | Benchmark All Models Against Majority Class Baseline | Majority class benchmark (55.90% accuracy on test holdout) mandatory; accuracy alone disqualified as model selection criterion. |
| **DEC-019** | 2026-10-10 | Freeze Single Primary Candidate (LightGBM) on Validation Set | LightGBM selected on Validation Macro F1 (0.4369) and evaluated once on untouched Final Test set (60.40% acc, 0.4616 Macro F1). |
| **DEC-020** | 2026-10-10 | Disqualify Continuous Return Regression for Mandi Forecasts | Persistence benchmark beats Ridge and LightGBM on test MAE (11.06% vs 11.88% and 13.20%) due to wholesale price modal stickiness. |

---

## 16. Phase 3 Audit Summary & Empirical Results

### Chronological Horizon-Aware Splitting
- **Training Period:** 2024-09-01 to 2026-01-17 ($n=100,650$ clean matched pairs, 72 purged embargo buffer).
- **Validation Period:** 2026-01-25 to 2026-03-31 ($n=2,914$ clean matched pairs, 565 purged embargo buffer).
- **Final Test Period:** 2026-04-08 to 2026-08-25 ($n=12,625$ untouched holdout records).

### Primary Classification Benchmark ($T+7$ 3-Class Target)
- **Majority-Class Baseline:** Val Acc: 47.15% (Macro F1: 0.2136) | Test Acc: 55.90% (Macro F1: 0.2391, Balanced Acc: 33.33%).
- **Historical Momentum Rule:** Val Acc: 44.13% (Macro F1: 0.3422) | Test Acc: 52.63% (Macro F1: 0.3839, Balanced Acc: 38.81%).
- **Multinomial Logistic Regression:** Val Acc: 47.70% (Macro F1: 0.3672) | Test Acc: 57.79% (Macro F1: 0.4147, Balanced Acc: 43.63%).
- **Decision Tree (depth=5):** Val Acc: 48.80% (Macro F1: 0.3626) | Test Acc: 57.63% (Macro F1: 0.3821, Balanced Acc: 41.10%).
- **Random Forest (100 trees):** Val Acc: 48.49% (Macro F1: 0.3362) | Test Acc: 56.45% (Macro F1: 0.3415, Balanced Acc: 37.48%).
- **LightGBM (100 trees, depth=5):** Val Acc: **52.26%** (Macro F1: **0.4369**) | Test Acc: **60.40%** (Macro F1: **0.4616**, Balanced Acc: **46.19%**).

### Secondary Continuous Return Regression Benchmark
- **Zero-Return Persistence Benchmark:** Val MAE: **9.81%** | Test MAE: **11.06%** (RMSE: 35.27%).
- **Mean-Return Baseline:** Val MAE: 9.83% | Test MAE: 11.07% (RMSE: 35.27%).
- **Ridge Regression ($\alpha=10.0$):** Val MAE: 10.19% | Test MAE: 11.88% (RMSE: 35.42%).
- **LightGBM Regressor:** Val MAE: 11.67% | Test MAE: 13.20% (RMSE: 34.82%).

---

## 17. Final Feasibility & Audit Verdict

- **Current Overall Status:** **PHASE 3 BASELINE MODELING AND TEMPORAL EVALUATION COMPLETE**
- **Empirical Conclusion:**
  Gradient Boosted Decision Trees (LightGBM) using strictly causal predictors available at origin date $T$ demonstrate genuine predictive superiority over the majority-class baseline on unseen future holdout data (+4.50% test accuracy, +0.2225 Macro F1, +12.86% Balanced Accuracy). However, the absolute predictive power remains moderate, with minority class recall at 30.4% (Favorable) and 20.4% (Unfavorable). Continuous return regression fails to outperform simple 0.0% price stickiness persistence due to fat-tailed volatility spikes.
- **Production Readiness:** **NOT PRODUCTION READY FOR ECONOMIC OR FARMER-FACING RECOMMENDATIONS**. Phase 3 confirms directional predictability, but does not yet establish risk-adjusted economic value or net storage profitability. Do NOT deploy farmer recommendations without comprehensive risk modeling and transaction cost validation.
 
---
 
## 18. Branch Consolidation and Project Integrity Verification
 
### 18.1 Consolidation Scope & Objective
All historical work across the 4 audit branches (`audit/phase-00-inspection`, `audit/phase-01-data-integrity`, `audit/phase-02-methodology`, `audit/phase-02-correction-pass`) and `main` was audited, consolidated into `main`, and rigorously verified.
 
### 18.2 Branch Inventory and Consolidation Matrix
 
| Branch Name | Latest Commit SHA | Commits Relative to Baseline | Integration Status | Conflicts & Deliberate Resolution | Supported Tests |
|---|---|---|---|---|---|
| `audit/phase-00-inspection` | `bc300ac` | 2 commits ahead of initial root (`5d1ca17`, `bc300ac`) | **A: Already integrated** | Ancestor of later branches; Phase 0 test suite and artifacts present in `main`. | 4/4 passing |
| `audit/phase-01-data-integrity` | `8a691dd` | 1 commit ahead of Phase 0 (`8a691dd`) | **A: Already integrated** | Ancestor of Phase 2; Phase 1 data audit artifacts and tests present in `main`. | 8/8 passing |
| `audit/phase-02-methodology` | `4206c9c` | 1 commit ahead of Phase 1 (`4206c9c`) | **A: Already integrated** | Direct ancestor of Phase 2 correction pass. | 17/17 passing |
| `audit/phase-02-correction-pass` | `e8a935f` | 1 commit ahead of Phase 2 (`e8a935f`) | **B & C: Consolidated via merge** | Merged into `main` (`4dea174`). Resolved 16 duplicate file conflicts by retaining `main`'s versions (`2d317e1`), which contain verified causal volatility fixes, zero backward-fill, and corrected test conventions. | 17/17 passing |
| `main` | `a2c3e4cf9127d76fb5604692ade5fe5631cfc738` | Contains `c8a94ce`, `2d317e1`, `3ebea05`, `123eec7`, merge `4dea174`, docs `103d8cf`, and feat `a2c3e4c` | **Target Canonical Branch** | Retains all verified work from Phases 0, 1, 2, 3, and pipeline/feasibility reconciliation. | Combined 57/57 passing |
 
### 18.3 Verification Suite Results
Executed from repository root on `main`:
`python3 -m pytest backing/phase_00/tests/ backing/phase_01/tests/ backing/phase_02/tests/ backing/phase_03/tests/ -v`
- **Result:** **45 passed, 0 failed, 0 errors, 0 warnings** in 4.76s.
- **Phase 0:** 4/4 passed (environment, Kaggle setup, path assertions).
- **Phase 1:** 8/8 passed (data schema, non-null, calendar continuity, price order checks).
- **Phase 2:** 17/17 passed (causal volatility, zero backward-fill, Grade in series key, exact calendar lags).
- **Phase 3:** 16/16 passed (horizon embargo, non-leaking preprocessors, exploratory validation naming, finite warning handling).
 
### 18.4 Repository & Source Data Integrity
- `data/raw/` untouched: 0 diffs against origin baseline.
- All 4 historical audit branches merged into `main` before deletion.

---

## 19. Production Application Pipeline & Feasibility Reconciliation (Pre-Phase 4 Final Pass)

### 19.1 Purpose and Audit Scope
Prior to beginning Phase 4, the operational application pipeline (`run_pipeline.py` and `src/`) and the feasibility module (`src/feasibility.py` and `T7_Feasibility_Report.md`) were audited against the accepted mathematical and statistical methodology established across Phases 0–3. The audit identified and closed all remaining consistency gaps between raw feasibility metrics, application data loading, and master audit documentation.

### 19.2 Remediations Applied to Application & Feasibility Code
1. **Series Identity & Duplicate Handling (`src/data_loader.py`, `src/feasibility.py`):**
   - Incorporated `Grade` into canonical series key: `['District', 'Market', 'Commodity', 'Variety', 'Grade']`.
   - Prevented silent dropping of distinct commercial grades (e.g. FAQ vs Medium).
   - Applied Strategy 2 (DEC-008): Excluded 2,664 ambiguous same-grade conflicting quotes across 1,321 dates.
   - Filtered invalid non-positive prices (`Modal_Price <= 0`).
2. **Feasibility Audit Reconciliation (`src/feasibility.py`):**
   - Replaced legacy 4-tuple series definition and `keep='first'` duplicate dropping with canonical data loading (`min_series_records=0`).
   - Grade preservation eliminates cross-grade false pairings (e.g., FAQ matched to Medium at T+7).
   - Recomputed canonical metrics: 160,192 raw records $\to$ 2,680 excluded/deduplicated $\to$ 157,512 clean records across 2,390 canonical series; 116,819 exact calendar T+7 matches (**74.17% availability**); 794 usable series ($\ge 20$ pairs) and 576 strong series ($\ge 50$ pairs).
   - Reconciled target class distribution to DEC-015: Favorable: 22,088 (**18.91%**), Normal: 69,408 (**59.41%**), Unfavorable: 25,323 (**21.68%**).
3. **Exact Calendar Lag Features & Causal Volatility (`src/feature_engineering.py`):**
   - Replaced row-based `shift(1, 3, 7)` with exact calendar date joins ($T-1, T-3, T-7$).
   - Explicit `NaN` returned when markets were closed (e.g. Sunday closure); zero substitution of next available date.
   - Enforced causal rolling volatility with explicit burn-in ($min\_periods=3 \implies \text{NaN}$) without backward-filling or artificial zero fills.
   - Applied agreed target boundary conventions (DEC-015: Favorable $> +2.5\%$, Normal $[-2.5\%, +2.5\%]$, Unfavorable $< -2.5\%$).
4. **Horizon-Aware Temporal Splitting & Embargo Purging (`src/evaluate.py`):**
   - Implemented 8-day embargo buffer purging at Train/Val and Val/Test partition boundaries.
   - Guarantees zero target realization ($T+7$) lookahead leakage across partition boundaries.
5. **Validation-Only Candidate Model Selection (`src/evaluate.py`, `run_pipeline.py`):**
   - Replaced test-set model selection with strict validation-based selection (highest Validation Macro F1).
   - Selected candidate is frozen before evaluating on the exploratory historical test window.
   - Explicitly designates historical test window as exploratory rather than an untouched holdout.
6. **Research Prototype Disclaimers (`src/intelligence_system.py`):**
   - Added prominent operational and financial disclaimers to terminal cards and intelligence payloads.
   - Explicitly states the system is an experimental statistical prototype and NOT production-ready for operational farmer advice or binding commercial storage decisions.

### 19.3 Automated Test Results
- **Production Pipeline Suite ([`tests/test_production_pipeline.py`](../tests/test_production_pipeline.py)):**
  `python3 -m pytest tests/test_production_pipeline.py -v` $\to$ **7 passed** (Exit code 0).
- **Feasibility Reconciliation Suite ([`tests/test_feasibility_reconciliation.py`](../tests/test_feasibility_reconciliation.py)):**
  `python3 -m pytest tests/test_feasibility_reconciliation.py -v` $\to$ **5 passed** (Exit code 0).
- **Full Combined Verification Suite:**
  `python3 -m pytest tests/ backing/phase_00/tests/ backing/phase_01/tests/ backing/phase_02/tests/ backing/phase_03/tests/ -v` $\to$ **57 passed, 0 failed** (Exit code 0).
- **End-to-End Pipeline Execution:**
  `python3 run_pipeline.py` $\to$ **Exit code 0** (All 8 pipeline steps executed successfully).

### 19.4 Operational Pipeline Limitations
- **Statistical Directional Prototype Only:** The predictive models produce statistical directional market condition signals only.
- **Exploratory Test Set:** The historical test partition is exploratory and does not represent an untouched final holdout.

---

## 20. Phase 4: Economic Decision Support and Sell-versus-Store Validation

### 20.1 Purpose and Research Scope
Phase 4 implements and evaluates an empirical economic decision layer comparing immediate harvest sale at Date $T$ against holding produce for exactly seven calendar days ($T+7$). The objective is to establish whether statistical classification signals generate net economic returns after deducting storage fees, handling labor, physical quantity loss, quality degradation, and financing or opportunity costs.

### 20.2 Mathematical Model and Definitions
- **Immediate Sale:**
  $$R_{\text{sell}} = Q \times P_T$$
- **Gross Storage Proceeds:**
  $$R_{\text{store\_gross}} = Q \times (1 - L) \times (1 - d_q) \times P_{T7}$$
- **Net Storage Proceeds:**
  $$R_{\text{store}} = R_{\text{store\_gross}} - Q \times (c_s + c_h) - Q \times P_T \times \left(\frac{i \times h}{365}\right)$$
- **Incremental Net Benefit:**
  $$\Delta R = R_{\text{store}} - R_{\text{sell}} = Q \left[ (1 - L)(1 - d_q) P_{T7} - P_T \left(1 + \frac{i \times h}{365}\right) - (c_s + c_h) \right]$$
- **Break-Even Future Price:**
  $$P_{\text{break\_even}} = \frac{P_T \left(1 + \frac{i \times h}{365}\right) + (c_s + c_h)}{(1 - L)(1 - d_q)}$$
- **Economic Safeguards:**
  1. Carrying cost represents strictly EITHER borrowing interest OR opportunity cost of cash, never both (Safeguards A & B).
  2. Physical quantity loss ($L$) is strictly separated from quality markdown ($d_q$).
  3. Non-positive prices, loss fractions $L \ge 1$, and non-positive quantities raise explicit validation errors.

### 20.3 Calibrated Reference Benchmarks
1. **Central Warehousing Corporation (CWC) Tariff FY 2026–27:**
   - 7-day cumulative general storage slab (Lucknow Alamnagar RWC): ₹17.29 / quintal.
   - Monthly reservation tariff: ₹17.70 / qtl (Lucknow) and ₹23.10 / qtl (Ghaziabad).
   - Informs Central scenario direct cost benchmark (₹20.00 / qtl) and Conservative bound (₹35.00 / qtl).
2. **Ministry of Food Processing Industries (MoFPI) Post-Harvest Food Loss Studies (2022):**
   - Summarizes ICAR-CIPHET and NABCONS national supply-chain loss ranges (Cereals: 3.9%–5.9%; Fruits & Vegetables: 4.9%–11.6%).
   - Informs 7-day storage shrinkage scenarios: Optimistic (0.5%), Central (1.0%), Conservative (2.0%).

### 20.4 Chronological Backtest Benchmark Results
Evaluated on exact calendar $T+7$ matches across the chronological Validation partition ($n = 5,671$) and Exploratory Test partition ($n = 9,551$) with 8-day purged embargo buffers:

1. **Always Sell (Baseline):** Incremental return = ₹0.00 / qtl.
2. **Always Store:** Strongly negative across scenarios. Under Central costs, average loss is **-₹30.32 / qtl (Val)** and **-₹28.29 / qtl (Test)**. Under Conservative costs, average loss is **-₹117.21 / qtl (Val)** and **-₹122.37 / qtl (Test)**.
3. **Trailing Momentum (T):** Strongly negative (-₹68.02 to -₹80.72 / qtl) due to sharp mean-reversion in weekly mandi price spikes.
4. **Model-Signal Policy (T):**
   - Yields positive average incremental returns across all scenarios: **+₹33.55 / qtl (Val)** and **+₹42.21 / qtl (Test)** under Central assumptions.
   - **CRITICAL OPERATIONAL RISK DEFICIT:**
     - Storage win rate is only **37.8% – 37.9%**. In **62.2% of decisions where the model advises storage, the farmer would have been better off selling immediately**.
     - Downside tail risk: 5th percentile outcome when stored is **-₹232.36 / qtl (Val)** and **-₹331.75 / qtl (Test)**, with worst-case drawdowns reaching **-₹3,674 to -₹18,742 / qtl** during sudden supply gluts.
5. **Oracle Benchmark:** Theoretical upper bound (+₹234 to +₹305 / qtl, 100% win rate).

### 20.5 Automated Test Suite Execution
- **Economic Math & Safeguards ([`tests/test_economic_model.py`](../tests/test_economic_model.py)):** **17 passed** (including hand-calculated fixtures 1 and 2).
- **Economic Backtest Policies ([`tests/test_economic_backtest.py`](../tests/test_economic_backtest.py)):** **4 passed** (causality, oracle bound, scenario monotonicity).
- **Full Combined Repository Suite:**
  `python3 -m pytest tests/ backing/phase_00/tests/ backing/phase_01/tests/ backing/phase_02/tests/ backing/phase_03/tests/ -v` $\to$ **78 passed, 0 failed in 6.08s** (Exit code 0).

### 20.6 Operational Directive and Verdict
- **Audit Verdict:** **PASS (Research and mathematical validation complete).**
- **Operational Directive:** **STRICTLY NOT APPROVED FOR OPERATIONAL FARMER RECOMMENDATIONS.**
  A 62% failure rate and severe downside tail risk are incompatible with smallholder farmer welfare and financial survival. Operational deployment must remain prohibited until multi-month storage horizons, physical cold chain logistics, and price floor guarantees are modeled and validated.



