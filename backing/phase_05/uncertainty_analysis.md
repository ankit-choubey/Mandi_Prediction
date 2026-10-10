# Phase 5: Statistical Uncertainty and Sampling Variation Analysis

**Project:** Mandi_Prediction
**Repository:** `ankit-choubey/Mandi_Prediction`
**Phase:** 5 — Robustness, Statistical Uncertainty, and Generalization Audit
**Date:** October 10, 2026
**Artifact:** `backing/phase_05/uncertainty_analysis.md`

---

## 1. Methodology: Cluster-Resampling by Canonical Market Series

### 1.1 Why Standard Row-Level I.I.D. Resampling is Invalid
Wholesale agricultural mandi transaction records exhibit substantial serial dependence and intra-series price correlation. Multiple daily price quotes from the same canonical series $\text{Series ID} = (\text{District}, \text{Market}, \text{Commodity}, \text{Variety}, \text{Grade})$ are subject to shared local market shocks, grading standards, and common harvest arrival waves. Treating individual rows as independent and identically distributed (i.i.d.) would artificially compress standard errors and yield overly narrow, overconfident confidence intervals.

### 1.2 Chosen Resampling Estimator: Cluster Bootstrap
To preserve intra-series temporal and cross-date dependencies while evaluating uncertainty across the population of trading series:
- **Resampling Unit:** Entire canonical series clusters.
- **Cluster Counts:**
  - **Validation Partition:** 354 unique series clusters across 5,671 records.
  - **Exploratory Test Partition:** 357 unique series clusters across 9,551 records.
- **Protocol:**
  - 500 bootstrap iterations ($B = 500$) with a fixed pseudo-random seed (`random_state=42`).
  - In each iteration, $K$ clusters are sampled with replacement, retaining all intra-cluster temporal observations.
  - 95% empirical percentile confidence intervals are constructed from the 2.5th and 97.5th percentiles of the bootstrap distribution.
- **Temporal Alignment:** The chronological train/validation/test ordering is strictly preserved; observations are never shuffled across temporal boundaries.

---

## 2. Empirical 95% Confidence Intervals

Summary generated across 500 cluster bootstrap iterations:

| Partition | Metric Description | Point Estimate | Bootstrap Mean | Bootstrap Std | 95% CI [Lower, Upper] |
|---|---|---|---|---|---|
| **Validation** | Macro F1 Score | 0.4957 | 0.4946 | 0.0120 | **[0.4710, 0.5193]** |
| | Balanced Accuracy | 49.48% | 49.40% | 1.12% | **[47.25%, 51.69%]** |
| | Model Policy Win Rate (Central) | 37.90% | 37.89% | 3.08% | **[32.48%, 44.43%]** |
| | Model Mean Incremental Return (Central, ₹/qtl) | +₹33.55 | +₹34.15 | ₹10.15 | **[+₹16.53, +₹54.97]** |
| | Model Mean Return (Conservative, ₹/qtl) | +₹25.26 | +₹25.80 | ₹9.71 | **[+₹9.36, +₹45.78]** |
| | Model Mean Return (Optimistic, ₹/qtl) | +₹36.82 | +₹37.44 | ₹10.26 | **[+₹19.65, +₹58.47]** |
| | Difference: Model vs Always Store (₹/qtl) | +₹63.87 | +₹64.13 | ₹20.43 | **[+₹25.55, +₹104.39]** |
| | Difference: Model vs Trend Policy (₹/qtl) | +₹101.57 | +₹103.43 | ₹23.46 | **[+₹65.79, +₹154.46]** |
| **Exploratory Test** | Macro F1 Score | 0.5041 | 0.5038 | 0.0106 | **[0.4822, 0.5242]** |
| | Balanced Accuracy | 49.59% | 49.61% | 1.02% | **[47.57%, 51.65%]** |
| | Model Policy Win Rate (Central) | 37.81% | 37.99% | 2.41% | **[32.88%, 42.48%]** |
| | Model Mean Incremental Return (Central, ₹/qtl) | +₹42.21 | +₹41.84 | ₹7.91 | **[+₹27.37, +₹57.21]** |
| | Model Mean Return (Conservative, ₹/qtl) | +₹31.98 | +₹31.56 | ₹7.51 | **[+₹17.84, +₹46.05]** |
| | Model Mean Return (Optimistic, ₹/qtl) | +₹46.12 | +₹45.76 | ₹8.03 | **[+₹30.92, +₹61.69]** |
| | Difference: Model vs Always Store (₹/qtl) | +₹70.50 | +₹71.02 | ₹22.20 | **[+₹29.65, +₹118.49]** |
| | Difference: Model vs Trend Policy (₹/qtl) | +₹122.93 | +₹123.34 | ₹22.16 | **[+₹86.17, +₹169.83]** |

---

## 3. Methodological Interpretations & Safeguards

### 3.1 The Win-Rate Ceiling Remains Firmly Below 50%
Across all 500 resamples:
- The **upper 97.5th percentile bound for the storage win rate is 44.43% on Validation and 42.48% on Exploratory Test**.
- Even under generous sampling draws across market series, the model-driven storage policy results in a net financial loss in the clear majority of stored decisions ($55.6\% - 67.5\%$).
- This confirms that positive mean returns are driven entirely by a minority of large upward price realizations rather than reliable weekly edge.

### 3.2 Predictive Metric Stability
- The Macro F1 score (95% CI: 0.471 to 0.524) and Balanced Accuracy (95% CI: 47.3% to 51.7%) confirm that the model's predictive skill across classes is modest but statistically differentiated from the naive 33.3% random or majority guessing baseline.

### 3.3 Strict Governance Caveat on Confidence Intervals
> **CRITICAL METHODOLOGICAL WARNING:**
> An empirical confidence interval for incremental return that excludes zero ($[+₹16.53, +₹54.97]$) **DOES NOT constitute proof of real-world economic profitability or operational viability**.
> The interval only quantifies sampling variability under the stylized assumptions of the mathematical simulation (fixed ₹20/qtl warehouse fee, frictionless access, modal price executability, zero localized shrinkage spikes). It does not incorporate unmodeled friction, distress selling liquidity needs, physical transit, or localized batch rejections.
