# Phase 4 Findings: Economic Decision Support and Sell-versus-Store Validation

**Project:** Mandi_Prediction  
**Repository:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 4 — Economic Decision Support and Sell-versus-Store Validation  
**Date:** October 10, 2026  
**Status:** **RESEARCH COMPLETED (VERIFIED)**  
**Operational Verdict:** **NOT APPROVED FOR OPERATIONAL FARMER DEPLOYMENT**

---

## 1. Executive Summary

Phase 4 evaluated the empirical economic feasibility of using machine-learning market condition classifications to guide tactical 7-day agricultural storage decisions across major APMC mandis in Uttar Pradesh.

### Core Empirical Conclusions:
1. **Blind Storage Fails Catastrophically:**
   - Under central storage costs (₹20/qtl storage, 1% physical loss, 7% KCC opportunity interest), an "Always Store" policy produces an average **loss of -₹30.32 / quintal (Validation)** and **-₹28.29 / quintal (Exploratory Test)**.
   - Under conservative costs (₹35/qtl, 2% loss, 12% interest), blind storage loses **-₹117.21 / quintal** and **-₹122.37 / quintal**, winning in fewer than 19% of market dates.
2. **Simple Trailing Momentum Fails:**
   - Storing based on whether trailing 7-day momentum exceeds break-even loses **-₹68.02 / qtl (Validation)** and **-₹80.72 / qtl (Exploratory Test)** due to aggressive weekly mean-reversion in wholesale mandis.
3. **Model Selectivity Generates Positive Mean Returns but Unacceptable Smallholder Risk:**
   - Storing only when the gradient-boosted classifier forecasts a `Favorable` market condition ($> +2.5\%$ appreciation) yields positive average incremental returns across all scenarios:
     - **Central Scenario:** **+₹33.55 / qtl** (Validation) and **+₹42.21 / qtl** (Exploratory Test).
     - **Conservative Scenario:** **+₹25.26 / qtl** (Validation) and **+₹31.98 / qtl** (Exploratory Test).
     - **Optimistic Scenario:** **+₹36.82 / qtl** (Validation) and **+₹46.12 / qtl** (Exploratory Test).
   - **CRITICAL OPERATIONAL RISK DEFICIT:**
     - The **storage win rate is only 37.8% – 37.9%**. In **62.2% of decisions where the model advises storage, storing resulted in a net financial loss compared to selling immediately**.
     - Severe downside tail risk: The 5th percentile outcome when stored is **-₹232.36 / qtl (Validation)** and **-₹331.75 / qtl (Exploratory Test)**, with worst-case losses exceeding **-₹3,600 to -₹18,000 / qtl** during sudden commodity arrival crashes.
   - Smallholder farmers operating near subsistence cannot withstand a 62% failure rate or catastrophic downside drawdowns.
4. **Phase 4 Determination:**
   The economic decision layer is mathematically verified and reproducible. However, **farmer-facing recommendations are strictly NOT approved**.

---

## 2. Policy Performance Benchmark Matrix

Evaluated on exact calendar $T+7$ matches across the chronological Validation partition ($n = 5,671$) and Exploratory Test partition ($n = 9,551$) with 8-day purged embargo buffers:

### 2.1 Validation Partition Results ($n = 5,671$, Jan 2026 – May 2026)

| Scenario | Decision Policy | Times Stored | % Stored | Storage Win Rate (%) | Mean Incremental Return (₹/qtl) | Total Net Gain (₹ / 10 qtl batch) | 5th Percentile Outcome (₹/qtl) |
|---|---|---|---|---|---|---|---|
| **Central** | **Always Sell (Baseline)** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 |
| | **Always Store** | 5,671 | 100.0% | 25.89% | **-₹30.32** | -₹1,719,222 | -₹922.99 |
| | **Trend Momentum (T)** | 896 | 15.80% | 22.10% | **-₹68.02** | -₹3,857,483 | -₹2,701.09 |
| | **Model Signal (T)** | 1,000 | 17.63% | 37.90% | **+₹33.55** | +₹1,902,742 | **-₹232.36** |
| | **Oracle Benchmark (Upper Bound)** | 1,468 | 25.89% | 100.0% | **+₹234.36** | +₹13,290,461 | +₹8.48 |
| **Conservative** | **Always Sell** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 |
| | **Always Store** | 5,671 | 100.0% | 18.92% | **-₹117.21** | -₹6,647,183 | -₹1,080.68 |
| | **Trend Momentum (T)** | 624 | 11.00% | 15.54% | **-₹76.06** | -₹4,313,490 | -₹3,829.72 |
| | **Model Signal (T)** | 1,000 | 17.63% | 29.00% | **+₹25.26** | +₹1,432,497 | **-₹283.42** |
| | **Oracle Benchmark (Upper Bound)** | 1,073 | 18.92% | 100.0% | **+₹206.22** | +₹11,694,941 | +₹7.45 |
| **Optimistic** | **Always Sell** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 |
| | **Always Store** | 5,671 | 100.0% | 28.83% | **-₹1.02** | -₹57,576 | -₹876.86 |
| | **Trend Momentum (T)** | 1,005 | 17.72% | 25.07% | **-₹63.71** | -₹3,613,140 | -₹2,416.97 |
| | **Model Signal (T)** | 1,000 | 17.63% | 42.40% | **+₹36.82** | +₹2,088,028 | **-₹216.15** |
| | **Oracle Benchmark (Upper Bound)** | 1,635 | 28.83% | 100.0% | **+₹244.53** | +₹13,867,468 | +₹9.27 |

---

### 2.2 Exploratory Historical Test Partition Results ($n = 9,551$, May 2026 – Aug 2026)

| Scenario | Decision Policy | Times Stored | % Stored | Storage Win Rate (%) | Mean Incremental Return (₹/qtl) | Total Net Gain (₹ / 10 qtl batch) | 5th Percentile Outcome (₹/qtl) |
|---|---|---|---|---|---|---|---|
| **Central** | **Always Sell (Baseline)** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 |
| | **Always Store** | 9,551 | 100.0% | 24.15% | **-₹28.29** | -₹2,701,770 | -₹1,409.08 |
| | **Trend Momentum (T)** | 1,559 | 16.32% | 23.41% | **-₹80.72** | -₹7,709,707 | -₹3,501.94 |
| | **Model Signal (T)** | 1,870 | 19.58% | 37.81% | **+₹42.21** | +₹4,031,741 | **-₹331.75** |
| | **Oracle Benchmark (Upper Bound)** | 2,307 | 24.15% | 100.0% | **+₹305.22** | +₹29,151,388 | +₹9.38 |
| **Conservative** | **Always Sell** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 |
| | **Always Store** | 9,551 | 100.0% | 18.58% | **-₹122.37** | -₹11,687,177 | -₹1,553.47 |
| | **Trend Momentum (T)** | 1,183 | 12.39% | 20.03% | **-₹91.42** | -₹8,731,633 | -₹4,202.32 |
| | **Model Signal (T)** | 1,870 | 19.58% | 30.75% | **+₹31.98** | +₹3,053,951 | **-₹375.24** |
| | **Oracle Benchmark (Upper Bound)** | 1,775 | 18.58% | 100.0% | **+₹275.66** | +₹26,328,237 | +₹14.50 |
| **Optimistic** | **Always Sell** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 |
| | **Always Store** | 9,551 | 100.0% | 28.07% | **+₹2.94** | +₹280,760 | -₹1,353.30 |
| | **Trend Momentum (T)** | 1,830 | 19.16% | 27.32% | **-₹73.59** | -₹7,028,817 | -₹2,904.21 |
| | **Model Signal (T)** | 1,870 | 19.58% | 42.35% | **+₹46.12** | +₹4,404,497 | **-₹310.30** |
| | **Oracle Benchmark (Upper Bound)** | 2,681 | 28.07% | 100.0% | **+₹315.70** | +₹30,152,889 | +₹6.33 |

---

## 3. Commodity-Level Economic Breakdown (Central Scenario, Exploratory Test)

| Commodity | Sample Count | Always Store Mean Return | Always Store Win Rate | Model Policy Mean Return | Model Policy Win Rate | P05 Loss on Model Policy |
|---|---|---|---|---|---|---|
| **Wheat** | 2,424 | -₹44.41 / qtl | 8.79% | **-₹0.22 / qtl** | 15.38% | -₹189.07 / qtl |
| **Potato** | 572 | -₹27.42 / qtl | 11.19% | **+₹5.66 / qtl** | 20.52% | -₹106.98 / qtl |
| **Onion** | 380 | +₹87.87 / qtl | 39.47% | **+₹46.47 / qtl** | 55.26% | -₹234.57 / qtl |
| **Tomato** | 342 | -₹14.63 / qtl | 26.02% | **-₹3.14 / qtl** | 35.29% | -₹337.13 / qtl |
| **Rice** | 374 | +₹51.28 / qtl | 35.03% | **+₹148.81 / qtl** | 55.32% | -₹658.71 / qtl |

### Key Insights:
- **Cereals (Wheat):** Storing wheat for 7 days is strictly economically irrational. The price movement over 7 days rarely covers ₹20/qtl storage and 1% shrinkage.
- **Perishables (Tomato):** Storing tomatoes yields negative returns on average due to rapid quality degradation and arrival gluts.
- **Semi-Perishables (Onion, Rice):** High price volatility allows the model policy to capture positive average returns (+₹46 to +₹148 / qtl), but tail risk is extreme (worst cases reach -₹658 to -₹5,200 / qtl).

---

## 4. Final Recommendation and Next Steps

1. **System Status:** Phase 4 successfully establishes the mathematical framework, calibrated sensitivity bounds, and leakage-safe backtest.
2. **Farmer Advice Gate:** **REJECTED FOR PRODUCTION USE.** The high loss rate (62%) and severe tail risk preclude operational deployment for smallholders.
3. **Future Research Requirements:**
   - Multi-horizon storage analysis (e.g. 1-month to 3-month seasonal holding rather than tactical 7-day holding).
   - Integration of localized warehouse inventory, cold storage availability, and freight transit cost models.
   - Downside risk-hedging and minimum price guarantee thresholds before issuing store recommendations.
