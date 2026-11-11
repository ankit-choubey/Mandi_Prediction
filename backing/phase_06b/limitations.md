# Phase 06b: Comprehensive System Limitations, Structural Risks & Governance Directives

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 06b — Data Discovery, Validation & Mathematical Feasibility  
**Date:** October 2026  
**Auditor:** Priyanshu  

---

## 1. Executive Directive: Strict Continuation of Operational Prohibition

> **MANDATORY POLICY DIRECTIVE:**
> **The Mandi Market Intelligence System is an experimental research prototype. It is strictly PROHIBITED from being deployed for farmer-facing operational advice or used to recommend that individual agricultural producers hold or store produce rather than sell immediately.**

While machine-learning classification models achieve statistically detectable predictive skill over naive baselines on unseen holdouts (+4.50% accuracy gain, $p < 0.001$), Phase 06b empirical feasibility tests reveal insurmountable structural, economic, and physical barriers to operational deployment.

---

## 2. Structural & Statistical Limitations

### 2.1 The Regression Failure Invariant
- **Empirical Reality:** Across all five tested forward horizons ($T+1, T+3, T+7, T+14, T+30$), continuous machine-learning regression (LightGBM / Ridge) fails to beat simple zero-return price stickiness persistence out-of-sample.
- **Root Cause:** Modal price stickiness (18%–36% of days have exactly 0.00% price change) combined with heavy-tailed non-Gaussian volatility spikes. Regression models overfit to noise and predict small non-zero drift values that inflate absolute errors relative to predicting no change.
- **Operational Implication:** The system cannot provide reliable numerical price forecasts (e.g. "Wheat will be ₹2,435.50 in 7 days"). It can only provide directional market condition indicators.

### 2.2 Threshold Trapping under Fixed Bands
- **Empirical Reality:** Under the standard fixed $\pm 2.5\%$ convention (DEC-015), **59.48%** of $T+7$ records and **80.08%** of $T+1$ records fall into the "Normal" (stable) class.
- **Root Cause:** Mandi modal quotes are sticky. A fixed percentage band captures the vast majority of regular trading days in a single class, resulting in severe class imbalance (3.15x to 6.25x ratio).
- **Operational Implication:** Accuracy alone cannot evaluate model quality. Models must be benchmarked against the 59.5% majority class baseline and evaluated on Macro F1 and Balanced Accuracy.

### 2.3 The Bundelkhand Generalization Deficit (Cross-District Transfer)
- **Empirical Reality:** When an ML model trained on Ghaziabad, Kanpur, Lucknow, and Unnao is evaluated on **Jhansi** (Leave-One-District-Out), its test accuracy drops to **53.86%**, which is **worse than the naive 54.67% baseline** (-0.81% gain).
- **Root Cause:** Jhansi belongs to the semi-arid Bundelkhand agro-climatic zone, with distinct cropping patterns, water scarcity constraints, and pulse/oilseed trading dynamics that cannot be generalized from Indo-Gangetic plain mandis.
- **Operational Implication:** **Pan-India generalization from a unified model is an illusion.** Any future national rollout must train localized models partitioned by Agro-Climatic Zones.

---

## 3. Physical & Agronomic Limitations

### 3.1 The Perishable Storage Fallacy
- **Empirical Reality:** Storing perishables (Tomato, Cucumber, Brinjal, Cabbage) for 7 days under ambient or ventilated on-farm conditions results in an **empirical economic loss in 93.06% of historical cases** (storage win rate = 6.94%).
- **Agronomic Cause:** Fresh vegetables have active respiration rates and high moisture content (90%–95%). At ambient temperatures in UP (25°C–42°C), physiological weight loss exceeds 8% to 12% per week, and bacterial/fungal decay causes 5% to 10% quality markdown.
- **The Hurdle:** To overcome an 8% physical shrinkage, 5% quality discount, and ₹50/qtl storage/handling friction, tomato prices must surge by **+18.06% in 7 calendar days** just to break even. In historical APMC data, mean weekly price change is only +0.49%. Advising a smallholder to hold fresh tomatoes for 7 days without specialized refrigerated cold storage is financial malpractice.

### 3.2 The Grain Horizon Mismatch
- **Empirical Reality:** Storing durable food grains (Wheat, Rice, Maize) for 7 days loses money in **87.25% of cases** (storage win rate = 12.75%).
- **Economic Cause:** Fixed loading, unloading, weighing, and bagging charges (Palledari = ₹15–₹25/qtl) impose an immediate transaction friction that exceeds normal weekly price fluctuations (+0.59% mean weekly change).
- **Correct Horizon:** Grains are economically viable for storage only over **60 to 180-day seasonal horizons** (absorbing the post-harvest glut discount into the lean season premium), NOT 7-day tactical holding.

---

## 4. Operational & Farmgate Data Blindspots

### 4.1 Omission of Commission Agent (Arhatiya) Cuts & Informal Grading
- Mandi trade data records the official auctioned modal price at the APMC yard. It does NOT record:
  - Commission agent deductions (1.5% to 2.5%).
  - Subjective visual quality discounts imposed by buyers after auction.
  - Weighment deductions (Karda/dami) frequently forced on farmers.
  - Unloading and gate entry charges.
- Realized farmgate net proceeds are systematically 5% to 10% lower than published APMC modal quotes.

### 4.2 Non-Existent Smallholder Public Cold Chain Access
- Over 90% of cold storage capacity in Uttar Pradesh is privately owned and dedicated almost exclusively to multi-month bulk potato storage (500+ quintal minimum allocations).
- There is virtually zero public, regulated cold storage infrastructure near APMC mandis willing to accept a 5-to-10 quintal lot of tomatoes from a smallholder for a 7-day holding window.
- Assuming a farmer can simply "pay ₹17/qtl to store tomatoes for 7 days" is a theoretical abstraction disconnected from physical rural realities.

---

## 5. Governance Directives for Future Research

1. **Mandatory Research Disclaimer:** Every user-facing UI, API endpoint, or terminal output generated by this repository must display a prominent disclaimer stating that predictions represent experimental statistical prototypes and must not be used for binding financial decisions.
2. **Deprecation of 7-Day Storage Engine:** The 7-day sell-vs-store economic module must be formally frozen as an illustrative audit artifact and replaced in Phase 7 by a **multi-horizon crop-appropriate framework** ($T+1$ to $T+3$ for perishables; $T+60$ to $T+180$ for grains).
3. **No Synthetic Reality:** Synthetic cost scenarios may be used strictly for sensitivity testing; they must never be presented as empirical evidence of real-world farmer profitability.
