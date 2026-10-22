# Decisions Pending Approval: Phase 03 Classification Protocol

**Investigator:** Suryansh  
**Target:** User Approval Checkpoint  
**Date:** October 23, 2026  

---

## 1. Decision on Primary Performance Metric Suite

- **Proposed Recommendation:**
  1. **Primary Summary Metric:** **Macro F1-Score** (Arithmetic mean of class F1-scores; forces models to learn minority breakout classes equally).
  2. **Primary Diagnostic Metric:** **Balanced Accuracy** (Macro-average of class recalls; immediately exposes majority-class collapse).
  3. **Mandatory Diagnostic Artifact:** **3x3 Confusion Matrix** (Audits exact breakout predictions and directional reversal errors).
  4. **Per-Class Metrics:** **Precision, Recall, and F1-Score** for each class (`Unfavorable`, `Normal`, `Favorable`).
  5. **Supporting Metric Only:** **Overall Accuracy** and **Weighted F1-Score**, strictly accompanied by **Lift over Naive Majority-Class Baseline**.
- **User Decision Required:**  
  *Do you approve this metric suite as the mandatory standard for all subsequent feature experiments?*

---

## 2. Decision on Wheat Evaluation Protocol

- **Context:** Due to government MSP and market quote stickiness, 87.13% of Wheat observations fall into the `Normal` class. The baseline model achieves 85.93% accuracy but fails completely on minority breakouts (Recall is 1.1% on Favorable and 3.1% on Unfavorable; Balanced Accuracy is 34.13%).
- **Proposed Protocol Options:**
  - **Option A (Recommended):** Retain Wheat in the main study, but evaluate it strictly using **Balanced Accuracy, Macro F1, and minority-class recall**, forbidding Overall Accuracy as a success criterion.
  - **Option B (Exploratory Threshold Test):** In Stage 4, test commodity-specific volatility quantile thresholds (e.g., 20th and 80th percentiles of Wheat returns) alongside the static $\pm 2.5\%$ band to determine whether meaningful directional signals can be resolved.
- **User Decision Required:**  
  *Which Wheat evaluation protocol do you approve?*

---

## 3. Decision on Baseline Execution Gate

- **Context:** We have audited and extracted exact baseline metrics across all four approved crops from the verified Phase 5 prediction outputs (`test_predictions.csv.gz` and `val_predictions.csv.gz`).
- **Options:**
  - **Option 1 (Recommended):** Approve the documented Phase 5 baseline metrics as our frozen baseline, avoiding redundant CPU re-training.
  - **Option 2:** Authorize a fresh local re-execution of `run_pipeline.py` inside the workspace to re-generate raw prediction artifacts from scratch.
- **User Decision Required:**  
  *Do you approve freezing the verified Phase 5 baseline metrics, or do you request a fresh re-training run?*

---

## 4. Authorization to Proceed to Prompt 4

- **Next Step:** Prompt 4 — Feature Discovery, Arrival Volume Ingestion (via CEDA), and Agroclimatological Signal Research (via NASA POWER).
- **User Decision Required:**  
  *May I proceed to the feature discovery and validation phase once these protocol decisions are confirmed?*
