# Phase 5: Decision Rule and Probability Threshold Audit

**Project:** Mandi_Prediction
**Repository:** `ankit-choubey/Mandi_Prediction`
**Phase:** 5 — Robustness, Statistical Uncertainty, and Generalization Audit
**Date:** October 10, 2026
**Artifact:** `backing/phase_05/decision_rule_audit.md`
**Underlying Data:** `backing/phase_05/outputs/decision_rule_comparison.csv`

---

## 1. Objective and Hypothesis

The Phase 4 economic backtest utilized a simple argmax heuristic:
$$\text{Action}_T = \text{STORE} \iff \hat{Y}_T = \text{Favorable (Class 2)}$$
This audit tests whether:
1. Storing based on predicted probability thresholds $P(\text{Favorable} \mid X_T) \ge \tau$ improves the storage win rate or net return.
2. An optimal threshold calibrated strictly on Validation ($n = 5,671$) generalizes out-of-sample to the Exploratory Test partition ($n = 9,551$).
3. Probability filtering resolves the acute 62% failure rate deficit or merely reduces decision volume.

---

## 2. Empirical Decision Rule Evaluation Matrix (Central Scenario)

Evaluated across candidate decision rules on Validation and Exploratory Test:

| Partition | Decision Rule Description | Threshold ($\tau$) | Storage Decisions ($N_{\text{stored}}$) | % Stored | Storage Win Rate (%) | Unconditional Return (₹/eligible qtl) | Conditional Return (₹/stored qtl) |
|---|---|---|---|---|---|---|---|
| **Validation** | **Baseline Argmax ($\hat{Y} = 2$)** | — | 1,000 | 17.63% | **37.90%** | **+₹33.55** | +₹190.27 |
| | $P(\text{Favorable}) \ge 0.30$ | 0.30 | 1,648 | 29.06% | 33.50% | +₹43.04 | +₹148.12 |
| | $P(\text{Favorable}) \ge 0.35$ | 0.35 | 1,223 | 21.57% | 35.98% | +₹37.13 | +₹172.18 |
| | $P(\text{Favorable}) \ge 0.40$ | 0.40 | 858 | 15.13% | 37.30% | +₹27.40 | +₹181.10 |
| | $P(\text{Favorable}) \ge 0.45$ | 0.45 | 581 | 10.25% | 37.87% | +₹16.66 | +₹162.57 |
| | $P(\text{Favorable}) \ge 0.50$ | 0.50 | 386 | 6.81% | 38.34% | +₹8.32 | +₹122.22 |
| | $P(\text{Favorable}) \ge 0.55$ | 0.55 | 258 | 4.55% | 42.25% | +₹7.65 | +₹168.07 |
| | $P(\text{Favorable}) \ge 0.60$ | 0.60 | 156 | 2.75% | **46.79%** | **+₹7.17** | **+₹260.79** |
| **Exploratory Test** | **Baseline Argmax ($\hat{Y} = 2$)** | — | 1,870 | 19.58% | **37.81%** | **+₹42.21** | +₹215.60 |
| | $P(\text{Favorable}) \ge 0.30$ | 0.30 | 2,892 | 30.28% | 34.41% | +₹57.00 | +₹188.26 |
| | $P(\text{Favorable}) \ge 0.35$ | 0.35 | 2,331 | 24.41% | 35.74% | +₹52.40 | +₹214.70 |
| | $P(\text{Favorable}) \ge 0.40$ | 0.40 | 1,783 | 18.67% | 37.52% | +₹44.48 | +₹238.28 |
| | $P(\text{Favorable}) \ge 0.45$ | 0.45 | 1,345 | 14.08% | 40.15% | +₹36.16 | +₹256.79 |
| | $P(\text{Favorable}) \ge 0.50$ | 0.50 | 996 | 10.43% | 41.16% | +₹30.80 | +₹295.33 |
| | $P(\text{Favorable}) \ge 0.55$ | 0.55 | 654 | 6.85% | 43.73% | +₹19.26 | +₹281.30 |
| | $P(\text{Favorable}) \ge 0.60$ | 0.60 | 371 | 3.88% | **46.90%** | **+₹12.87** | **+₹331.26** |

---

## 3. Critical Analytical Findings

### 3.1 The Win-Rate Ceiling Cannot Be Broken by Confidence Filtering
- Even requiring an extreme forecast probability threshold of $P(\text{Favorable}) \ge 0.60$ (in a 3-class distribution where baseline frequency is ~19%):
  - The storage win rate **peaks at only 46.79% on Validation and 46.90% on Exploratory Test**.
  - **No tested threshold achieves a $> 50\%$ win rate**. In more than 53% of storage decisions under the highest confidence threshold, storing produce resulted in lower net returns than immediate sale.

### 3.2 Severe Return Starvation at High Thresholds
- Attempting to filter out bad storage decisions by raising $\tau$ to $0.50$ or $0.60$ **starves decision volume**:
  - Storage frequency plummets from ~18% down to 2.75% (Validation) and 3.88% (Exploratory Test).
  - Unconditional return per eligible quintal collapses by **78% on Validation** (+₹33.55 down to +₹7.17 / qtl) and by **70% on Exploratory Test** (+₹42.21 down to +₹12.87 / qtl).
- The high-threshold rule trades away the majority of cumulative economic gains for a negligible 8–9 percentage point gain in win rate.

### 3.3 Status of the Baseline Argmax Policy
- The baseline argmax rule ($\hat{Y} = 2$) implicitly functions as an effective threshold of approximately $P(\text{Favorable}) \approx 0.38 - 0.40$ against the Normal majority class.
- It strikes a balanced trade-off between volume and expected gain, but **neither argmax nor probability thresholding solves the underlying smallholder risk deficit**.
