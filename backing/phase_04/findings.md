# Phase 4 Findings: Economic Decision Support and Sell-versus-Store Validation

**Project:** Mandi_Prediction
**Repository:** `ankit-choubey/Mandi_Prediction`
**Phase:** 4 — Economic Decision Support and Sell-versus-Store Validation
**Date:** October 10, 2026
**Status:** **METHODOLOGY & CODE VERIFIED (RESEARCH PROTOTYPE; LOCAL FARMER PARAMETERS UNVALIDATED)**
**Operational Verdict:** **STRICTLY NOT APPROVED FOR OPERATIONAL FARMER ADVICE**

---

## 1. Executive Summary

Phase 4 evaluated the empirical economic feasibility of using machine-learning market condition classifications to guide tactical 7-day agricultural storage decisions across major APMC mandis in Uttar Pradesh.

### Core Empirical Conclusions:
1. **Blind Storage Fails Substantially:**
   - Under central storage costs (₹20/qtl storage, 1% physical loss, 7% KCC opportunity interest), an "Always Store" policy produces an average **loss of -₹30.32 / eligible quintal (Validation)** and **-₹28.29 / eligible quintal (Exploratory Test)**.
   - Under conservative costs (₹35/qtl, 2% loss, 12% interest), blind storage loses **-₹117.21 / eligible quintal** and **-₹122.37 / eligible quintal**, winning in fewer than 19% of market dates.
2. **Simple Trailing Momentum Fails:**
   - Storing based on whether trailing 7-day momentum exceeds break-even loses **-₹68.02 / eligible qtl (Validation)** and **-₹80.72 / eligible qtl (Exploratory Test)**; in this sample, trailing weekly price appreciation did not reliably persist into the subsequent 7-day holding window.
3. **Model Selectivity Generates Positive Mean Returns but Unacceptable Smallholder Risk:**
   - Storing only when the gradient-boosted classifier forecasts a `Favorable` market condition ($> +2.5\%$ appreciation) yields positive average incremental returns across all scenarios:
     - **Central Scenario:** **+₹33.55 / eligible qtl** (Validation) and **+₹42.21 / eligible qtl** (Exploratory Test); conditional on storage, returns average **+₹190.27 / stored qtl** (Validation) and **+₹215.60 / stored qtl** (Exploratory Test).
     - **Conservative Scenario:** **+₹25.26 / eligible qtl** (Validation) and **+₹31.98 / eligible qtl** (Exploratory Test); conditional on storage: **+₹143.25 / stored qtl** (Validation) and **+₹163.31 / stored qtl** (Exploratory Test).
     - **Optimistic Scenario:** **+₹36.82 / eligible qtl** (Validation) and **+₹46.12 / eligible qtl** (Exploratory Test); conditional on storage: **+₹208.80 / stored qtl** (Validation) and **+₹235.53 / stored qtl** (Exploratory Test).
   - **CRITICAL OPERATIONAL RISK DEFICIT:**
     - The **storage win rate is only 37.8% – 37.9%**. In **62.2% of decisions where the model advises storage, storing resulted in a net financial loss compared to selling immediately**.
     - Severe downside tail risk: The 5th percentile outcome when stored is **-₹232.36 / qtl (Validation)** and **-₹331.75 / qtl (Exploratory Test)**. Worst-case losses identify acute tail risk in specific market partitions and cost scenarios:
       - Validation Partition: **-₹3,674.71 / qtl (Central)**, **-₹3,776.20 / qtl (Conservative)**.
       - Exploratory Test Partition: **-₹18,741.94 / qtl (Central)**, **-₹18,914.28 / qtl (Conservative)**.
   - An unhedged decision rule with a 62.2% loss frequency and heavy downside tail distribution represents an unacceptable risk profile for practical deployment. Individual farmers' risk preferences, household liquidity buffers, and operating margins cannot be observed or inferred from aggregate APMC mandi price series, but the empirical loss distribution alone precludes operational recommendation.
4. **Phase 4 Determination:**
   The economic decision formulas and pipeline are unit-tested and computationally verified. However, **farmer-facing recommendations are strictly NOT approved**. Reported backtest outcomes represent simulated results under stylized assumptions, distinct from independently validated field trial evidence. Local storage rates, physical shrinkage, quality degradation, and liquidity costs remain illustrative assumptions informed by public benchmarks rather than locally validated farmgate measurements. Furthermore, the May–August 2026 test partition is explicitly an exploratory historical evaluation window, not an untouched blind holdout.

---

## 2. Policy Performance Benchmark Matrix

Evaluated on exact calendar $T+7$ matches across the chronological Validation partition ($n = 5,671$) and Exploratory Test partition ($n = 9,551$) with 8-day purged embargo buffers.

**Metric Definitions and Denominators:**
- **Unconditional Mean Return (₹/eligible qtl):** $\mu_{\text{eligible}} = \frac{1}{N} \sum_{k=1}^N (d_k \Delta r_k)$, where $N = \text{Eligible Decisions}$ and SELL decisions contribute ₹0.00.
- **Mean Gain (₹ / 10-qtl eligible decision):** $10 \times \mu_{\text{eligible}}$.
- **Conditional Mean Return (₹/stored qtl):** $\mu_{\text{stored}} = \frac{1}{N_{\text{stored}}} \sum_{k: d_k=1} \Delta r_k$, calculated strictly over the $N_{\text{stored}}$ decisions where produce was stored.
- **Aggregate Net Gain (₹ / all decisions):** $\sum_{k=1}^N (10 \cdot d_k \Delta r_k) = N \times (10 \cdot \mu_{\text{eligible}})$. Total financial sum assuming each decision was 10 quintals.
- **Storage Win Rate (%):** Fraction of STORE decisions where storage beat immediate selling ($\Delta r_k > 0$).

### 2.1 Validation Partition Results ($n = 5,671$, Jan 2026 – May 2026)

| Scenario | Decision Policy | Times Stored | % Stored | Storage Win Rate (%) | Unconditional Return (₹/eligible qtl) | Mean Gain (₹ / 10-qtl decision) | Conditional Return (₹/stored qtl) | Aggregate Net Gain (₹ / all decisions) | 5th Percentile (₹/qtl) |
|---|---|---|---|---|---|---|---|---|---|
| **Central** | **Always Sell (Baseline)** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| | **Always Store** | 5,671 | 100.0% | 25.89% | **-₹30.32** | -₹303.16 | -₹30.32 | -₹1,719,222.39 | -₹922.99 |
| | **Trend Momentum (T)** | 896 | 15.80% | 22.10% | **-₹68.02** | -₹680.21 | -₹430.52 | -₹3,857,483.49 | -₹2,701.09 |
| | **Model Signal (T)** | 1,000 | 17.63% | 37.90% | **+₹33.55** | +₹335.52 | **+₹190.27** | +₹1,902,741.76 | **-₹232.36** |
| | **Oracle Benchmark (Upper Bound)** | 1,468 | 25.89% | 100.0% | **+₹234.36** | +₹2,343.58 | +₹905.34 | +₹13,290,460.97 | +₹8.48 |
| **Conservative** | **Always Sell** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| | **Always Store** | 5,671 | 100.0% | 18.92% | **-₹117.21** | -₹1,172.14 | -₹117.21 | -₹6,647,183.38 | -₹1,080.68 |
| | **Trend Momentum (T)** | 624 | 11.00% | 15.54% | **-₹76.06** | -₹760.62 | -₹691.26 | -₹4,313,490.37 | -₹3,829.72 |
| | **Model Signal (T)** | 1,000 | 17.63% | 29.00% | **+₹25.26** | +₹252.60 | **+₹143.25** | +₹1,432,497.48 | **-₹283.42** |
| | **Oracle Benchmark (Upper Bound)** | 1,073 | 18.92% | 100.0% | **+₹206.22** | +₹2,062.24 | +₹1,089.93 | +₹11,694,940.66 | +₹7.45 |
| **Optimistic** | **Always Sell** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| | **Always Store** | 5,671 | 100.0% | 28.83% | **-₹1.02** | -₹10.15 | -₹1.02 | -₹57,576.35 | -₹876.86 |
| | **Trend Momentum (T)** | 1,005 | 17.72% | 25.07% | **-₹63.71** | -₹637.13 | -₹359.52 | -₹3,613,139.85 | -₹2,416.97 |
| | **Model Signal (T)** | 1,000 | 17.63% | 42.40% | **+₹36.82** | +₹368.19 | **+₹208.80** | +₹2,088,028.40 | **-₹216.15** |
| | **Oracle Benchmark (Upper Bound)** | 1,635 | 28.83% | 100.0% | **+₹244.53** | +₹2,445.33 | +₹848.16 | +₹13,867,467.87 | +₹9.27 |

---

### 2.2 Exploratory Historical Test Partition Results ($n = 9,551$, May 2026 – Aug 2026)

| Scenario | Decision Policy | Times Stored | % Stored | Storage Win Rate (%) | Unconditional Return (₹/eligible qtl) | Mean Gain (₹ / 10-qtl decision) | Conditional Return (₹/stored qtl) | Aggregate Net Gain (₹ / all decisions) | 5th Percentile (₹/qtl) |
|---|---|---|---|---|---|---|---|---|---|
| **Central** | **Always Sell (Baseline)** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| | **Always Store** | 9,551 | 100.0% | 24.15% | **-₹28.29** | -₹282.88 | -₹28.29 | -₹2,701,769.67 | -₹1,409.08 |
| | **Trend Momentum (T)** | 1,559 | 16.32% | 23.41% | **-₹80.72** | -₹807.21 | -₹494.53 | -₹7,709,706.61 | -₹3,501.94 |
| | **Model Signal (T)** | 1,870 | 19.58% | 37.81% | **+₹42.21** | +₹422.13 | **+₹215.60** | +₹4,031,741.12 | **-₹331.75** |
| | **Oracle Benchmark (Upper Bound)** | 2,307 | 24.15% | 100.0% | **+₹305.22** | +₹3,052.18 | +₹1,263.61 | +₹29,151,388.05 | +₹9.38 |
| **Conservative** | **Always Sell** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| | **Always Store** | 9,551 | 100.0% | 18.58% | **-₹122.37** | -₹1,223.66 | -₹122.37 | -₹11,687,177.26 | -₹1,553.47 |
| | **Trend Momentum (T)** | 1,183 | 12.39% | 20.03% | **-₹91.42** | -₹914.21 | -₹738.09 | -₹8,731,633.41 | -₹4,202.32 |
| | **Model Signal (T)** | 1,870 | 19.58% | 30.75% | **+₹31.98** | +₹319.75 | **+₹163.31** | +₹3,053,950.74 | **-₹375.24** |
| | **Oracle Benchmark (Upper Bound)** | 1,775 | 18.58% | 100.0% | **+₹275.66** | +₹2,756.59 | +₹1,483.28 | +₹26,328,237.34 | +₹14.50 |
| **Optimistic** | **Always Sell** | 0 | 0.0% | 0.0% | **₹0.00** | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| | **Always Store** | 9,551 | 100.0% | 28.07% | **+₹2.94** | +₹29.40 | +₹2.94 | +₹280,760.34 | -₹1,353.30 |
| | **Trend Momentum (T)** | 1,830 | 19.16% | 27.32% | **-₹73.59** | -₹735.92 | -₹384.09 | -₹7,028,817.23 | -₹2,904.21 |
| | **Model Signal (T)** | 1,870 | 19.58% | 42.35% | **+₹46.12** | +₹461.16 | **+₹235.53** | +₹4,404,496.55 | **-₹310.30** |
| | **Oracle Benchmark (Upper Bound)** | 2,681 | 28.07% | 100.0% | **+₹315.70** | +₹3,157.04 | +₹1,124.69 | +₹30,152,888.96 | +₹6.33 |

---

## 3. Commodity-Level Economic Breakdown (Central Scenario, Exploratory Test)

| Commodity | Sample Count | Always Store Win Rate | Always Store Unconditional Return | Model Stored Decisions | Model Win Rate | Model Unconditional Return | Model Conditional Return | P05 Loss on Model Policy |
|---|---|---|---|---|---|---|---|---|
| **Wheat** | 2,424 | 8.79% | -₹44.41 / qtl | 13 | 15.38% | **-₹0.22 / qtl** | -₹40.39 / qtl | -₹189.07 / qtl |
| **Potato** | 572 | 11.19% | -₹27.42 / qtl | 229 | 20.52% | **+₹5.66 / qtl** | +₹14.14 / qtl | -₹106.98 / qtl |
| **Onion** | 380 | 39.47% | +₹87.87 / qtl | 114 | 55.26% | **+₹46.47 / qtl** | +₹154.89 / qtl | -₹234.57 / qtl |
| **Tomato** | 342 | 26.02% | -₹14.63 / qtl | 102 | 35.29% | **-₹3.14 / qtl** | -₹10.54 / qtl | -₹337.13 / qtl |
| **Rice** | 374 | 35.03% | +₹51.28 / qtl | 94 | 55.32% | **+₹148.81 / qtl** | +₹592.06 / qtl | -₹658.71 / qtl |

### Key Insights:
- **Cereals (Wheat):** Storing wheat for 7 days is economically unviable under the tested 7-day tactical horizon and stated cost assumptions in this sample. Observed price movement over 7 days rarely covers ₹20/qtl storage and 1% shrinkage.
- **Perishables (Tomato):** Storing tomatoes yields negative returns on average due to rapid quality degradation and sharp downward market price swings.
- **Semi-Perishables (Onion, Rice):** High price volatility allows the model policy to capture positive average returns (+₹46 to +₹148 / qtl unconditional; +₹154 to +₹592 / qtl conditional), but tail risk is extreme (worst cases reach -₹658 to -₹5,200 / qtl).

---

## 4. Final Recommendation and Next Steps

1. **System Status:** Phase 4 successfully establishes the mathematical framework, calibrated sensitivity bounds, and leakage-safe backtest.
2. **Farmer Advice Gate:** **REJECTED FOR PRODUCTION USE.** The high loss rate (62%) and severe tail risk preclude operational deployment for smallholders.
3. **Future Research Requirements:**
   - Multi-horizon storage analysis (e.g. 1-month to 3-month seasonal holding rather than tactical 7-day holding).
   - Integration of localized warehouse inventory, cold storage availability, and freight transit cost models.
   - Downside risk-hedging and minimum price guarantee thresholds before issuing store recommendations.
