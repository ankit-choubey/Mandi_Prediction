# Model Robustness, Error Diagnostics, and Subgroup Stability Plan

**Project:** Mandi Prediction — APMC Market Intelligence System  
**Investigator:** Suryansh  
**Workspace:** [`/Users/kumarsuryansh/Desktop/Temporary/suryansh - work`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work)  
**Deliverable:** `reports/robustness/robustness_plan.md`  
**Status:** **AWAITING USER EXPLICIT APPROVAL (DO NOT EXECUTE UNTIL SIGNED OFF)**  
**Date:** October 23, 2026  

---

## 1. Objective & Motivation

Standard machine learning evaluation reports single aggregate test statistics (e.g. statewide accuracy or macro F1). In agricultural wholesale markets, however, models often fail heterogeneously across:
- **Seasonal Shifts:** High performance during summer vegetable shortages (Zaid/Kharif) masking collapse during winter post-harvest gluts (Rabi).
- **Geographic Fragmentation:** High accuracy in large urban terminal mandis (Lucknow, Kanpur) masking failure in peripheral rural yards (Purwa, Mauranipur).
- **Asymmetric Prediction Directionality:** False Favorable predictions (advising farmers to hold produce right before a market crash) incurring catastrophic financial losses, compared to benign false Normal predictions.

This plan details a structured suite of six robustness and error-diagnostic tests to be executed post-approval.

---

## 2. Robustness Testing Suite Specification

```text
========================================================================================================================
TEST ID  ROBUSTNESS DIMENSION           EVALUATION METHODOLOGY                                   SAMPLE CRITERIA
========================================================================================================================
ROB-01   Seasonal Out-of-Distribution   Compare Summer Zaid (May-Jun) vs Monsoon Kharif (Jul-Aug) All test records (N=9,551)
ROB-02   District-by-District Stability Sliced evaluation across Ghaziabad, Jhansi, Kanpur, etc. Subgroup N >= 300 obs
ROB-03   Quote Stickiness Stress Test   Stratify records by trailing price volatility (zero vs dynamic) Wheat & Potato slices
ROB-04   Missing Feature Sensitivity    Zero-imputation / median-imputation ablation on lags & rolls Test partition features
ROB-05   Severe Directional Reversals   Audit CM[0, 2] (True Unfav, Pred Fav) and CM[2, 0]      All crops & per-crop
ROB-06   Probability Calibration Audit  Brier Score, Expected Calibration Error (ECE), & curves  Predicted probability matrix
========================================================================================================================
```

---

## 3. In-Depth Test Methodologies

### ROB-01: Seasonal Regime Stability (Zaid vs. Kharif)
- **Rationale:** The historical test partition spans April 08 to August 25, 2026. This window naturally splits into two distinct agricultural micro-seasons:
  - **Zaid Dry Summer Season (April – June):** Characterized by high temperatures, supply tapering, and volatile vegetable prices.
  - **Kharif Monsoon Onset Season (July – August):** Characterized by heavy rainfall, transportation disruptions, and early monsoon crop arrivals.
- **Protocol:** Compute Macro F1, Balanced Accuracy, and Lift separately for both seasonal windows. A performance delta $|\Delta \text{Macro F1}| > 0.10$ flags seasonal instability.

### ROB-02: Spatial & District-Level Generalization
- **Rationale:** APMC mandis vary from state-level transit hubs (Kanpur Nagar) to Bundelkhand drylands (Jhansi).
- **Protocol:** Compute per-district confusion matrices and accuracy lifts. Mandis with $N < 100$ test observations will be flagged as statistically sparse and evaluated with bootstrap confidence intervals.

### ROB-03: Quote Stickiness Sensitivity (Wheat Diagnostic)
- **Rationale:** In Wheat, 29.80% of historical pairs exhibit exactly 0.00% return over 7 calendar days.
- **Protocol:** Segment the test set into two cohorts:
  - *Cohort A (Active Quote Changes):* $|\text{Return}_{7d}| > 0.0\%$.
  - *Cohort B (Completely Frozen Quotes):* $\text{Return}_{7d} = 0.0\%$.
- Evaluate whether the model's high accuracy on Wheat is merely an artifact of Cohort B or whether it retains any predictive skill on Cohort A.

### ROB-05: Asymmetric Error Cost & Directional Reversals
- **Rationale:** In agricultural decision support, errors have highly asymmetric real-world consequences:
  - **Type I Catastrophe (True Unfavorable, Predicted Favorable — $CM[0, 2]$):** The farmer is advised to pay storage fees, only to face a price collapse.
  - **Type II Opportunity Loss (True Favorable, Predicted Unfavorable — $CM[2, 0]$):** The farmer sells immediately and misses a market rally.
  - **Type III Inertia (True Extreme, Predicted Normal):** The farmer takes routine action.
- **Protocol:** Audit the exact frequencies of Type I, II, and III errors across Potato and Onion, calculating the total financial penalty per 100 quintals stored.

### ROB-06: Multi-Class Probability Calibration
- **Rationale:** When guiding farmer storage decisions, predicted probabilities $\hat{P}(y = c \mid x)$ must represent genuine empirical clearing frequencies.
- **Protocol:** Compute the Brier Multi-Class Score and Expected Calibration Error (ECE) with 10 reliability bins. Evaluate whether isotonic regression or Platt scaling on the validation partition improves probability reliability.

---

## 4. Execution Command & Output Deliverables

```bash
# Proposed execution script (Awaiting User Sign-off at Checkpoint 1):
python3 "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work/experiments/run_robustness_diagnostics.py"
```
- **Expected Outputs:**
  - `results/robustness/robustness_comparison.csv`
  - `results/robustness/error_analysis.md`
  - `results/robustness/calibration_curves.png`
  - `results/robustness/execution_log.md`
- **Runtime:** $< 60\text{ seconds}$ on CPU.
