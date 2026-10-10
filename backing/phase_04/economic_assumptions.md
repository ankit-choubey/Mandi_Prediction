# Phase 4: Economic Assumptions and Calibrated Parameters

**Project:** Mandi_Prediction  
**Repository:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 4 — Economic Decision Support and Sell-versus-Store Validation  
**Date:** October 10, 2026  

---

## 1. Mathematical Notation and Units

The economic decision-support model evaluates whether a farmer should sell harvested produce immediately at Date $T$ or hold and sell at Date $T+7$ (7 calendar days).

| Symbol | Parameter Description | Base Unit | Dimensionality |
|---|---|---|---|
| $Q$ | Batch quantity of harvested produce | Quintals ($1 \text{ qtl} = 100 \text{ kg}$) | Batch volume |
| $P_T$ | Spot modal price observed at Date $T$ | Rupees per quintal (₹ / qtl) | Price per unit mass |
| $P_{T7}$ | Spot modal price observed at Date $T+7$ | Rupees per quintal (₹ / qtl) | Price per unit mass |
| $L$ | Physical quantity lost during storage | Dimensionless fraction ($0 \le L < 1$) | Shrinkage / spoilage rate |
| $c_s$ | Incremental storage cost per initial quintal | Rupees per initial quintal (₹ / qtl) | Direct storage expenditure |
| $c_h$ | Incremental handling and loading cost | Rupees per initial quintal (₹ / qtl) | In/out handling labor |
| $i$ | Annual financing or opportunity-cost rate | Decimal per annum ($0 \le i < 1$) | Carrying cost rate |
| $h$ | Holding period in calendar days | Days (fixed at $h = 7$) | Time duration |
| $d_q$ | Quality markdown / discount fraction | Dimensionless fraction ($0 \le d_q < 1$) | Degradation price discount |

---

## 2. Definitive Mathematical Formulas

### 2.1 Immediate Sale Baseline
$$R_{\text{sell}} = Q \times P_T$$
- Assumes harvest is sold at current spot modal price.
- Gross baseline representation (handling costs that are identical between immediate sale and storage sale cancel out).

### 2.2 Storage Sale Gross Proceeds
$$R_{\text{store\_gross}} = Q \times (1 - L) \times (1 - d_q) \times P_{T7}$$
- Physical quantity sold is reduced by $Q \times L$.
- Realized price is adjusted for any quality discount $P_{T7} \times (1 - d_q)$.

### 2.3 Net Storage Proceeds
$$R_{\text{store}} = R_{\text{store\_gross}} - Q \times (c_s + c_h) - Q \times P_T \times \left(\frac{i \times h}{365}\right)$$
- Safeguard A & B: Carrying cost represents EITHER borrowing interest OR opportunity cost of cash, never both simultaneously.

### 2.4 Incremental Benefit ($\Delta R$)
$$\Delta R = R_{\text{store}} - R_{\text{sell}} = Q \left[ (1 - L)(1 - d_q) P_{T7} - P_T \left(1 + \frac{i \times h}{365}\right) - (c_s + c_h) \right]$$
Per-quintal net benefit ($\Delta r = \Delta R / Q$):
$$\Delta r = (1 - L)(1 - d_q) P_{T7} - P_T \left(1 + \frac{i \times h}{365}\right) - (c_s + c_h)$$
Notice that for any positive batch size $Q > 0$, $\text{sign}(\Delta R) \equiv \text{sign}(\Delta r)$.

### 2.5 Break-Even Future Price ($P_{\text{break\_even}}$)
Setting $\Delta R = 0$ yields the exact future price required for storage to equal immediate sale:
$$P_{\text{break\_even}} = \frac{P_T \left(1 + \frac{i \times h}{365}\right) + (c_s + c_h)}{(1 - L)(1 - d_q)}$$
Required percentage price increase ($\Delta P_{\text{break\_even}}\%$):
$$\Delta P_{\text{break\_even}}\% = \left(\frac{P_{\text{break\_even}} - P_T}{P_T}\right) \times 100$$

---

## 3. Calibrated Scenario Definitions

Based on official reference documentation ([CWC Tariff FY 2026–27](./references/source_manifest.md#2-document-1-official-warehousing-tariff-reference) and [MoFPI Post-Harvest Loss Report 2022](./references/source_manifest.md#3-document-2-official-agricultural-post-harvest-loss-reference)), three scenarios are formally structured:

| Parameter | Optimistic Scenario | Central (Benchmark) Scenario | Conservative Scenario |
|---|---|---|---|
| **Storage & Handling Cost ($c_s + c_h$)** | ₹10.00 / quintal | ₹20.00 / quintal | ₹35.00 / quintal |
| **Physical Loss Fraction ($L$)** | 0.5% ($0.005$) | 1.0% ($0.010$) | 2.0% ($0.020$) |
| **Annual Carrying Rate ($i$)** | 4.0% p.a. ($0.04$) | 7.0% p.a. ($0.07$) | 12.0% p.a. ($0.12$) |
| **Carrying Cost Type** | Opportunity Cost | Opportunity Cost | Borrowing Interest |
| **Quality Markdown ($d_q$)** | 0.0% ($0.000$) | 0.0% ($0.000$) | 1.0% ($0.010$) |
| **Holding Horizon ($h$)** | 7 calendar days | 7 calendar days | 7 calendar days |
| **Operational Setting** | Low-cost on-farm / subsidized PACS ambient storage | Standard public warehouse benchmark (CWC slab) | Disadvantaged smallholder, private yard, perishable risk |

---

## 4. Break-Even Price Sensitivities Across Commodity Price Levels

Evaluating the required 7-day price appreciation across benchmark commodity price levels:

| Commodity Example | Spot Price ($P_T$) | Optimistic $\Delta P_{\text{be}}\%$ | Central $\Delta P_{\text{be}}\%$ | Conservative $\Delta P_{\text{be}}\%$ |
|---|---|---|---|---|
| **Potato / Tomato** | ₹1,500 / qtl | **+1.24%** | **+2.49%** | **+5.74%** |
| **Wheat / Paddy** | ₹2,500 / qtl | **+0.98%** | **+1.95%** | **+4.75%** |
| **Onion / Pulses** | ₹3,500 / qtl | **+0.86%** | **+1.71%** | **+4.33%** |

### Critical Finding: Threshold Divergence from Model Target
- The statistical classification target (DEC-015) defines a `Favorable` market condition as price appreciation $> +2.5\%$.
- In the **Central Scenario**, the economic break-even threshold is $+1.71\%$ to $+2.49\%$, which is close to the $+2.5\%$ threshold.
- However, in the **Conservative Scenario**, break-even requires **$+4.33\%$ to $+5.74\%$** appreciation. A generic `Favorable` prediction ($> +2.5\%$) is **insufficient** to guarantee net profitability under conservative costs.
