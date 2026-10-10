# Phase 5: Robustness, Uncertainty, and Governance Limitations

**Project:** Mandi_Prediction
**Repository:** `ankit-choubey/Mandi_Prediction`
**Phase:** 5 — Robustness, Statistical Uncertainty, and Generalization Audit
**Date:** October 10, 2026
**Artifact:** `backing/phase_05/limitations.md`

---

## 1. Executive Directive: Continuation of Operational Prohibition

> **MANDATORY POLICY DIRECTIVE:**
> **Under NO circumstances should the market intelligence system be deployed for farmer-facing operational advice or used to recommend that individual agricultural producers store produce rather than sell immediately.**

While the machine-learning classification model demonstrates statistically detectable predictive skill over naive baselines and captures positive average incremental return in historical backtests, the Phase 5 robustness audit reveals insurmountable structural barriers to operational deployment:
1. **The ~62% Loss Rate is Structurally Invariant:** Even under cluster bootstrap resampling across market series or strict probability threshold filtering ($P \ge 0.60$), the storage policy loses money in **53% to 68% of storage decisions**.
2. **Acute Commodity Failure:** For major food grains (Wheat) and perishables (Tomato), 7-day tactical storage is structurally unprofitable, with win rates as low as **15.4%** and negative net returns.
3. **Severe Downside Tail Exposure:** Stored batches suffer extreme tail drawdowns exceeding **-₹232 to -₹331 / quintal (5th percentile)** and up to **-₹3,674 to -₹18,742 / quintal (worst case)**.
4. **Aggregate APMC Data Limitations:** Individual smallholder risk preferences, credit constraints, household cash-flow margins, and physical warehouse accessibility cannot be observed or validated from aggregate APMC modal price records.

---

## 2. Four-Tier Classification of Phase 5 Evidence

In compliance with project governance standards, all empirical and methodological findings are categorized into four rigorous evidentiary tiers:

### Tier A: Independently Reproduced
- **Cryptographic & Record Provenance:** Full pipeline ingestion of 160,192 raw records across 5 district files, filtering 2,664 conflicting same-grade records (Strategy 2), retaining 1,069 active series ($n = 150,687$), and verifying 115,833 exact calendar $T+7$ target matches.
- **Chronological Split & Embargo Alignment:** Exact partitioning into Train (99,881 records, Sep 2024 – Jan 2026), Val (5,671 records, Jan – May 2026), and Exploratory Test (9,551 records, May – Aug 2026) with 8-day purged embargoes.
- **Baseline Predictive Metrics:** GBDT baseline achieving Macro F1 = 0.4957 (Val) and 0.5041 (Test); Balanced Accuracy = 49.48% (Val) and 49.59% (Test).
- **Economic Formula Alignment:** Perfect bit-for-bit mathematical consistency between `evaluate_sell_vs_store`, `calculate_break_even_future_price`, and `run_economic_backtest` across all 144 baseline and 576 quality-discount sensitivity records.

### Tier B: Supported by the Available Exploratory Evidence
- **Model Selectivity Outperforms Heuristic Baselines:** The model policy generates positive average incremental returns (+₹33.55 Val, +₹42.21 Test per eligible qtl) outperforming both Always Store (-₹28 to -₹30 / qtl) and Trailing Momentum (-₹68 to -₹80 / qtl) across all 8 evaluated calendar months.
- **Cluster Bootstrap Uncertainty Bounds:** 95% confidence intervals for mean return remain positive ([+₹16.53, +₹54.97] on Val, [+₹27.37, +₹57.21] on Test), while the 95% CI for the win rate is strictly bounded below 45% ([32.48%, 44.43%] Val, [32.88%, 42.48%] Test).
- **The Threshold Trade-Off:** Probability filtering ($P \ge 0.60$) raises win rate marginally to 46.8%–46.9% while collapsing decision volume by >80% and reducing net gain by >70%.

### Tier C: Sensitive to Assumptions or Sample Selection
- **Break-Even Tipping Boundaries:** Positive economic expectation persists across central warehousing tariffs (₹10–₹50/qtl) and mild losses (0.5%–2%), but collapses into negative returns when physical loss reaches $\ge 5\%$, quality markdown reaches $\ge 5\%-8\%$, or handling/freight friction reaches $\ge ₹75/\text{qtl}$.
- **Geographic and Subgroup Heterogeneity:** Positive returns are heavily concentrated in large peri-urban consuming markets (Ghaziabad: +₹99.62/qtl, Lucknow: +₹84.76/qtl) and semi-perishables (Onion, Rice). Five rural secondary mandis (Uttaripura, Choubepur, Gurusarai, Purwa, Mauranipur) exhibit negative policy returns.
- **Test Window Exploratory Status:** The May–August 2026 test partition was inspected across earlier research iterations and represents an exploratory historical window, not an untouched blind holdout.

### Tier D: Not Established by the Available Data
- **Causality of Mandi Price Dynamics:** Observational APMC price series cannot establish economic causality or identify whether price swings are driven by arrival supply shocks, speculative hoarding, or external weather events.
- **Farmgate Realized Net Prices:** Modal APMC prices do not reflect individual farmer transaction realities, including commission agent cuts (1.5%–2.5%), subjective grading discounts, unloading charges, transport costs, or distress liquidation pressures.
- **Physical Feasibility of Tactical Storage:** Price data provides zero evidence regarding whether village-level farmers possess physical access to licensed public warehouses or cold storages willing to accept 10-quintal batches for 7-day tactical holding.
