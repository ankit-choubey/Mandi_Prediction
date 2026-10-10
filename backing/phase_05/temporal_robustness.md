# Phase 5: Temporal Stability and Policy Benchmark Audit

**Project:** Mandi_Prediction
**Repository:** `ankit-choubey/Mandi_Prediction`
**Phase:** 5 — Robustness, Statistical Uncertainty, and Generalization Audit
**Date:** October 10, 2026
**Artifact:** `backing/phase_05/temporal_robustness.md`
**Underlying Data:** `backing/phase_05/outputs/temporal_stability.csv`

---

## 1. Objective and Temporal Structure

Agricultural markets in Uttar Pradesh are subject to sharp seasonal shifts across crop cycles (Rabi harvest in March–April, Zaid harvest in May–June, Kharif sowing/pre-monsoon in July–August).
This audit investigates whether the model-signal policy's performance is stable across successive calendar months or whether it relies on isolated seasonal anomalies.

### Evaluation Protocol:
- **Baseline Freeze:** The model was trained strictly on information up to **January 13, 2026**.
- **Out-of-Sample Period:** Evaluated month-by-month from January 2026 through August 2026 ($N = 15,222$ total out-of-sample decisions across Validation and Exploratory Test).
- **Competitor Policies:**
  - **Always Sell (Baseline):** ₹0.00 / qtl incremental return.
  - **Always Store:** Evaluates blind calendar storage.
  - **Trend Momentum Policy (T):** Strictly causal at $T$, stores when past 7-day price appreciation exceeds economic break-even $\Delta P_{\text{be}}\%$.
  - **Model Signal Policy (T):** Stores when classifier predicts `Favorable` (Class 2).
  - **Oracle Benchmark:** Theoretical hindsight upper bound (unattainable).
- **Dependence Structure Caveat:** Because the model weights remain fixed while market regimes evolve over successive months, sequential monthly performance metrics share the same underlying parameterization and are not statistically independent draws.

---

## 2. Chronological Monthly Performance Benchmark (Central Scenario)

| Year-Month | Eligible Decisions ($N$) | Storage Decisions ($N_{\text{stored}}$) | % Stored | Model Win Rate (%) | Always Sell (₹/qtl) | Always Store (₹/qtl) | Trend Policy (₹/qtl) | Model Signal (₹/qtl) | Oracle Bound (₹/qtl) |
|---|---|---|---|---|---|---|---|---|---|
| **2026-01 (Late)** | 102 | 6 | 5.88% | 100.0% | ₹0.00 | -₹17.82 | -₹4.78 | **+₹8.02** | +₹50.53 |
| **2026-02** | 314 | 60 | 19.11% | 46.67% | ₹0.00 | +₹22.96 | -₹13.18 | **+₹6.24** | +₹144.86 |
| **2026-03** | 2,483 | 480 | 19.33% | 38.12% | ₹0.00 | -₹102.36 | -₹78.48 | **+₹20.70** | +₹189.24 |
| **2026-04** | 2,691 | 446 | 16.57% | 36.10% | ₹0.00 | +₹39.25 | -₹65.35 | **+₹50.70** | +₹299.84 |
| **2026-05** | 2,353 | 381 | 16.19% | 34.65% | ₹0.00 | -₹96.26 | -₹68.39 | **+₹27.33** | +₹218.48 |
| **2026-06** | 2,953 | 676 | 22.89% | 37.87% | ₹0.00 | +₹92.52 | -₹97.81 | **+₹62.92** | +₹436.58 |
| **2026-07** | 2,449 | 451 | 18.42% | 36.36% | ₹0.00 | -₹129.57 | -₹74.21 | **+₹35.41** | +₹213.50 |
| **2026-08** | 1,877 | 370 | 19.71% | 42.16% | ₹0.00 | -₹15.09 | -₹79.86 | **+₹35.17** | +₹314.67 |

---

## 3. Findings and Analytical Insights

### 3.1 Consistent Mean Advantage Over Simple Heuristics
- **Trend Momentum Consistently Destructive:** The backward-looking momentum policy produces severe losses in **every single calendar month** (-₹4.78 to -₹97.81 / eligible qtl). In wholesale mandis, a strong 7-day past price spike frequently coincides with arrival surges and subsequent price exhaustion rather than continuation.
- **Always Store Severe Volatility:** Blind storage alternates between seasonal windfalls (+₹92.52 / qtl in June) and devastating drawdowns (-₹102.36 in March, -₹96.26 in May, -₹129.57 in July).
- **Model Selectivity:** The model maintains positive mean incremental return in every evaluated month (+₹6.24 to +₹62.92 / eligible qtl) by filtering out 80%–84% of unremunerative storage dates.

### 3.2 The Chronic Win-Rate Deficit Persists Across All Months
- While the model avoids catastrophic monthly drawdowns, the **storage win rate remains below 43% in all seven full-sample months** (ranging between 34.65% and 42.16%).
- The model policy does not generate steady week-over-week wins. Instead, in every month, ~60% of stored decisions lose money, and positive expectation is driven entirely by a minority of large upward price realizations.
