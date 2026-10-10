# Phase 0: Unresolved Questions & Methodological Blockers
**Project:** APMC Mandi Market Intelligence System  
**Repository:** [ankit-choubey/Mandi_Prediction](https://github.com/ankit-choubey/Mandi_Prediction)  
**Audit Phase:** Phase 0 — Discovery and Setup  
**Date:** October 10, 2026  

---

## 1. Primary Methodological Blockers (Discovered in Phase 0)

### Blocker 1: The Mandi APMC Renaming Discontinuity
- **Observation:** In November 2025, the data source changed all market names from `<Market>` to `<Market> APMC` (e.g. `Lucknow` $\to$ `Lucknow APMC`).
- **Problem:** Because `series_id` is defined as `District + Market + Commodity + Variety`, the time series for every commodity was severed into two fragments.
- **Unresolved Decision:** Should `data_loader.py` canonicalize all market strings by stripping ` APMC` and mapping `Baripaal` to `Varipaal` (reducing 42 nominal mandis to 21 physical mandis)?
- **Audit Recommendation:** Yes, canonicalization must be implemented in Phase 1 before running temporal lag and continuity calculations.

---

### Blocker 2: Observation Shift vs Calendar Lag
- **Observation:** In `src/feature_engineering.py`, price lags are computed using `grouped['Modal_Price'].shift(7)`.
- **Problem:** In 79.86% of records, `shift(7)` is **not** 7 calendar days ago (mean gap is 11.45 days) due to Sunday market closures and reporting gaps. Meanwhile, the prediction target is strictly defined at $T+7$ calendar days.
- **Unresolved Decision:** How should feature engineering handle missing calendar days $T-7$, $T-3$, and $T-1$?
  - *Option A:* Strict calendar date merge (`Arrival_Date - 7 days`), setting missing days to `NaN` with explicit indicator features.
  - *Option B:* Calendar merge with forward-fill bounded by a maximum staleness threshold (e.g. $\le 2$ days).
- **Audit Recommendation:** Benchmark Option A vs Option B in Phase 1; eliminate unbounded observation shifts.

---

### Blocker 3: Baseline Disconnect & Class Imbalance
- **Observation:** The naive majority baseline on the chronological test set (always predicting "Normal") achieves **54.00%** accuracy.
- **Problem:** Decision Tree (49.34%), Extra Trees (49.95%), and Random Forest (53.23%) perform *worse* than guessing the majority class. Voting Ensemble (56.11%) is only +2.11% above naive guessing.
- **Unresolved Decision:** Is a static $\pm 2.5\%$ threshold justifiable when the median 7-day price return is 0.00% and 17.11% of all records experience exactly zero price change?
- **Audit Recommendation:** In Phase 1, evaluate volatility-adjusted thresholds ($k \sigma_i$) and empirical quantile splits alongside the fixed $\pm 2.5\%$ threshold.

---

### Blocker 4: External Price and Cost Data Grounding
- **Observation:** The repository currently contains only 5 raw APMC CSV files. No external logistics or cost data exists.
- **Problem:** A profit prediction layer ($Profit = P_{T+7} - Cost$) cannot be defended without verified external baselines for storage, transport, labour, and spoilage.
- **Unresolved Decision:** What specific external sources must be staged before Phase 2?
  - *Storage:* Central Warehousing Corporation (CWC) UP warehouse-wise tariffs (FY 2025–26 & FY 2026–27).
  - *Labour:* Department of Agriculture & Farmers Welfare "Agricultural Wages in India" (2024–25).
  - *Transport:* Road distance matrix between mandis and vehicle load capacities.
  - *External Price Agreement:* Department of Consumer Affairs (PMD) daily essential commodity wholesale monitoring series.

---

## 2. Inventory of Checks Performed vs Pending

| Check / Analysis | Phase 0 Status | Next Phase Scheduled |
|---|---|---|
| **Repository Inventory & Schema Discovery** | **COMPLETED** | N/A |
| **Row Count & Date Range Verification** | **COMPLETED** | N/A |
| **Missingness & Price Rule Compliance** | **COMPLETED** | N/A |
| **Local & Kaggle Notebook Execution** | **COMPLETED** | N/A |
| **Granular Per-Commodity Continuity Breakdown** | **Pending** | Phase 1 |
| **Systematic Missingness Mechanism (Sunday Closures)** | **Pending** | Phase 1 |
| **Calendar-Aware Feature Lag Reformation** | **Pending** | Phase 1 |
| **Alternative Target Formulation Comparisons** | **Pending** | Phase 1 |
| **External Source Agreement (DCA PMD Benchmark)** | **Pending** | Phase 2 |
| **Cost & Decision Layer Implementation** | **Pending** | Phase 3 |
