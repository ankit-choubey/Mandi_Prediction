# Controlled Feature Ablation & Wheat Imbalance Experiment Plan

**Project:** Mandi Prediction — APMC Market Intelligence System  
**Investigator:** Suryansh  
**Workspace:** [`/Users/kumarsuryansh/Desktop/Temporary/suryansh - work`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work)  
**Deliverable:** `experiments/feature_ablation/experiment_plan.md`  
**Status:** **AWAITING USER EXPLICIT APPROVAL (DO NOT EXECUTE UNTIL SIGNED OFF)**  
**Date:** October 23, 2026  

---

## 1. Experimental Objectives & Research Questions

The objective of this controlled experiment suite is to isolate the true marginal contribution of each feature family to 3-state market condition classification ($T+7$), and to systematically remediate the majority-class collapse on **Wheat**.

### Core Research Questions:
1. **RQ-1 (Price Lags & Momentum):** Do exact calendar lags ($T-1, T-3, T-7$) provide reliable directional lift over simple spot quote benchmarks?
2. **RQ-2 (Causal Rolling Volatility):** Does `Roll_Std_Price_7` (ranked #1 in feature importance) genuinely improve minority-class capture or simply reflect quote frequency?
3. **RQ-3 (Spatial Arbitrage):** Does inter-district price transmission (Kanpur $\leftrightarrow$ Unnao $\leftrightarrow$ Lucknow) add orthogonal predictive information beyond local historical lags?
4. **RQ-4 (External Signals - Conditional on Acquisition):** Do arrival volumes (CEDA) and rainfall/temperature shocks (NASA POWER) improve classification lift or add noise?
5. **RQ-5 (Wheat Imbalance Remediation):** Can class-weighted loss functions (`class_weight='balanced'`), training-only resampling (SMOTE / Random Under-Sampling), or validation probability threshold tuning rescue Wheat Balanced Accuracy from its collapsed baseline (35.32%)?

---

## 2. Experimental Discipline & Leakage Controls

All experiments will strictly adhere to the audited validation protocol:
1. **Fixed Prediction Horizon & Target Definition:** Exactly $T+7$ calendar days. Class boundaries: Unfavorable ($R_7 < -2.5\%$), Normal ($-2.5\% \le R_7 \le +2.5\%$), Favorable ($R_7 > +2.5\%$).
2. **Chronological 3-Way Partitioning with Embargo:**
   - **Training Set (70%):** September 01, 2024 to January 17, 2026 ($N = 99,881$).
   - **Embargo Buffer 1:** 8 days purged ($T+7$ realization $\le \text{Train Cutoff} - 1$).
   - **Validation Set (15%):** January 25, 2026 to March 31, 2026 ($N = 5,671$).
   - **Embargo Buffer 2:** 8 days purged.
   - **Exploratory Test Set (15%):** April 08, 2026 to August 25, 2026 ($N = 9,551$).
3. **Preprocessing Encapsulation:** All scalers and `SimpleImputer(strategy='median')` encapsulated in Pipelines fitted strictly on `X_train`.
4. **Identical Test Evaluation Population:** All ablation variants evaluated on the identical $9,551$ test records, guaranteeing direct comparability.

---

## 3. Controlled Ablation Design: 6 Feature Configurations

```text
========================================================================================================================
EXP ID   CONFIGURATION NAME             FEATURE SUBSET INCLUDED                                  N FEATURES
========================================================================================================================
EXP-01   Baseline (Spot + Intraday)     Modal_Price, Min_Price, Max_Price, Spreads              5 features
EXP-02   + Historical Calendar Lags     EXP-01 + Lag_1, Lag_3, Lag_7, Return_1d, 3d, 7d        11 features
EXP-03   + Causal Rolling Volatility    EXP-02 + Roll_Mean_3, Roll_Mean_7, Roll_Std_7, Ratios   16 features
EXP-04   + Calendar & Seasonality       EXP-03 + Month, DayOfWeek, DayOfMonth, Quarter, Season   21 features
EXP-05   + Spatial Neighbor Arbitrage   EXP-04 + District & Neighbor Mean Prices, Spreads, Ratio 27 features (Current Baseline)
EXP-06   + External Signals (Targeted)  EXP-05 + CEDA Arrival Lag (T-1) + NASA Rainfall/Temp    31 features (Pending Acq)
========================================================================================================================
```

---

## 4. Priority Diagnostic: Wheat Class Imbalance Remediation Suite

To resolve the pathological Wheat collapse (87.25% Normal class concentration; Balanced Acc = 35.32%; Recall_Fav = 1.1%; Recall_Unfav = 6.9%), we propose three controlled interventions evaluated against the default model:

### Intervention W-1: Class-Weighted Loss Calibration
- Adjust loss penalization in Gradient Boosting / Random Forest to inversely scale with class frequencies:
  $$w_c = \frac{N}{3 \times N_c}$$
- For Wheat, $w_{\text{Normal}} \approx 0.38$, while $w_{\text{Unfav}} \approx 5.3$ and $w_{\text{Fav}} \approx 5.1$.
- Forces trees to split on minority price-breakout features rather than collapsing to the majority class.

### Intervention W-2: Training-Only Resampling (Balanced Pipeline)
- Apply Random Under-Sampling or SMOTE **exclusively inside the training Pipeline**:
  - Training partition ($N = 99,881$) is balanced.
  - Validation and Test partitions remain **100% untouched and pristine** (zero synthetic test samples).

### Intervention W-3: Post-Processing Decision Threshold Tuning
- In standard argmax classification, class prediction is:
  $$\hat{y} = \arg\max_{c \in \{0, 1, 2\}} P(y = c \mid x)$$
- Because $P(y = \text{Normal})$ dominates, the argmax rarely fires for minority classes.
- We tune decision thresholds $\theta_0, \theta_2$ on the **Validation Set** to maximize Validation Macro F1 and minority recall, then apply the fixed thresholds to the Test Set.

---

## 5. Required Metric Suite & Output Specifications

Every ablation variant will log the complete metric suite:
- **Primary Performance Standard:** Macro F1-Score and Balanced Accuracy.
- **Economic Sensitivity:** Per-class Precision, Recall, and F1 for Unfavorable (0), Normal (1), Favorable (2).
- **Benchmark Lift:** Overall Accuracy vs. Naive Majority Baseline ($\Delta \text{Acc}$).
- **Probabilistic Calibration:** Multi-Class Log Loss (cross-entropy on predicted probability vectors).
- **Full 3x3 Confusion Matrix:** Exported to `results/feature_ablation/confusion_matrices/`.

---

## 6. Execution Command & Resource Requirements

```bash
# Proposed execution command (Awaiting User Sign-off at Checkpoint 1):
python3 "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work/experiments/run_feature_ablation.py"
```
- **Estimated Runtime:** $\sim 6\text{ to } 8\text{ minutes}$ across all 6 ablation runs and 3 Wheat interventions on Apple Silicon CPU.
- **Hardware Resources:** Pure CPU multi-processing (`n_jobs=-1`); zero GPU requirements; $< 2\text{ GB}$ peak memory.
- **Safeguards:** Parent clone remains strictly untouched; outputs written to `results/feature_ablation/`.
