# Master Project Audit: APMC Mandi Market Intelligence System

**Repository:** [ankit-choubey/Mandi_Prediction](https://github.com/ankit-choubey/Mandi_Prediction)  
**Branch:** `audit/phase-00-inspection`  
**Current Audit Status:** Active Investigation (Phase 0 Completed, Phase 1 Pending)  
**Master Document Version:** 1.0.0 (Initialized: October 10, 2026)  

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

An end-to-end procedural pipeline orchestrated via [`run_pipeline.py`](../run_pipeline.py):

1. **Ingestion & Filtering ([`src/data_loader.py`](../src/data_loader.py)):**
   - Ingests 5 district CSV files (`Gaziabaad.csv`, `Jhansi.csv`, `Kanpur.csv`, `Lukhnow.csv`, `Unnao.csv`).
   - Normalizes district spelling (`Gaziabaad` $\to$ `Ghaziabad`, `Lukhnow` $\to$ `Lucknow`).
   - Parses dates (`%d/%m/%Y`), deduplicates exact series-date tuples, and filters out series with fewer than 20 records.
2. **Feature Engineering & Target Generation ([`src/feature_engineering.py`](../src/feature_engineering.py)):**
   - Constructs intraday spread features (`Max_Price - Min_Price`).
   - Computes historical lags via row shifts: `shift(1)`, `shift(3)`, `shift(7)`.
   - Computes rolling moving averages and standard deviation over 3 and 7 observations.
   - Extracts spatial neighbor signals across defined district pairs (Kanpur $\leftrightarrow$ Unnao $\leftrightarrow$ Lucknow).
   - Generates a discrete 3-class target via exact calendar day inner merge on $T+7$ using a static $\pm 2.5\%$ price change threshold.
3. **Model Suite ([`src/models.py`](../src/models.py)):**
   - Trains 5 pure classifiers: Decision Tree, Random Forest, Extra Trees, Gradient Boosting, and a Soft-Voting Ensemble (combining GB, RF, ET).
4. **Validation ([`src/evaluate.py`](../src/evaluate.py)):**
   - Applies chronological partitioning: 70% Train, 15% Validation, 15% Test based on sorted calendar dates.
   - Computes accuracy, macro/weighted precision, recall, F1, confusion matrices, and feature importance.
5. **Advisory Inferences ([`src/intelligence_system.py`](../src/intelligence_system.py)):**
   - Generates advisory recommendations based on predicted market condition classes.

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

### Current Formulation
The target predicts price change over exactly 7 calendar days:
$$R_7 = \left(\frac{P_{T+7} - P_T}{P_T}\right) \times 100$$
Discrete classes:
- **Favorable (Class 2):** $R_7 \ge +2.5\%$
- **Normal (Class 1):** $-2.5\% < R_7 < +2.5\%$
- **Unfavorable (Class 0):** $R_7 \le -2.5\%$

### Empirical Distribution of $R_7$ ($n = 116,361$)
- Mean: $+0.6306\%$ | Median: $0.0000\%$ | Std Dev: $18.0922\%$
- 25th Percentile: $-1.9608\%$ | 75th Percentile: $+1.5000\%$ | IQR: $3.4608\%$
- **Sticky Prices:** Exactly 0.00% change occurs in **19,914 records (17.11%)**.
- **Class Breakdown:**
  - Normal: 67,337 records (**57.87%**)
  - Unfavorable: 26,095 records (**22.43%**)
  - Favorable: 22,929 records (**19.71%**)

### Defect Identified
Because 50% of all observations fall within $[-1.96\%, +1.50\%]$, the static $\pm 2.5\%$ band captures ~58% of the data. This creates severe majority-class imbalance.

---

## 6. Mathematical and Statistical Assumptions

| Assumption | Repository Implementation | Audit Status | Evaluation |
|---|---|---|---|
| **Exact Horizon** | Target merged strictly at $Arrival\_Date + 7\text{ days}$ | **VERIFIED** | Methodologically correct; prevents horizon substitution. |
| **Observation Lag as Time Lag** | `Lag_Price_7 = shift(7)` | **FAIL** | Flawed. In 79.86% of cases, `shift(7)` is NOT 7 calendar days ago (mean gap: 11.45 days). |
| **Static Economic Threshold** | Fixed $\pm 2.5\%$ for all commodities | **QUESTIONABLE** | Fails to account for commodity volatility differences (Wheat $\sigma=10.1\%$ vs Tomato $\sigma=19.9\%$). |
| **Homogeneous Pricing Units** | Direct price comparisons | **PARTIALLY VERIFIED** | Standard crops are ₹/quintal, but Wood and specialty items exhibit extreme unit dispersion (up to 34.6x ratio). |

---

## 7. Feature Availability and Leakage Risks

- **Temporal Leakage:** Features at row $T$ are computed using rows with index $\le T$. However, because data is sorted by `(series_id, Arrival_Date)`, chronological order within each series is preserved.
- **Lookahead Leakage:** Zero lookahead leakage observed in feature engineering; target lookup is strictly separated into future lookup table.
- **Asymmetry Risk:** Target predicts strictly 7 calendar days forward, but lag features look back variable calendar days (8–16 days), distorting momentum signals.

---

## 8. Validation Protocol and Baseline Comparisons

### Protocol
- **Method:** Chronological split by calendar date:
  - Train: Earliest 70% unique dates (2024-09-01 to 2026-01-20; 98,882 records)
  - Validation: Next 15% dates (2026-01-21 to 2026-05-08; 7,082 records)
  - Test: Final 15% dates (2026-05-09 to 2026-08-25; 10,397 records)

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

## 14. Unresolved Questions and Risks

1. **Reconciliation of Conflicting Duplicates:** Should the 4,380 conflicting rows be replaced with daily medians plus an `Is_Ambiguous_Price_Date` flag, or excluded from training?
2. **Correction of Inverted Price Rows:** Impute `Max_Price = Modal_Price` on the 6 zero-max rows or drop them?
3. **Market String Canonicalization Boundaries:** Adopting proposed mapping from [`market_mapping_review.csv`](./phase_01/outputs/market_mapping_review.csv) to merge pre/post APMC variants while keeping parallel yards (Jhansi vs Jhansi Grain) distinct.
4. **Low-Continuity Commodity Screening:** Should commodities with $<60\%$ T+7 continuity (e.g. Lobia at 15.3%, Til at 15.2%) be formally excluded from automated model training?
5. **Calendar Lag Implementation ($T-k$):** Bounded forward-fill ($\le 2$ calendar days) with staleness indicators vs strict joins.

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

---

## 16. Final Feasibility Verdict

- **Current Overall Status:** **PHASE 1 COMPLETE / READY FOR PHASE 2 (METHODOLOGY & FEATURE REMEDIATION)**
- **Interim Conclusion:**
  Phase 1 has established exact empirical baselines for data integrity: the raw Agmarknet dataset contains 160,192 records with 75.73% eligible calendar T+7 availability and 99.996% price order validity. However, the original modeling pipeline's reliance on `shift(7)` (11.45-day mean lag), silent dropping of 4,380 conflicting duplicates, and artificial time-series fragmentation from the APMC string rename must be remediated in Phase 2 before models can be trained or evaluated.
- **Production Readiness:** **NOT PRODUCTION READY**. Proceed to Phase 2 (Calendar-Aware Feature Engineering & Leakage-Free Lag Reformation).
